# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class AduanasUnidadesMedida(models.Model):
    _inherit = 'product.uom'

    code = fields.Char(
            string="Código Aduanas",
        )
