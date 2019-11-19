# -*- coding: utf-8 -*-
import base64
import json
import logging

import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DeliveryGuidePrint(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'docs_online.print']
