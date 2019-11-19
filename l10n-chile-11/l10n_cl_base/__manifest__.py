# -*- coding: utf-8 -*-
{
    'name': 'Chile - Localization Installation Wizard',
    'version': '11.0.1.0.1',
    'category': 'Chilean Localization',
    'license': 'AGPL-3',
    'sequence': 14,
    'summary': 'Localization, Chile, Configuration',
    'author': u'Blanco Martín & Asociados',
    'website': 'http://blancomartin.cl',
    'depends': [
        'base',
        'web',
        'account_invoicing',
    ],
    'data': [
        'views/template.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'application': True,
}
