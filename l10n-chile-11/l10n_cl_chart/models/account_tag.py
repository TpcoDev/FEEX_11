# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountTags(models.Model):
    _name = 'account.account.tag'
    _inherit = ['account.account.tag', 'l10n.cl.localization.filter']

    account_tag_code = fields.Char('Tag Code')
