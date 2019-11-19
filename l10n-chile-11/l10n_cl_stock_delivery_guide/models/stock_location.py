# -*- coding: utf-8 -*-
from odoo import osv, models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import except_orm, UserError
import logging
_logger = logging.getLogger(__name__)


class StockLocation(models.Model):
    _name = 'stock.location'
    _inherit = ['stock.location', 'l10n.cl.localization.filter']

    document_type_id = fields.Many2one(
        'account.document.type',
        string="Document Type",
        required=False,
        domain=[
            ('internal_type', 'in', ['stock_picking']),
            ('dte', '=', True),
            ('localization', '=', 'chile'), ],
    )
    sequence_id = fields.Many2one(
        'ir.sequence',
        string='Entry Sequence',
        required=False,
        help="""This field contains the information related to the numbering \
for delivery guides.""",
    )
    sii_code = fields.Char(
        string="Código de Sucursal SII",
    )
