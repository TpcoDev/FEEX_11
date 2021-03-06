# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class MasiveDTEAcceptWizard(models.TransientModel):
    _name = 'sii.dte.masive.accept.wizard'
    _description = 'SII Masive DTE Accept Wizard'

    @api.multi
    def confirm(self):
        dtes = self.env['mail.message.dte.document'].browse(self._context.get('active_ids', []))
        return dtes.accept_document()
