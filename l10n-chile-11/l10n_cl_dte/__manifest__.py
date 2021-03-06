# -*- coding: utf-8 -*-
{
    "name": """Chile - Web Services de Documentos Tributarios Electrónicos""",
    'version': '11.0.5.0.0',
    'category': 'Localization/Chile',
    'sequence': 12,
    'author':  'Blanco Martín & Asociados, OdooCoop',
    'website': 'http://blancomartin.cl',
    'license': 'AGPL-3',
    'depends': [
        'mail',
        'l10n_cl_counties',
        'l10n_cl_account',
        'l10n_cl_partner_activities',
        'l10n_cl_dte_caf',
        'account',
        'purchase',
        'user_signature_key',
        'l10n_cl_localization_filter',
        ],
    'external_dependencies': {
        'python': [
            'cchardet',
            'dicttoxml',
            'M2Crypto',
            'OpenSSL',
            'pysiidte',
            'cryptography',
            'lxml',
            'OpenSSL',
            'six',
            'urllib3',
            'zeep',
            'pdf417gen',
            'xmltodict',
            'hashlib',
            'signxml',
            'ast'
        ],
    },
    'data': [
        'views/invoice_view.xml',
        'views/partner_view.xml',
        'views/company_view.xml',
        'views/payment_t_view.xml',
        'views/layout.xml',
        'views/currency_view.xml',
        'wizard/masive_send_dte.xml',
        'views/email_templates.xml',
        'views/sii_send_queue.xml',
        'views/sii_regional_offices_view.xml',
        'views/global_descuento_recargo.xml',
        # 'views/sii_xml_envio.xml',
        # 'views/mail_dte.xml',
        'data/sii.regional.offices.csv',
        'data/sequence.xml',
        'data/cron.xml',
        'data/product.xml',
        'data/res.currency.csv',
        'security/ir.model.access.csv',
        # 'views/automated_action_ensure_send.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
