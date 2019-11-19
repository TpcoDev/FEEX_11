# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SendDTEWizardMulti(models.TransientModel):
    _name = 'sii.dte.build.sales.book.wizard'
    _description = 'SII Build Sales Book'

    @api.model
    def _getIDs(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        return self.env['account.move'].browse(active_ids)

    @api.model
    def _getCompany(self):
        return self.company_id.id
        
    company_id = fields.Many2one('res.company', default=_getCompany)
    move_ids = fields.Many2many('account.move', string="Moves", default=_getIDs)

    @api.multi
    def confirm(self):
        data = {
                'move_ids': self.move_ids,
                'tipo_libro': 'ESPECIAL',
                'tipo_operacion': 'COMPRA',
                'tipo_envio': 'TOTAL',
                'folio_notificacion': 612124,
                'fiscal_period': '2016-07',
                'company_id': self.company_id.id,
            }
        libro = self.env['account.move.libro'].create(data)
        libro.write(data)
        libro.do_dte_send_libro()
