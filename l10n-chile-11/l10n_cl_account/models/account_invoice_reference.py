##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class InvoiceReference(models.Model):
    _name = 'account.invoice.reference'
    _inherit = 'l10n.cl.localization.filter'

    origin = fields.Char(
        string="Origin",
    )
    reference_doc_type = fields.Many2one(
        'account.document.type',
        string="SII Document Type", oldname='sii_reference_TpoDocRef',
    )
    reference_doc_code = fields.Selection(
        [
            ('1', '1. Anula Documento de Referencia'),
            ('2', '2. Corrige texto Documento Referencia'),
            ('3', '3. Corrige montos')
        ],
        string="SII Reference Code", oldname='sii_reference_CodRef'
    )
    reason = fields.Char(
        string="Reason",
    )
    invoice_id = fields.Many2one(
        'account.invoice',
        ondelete='cascade',
        index=True,
        copy=False,
        string="Referenced Document",
    )
    date = fields.Date(
        string="Document Date",
        required=True,
    )
