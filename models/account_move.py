from odoo import models, api, fields
from datetime import timedelta

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def get_last_invoice(self, partner_id):
        print("Vamos a buscar todas las facturas pendientes con más de 60 días desde la fecha de factura")
        partner = self.env['res.partner'].browse(partner_id)
        print(f"partner ID {partner.id} --> {partner.name}")
        
        # Calculamos la fecha límite (hoy - 60 días)
        today = fields.Date.today()
        date_limit = today - timedelta(days=60)
        
        # Buscamos TODAS las facturas no pagadas con más de 60 días desde invoice_date
        invoices = self.search([
            ('partner_id', '=', partner.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),  # Solo facturas validadas
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date', '<=', date_limit),  # Facturas con 60+ días desde su fecha
        ], order='invoice_date asc')  # Ordenamos por la más antigua primero
        
        print(f"Se encontraron {len(invoices)} facturas pendientes con más de 60 días")
        print(f"Fecha límite para búsqueda: {date_limit} (facturas hasta esta fecha)")
        
        # Agregamos debug para ver qué facturas encontró
        for inv in invoices:
            days_old = (today - inv.invoice_date).days
            print(f"id {inv.id} - Factura: {inv.name} - Fecha factura: {inv.invoice_date} - Días: {days_old} - Estado pago: {inv.payment_state} - Monto residual: {inv.amount_residual}")

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
            
            days_old = (today - invoice.invoice_date).days
            amount_due = invoice.amount_residual
            
            # Solo agregamos si tiene saldo pendiente
            if amount_due > 0:
                total_due += amount_due
                messages.append(
                    f"- {invoice.name} ({days_old} días de antigüedad): {amount_due:,.2f}"
                )
        
        # Construimos el mensaje final
        if messages:
            header = f"⚠️ CLIENTE CON FACTURAS PENDIENTES (+60 DÍAS):\n"
            details = "\n".join(messages)
            footer = f"\n💵 TOTAL PENDIENTE: {total_due:,.2f}"
            return header + details + footer
        
        return False