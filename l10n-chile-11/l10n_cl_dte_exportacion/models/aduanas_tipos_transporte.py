# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class AduanasTiposTransporte(models.Model):
    _name = 'aduanas.tipos_transporte'

    name = fields.Char(
            string= 'Nombre',
        )
    code = fields.Char(
            string="Código",
        )
