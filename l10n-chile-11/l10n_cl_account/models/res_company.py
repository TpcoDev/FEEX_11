##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models

# from odoo.addons.account_document.models.res_company import ResCompany

# localization = ResCompany._localization_selection

# new_selection = localization.append(('chile', 'Chile'))
# ResCompany._localization_selection = new_selection


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = ['res.company', 'l10n.cl.localization.filter']

    localization = fields.Selection(selection_add=[('chile', 'Chile')])

    start_date = fields.Date(
        related='partner_id.start_date',
    )
    taxpayer_type_id = fields.Many2one(
        related='partner_id.taxpayer_type_id',
    )
    company_requires_vat = fields.Boolean(
        related='taxpayer_type_id.company_requires_vat',
        readonly=True,
    )
    # use globally as default so that if child companies are created they
    # also use this as default
    tax_calculation_rounding_method = fields.Selection(
        default='round_globally',
    )

    @api.onchange('localization')
    def change_localization(self):
        if self.localization == 'chile' and not self.country_id:
            self.country_id = self.env.ref('base.cl')
    # TODO ver si lo movemos a account_document
    # journal_ids = fields.One2many(
    #     'account.journal',
    #     'company_id',
    #     'Journals'
    #     )
