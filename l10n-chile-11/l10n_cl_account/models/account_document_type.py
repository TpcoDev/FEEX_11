from odoo import api, fields, models

# from odoo.exceptions import UserError


class AccountDocumentType(models.Model):
    _inherit = 'account.document.type'

    internal_type = fields.Selection(
        selection_add=[
            ('invoice_in', 'Purchase Invoices'),
            ('stock_picking', 'Stock Picking'),
            ('other_document', 'Other Documents')])
    document_letter_id = fields.Many2one(
        'account.document.letter',
        'Document Letter')
    code_template = fields.Char(
        'Code Template for Journal')
    dte = fields.Boolean('DTE')
    use_prefix = fields.Boolean(string="Usar Prefix en las referencias DTE", default=False, )

    @api.multi
    def get_document_sequence_vals(self, journal):
        vals = super(AccountDocumentType, self).get_document_sequence_vals(journal)
        if self.localization == 'chile':
            vals.update({
                'padding': 6,
                'implementation': 'no_gap',
                'prefix': '',
                'number_next_actual': 1, })
        return vals

    @api.multi
    def get_taxes_included(self):
        self.ensure_one()
        if self.localization == 'chile':
            if self.document_letter_id.taxes_included:
                return self.env['account.tax'].search([])
        else:
            return super(AccountDocumentType, self).get_taxes_included()
