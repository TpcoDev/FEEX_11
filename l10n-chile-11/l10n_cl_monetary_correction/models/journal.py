# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountJournal(models.Model):
    _name = 'account.journal'
    _inherit = 'account.journal'

    type = fields.Selection(
        [
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
            ('cash', 'Cash'),
            ('bank', 'Bank'),
            ('general', 'General'),
            ('monetary_correction', 'Monetary Correction'),
        ], string='Type'
    )
    correction_journal_id = fields.Many2one(
        'account.journal', string='Journal for correction entries',
        help='Journal to be used to register correction entries')
    journal_ids = fields.One2many(
        'account.journal', 'correction_journal_id', string='Corrected Journals',
        help='This journal is used to register correction entries for the following journals')
    monetary_correction = fields.Selection(
        [('yes', 'Yes'), ('no', 'No'), ],
        string='Monetary Correction', help='Correct Account Entries in this Journal Using IPC Values')

    @api.onchange('type', 'monetary_correction')
    def _not_show_on_dashboard(self):
        if self.type == 'monetary_correction':
            self.show_on_dashboard = False
