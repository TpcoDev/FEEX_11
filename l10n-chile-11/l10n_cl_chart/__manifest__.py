# -*- coding: utf-8 -*-
# Copyright (c) 2016 Blanco Martin y Asociados - Nelson Ramírez Sánchez http://www.bmya.cl

{
    'name': 'Chile Localization Chart Account BMyA',
    'version': '11.0.1.0.0',
    'license': 'AGPL-3',
    'author': u'Blanco Martin & Asociados',
    'website': 'http://blancomartin.cl',
    'category': 'Localization/Chile',
    'depends': [
        'l10n_cl', 'l10n_cl_localization_filter',
    ],
    'data': [
        'account_noupdate.sql',
        'data/account_chart_template_data.xml',
        'data/account_tags_data.xml',
        'data/account_tax_group_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_fiscal_position_template_data.xml',
    ],
    #'application': False,
    #'auto-install': False,
    #'active': False,
    #'installable': True
}
