##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ProductUom(models.Model):
    _inherit = 'product.uom'

    sii_code = fields.Char(
        'SII Code'
    )
