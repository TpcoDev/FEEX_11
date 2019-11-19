# -*- coding: utf-8 -*-
{
    'author': "Blanco Martin & Asociados",
    'category': 'Localization/Chile',
    'depends': [
        'partner_identification',
        'l10n_cl_counties',
    ],
    'installable': True,
    'license': 'AGPL-3',
    'name': 'Títulos de Personería y Tipos de documentos Chilenos relacionado con partners',
    'data': [
        'data/res_partner_title_data.xml',
        'data/res_partner_id_category_data.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/res_partner_id_category_view.xml',
        'views/res_partner_id_number_view.xml',
        'security/security.xml',
    ],
    'demo': [
        # 'demo/partner_demo.xml',
    ],
    'version': '11.0.1.2.0',
}
