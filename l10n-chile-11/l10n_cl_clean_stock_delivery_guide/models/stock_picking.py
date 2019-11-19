# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import logging
import re

from odoo import api, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Invoice(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def clean_internal_number(self):
        self.ensure_one()
        _logger.info('document number: %s' % self.document_number)
        if int(re.findall('\d+', self.document_number)[0]) == self.location_id.sequence_id.number_next_actual-1:
            self.location_id.sequence_id.number_next_actual -= 1
        self.clean_relationships('stock.picking.reference')
        self.clean_queue()
        self.write({
            'sii_batch_number': False,
            'sii_barcode': False,
            'sii_barcode_img': False,
            'sii_document_number': False,
            'sii_message': False,
            'sii_xml_dte': False,
            'sii_result': False,
            'sii_xml_request': False,
            'document_number': False,
        })
        _logger.info('Clean number')

    def clean_relationships(self, *models):
        for model in models:
            ref_obj = self.env[model]
            ref_obj.search([('stock_picking_id', '=', self.id)]).unlink()

    def clean_queue(self):
        ref_obj = self.env['sii.send_queue']
        queue_ids = ref_obj.search(
            [('doc_ids', '=', '[%s]' % self.id),
             '|', ('model', '=', 'stock.picking'), ('model_selection', '=', 'stock.picking')])
        for queue_id in queue_ids:
            queue_id.unlink()
