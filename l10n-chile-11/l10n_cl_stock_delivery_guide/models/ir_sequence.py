# -*- coding: utf-8 -*-
from odoo import models, fields, api, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


class Sequence(models.Model):
    _inherit = "ir.sequence"

    def _check_dte(self):
        super(Sequence, self)._check_dte()
        for r in self:
            obj = self.env['stock.location'].search([('sequence_id', '=', r.id)], limit=1)
            if not r.is_dte and obj:
                r.is_dte = True

    def _get_sii_document_class(self):
        super(Sequence, self)._get_sii_document_class()
        for r in self:
            if not r.document_type_id:
                 obj = self.env['stock.location'].search([('sequence_id', '=', r.id)], limit=1)
                 r.document_type_id = obj.document_type_id.code
