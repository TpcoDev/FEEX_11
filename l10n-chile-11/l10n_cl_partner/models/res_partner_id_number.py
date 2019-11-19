# -*- coding: utf-8 -*-
from openerp import _, api, fields, models
from openerp.exceptions import UserError
from openerp.tools.safe_eval import safe_eval


class ResPartnerIdNumber(models.Model):
    _inherit = "res.partner.id_number"
    _order = "sequence"

    sequence = fields.Integer(
        default=10,
        required=True,
    )

    @api.multi
    @api.constrains('name', 'category_id')
    def check(self):
        if not safe_eval(self.env['ir.config_parameter'].sudo().get_param(
                "l10n_cl_partner.unique_id_numbers", 'False')):
            return True
        for rec in self:
            related_partners = rec.partner_id.search([
                '|', ('id', 'parent_of', rec.partner_id.id),
                ('id', 'child_of', rec.partner_id.id)])
            same_id_numbers = rec.search([
                ('name', '=', rec.name),
                ('category_id', '=', rec.category_id.id),
                ('partner_id', 'not in', related_partners.ids),
            ]) - rec
            if same_id_numbers:
                raise UserError(_(
                    'Id Number must be unique per id category!\nSame number '
                    'is only allowed for partner with parent/child relation'))
