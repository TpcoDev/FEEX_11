# -*- coding: utf-8 -*-
# Init module for l10n_cl_base
# Daniel Blanco - Blanco Martin & Asociados
##############################################################################
'''This code intended to define transient fields for installing modules'''
from odoo import _, api, fields, models


class ChileanBaseConfiguration(models.TransientModel):
    _inherit = 'res.config.settings'

    module_l10n_cl_chart = fields.Boolean(
        'Install Chilean Accounting Plan',
        help="""Installs module l10n_cl_chart, allowing to choose different \
account options.""")

    module_l10n_cl_account_vat_ledger = fields.Boolean(
        'Install VAT Ledger',
        help="""Installs module for vat ledger, allowing to export \
sales and purchases VAT ledger in XLS format. Requires Aeroo Reports.""")

    module_l10n_cl_banks_sbif = fields.Boolean(
        'Banks in Chile, According SBIF',
        help="""Installs module l10n_cl_banks_sbif, and includes authorized \
banks, and financial institutions in Chile.""")

    module_l10n_cl_financial_indicators = fields.Boolean(
        'Update UF, UTM, Dollar and Euro automatically',
        help="""Installs module l10n_cl_financial_indicators, allowing to \
update indicators daily, from SBIF.""")

    module_l10n_cl_counties = fields.Boolean(
        'Include Chilean Counties for partners and companies',
        help="""Installs l10n_cl_counties, which includes all chilean \
counties to partners.""")

    module_l10n_cl_partner_activities = fields.Boolean(
        'Include Partner\'s turn', help="""Installs l10n_cl_partner_activities \
module, which includes your partners' turns in their record using the SII \
activities table and allows you to select the activity when invoicing.""")

    activity_description_invisible = fields.Boolean(
        'Activity Description Hidden',
        help='Check this box if you don\'t want activities descriptions at all')

    activities_opt = fields.Selection([
        ('activity_description', 'Business Turn Based on Activity Description \
(B2C or MSEs)'),
        ('encoded_activity', 'Business Turn Based on Economic Activities \
(B2B or SMEs)'), ],
        help="""If your company is a small or medium business, probably you'd \
prefer to describe your activity or your partner's activities based on the \
SII's economic activities nomenclator.
But if your company is a micro or small enterprise, or if you mostly serves \
your customers at a counter, you will probably prefer to describe your 
partners' activities based on a simple description through a phrase.
In either case, establishing at least one of the economic activities for your \
own company is mandatory. """)

    api_sbif_token = fields.Char('SBIF API Token',
help="""If you want to update the currency and financial indicators rate, you \
will need to susribe to SBIF. Follow the instructions.""")

    module_l10n_cl_account = fields.Boolean(
        'Centralized sales journal for multiple type of document stubs \
         (recommended)!',
        help="""Installs l10n_cl_account. It links your invoicing, picking and \
receipts stubs with journals for easiest configuration. This is a base module \
for DTE compliance, and a fundamental option for companies with multiple \
branches.""")

    module_l10n_cl_dte = fields.Boolean(
        'Use Electronic Invoicing', help="""Installs several dependencies in \
order to performn Electronic invoicing, and sales invoicing in xml.""")

    auto_send_dte = fields.Integer(
            string="Tiempo de Espera para Enviar DTE automático al SII (en minutos)",
            default=60,
        )
    auto_send_email = fields.Boolean(
            string="Enviar Email automático al Auto Enviar DTE al SII",
            default=True,
        )

    module_user_signature_key = fields.Boolean(
        'SII Directly (adds User signature and CAF management).',
        help="""Works without gateways, directly to SII. This set Odoo to \
work directly with SII, installing module l10n_cl_dte_caf and \
other dependencies""")

    module_l10n_cl_pos_basic_users = fields.Boolean(
        'Install dummy-proof terminology - (not recommended)',
        help="""Installs l10n_cl_pos_basic_users module, which helps \
against POS closed minded operators. (factura/boleta cliente factura, \
cliente boleta. Adds generic partners to make invoicing easier, but is not \
recommended, except for dummy users.""")

    module_l10n_cl_pos_credit_card_voucher = fields.Boolean(
        'Exclude final consumer credit card sales from VAT report (recommended \
only for pre-printed invoicing)',
        help="""Installs module l10n_cl_pos_credit_card_voucher, allowing you \
to link the sales note with a credit card voucher, in order to keep \
it unreported in boletas sales.""")

    module_invoice_printed = fields.Boolean(
        'Invoice in TXT Format', help="""Installs invoice_printed module, to \
interact with prnfiscal dependency in your local machine, in order to have \
your fiscal documents rendered in TXT format. This allows printing in fiscal \
printers, or connect to external electronic invoices services""")

    module_l10n_cl_aeroo_einvoice = fields.Boolean(
        'Electronic Invoice Format', help="""Installs output form report \
including PDF417 electronic stamp""")

    module_l10n_cl_dte_incoming = fields.Boolean(
        'Electronic Invoice from Suppliers', help="""Installs the capability \
of receiving electronic documents from suppliers.""")

    module_l10n_cl_dte_pdf = fields.Boolean(
        'Electronic Invoice Format', help="""Installs output form report \
    including PDF417 electronic stamp""")

    module_l10n_cl_aeroo_stock = fields.Boolean(
        'Electronic Stock picking', help="""Installs output form report \
including PDF417 electronic stamp""")

    module_l10n_cl_aeroo_purchase = fields.Boolean(
        'Purchase Order Form', help="""Report for purchase order""")

    module_l10n_cl_aeroo_sale = fields.Boolean(
        'Sales Order Form', help="""Report for sales order""")

    module_l10n_cl_aeroo_receipt = fields.Boolean(
        'Payment Receipt Form', help="""Report for payment receipt""")

    module_l10n_cl_hr_payroll = fields.Boolean(
        'Install payroll and AFPs chilean modules',
        help="""Install l10n_cl_hr_payroll for payroll and AFPs chilean \
modules""")

    module_l10n_cl_hr_previred = fields.Boolean(
        'Update Previred\'s Monthly indexes',
        help="""Installs l10n_cl_hr_previred module, to update needed indexes \
in order to issue your payroll""")

    module_l10n_cl_hr_send_to_previred = fields.Boolean(
        'Send payroll Information to Previred monthly',
        help="""Installs l10n_cl_send_to_previred module, which allows you to \
send a monthly report with 105 fields per employee, to Previred.""")

    module_l10n_cl_docsonline_print = fields.Boolean(
        'Enable printing or backup from www.documentosonline.cl',
        help="""Enable printing or backup from www.documentosonline.cl""")

    module_l10n_cl_docsonline_factoring = fields.Boolean(
        'Get factoring offers from www.documentosonline.cl',
        help="""Get factoring offers from www.documentosonline.cl""")

    module_l10n_cl_docsonline_partner = fields.Boolean(
        'Get partner data from www.documentosonline.cl',
        help="""Get partner data from www.documentosonline.cl""")

    @api.onchange('module_l10n_cl_account')  # if these fields are changed
    def check_change_cl_account(self):
        if self.module_l10n_cl_account:
            self.module_l10n_cl_partner_activities = True

    @api.onchange('module_l10n_cl_dte', 'module_l10n_cl_account_vat_ledger')
    # if these fields are changed, call method
    def check_change_cl_dte(self):
        if self.module_l10n_cl_dte or self.module_l10n_cl_account_vat_ledger:
            self.module_l10n_cl_account = True
            self.module_l10n_cl_counties = True

    @api.model
    def get_values(self):
        res = super(ChileanBaseConfiguration, self).get_values()

        get_param = self.env['ir.config_parameter'].sudo().get_param

        if not get_param('activities_description_required', default=False) \
                and not get_param('activities_invisible', default=False):
            activities_opt = 'encoded_activity'
        else:
            activities_opt = 'activity_description'

        activity_description_invisible = get_param(
            'activity_description_invisible_company', default=False)

        api_sbif_token = get_param(
            'sbif.financial.indicators.apikey', default=False)

        account_auto_send_dte = int(get_param('account.auto_send_dte', default=60))
        
        account_auto_send_email = get_param('account.auto_send_email', default=True)

        res.update(
            activities_opt=activities_opt,
            activity_description_invisible=activity_description_invisible,
            api_sbif_token=api_sbif_token,
            auto_send_email=account_auto_send_email,
            auto_send_dte=account_auto_send_dte,
            )
        return res

    @api.multi
    def set_values(self):
        super(ChileanBaseConfiguration, self).set_values()

        set_param = self.env['ir.config_parameter'].sudo().set_param
        
        if self.activities_opt == 'encoded_activity':
            set_param('activities_description_required', False)
            set_param('activities_invisible', False)
            # activities is always required for own company (at least one)
            # in this case description is optional, since if it is not set
            # electronic invoice module gets, the text from first encoded
            # activity for the company (emitter)
            if self.activity_description_invisible:
                set_param('activity_description_invisible_company', True)
            else:
                set_param('activity_description_invisible_company', False)

        else:  # self.activities_opt == 'activity_description'
            set_param('activities_description_required', True)
            set_param('activities_invisible', True)
            set_param('activity_description_invisible_company', False)

        if self.api_sbif_token:
            set_param('sbif.financial.indicators.apikey', self.api_sbif_token)

        if self.auto_send_dte:
            set_param('account.auto_send_dte', self.auto_send_dte)

        if self.auto_send_email:
            set_param('account.auto_send_email', self.auto_send_email)
