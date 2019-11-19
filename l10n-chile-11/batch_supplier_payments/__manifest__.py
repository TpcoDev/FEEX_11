# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Batch Supplier Payment',
    'summary': '''This module allows you to Pay several invoices under a workflow
     and Export a XLS file for the Bank''',
    'version': '11.0.1.0.0',
    'category': 'Payments',
    'website': 'http://blancomartin.cl',
    'author': 'Blanco Martin & Asociados',
    'external_dependencies': {
        'python': ['xlsxwriter'],
        },
    'depends': [
        'base',
        'account',
        "report_xlsx",
                ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/invoices_wizard.xml',
        'views/account_batch_payments_view.xml',
        'views/journal_view.xml',
        'report/report_xls.xml',
    ],
    'application': False,
    'installable': True,
}
