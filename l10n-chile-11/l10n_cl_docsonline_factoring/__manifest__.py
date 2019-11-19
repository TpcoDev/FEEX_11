# -*- coding: utf-8 -*-
{
    "name": """Chile receive offers for factoring from www.documentosonline.cl""",
    'version': '11.0.1.0.0',
    'category': 'Localization/Chile',
    'sequence': 12,
    'author':  'Blanco Martín & Asociados',
    'website': 'http://blancomartin.cl',
    'license': 'AGPL-3',
    'summary': '',
    'depends': [
        'account',
        'l10n_cl_docsonline_print',
    ],
    'data': [
        'views/invoice_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
