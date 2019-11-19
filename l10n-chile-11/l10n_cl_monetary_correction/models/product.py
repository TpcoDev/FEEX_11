# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    origin_monetary_correction = fields.Selection(
        [
            ('domestic', 'Domestic'),
            ('foreign', 'Foreign'),
        ],
        string='Type of product for Monetary Correction')
    highest_cost_in_period = fields.Monetary(
        compute='_get_highest_cost', string='Hightest cost in period'
    )

    def _get_highest_cost(self):
        for record in self:
            record.highest_cost_in_period = record.standard_price


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = 'product.product'

    origin_monetary_correction = fields.Selection(
        [
            ('domestic', 'Domestic'),
            ('foreign', 'Foreign'),
        ],
        related='product_tmpl_id.origin_monetary_correction',
        string='Type of product for Monetary Correction',
    )
    highest_cost_in_period = fields.Monetary(
        compute='_get_highest_cost', string='Hightest cost in period'
    )

    def _get_highest_cost(self):
        for record in self:
            record.highest_cost_in_period = record.standard_price


class ProductCategory(models.Model):
    _name = 'product.category'
    _inherit = 'product.category'

    origin_monetary_correction = fields.Selection(
        [
            ('domestic', 'Domestic'),
            ('foreign', 'Foreign'),
        ],
        string='Type of product for Monetary Correction')
