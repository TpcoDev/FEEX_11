# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountJournalDocumentConfig(models.TransientModel):
    _name = 'account.journal.document_config'

    debit_notes = fields.Selection(
        [('dont_use', 'Do not use'), ('own_sequence', 'Use')],
        string='Debit Notes', required=True, default='own_sequence')
    credit_notes = fields.Selection(
        [('own_sequence', 'Use')], string='Credit Notes', required=True,
        default='own_sequence')
    dte_register = fields.Boolean(
        'Register Electronic Documents?', default=True, help="""
This option allows you to register electronic documents (DTEs) issued by \
MiPyme SII Portal, Third parties services, or by Odoo itself (to register \
DTEs issued by Odoo l10n_cl_dte/caf modules are needed.
""")
    non_dte_register = fields.Boolean(
        'Register Manual Documents?')
    electronic_ticket = fields.Boolean(
        'Register Electronic Ticket')
    free_tax_zone = fields.Boolean(
        'Register Free-Tax Zone or # 1057 Resolution Documents?')
    settlement_invoice = fields.Boolean(
        'Register Settlement Invoices?')
    dte_export = fields.Boolean(
        'Register DTE Export')
    weird_documents = fields.Boolean(
        'Unusual Documents', help="""
Include unusual taxes documents, as transfer invoice, and reissue
""")

    other_available = fields.Boolean(
        'Others available?', default='_get_other_avail')

    @api.model
    def _get_other_avail(self):
        return True

    def confirm(self, context=None):
        """
        Confirm Configure button
        """
        if context is None:
            context = {}

        journal_id = self.env['account.journal'].browse(
            context.get('active_id', False))
        wizard = self.browse()
        vals = {
                'dte_register': self.dte_register,
                'non_dte_register': self.non_dte_register,
                'electronic_ticket': self.electronic_ticket,
                'free_tax_zone': self.free_tax_zone,
                'settlement_invoice': self.settlement_invoice,
                'dte_export': self.dte_export,
                'weird_documents': self.weird_documents,
                }
        journal_id.update_journal_document_types(vals)
