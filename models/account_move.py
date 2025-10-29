from odoo import models, api, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def get_last_invoice(self, partner_id):
        print("Vamos a buscar todas las facturas vencidas del cliente")
        partner = self.env['res.partner'].browse(partner_id)
        print(f"partner ID {partner.id} --> {partner.name}")
        
        # Buscamos TODAS las facturas no pagadas que estén vencidas
        today = fields.Date.today()
        invoices = self.search([
            ('partner_id', '=', partner.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),  # Solo facturas validadas
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', today),  # Solo facturas vencidas
        ], order='invoice_date_due asc')  # Ordenamos por la más antigua primero
        
        print(f"Se encontraron {len(invoices)} facturas vencidas")
        
        # Agregamos debug para ver qué facturas encontró
        for inv in invoices:
            print(f"id {inv.id} - Factura: {inv.name} - Fecha vencimiento: {inv.invoice_date_due} - Estado pago: {inv.payment_state} - Monto residual: {inv.amount_residual}")

        if not invoices:
            return False

        # Usamos un set para evitar duplicados
        seen_invoices = set()
        messages = []
        total_due = 0
        
        for invoice in invoices:
            # Evitamos duplicados por ID de factura
            if invoice.id in seen_invoices:
                continue
            seen_invoices.add(invoice.id)
            
            days_due = (today - invoice.invoice_date_due).days
            amount_due = invoice.amount_residual
            
            # Solo agregamos si tiene saldo pendiente
            if amount_due > 0:
                total_due += amount_due
                messages.append(
                    f"- {invoice.name} (Vencida hace {days_due} días): {amount_due:,.2f}"
                )
        
        # Construimos el mensaje final
        if messages:
            header = f"⚠️ CLIENTE CON FACTURAS VENCIDAS:\n"
            details = "\n".join(messages)
            footer = f"\n💵 TOTAL PENDIENTE: {total_due:,.2f}"
            return header + details + footer
        
        return False