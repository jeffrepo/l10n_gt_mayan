from odoo import models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _check_mayan_credit(self):
        for order in self:
            # Keep cancellations and pure refunds available. Mixed orders containing
            # new consumption still require credit clearance, even with a net refund.
            if order.state != "draft" or not any(line.qty > 0 for line in order.lines):
                continue
            message = self.env["account.move"]._mayan_credit_warning(
                order.partner_id, order.company_id
            )
            if message:
                raise UserError(message)

    def _process_saved_order(self, draft):
        # Core catches errors from action_pos_order_paid and continues processing.
        # Check BEFORE that catch so sync_from_ui rolls the entire sale back.
        if not draft:
            self._check_mayan_credit()
        return super()._process_saved_order(draft)

    def action_pos_order_paid(self):
        self._check_mayan_credit()
        return super().action_pos_order_paid()
