"""Exercise the production Python methods without an Odoo database.

The small ORM adapter evaluates the actual search domain against invoice fixtures;
Odoo access rules and transactions still require the installation test in README.
"""
import importlib.util
import sys
import unittest
from copy import copy
from datetime import date
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class AccessError(Exception):
    pass


class UserError(Exception):
    pass


class BaseModel:
    def with_context(self, **context):
        result = copy(self)
        result.context = {**getattr(self, 'context', {}), **context}
        return result

    def sudo(self):
        self.sudo_used = True
        return self

    def _process_saved_order(self, draft):
        self.processed = True
        return 99

    def action_pos_order_paid(self):
        self.paid = True
        return True

    def _load_pos_data_fields(self, config_id):
        return ['name', 'user_id']


class DateField:
    today = date(2026, 11, 1)
    last_timezone = None

    @classmethod
    def context_today(cls, record):
        cls.last_timezone = record.context['tz']
        return cls.today


def translate(text, *args, **kwargs):
    return text % (kwargs or args) if args or kwargs else text


def load_models():
    odoo = ModuleType('odoo')
    odoo.models = SimpleNamespace(Model=BaseModel)
    odoo.api = SimpleNamespace(model=lambda method: method)
    odoo.fields = SimpleNamespace(Date=DateField, Boolean=lambda **kwargs: None)
    odoo._ = translate
    exceptions = ModuleType('odoo.exceptions')
    exceptions.AccessError = AccessError
    exceptions.UserError = UserError
    misc = ModuleType('odoo.tools.misc')
    misc.format_date = lambda env, value: value.isoformat()
    misc.formatLang = lambda env, value, currency_obj: f'{currency_obj.name} {value:.2f}'
    result = []
    with patch.dict(sys.modules, {'odoo': odoo, 'odoo.exceptions': exceptions,
                                 'odoo.tools.misc': misc}):
        for filename in ['account_move', 'pos_order', 'hr_employee']:
            spec = importlib.util.spec_from_file_location(filename, ROOT / 'models' / f'{filename}.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            result.append(module)
    return result


account_module, order_module, employee_module = load_models()


class Currency:
    def __init__(self, name):
        self.name = name

    def is_zero(self, value):
        return round(value, 2) == 0


class Record(SimpleNamespace):
    def exists(self):
        return self

    def ensure_one(self):
        return self

    def check_access(self, operation):
        if getattr(self, 'denied', False):
            raise AccessError('record access denied')


class Invoices(account_module.AccountMove):
    def search(self, domain, order):
        self.last_domain = domain
        operators = {'=': lambda a, b: a == b, '<': lambda a, b: bool(a) and a < b,
                     '>': lambda a, b: a > b}
        return sorted(
            (invoice for invoice in self.records if all(
                operators[op](getattr(invoice, field), value) for field, op, value in domain
            )), key=lambda invoice: invoice.invoice_date,
        )


class Orders(order_module.PosOrder):
    def __iter__(self):
        yield self


class CreditTests(unittest.TestCase):
    def setUp(self):
        DateField.today = date(2026, 11, 1)
        self.currency = Currency('GTQ')
        self.company = Record(id=2, partner_id=Record(tz=False))
        self.customer = Record(id=7)
        self.customer.commercial_partner_id = self.customer
        self.config = Record(id=3, company_id=self.company)
        self.is_cashier = True
        self.moves = Invoices()
        self.moves.records = []
        self.moves.env = SimpleNamespace(companies=[self.company])

    def invoice(self, day, **kwargs):
        values = dict(name=f'INV/{len(self.moves.records) + 1}', invoice_date=day,
                      company_id=2, commercial_partner_id=7, move_type='out_invoice',
                      state='posted', amount_residual=100, currency_id=self.currency)
        values.update(kwargs)
        result = Record(**values)
        self.moves.records.append(result)
        return result

    def warning(self):
        return self.moves._mayan_credit_warning(self.customer, self.company)

    def test_september_invoices_allowed_through_october_31(self):
        for day in [1, 5, 10, 30]:
            self.invoice(date(2026, 9, day))
        for today in [date(2026, 9, 30), date(2026, 10, 1), date(2026, 10, 31)]:
            DateField.today = today
            self.assertFalse(self.warning(), today)

    def test_all_september_invoices_block_on_november_1(self):
        for day in [1, 5, 10, 30]:
            invoice = self.invoice(date(2026, 9, day))
        message = self.warning()
        self.assertEqual(message.count('| Fecha:'), 4)
        self.assertIn('GTQ 400.00', message)
        self.assertIn(invoice.name, message)

    def test_october_allowed_until_november_30_then_blocks(self):
        self.invoice(date(2026, 10, 1))
        for today in [date(2026, 11, 1), date(2026, 11, 30)]:
            DateField.today = today
            self.assertFalse(self.warning())
        DateField.today = date(2026, 12, 1)
        self.assertTrue(self.warning())

    def test_year_transition(self):
        self.invoice(date(2026, 12, 31))
        DateField.today = date(2027, 1, 31)
        self.assertFalse(self.warning())
        DateField.today = date(2027, 2, 1)
        self.assertTrue(self.warning())

    def test_february_and_leap_year(self):
        for year, last_day in [(2026, 28), (2028, 29)]:
            self.moves.records = []
            self.invoice(date(year, 1, 31))
            DateField.today = date(year, 2, last_day)
            self.assertFalse(self.warning())
            DateField.today = date(year, 3, 1)
            self.assertTrue(self.warning())

    def test_partial_payment_blocks_then_payment_unblocks(self):
        invoice = self.invoice(date(2026, 9, 10), amount_residual=0.01)
        self.assertTrue(self.warning())
        invoice.amount_residual = 0
        self.assertFalse(self.warning())

    def test_old_debt_keeps_blocking(self):
        self.invoice(date(2025, 1, 1))
        self.assertTrue(self.warning())

    def test_ignore_draft_cancel_refund_other_company_and_other_customer(self):
        for changes in [dict(state='draft'), dict(state='cancel'), dict(move_type='out_refund'),
                        dict(move_type='in_invoice'), dict(company_id=8),
                        dict(commercial_partner_id=10), dict(amount_residual=0),
                        dict(amount_residual=0.001), dict(invoice_date=False)]:
            self.invoice(date(2026, 9, 1), **changes) if 'invoice_date' not in changes else self.invoice(False)
        self.assertFalse(self.warning())

    def test_contact_uses_commercial_customer(self):
        self.invoice(date(2026, 9, 1))
        child = Record(id=15, commercial_partner_id=self.customer)
        self.assertTrue(self.moves._mayan_credit_warning(child, self.company))

    def test_company_timezone_is_consistent(self):
        self.warning()
        self.assertEqual(DateField.last_timezone, 'America/Guatemala')
        self.company.partner_id.tz = 'America/Mexico_City'
        self.warning()
        self.assertEqual(DateField.last_timezone, 'America/Mexico_City')

    def test_totals_are_separate_by_currency(self):
        self.invoice(date(2026, 9, 1), amount_residual=75)
        self.invoice(date(2026, 9, 1), amount_residual=10, currency_id=Currency('USD'))
        self.assertIn('GTQ 75.00; USD 10.00', self.warning())

    def test_disallowed_company_rejected_before_sudo(self):
        self.moves.env.companies = []
        with self.assertRaises(AccessError):
            self.warning()
        self.assertFalse(getattr(self.moves, 'sudo_used', False))

    def rpc_env(self):
        test = self
        class Env:
            companies = [test.company]
            user = SimpleNamespace(has_group=lambda name: test.is_cashier)
            def __getitem__(self, name):
                return SimpleNamespace(browse=lambda value: test.config if name == 'pos.config' else test.customer)
        self.moves.env = Env()

    def test_cashier_can_check_without_accounting_acl(self):
        self.rpc_env()
        self.invoice(date(2026, 9, 1))
        self.assertTrue(self.moves.get_last_invoice(7, 3))

    def test_non_pos_user_and_inaccessible_records_rejected(self):
        self.rpc_env()
        self.is_cashier = False
        with self.assertRaises(AccessError):
            self.moves.get_last_invoice(7, 3)
        self.is_cashier = True
        for record in [self.config, self.customer]:
            record.denied = True
            with self.assertRaises(AccessError):
                self.moves.get_last_invoice(7, 3)
            record.denied = False

    def make_order(self, quantities=(1,), state='draft'):
        order = Orders()
        order.env = {'account.move': self.moves}
        order.lines = [Record(qty=q) for q in quantities]
        order.partner_id = self.customer
        order.company_id = self.company
        order.state = state
        return order

    def test_server_rejects_sale_before_native_processing(self):
        self.invoice(date(2026, 9, 1))
        order = self.make_order()
        with self.assertRaises(UserError):
            order._process_saved_order(False)
        self.assertFalse(getattr(order, 'processed', False))
        with self.assertRaises(UserError):
            order.action_pos_order_paid()
        self.assertFalse(getattr(order, 'paid', False))

    def test_server_allows_draft_refund_cancel_and_previously_paid_order(self):
        self.invoice(date(2026, 9, 1))
        self.assertEqual(self.make_order()._process_saved_order(True), 99)
        for order in [self.make_order((-1,)), self.make_order((), 'draft'),
                      self.make_order(state='cancel'), self.make_order(state='paid')]:
            self.assertEqual(order._process_saved_order(False), 99)

    def test_mixed_order_with_new_consumption_blocks_even_if_net_refund(self):
        self.invoice(date(2026, 9, 1))
        with self.assertRaises(UserError):
            self.make_order((-10, 1))._process_saved_order(False)

    def test_server_allows_sale_after_payment(self):
        invoice = self.invoice(date(2026, 9, 1))
        invoice.amount_residual = 0
        self.assertEqual(self.make_order()._process_saved_order(False), 99)

    def test_employee_permission_is_loaded_using_odoo18_hook(self):
        self.assertEqual(employee_module.HrEmployee()._load_pos_data_fields(3),
                         ['name', 'user_id', 'allow_delete_line'])


if __name__ == '__main__':
    unittest.main()
