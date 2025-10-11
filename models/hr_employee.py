# -*- coding: utf-8 -*-

from odoo import models, fields

class HREmployee(models.Model):
    _inherit = 'hr.employee'

    allow_delete_line = fields.Boolean(
        string="Permitir eliminar línea",
        help="Este empleado tendrá permiso para eliminar líneas en el punto de venta.",
        default=False
    )