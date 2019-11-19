##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class SIIIncoterms(models.Model):
    _name = 'stock.incoterms'
    _inherit = ['stock.incoterms', 'l10n.cl.localization.filter']

    sii_code = fields.Char(
        'SII Code',
        required=False
    )
