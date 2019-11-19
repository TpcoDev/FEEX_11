# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class AduanasFormasPago(models.Model):
    _name = 'aduanas.formas_pago'

    name = fields.Char(
            string= 'Nombre',
        )
    code = fields.Char(
            string="Código",
        )
    sigla = fields.Char(
            string="Sigla",
        )
