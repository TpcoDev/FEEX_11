# -*- coding: utf-8 -*-
{
    'active': True,
    'author': u'Odoocoop.  Modificaciones para compatibilizar con nueva localización v11.0: por Blanco Martin & Asociados',
    'website': 'http://bmya.cl',
    'category': 'Stock/picking',
    'external_dependencies': {
        'python': [
            'io',
            'zeep',
            'urllib3',
            'xmltodict',
            'dicttoxml',
            'pdf417gen',
            'base64'
        ],
    },
    'depends': [
        'stock',
        'fleet',
        'delivery',
        'sale_stock',
        'l10n_cl_dte',
        'l10n_cl_localization_filter',
    ],
    'license': 'AGPL-3',
    'name': u'Guías de Despacho Electrónica para Chile',
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking.xml',
        'views/layout.xml',
        'views/libro_guias.xml',
        "views/account_invoice.xml",
        "views/stock_picking.xml",
        "views/sii_send_queue_view.xml",
        'wizard/masive_send_dte.xml',
    ],
    'version': '11.0.1.0.0',
    'application': False,
    'installable': True,
}
