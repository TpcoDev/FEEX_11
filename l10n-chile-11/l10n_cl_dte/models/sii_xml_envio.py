import collections
import logging
import urllib3
import xmltodict

from . import pysiidte

from odoo import api, fields, models
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)
urllib3.disable_warnings()
pool = urllib3.PoolManager(cert_reqs='CERT_NONE')


class SIIXMLEnvio(models.Model):
    _name = 'sii.xml.envio'

    name = fields.Char(
            string='Nombre de envío',
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    xml_envio = fields.Text(
            string='XML Envío',
            required=True,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    state = fields.Selection(
            [
                    ('draft', 'Borrador'),
                    ('NoEnviado', 'No Enviado'),
                    ('Enviado', 'Enviado'),
                    ('Aceptado', 'Aceptado'),
                    ('Rechazado', 'Rechazado'),
            ],
            default='draft',
        )
    company_id = fields.Many2one(
            'res.company',
            string='Compañia',
            required=True,
            default=lambda self: self.env.user.company_id.id,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    sii_xml_response = fields.Text(
            string='SII XML Response',
            copy=False,
            readonly=True,
            states={'NoEnviado': [('readonly', False)]},
        )
    sii_send_ident = fields.Text(
            string='SII Send Identification',
            copy=False,
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    sii_receipt = fields.Text(
            string='SII Mensaje de recepción',
            copy=False,
            readonly=False,
            states={'Aceptado': [('readonly', False)], 'Rechazado': [('readonly', False)]},
        )
    user_id = fields.Many2one(
            'res.users',
            string="Usuario",
            helps='Usuario que envía el XML',
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    invoice_ids = fields.One2many(
            'account.invoice',
            'sii_xml_request',
            string="Facturas",
            readonly=True,
            states={'draft': [('readonly', False)]},
        )
    sii_barcode = fields.Char(
        copy=False,
        string=_('SII Barcode'),
        help='SII Barcode Name',
        readonly=True,
        states={'draft': [('readonly', False)]}, )
    sii_barcode_img = fields.Binary(
        string=_('SII Barcode Image'),
        help='SII Barcode Image in PDF417 format',
        compute="_get_barcode_img", )

    @api.multi
    def name_get(self):
        result = []
        for r in self:
            name = r.name + " Código Envío: %s" % r.sii_send_ident if r.sii_send_ident else r.name
            result.append((r.id, name))
        return result

    def send_xml(self):
        return_value = {'state': 'NoEnviado'}
        signature_d = self.env.user.get_digital_signature(self.company_id)
        try:
            response = pysiidte.send_xml(
                mode=self.company_id.dte_service_provider,
                signature_d=signature_d,
                company_website=self.company_id.website,
                company_vat=self.company_id.vat,
                file_name=self.name,
                xml_message=self.xml_envio
            )
            return_value.update({'sii_xml_response': response.data})
        except Exception as error:
            _logger.error(error)
            return return_value
        if response.status != 200:
            return return_value
        parse_response = xmltodict.parse(response.data)
        return_value = pysiidte.procesar_recepcion(return_value, parse_response)
        self.write(return_value)
        return return_value

    def get_send_status(self, user_id=False):
        user_id = user_id or self.user_id
        signature_d = user_id.get_digital_signature(self.company_id)
        token = pysiidte.sii_token(self.company_id.dte_service_provider, signature_d['priv_key'], signature_d['cert'])
        response = pysiidte.get_send_status(
            token=token,
            dte_service_provider=self.company_id.dte_service_provider,
            track_id=self.sii_send_ident,
            company_vat=self.company_id.vat,
        )
        result = {"sii_receipt": response}
        resp = xmltodict.parse(response)
        result.update({"state": "Enviado"})
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "EPR":
            result.update({"state": "Aceptado"})
            if resp['SII:RESPUESTA']['SII:RESP_BODY']['RECHAZADOS'] == "1":
                result.update({"state": "Rechazado"})
        elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] in ['RCT', 'RFR']:
            result.update({"state": "Rechazado"})
            _logger.warning(resp)
        self.write(result)

    # TODO should be removed when pysiidte migration is finished
    @staticmethod
    def get_token(user, company):
        signature_d = user.get_digital_signature(company)
        seed = pysiidte.get_seed(company.dte_service_provider)
        return pysiidte.get_token(company.dte_service_provider, signature_d['priv_key'], signature_d['cert'], seed)