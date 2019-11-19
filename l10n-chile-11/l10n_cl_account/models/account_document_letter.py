from odoo import fields, models


class AccountDocumentLetter(models.Model):
    _name = 'account.document.letter'
    _description = 'Account Document Letter'

    name = fields.Char(
        'Name',
        required=True
    )
    document_type_ids = fields.One2many(
        'account.document.type',
        'document_letter_id',
        'Document Types'
    )
    issuer_ids = fields.Many2many(
        'account.taxpayer.type',
        'account_document_letter_taxpayer_issuer_rel',
        'document_letter_id',
        'taxpayer_type_id',
        'Issuers',
    )
    receptor_ids = fields.Many2many(
        'account.taxpayer.type',
        'account_document_letter_taxpayer_receptor_rel',
        'document_letter_id',
        'taxpayer_type_id',
        'Receptors',
    )
    active = fields.Boolean(
        'Active',
        default=True
    )
    taxes_included = fields.Boolean(
        'Taxes Included?',
        help='Documents related to this letter will include taxes on reports',
    )
    behavior = fields.Text(
        'Behavior', help='Type of behavior inside Odoo regarding taxes, and issuer and receptor tax payer type')
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position', string='Fiscal Position', help='Related fiscal position used in invoices')
    # taxes_discriminated = fields.Boolean(
    #     'Taxes Discriminated on Invoices?',
    #     help="If True, the taxes will be discriminated on invoice report.")

    _sql_constraints = [('name', 'unique(name)', 'Name must be unique!'), ]
