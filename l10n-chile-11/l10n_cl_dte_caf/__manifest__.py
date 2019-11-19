# -*- coding: utf-8 -*-
{
    'author': u'Blanco Martín & Asociados',
    'category': 'Localization/Chile',
    'depends': ['l10n_cl_account'],
    "external_dependencies": {
        'python': [
            'xmltodict',
            'base64'
        ]
    },
    'license': 'AGPL-3',
    'name': 'CAF Container for DTE Compliance',
    'test': [],
    'data': [
        'views/dte_caf.xml',
        'security/ir.model.access.csv',
    ],
    'update_xml': [],
    'version': '11.0.1.0.0',
    'website': 'http://blancomartin.cl',
    'installable': True,
    'auto-install': False,
    'active': False
}
