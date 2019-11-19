##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResCurrency(models.Model):
    _inherit = "res.currency"

    sii_code = fields.Char(
        'SII Code', size=4
    )
