from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    allow_delete_line = fields.Boolean(
        string="Permitir eliminar línea",
        help="Este empleado tendrá permiso para eliminar líneas en el punto de venta.",
        default=False,
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        return [*super()._load_pos_data_fields(config_id), "allow_delete_line"]
