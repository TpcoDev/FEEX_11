# -*- coding: utf-8 -*-
{
    "name": """Chile print dte from www.documentosonline.cl""",
    'version': '11.0.1.0.0',
    'category': 'Localization/Chile',
    'sequence': 12,
    'author':  'Blanco Martín & Asociados',
    'website': 'http://blancomartin.cl',
    'license': 'AGPL-3',
    'summary': '',
    'depends': [
        'account',
        'l10n_cl_dte',
        'l10n_cl_stock_delivery_guide',
    ],
    'data': [
        'views/stock_picking_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
