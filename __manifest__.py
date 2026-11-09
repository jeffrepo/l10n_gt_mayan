# -*- coding: utf-8 -*-
{
    "name": "Mayan - Control de crédito y permisos del POS",
    "summary": "Bloqueo de ventas por facturas pendientes al cierre del mes de pago",
    "version": "18.0.1.0.0",
    "author": "SISPAV",
    "website": "https://www.sispav.com",
    "category": "Sales/Point Of Sale",
    "license": "LGPL-3",
    "depends": ["point_of_sale", "pos_hr"],
    "data": ["views/hr_employee_views.xml"],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_gt_mayan/static/src/overrides/pos_store.js",
            "l10n_gt_mayan/static/src/overrides/payment_screen.js",
            "l10n_gt_mayan/static/src/overrides/order_summary.js",
        ],
    },
    "installable": True,
}
