# -*- coding: utf-8 -*-
{
    "name": """Chile - Hide product pack components on invoices and delivery guides""",
    'version': '11.0.1.0.0',
    'category': 'Localization/Chile',
    'sequence': 12,
    'author':  'Blanco Martín & Asociados',
    'website': 'http://blancomartin.cl',
    'license': 'AGPL-3',
    'depends': [
        'l10n_cl_dte',
        'l10n_cl_stock_delivery_guide',
        'product_pack',
    ],
    'data': [
        'views/invoice_view.xml',
        'views/picking_view.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
