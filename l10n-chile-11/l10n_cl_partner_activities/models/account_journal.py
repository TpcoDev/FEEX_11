from odoo import _, api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # journal_activities_ids = fields.Many2many(
    #     string='Activities Names',
    #     related='company_id.company_activities_ids',
    #     relation='partner.activities',
    #     help='Select the turns you want to invoice in this Journal')

    excempt_documents = fields.Boolean(
        'Exempt Documents Available', compute='_check_activities')

    @api.one
    @api.depends('type')
    def _check_activities(self):
        try:
            if 'purchase' in self.type:
                self.excempt_documents = True
            elif 'sale' in self.type:
                no_vat = False
                for turn in self.env.user.company_id.company_activities_ids:
                    print('turn %s' % turn.vat_affected)
                    if turn.vat_affected == 'SI':
                        continue
                    else:
                        no_vat = True
                        break
                self.excempt_documents = no_vat
        except:
            pass
