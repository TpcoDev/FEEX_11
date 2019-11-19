# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HideComponents(models.AbstractModel):
    _name = 'hide.components'

    def _are_there_kit_products(self):
        for record in self:
            if self._model == 'account.invoice':
                for line in record.invoice_line_ids:
                    if line.name.startswith('>'):
                        return True
            elif self._model == 'stock.picking':
                for line in record.move_lines:
                    if line.name.startswith('>'):
                        return True
            return False

    hide_kit_components = fields.Boolean(
        'Hide Kit Components',
        default=lambda self: self._are_there_kit_products())
