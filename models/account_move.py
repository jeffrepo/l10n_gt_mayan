from odoo import models, api, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def get_last_invoice(self, partner_id):
        print("Vamos a buscar la ultima factura del cliente")
        partner = self.env['res.partner'].browse(partner_id)
        print(f"partner ID {partner.id} --> {partner.name}")
        # Buscamos la factura más reciente no pagada
        invoice = self.search([
            ('partner_id', '=', partner.id),
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ['not_paid']),
        ], order='invoice_date desc', limit=1)
        print("invoice ", invoice)
        if not invoice:
            return False

        # Calculamos días de vencimiento
        days_due = (fields.Date.today() - invoice.invoice_date).days
        if days_due >= 32:
            return f"El cliente tiene una factura vencida ({invoice.name}) de hace {days_due} días."
        return False
