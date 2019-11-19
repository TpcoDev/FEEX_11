##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# WIP This class apparently is not needed in chilean localization.
# The method is not needed for sure
"""
class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.multi
    def _create_bank_journals_from_o2m(self, company, acc_template_ref):
        # hacemos que se cree diario de retenciones si modulo instaldo
        if company.localization == 'argentina':
            self = self.with_context(create_withholding_journal=True)

        # al final esto lo hacemos como customizacion
        # on chile localization we prefer to create banks manually
        # for tests, demo data requires a bank journal to be loaded, we
        # send this on context
        # NEW: we also prefer to create cashbox manually
        # if company.localization == 'argentina' and not self._context.get(
        #         'with_bank_journal'):
        #     for rec in self.bank_account_ids:
        #         if rec.account_type == 'bank':
        #             rec.unlink()
        return super(
            WizardMultiChartsAccounts, self)._create_bank_journals_from_o2m(
            company, acc_template_ref)
"""


class AccountChartTemplate(models.Model):
    _name = 'account.chart.template'
    _inherit = ['account.chart.template', 'l10n.cl.localization.filter']

    opening_clousure_account_id = fields.Many2one(
        'account.account.template',
        string='Opening / Closure Account',
        domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)],
    )

    @api.multi
    def generate_fiscal_position(
            self, tax_template_ref, acc_template_ref, company):
        """
        if chart is Chile localization, then we add sii_code to fiscal
        positions.
        We also add other data to add fiscal positions automatically
        """
        res = super(AccountChartTemplate, self).generate_fiscal_position(
            tax_template_ref, acc_template_ref, company)
        if self.localization != 'argentina':
            return res
        positions = self.env['account.fiscal.position.template'].search(
            [('chart_template_id', '=', self.id)])
        for position in positions:
            created_position = self.env['account.fiscal.position'].search([
                ('company_id', '=', company.id),
                ('name', '=', position.name),
                ('note', '=', position.note)], limit=1)
            if created_position:
                created_position.update({
                    'sii_code': position.sii_code,
                    'taxpayer_type_ids': (
                        position.taxpayer_type_ids),
                    # TODO this should be done in odoo core
                    'country_id': position.country_id.id,
                    'country_group_id': position.country_group_id.id,
                    'state_ids': position.state_ids.ids,
                    'zip_to': position.zip_to,
                    'zip_from': position.zip_from,
                    'auto_apply': position.auto_apply,
                })
        return res

    @api.multi
    def _prepare_all_journals(
            self, acc_template_ref, company, journals_dict=None):
        """
        Inherit this function in order to add use document and other
        configuration if company use chile localization
        """
        journal_data = super(
            AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict)
        opening_clousure_account_id = acc_template_ref.get(
            self.opening_clousure_account_id.id)
        journals = [
            ('Liquidación de Impuestos', 'LIMP', 'general', False),
            ('Sueldos y Jornales', 'SYJ', 'general', False),
            ('Asientos de Apertura / Cierre', 'A/C', 'general',
                opening_clousure_account_id),
        ]
        for name, code, type, default_account_id in journals:
            journal_data.append({
                'type': type,
                'name': name,
                'code': code,
                'default_credit_account_id': default_account_id,
                'default_debit_account_id': default_account_id,
                'company_id': company.id,
                'show_on_dashboard': False,
                'update_posted': True,
            })
        return journal_data
