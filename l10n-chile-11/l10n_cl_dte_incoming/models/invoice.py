# -*- coding: utf-8 -*-
import collections
import logging
import os
import pysiidte
import struct
import sys
import xml.dom.minidom
from datetime import date, datetime, timedelta

from lxml import etree
from lxml.etree import Element, SubElement
from six import string_types

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

try:
    from io import BytesIO
except:
    _logger.warning("no se ha cargado io")

try:
    from zeep.client import Client
except:
    pass
try:
    import textwrap
except:
    pass

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    import OpenSSL
    from OpenSSL import crypto
    type_ = crypto.FILETYPE_PEM
except:
    _logger.warning('Cannot import OpenSSL library')

try:
    import dicttoxml
except ImportError:
    _logger.warning('Cannot import dicttoxml library')

try:
    import pdf417gen
except ImportError:
    _logger.warning('Cannot import pdf417gen library')

try:
    import base64
except ImportError:
    _logger.warning('Cannot import base64 library')

try:
    import hashlib
except ImportError:
    _logger.warning('Cannot import hashlib library')

try:
    import cchardet
except ImportError:
    _logger.warning('Cannot import cchardet library')

timbre = pysiidte.stamp

try:
    import xmltodict
    result = xmltodict.parse(timbre)
except ImportError:
    _logger.warning('Cannot import xmltodict library')

dicttoxml.LOG.setLevel(logging.ERROR)

server_url = pysiidte.server_url
claim_url = pysiidte.claim_url
BC = pysiidte.BC
EC = pysiidte.EC

USING_PYTHON2 = True if sys.version_info < (3, 0) else False
xsdpath = os.path.dirname(os.path.realpath(__file__)).replace('/models', '/static/xsd/')

TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}


class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice', 'l10n.cl.localization.filter']

    @api.multi
    def validation_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dte.validate.wizard',
            'src_model': 'account.invoice',
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'tag': 'action_validate_wizard', }