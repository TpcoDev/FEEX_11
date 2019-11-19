# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import _, api, fields, models


class SiiRegionalOffices(models.Model):
    _name = 'sii.regional.offices'

    name = fields.Char('Regional Office Name')
    state_ids = fields.Many2many(
        'res.city', id1='sii_regional_office_id', id2='state_id',
        string='Counties')


class ResCity(models.Model):
    _inherit = 'res.city'

    sii_regional_office_ids = fields.Many2many(
        'sii.regional.offices', id1='state_id', id2='sii_regional_office_id',
        string='Regional Office')
