# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, fields, models
from openerp.tools.safe_eval import safe_eval


class SaleConfiguration(models.TransientModel):
    _inherit = 'res.config.settings'

    group_multiple_id_numbers = fields.Boolean(
        "Allow Multiple Id Numbers on Partners",
        help="If you allow multiple Id Numbers, then a new tab for 'Id "
        "NUmbers' will be added on partner form view",
        implied_group='l10n_cl_partner.group_multiple_id_numbers',
    )
    unique_id_numbers = fields.Boolean(
        "Restrict Id Numbers to be Unique",
        help="If you set it True, then we will check that partner Id Numbers "
        "(for eg. rut, dni, etc) are unique. Same number for partners in a "
        "child/parent relation are still allowed",
    )

    @api.model
    def get_values(self):
        res = super(SaleConfiguration, self).get_values()

        get_param = self.env['ir.config_parameter'].sudo().get_param
        unique_id_numbers = get_param("l10n_cl_partner.unique_id_numbers", default=False)
        res.update(unique_id_numbers=unique_id_numbers)
        return res

    @api.multi
    def set_values(self):
        super(SaleConfiguration, self).set_values()

        set_param = self.env['ir.config_parameter'].sudo().set_param

        for record in self:
            set_param("l10n_cl_partner.unique_id_numbers", record.unique_id_numbers)
