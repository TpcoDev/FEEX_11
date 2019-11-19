# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class Incoterms(models.Model):
    _inherit = "stock.incoterms"

    aduanas_code = fields.Integer(
            string="Código de aduanas"
        )
