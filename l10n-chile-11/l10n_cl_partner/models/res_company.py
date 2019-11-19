# -*- coding: utf-8 -*-
import re

from openerp import api, fields, models
from openerp.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    main_id_category_id = fields.Many2one(
        related='partner_id.main_id_category_id',
    )
    main_id_number = fields.Char(
        related='partner_id.main_id_number',
    )
    rut = fields.Char(
        related='partner_id.rut'
    )

    @api.multi
    def rut_required(self):
        return self.partner_id.rut_required()

    @api.model
    def create(self, vals):
        """
        On create, we set id number to partner
        """
        company = super(ResCompany, self).create(vals)
        company.change_main_id_category()
        main_id_number = vals.get('main_id_number')
        if main_id_number:
            company.partner_id.main_id_number = main_id_number
        return company

    @api.onchange('main_id_category_id')
    def change_main_id_category(self):
        # we force change on partner to get updated number
        if self.partner_id:
            self.partner_id.main_id_category_id = self.main_id_category_id
            self.main_id_number = self.partner_id.main_id_number

    @api.onchange('main_id_number')
    def onchange_main_id_number(self):
        if self.main_id_category_id == self.env.ref('l10n_cl_partner.dt_RUT'):
            self.main_id_number = self.partner_id.format_document_number(
                self.main_id_number)
            if not self.partner_id.check_vat_cl(self.main_id_number):
                raise UserError('RUT no válido')
        clean_vat = (re.sub('[^1234567890Kk]', '', str(self.main_id_number))).zfill(9).upper()
        self.vat = 'CL%s' % clean_vat
