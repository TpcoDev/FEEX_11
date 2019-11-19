# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DeliveryGuide(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'hide.components']
