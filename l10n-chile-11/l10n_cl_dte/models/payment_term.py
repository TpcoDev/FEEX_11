# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PaymentTerm(models.Model):
    _name = 'account.payment.term'
    _inherit = ['account.payment.term', 'l10n.cl.localization.filter']

    dte_sii_code = fields.Selection((
        ('1', '1: Contado'),
        ('2', '2: Credito'),
        ('3', '3: Otro')), 'DTE Sii Code', )
