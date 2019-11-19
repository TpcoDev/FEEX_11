##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import fields, models


class ResCountry(models.Model):
    _name = 'res.country'
    _inherit = ['res.country', 'l10n.cl.localization.filter']

    sii_code = fields.Char(
        'SII Code',
        size=3,
    )
    rut_natural = fields.Char(
        'RUT persona nautural',
        size=11,
    )
    rut_juridica = fields.Char(
        'RUT persona juridica',
        size=11,
    )
    rut_otro = fields.Char(
        'RUT otro',
        size=11,
    )
