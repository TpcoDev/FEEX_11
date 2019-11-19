# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice', 'hide.components']
