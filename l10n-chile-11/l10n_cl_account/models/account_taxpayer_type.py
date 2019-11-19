from odoo import fields, models

# from odoo.exceptions import UserError


class TaxPayerType(models.Model):
    _name = 'account.taxpayer.type'
    _description = 'Tax Payer Type'
    _order = 'sequence'

    name = fields.Char(
        'Name',
        size=64,
        required=True
    )
    sequence = fields.Integer(
        'Sequence',
    )
    code = fields.Char(
        'Code',
        size=8,
        required=True
    )
    tp_sii_code = fields.Integer(
        'Tax Payer SII Code',
        required=True
        )
    active = fields.Boolean(
        'Active',
        default=True
    )
    issued_letter_ids = fields.Many2many(
        'account.document.letter',
        'account_document_letter_taxpayer_issuer_rel',
        'taxpayer_type_id',
        'document_letter_id',
        'Issued Document Letters'
    )
    received_letter_ids = fields.Many2many(
        'account.document.letter',
        'account_document_letter_taxpayer_receptor_rel',
        'taxpayer_type_id',
        'document_letter_id',
        'Received Document Letters'
    )
    # hacemos esto para que, principalmente, monotributistas y exentos no
    # requieran iva, otra forma sería poner el impuesto no corresponde, pero
    # no queremos complicar vista y configuración con un impuesto que no va
    # a aportar nada
    company_requires_vat = fields.Boolean(
        string='Company requires vat?',
        help='Companies of this type will require VAT tax on every invoice '
        'line of a journal that use documents'
    )

    _sql_constraints = [('name', 'unique(name)', 'Name must be unique!'),
                        ('code', 'unique(code)', 'Code must be unique!')]
