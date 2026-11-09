from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.tools.misc import format_date, formatLang


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _mayan_credit_cutoff(self, company):
        # Use one business timezone for all terminals, including server-side checks.
        timezone = company.partner_id.tz or "America/Guatemala"
        today = fields.Date.context_today(self.with_context(tz=timezone))
        # On November 1, invoices strictly before October 1 block credit.
        return (today.replace(day=1) - timedelta(days=1)).replace(day=1)

    @api.model
    def _mayan_credit_warning(self, partner, company):
        if not partner:
            return False
        if company not in self.env.companies:
            raise AccessError(_("No tiene acceso a la compañía del punto de venta."))
        cutoff = self._mayan_credit_cutoff(company)
        # Cashiers need the credit result without general accounting read access.
        # sudo is restricted to this company and this commercial customer's invoices.
        invoices = self.sudo().search([
            ("company_id", "=", company.id),
            ("commercial_partner_id", "=", partner.commercial_partner_id.id),
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", "<", cutoff),
            ("amount_residual", ">", 0),
        ], order="invoice_date, id")
        details = []
        totals = {}
        for invoice in invoices:
            currency = invoice.currency_id
            if currency.is_zero(invoice.amount_residual):
                continue
            details.append(_(
                "- %(invoice)s | Fecha: %(date)s | Pendiente: %(amount)s",
                invoice=invoice.name,
                date=format_date(self.env, invoice.invoice_date),
                amount=formatLang(self.env, invoice.amount_residual, currency_obj=currency),
            ))
            totals[currency] = totals.get(currency, 0) + invoice.amount_residual
        if not details:
            return False
        total_text = "; ".join(
            formatLang(self.env, amount, currency_obj=currency)
            for currency, amount in totals.items()
        )
        return "\n".join([
            _("Crédito bloqueado: hay facturas cuyo mes de pago ya terminó."),
            _("Las facturas pueden pagarse hasta el último día del mes siguiente a su emisión."),
            *details,
            _("Total pendiente que bloquea el crédito: %s", total_text),
        ])

    @api.model
    def get_last_invoice(self, partner_id, config_id):
        """Live POS check; the terminal cannot supply a cutoff date or company."""
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(_("Esta consulta requiere acceso al punto de venta."))
        config = self.env["pos.config"].browse(config_id).exists()
        config.ensure_one()
        config.check_access("read")
        partner = self.env["res.partner"].browse(partner_id).exists()
        partner.ensure_one()
        partner.check_access("read")
        return self._mayan_credit_warning(partner, config.company_id)
