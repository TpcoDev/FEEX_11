# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import logging
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class StockPickingReference(models.Model):
    _name = 'stock.picking.reference'

    origin = fields.Char(
        string="Origin",
    )
    reference_doc_type = fields.Many2one(
        'account.document.type',
        string="SII Ref. Document Type", oldname='sii_referencia_TpoDocRef',
    )
    date = fields.Date(
        string="Ref. Doc Date",
        required=True,
    )
    stock_picking_id = fields.Many2one(
        'stock.picking',
        ondelete='cascade',
        index=True,
        copy=False,
        string="Referenced Document",
    )
