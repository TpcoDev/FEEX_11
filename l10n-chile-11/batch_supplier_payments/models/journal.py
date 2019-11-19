from odoo import fields, models, api
from openerp.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class Journal(models.Model):
    _inherit = 'account.journal'

    bank_xls_format = fields.Selection([
        ('generic', 'Generic')], string="XLS Format")
