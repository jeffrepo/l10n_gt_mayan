# -*- coding: utf-8 -*-
{
    'name': "l10n_gt_mayan",

    'summary': "Control de permisos y personalización del Punto de Venta para empleados",

    'description': """
Este módulo extiende el Punto de Venta de Odoo para agregar controles específicos por empleado,
permitiendo definir qué usuarios pueden realizar determinadas acciones dentro del POS, como eliminar
líneas de pedido. 

Características principales:
- Campo adicional en empleados (`allow_delete_line`) para definir permisos.
- Sincronización automática del campo al frontend del POS.
- Integración transparente con el módulo `pos_hr`.
    """,

    'author': "SISPAV",
    'website': "https://www.sispav.com",  # o el sitio real de tu empresa si querés dejarlo

    'category': 'Sales/Point Of Sale',
    'version': '0.1',
    'license': 'LGPL-3',

    'depends': ['base', 'point_of_sale', 'pos_hr'],

    'data': [
        'views/hr_employee_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'l10n_gt_mayan/static/src/js/ProductScreen.js',
        ],
    },
}


