# -*- coding: utf-8 -*-
import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    rut = fields.Char(
        compute='_compute_rut',
    )
    formated_rut = fields.Char(
        compute='_compute_formated_rut',
    )
    main_id_number = fields.Char(
        compute='_compute_main_id_number',
        inverse='_set_main_id_number',
        store=True,
        string='Main Identification Number',
    )
    main_id_category_id = fields.Many2one(
        string="Main Identification Category",
        comodel_name='res.partner.id_category',
    )

    @api.multi
    def rut_required(self):
        self.ensure_one()
        if not self.rut:
            raise UserError(_('No RUT cofigured for partner %s') % (
                self.name))
        return self.rut

    @api.multi
    @api.depends('rut')
    def _compute_formated_rut(self):
        for rec in self:
            if rec.rut:
                rec.formated_rut = self.format_document_number(rec.rut)
                
    @staticmethod
    def check_vat_cl(vat):
        body, verification_digit = '', ''
        if len(vat) > 9:
            vat = vat.replace('-', '', 1).replace('.', '', 2)
        if len(vat) != 9:
            return False
        else:
            body, verification_digit = vat[:-1], vat[-1].upper()
        try:
            validator = list(range(2, 8)) + [2, 3]
            operate = '0123456789K0'[11 - (
                sum([int(digit)*factor for digit, factor in zip(
                    body[::-1], validator)]) % 11)]
            if operate == verification_digit:
                return True
            else:
                return False
        except IndexError:
            return False

    @api.multi
    @api.depends(
        'id_numbers.category_id.tax_entity_code',
        'id_numbers.name',
        'main_id_number',
        'main_id_category_id',
    )
    def _compute_rut(self):
        for rec in self:
            categ_rut_id = self.env.ref('l10n_cl_partner.dt_RUT')
            if rec.main_id_category_id != categ_rut_id:
                country = rec.country_id
                if country and country.code != 'CL':
                    if rec.is_company:
                        rec.rut = country.rut_juridica
                    else:
                        rec.rut = country.rut_natural
                continue
            rut = rec.id_numbers.search([
                ('partner_id', '=', rec.id),
                ('category_id', '=', categ_rut_id.id),
            ], limit=1)
            if not rut:
                rec.rut = rec.main_id_number
            else:
                rec.rut = rut.name

    @staticmethod
    def format_document_number(vat):
        clean_vat = (
            re.sub('[^1234567890Kk]', '',
                   str(vat))).zfill(9).upper()
        return '%s-%s' % (
            clean_vat[0:8], clean_vat[-1])

    @api.onchange('main_id_number')
    def onchange_main_id_number(self):
        if self.main_id_category_id == self.env.ref('l10n_cl_partner.dt_RUT'):
            self.main_id_number = self.format_document_number(
                self.main_id_number)
            if not self.check_vat_cl(self.main_id_number):
                self.main_id_number = ''
                raise UserError('RUT no válido')
            self._compute_vat()

    @api.multi
    @api.depends(
        'main_id_category_id',
        'id_numbers.category_id',
        'id_numbers.name',
    )
    def _compute_main_id_number(self):
        for partner in self:
            id_numbers = partner.id_numbers.filtered(
                lambda x: x.category_id == partner.main_id_category_id)
            if id_numbers:
                partner.main_id_number = id_numbers[0].name

    @api.depends('main_id_number')
    def _compute_vat(self):
        for x in self:
            if x.main_id_number == '55555555-5':
                return
            clean_vat = (
                re.sub('[^1234567890Kk]', '',
                       str(x.main_id_number))).zfill(9).upper()
            x.vat = 'CL%s' % clean_vat

    @api.multi
    def _inverse_vat(self):
        for x in self:
            if x.taxpayer_type_id == self.env.get('l10n_cl_partner.'):
                return
            x.main_id_number = x.format_document_number(x.vat)

    @api.multi
    def _set_main_id_number(self):
        for partner in self:
            name = partner.main_id_number
            category_id = partner.main_id_category_id
            if category_id:
                partner_id_numbers = partner.id_numbers.filtered(
                    lambda d: d.category_id == category_id)
                if partner_id_numbers and name:
                    partner_id_numbers[0].name = name
                elif partner_id_numbers and not name:
                    partner_id_numbers[0].unlink()
                # we only create new record if name has a value
                elif name:
                    partner_id_numbers.create({
                        'partner_id': partner.id,
                        'category_id': category_id.id,
                        'name': name
                    })

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """
        we search by id, if we found we return this results, else we do
        default search
        """
        if not args:
            args = []
        if name:
            recs = self.search(
                [('id_numbers', operator, name)] + args, limit=limit)
            if recs:
                return recs.name_get()
        return super(ResPartner, self).name_search(
            name, args=args, operator=operator, limit=limit)
