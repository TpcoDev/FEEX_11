# -*- coding: utf-8 -*-
import ast
import logging
from datetime import datetime
from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF

_logger = logging.getLogger(__name__)


class SendQueue(models.Model):
    _name = 'sii.send_queue'
    _inherit = 'sii.send_queue'

    picking_ids = fields.One2many(
        'stock.picking', 'picking_send_queue_id', string='Delivery Guide'
    )
