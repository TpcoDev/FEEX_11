from odoo import _, api, fields, models
from odoo.exceptions import Warning


class SIISucursal(models.Model):
    _name = 'sii.sucursal'

    name = fields.Char(string='Nombre de la Sucursal', required=True)
    sii_code = fields.Char(string="Código SII de la Sucursal", )
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda self: self.env.user.company_id.id, )
