# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class Invoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def clean_internal_number(self):
        self.ensure_one()
        if int(self.document_number) == self.journal_document_type_id.\
                sequence_id.number_next_actual-1 or \
                int(self.sii_document_number) == self.journal_document_type_id.\
                sequence_id.number_next_actual-1:
            self.journal_document_type_id.sequence_id.number_next_actual -= 1
        # despliegue de wizard
        self.clean_relationships('account.invoice.reference')
        self.write({
            'move_name': False,
            'reconciled': False,
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
        """
        Limpia relaciones
        todo: retomar un modelo de datos de relaciones de documentos
        más acorde, en lugar de account.invoice.referencias.
        #
        @author: Daniel Blanco daniel[at]blancomartin.cl
        @version: 2016-09-29
        :return:
        """

        for model in models:
            ref_obj = self.env[model]
            ref_obj.search([('invoice_id', '=', self.id)]).unlink()
