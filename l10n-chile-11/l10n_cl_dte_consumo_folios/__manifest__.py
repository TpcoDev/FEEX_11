# -*- coding: utf-8 -*-
{
    "name": """Chile - Envío de consumo de folios al SII""",
    'version': '11.0.1.0.0',
    'category': 'Localization/Chile',
    'sequence': 12,
    'author':  'Blanco Martín & Asociados, OdooCoop',
    'website': 'http://blancomartin.cl',
    'license': 'AGPL-3',
    'depends': [
        'l10n_cl_dte',
        ],
    'external_dependencies': {
        'python': ['zeep'],
    },
    'data': [
        'data/cron.xml',
        'security/ir.model.access.csv',
        'views/consumo_folios.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
