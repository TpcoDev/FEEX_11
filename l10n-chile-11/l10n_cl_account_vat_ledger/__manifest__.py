# -*- coding: utf-8 -*-
{
    'version': '11.0.3.1.0',
    'active': False,
    'author': u'Blanco Martín & Asociados',
    'website': 'http://blancomartin.cl',
    'category': 'Localization/Chile',
    'demo_xml': [],
    'depends': [
        'account',
        'l10n_cl_account',
        'l10n_cl_dte',
        'l10n_cl_partner_activities',
        'report_xlsx'
        ],
    'installable': False,
    'license': 'AGPL-3',
    'name': u'Chile - Libros mensuales de Compra y Venta',
    'test': [],
    'data': [
        'views/sale_purchase_book.xml',
        'views/export.xml',
        # 'views/libro_honorarios.xml',
        # 'wizard/build_and_send_moves.xml',
        'security/ir.model.access.csv',
        ],

}
