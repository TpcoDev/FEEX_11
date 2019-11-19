# -*- coding: utf-8 -*-
{
    'author': u'Blanco Martín & Asociados',
    'category': 'Localization/Chile',
    'depends': ['account_asset', 'l10n_cl_account'],
    'license': 'AGPL-3',
    'name': 'Monetary Correction',
    'test': [],
    'data': [
        'views/account_ipc_view.xml',
        'views/account_asset_category_view.xml',
        'views/account_asset_view.xml',
        'views/account_view.xml',
        'views/account_journal_view.xml',
        'views/product_template_view.xml',
        'security/ir.model.access.csv',
        'data/account.ipc.csv',
    ],
    'version': '11.0.1.0.0',
    'website': 'http://blancomartin.cl',
    'installable': True,
    'auto-install': True,
    'active': False
}
