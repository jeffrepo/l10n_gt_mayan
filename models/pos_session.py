# -*- coding: utf-8 -*-
from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_hr_employee(self):
        print("Cargando campos")
        result = super()._loader_params_hr_employee()
        result['search_params']['fields'].append('allow_delete_line')
        return result
