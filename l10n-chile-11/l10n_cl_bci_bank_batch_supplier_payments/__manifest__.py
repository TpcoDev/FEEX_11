# -*- coding: utf-8 -*-
{
    "name" : "Batch Supplier Payment XLS for Chilean Bank BCI",
    "summary": "XLS Generator for Chilean bank",
    "version": "11.0.1.0.0",
    'author': 'Blanco Martin & Asociados',
    'website': 'http://blancomartin.cl',
    "category": "Tools",
    "depends": [
        "l10n_cl_account",
        "batch_supplier_payments",
        "l10n_cl_banks_sbif",
    ],
    "data": [
        # 'views/res_partner_view.xml',
        'report/report_xls.xml',
    ],
    "installable": True,
}