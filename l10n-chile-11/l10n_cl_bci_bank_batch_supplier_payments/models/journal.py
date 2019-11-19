# -*- coding: utf-8 -*-

from odoo import fields, models, api
from openerp.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class Journal(models.Model):
    _inherit = 'account.journal'

    bank_xls_format = fields.Selection(
        selection_add=[('bci', 'Banco de Crédito e Inversiones (BCI)')])
