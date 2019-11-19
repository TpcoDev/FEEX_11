# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import datetime, timedelta, date
import logging
_logger = logging.getLogger(__name__)


class InvoiceFactoring(models.Model):
    _inherit = 'account.invoice'

    factoring_offers_count = fields.Integer(string='Factoring Offer Counts', compute='_compute_factoring_offers')

    @api.multi
    def _compute_factoring_offers(self):
        for record in self:
            if record.sii_result in ['Aceptado', 'Proceso'] and record.date_invoice < datetime.strftime(
                    datetime.now() - timedelta(days=0), '%Y-%m-%d'):
                record.factoring_offers_count = 1
            else:
                record.factoring_offers_count = 0

    @api.multi
    def hand_over_dte(self):
        _logger.info('handover dte')
        if self.docs_online_token:
            url_path = self.docs_online_token.replace('hgen/html', 'factoring')
        else:
            url_path = 'https://www.documentosonline.cl'
        return {
            'name': 'Go to Documentos online',
            'res_model': 'ir.actions.act_url',
            'type': 'ir.actions.act_url',
            'target': 'blank',
            'url': url_path, }
