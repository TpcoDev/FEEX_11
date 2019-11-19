# -*- coding: utf-8 -*-
{
    "name": """Chile - Referenciar Cotización en la factura""",
    'version': '11.0.1.0.0',
    'category': 'Localization/Chile',
    'sequence': 12,
    'author':  'Blanco Martín & Asociados',
    'website': 'http://blancomartin.cl',
    'license': 'AGPL-3',
    'depends': [
        'sale',
        'l10n_cl_account',
        'l10n_cl_dte',
    ],
    'data': [
        'wizard/sale_adv_payment_inv.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
