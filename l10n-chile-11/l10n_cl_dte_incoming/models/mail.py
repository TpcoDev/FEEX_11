# -*- coding: utf-8 -*-

import base64
import logging
import xmltodict
from datetime import datetime, timedelta
from typing import Any, List

from bs4 import BeautifulSoup as bs
from lxml import etree

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

status_dte = [
    ('no_revisado', 'No Revisado'),
    ('0', 'Conforme'),
    ('1', 'Error de Schema'),
    ('2', 'Error de Firma'),
    ('3', 'RUT Receptor No Corresponde'),
    ('90', 'Archivo Repetido'),
    ('91', 'Archivo Ilegible'),
    ('99', 'Envio Rechazado - Otros'), ]


# class ProcessMails(models.Model):
#     _inherit = "mail.message"
#
#     @api.model
#     def create(self, vals):
#         mail = super(ProcessMails, self).create(vals)
#         if mail.message_type in ['email'] and mail.attachment_ids and 'Acuse de Recibo' not in mail.subject:
#             _logger.info('entra al create con mail.body: %s y attachments: %s' % (mail.body, mail.attachment_ids))
#             dte = False
#             for att in mail.attachment_ids:
#                 if not att.name:
#                     continue
#                 name = att.name.upper()
#                 if att.mimetype in ['text/plain'] and name.find('.XML') > -1:
#                     if not self.env['mail.message.dte'].search([('name', '=', name)]):
#                         dte = {
#                             'mail_id': mail.id,
#                             'name': name, }
#             if dte:
#                 val = self.browse(mail.res_id)
#                 if not val:
#                     val = self.env['mail.message.dte'].create(dte)
#                 val.pre_process()
#                 val.mail_id = mail.id
#         return mail

# class ValidateDTEWizard(models.TransientModel):
#     _name = 'dte.validate.wizard'
#     _inherit = 'dte.validate.wizard'
#     _description = 'SII XML from Provider'


# noinspection PyTypeChecker
class ProcessMail(models.Model):
    _name = 'mail.message.dte'
    _description = 'DTEs Entrantes por Email'
    _inherit = ['mail.thread']
    _order = 'create_date DESC'

    name = fields.Char(
        string="Nombre Envío",
        readonly=True,
    )
    inner_status = fields.Selection(
        [
            ('new', 'New'),
            ('pre_processed', 'Pre Processed'),
            ('processed', 'Processed'),
            ('cancelled', 'Cancelled'),
        ], string='Inner Status', default='new',
    )

    mail_id = fields.Many2one(
        'mail.message',
        string="Email",
        readonly=True,
        ondelete='cascade',
        store=True,
    )
    email_from = fields.Char(related='mail_id.email_from', string='Email From')
    document_ids = fields.One2many(
        'mail.message.dte.document',
        'dte_id',
        string="Documents",
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        readonly=True,
    )
    rut_issuer = fields.Char(
        'RUT Issuer'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string="Partner",
        domain=[('supplier', '=', True)],
        # ('pointless_main_id_number', '=', rut_issuer)],
        # readonly=True,
    )
    reception_response_number = fields.Char("ID Resp. Automática")
    origin_type = fields.Selection(
        [
            ('', 'Not clasified'),
            ('outgoing_customer_document', 'Outgoing to Customer'),
            ('outgoing_acknowledge', 'Outgoing Acknowledge'),
            ('outgoing_commercial_accept', 'Outgoing Commercial Accept'),
            ('outgoing_merchandise_receive', 'Outgoing Merchandise Receive'),
            ('outgoing_supplier_document', 'Outgoing Supplier Document'),  # creada por DB para debug (para ver si el tipificado de esto hace sentido)
            ('outgoing_reject', 'Outgoing Reject'),
            ('incoming_supplier_document', 'Incoming Doc From Supplier'),
            ('incoming_customer_acknowledge', 'Acknowledge Incoming from Customer'),
            ('incoming_customer_commercial_accept', 'Commercial Accept Incoming from Customer'),
            ('incoming_customer_merchandise_receive', 'Merchandise Receive Incoming from Customer'),
            ('incoming_tax_ent_result_reject', 'Incoming SII Reject State'),
            ('incoming_tax_ent_result_accept', 'Incoming SII Accept State'),

        ], string='Origin / Type of message', default='',
        help='Type of message and its origin'
    )

    @staticmethod
    def _read_xml(xml_document, mode='etree'):
        # funcion usada para preproceso
        xml = base64.b64decode(xml_document).decode('ISO-8859-1').replace(
                '<?xml version="1.0" encoding="ISO-8859-1"?>', '').replace(
                '<?xml version="1.0" encoding="ISO-8859-1" ?>', '')
        if mode == "etree":
            parser = etree.XMLParser(remove_blank_text=True)
            return etree.fromstring(xml, parser=parser)
        if mode == "parse":
            envio = xmltodict.parse(xml)
            if 'EnvioBOLETA' in envio:
                return envio['EnvioBOLETA']
            elif 'EnvioDTE' in envio:
                return envio['EnvioDTE']
            else:
                return envio
        if mode == "soup":
            return bs(xml, 'xml')
        return xml

    def _get_origin_type(self, xml_file):
        _logger.info('xml file: %s' % xml_file)
        bsoup = bs(xml_file, 'xml')
        # _logger.info('objeto soup: %s' % bsoup)
        try:
            tag = bsoup.RESULTADO_ENVIO.text
            try:
                if int(bsoup.RECHAZO.text) > 1:
                    return 'incoming_tax_ent_result_reject'
                else:
                    return 'incoming_tax_ent_result_accept'
            except AttributeError:
                _logger.info('servicio: aceptacion (a comprobar)')
                return 'incoming_tax_ent_result_accept'
        except AttributeError:
            try:
                if bsoup.RUTEmisor.text == self.env.user.company_id.main_id_number.replace('.', ''):
                    return_value = 'outgoing_'
                else:
                    return_value = 'incoming_'
            except AttributeError:
                _logger.info('NO hay RUT emisor! ##### %s' % bsoup)
                return ''
            tag = ''
            try:
                tag = bsoup.DTE
                _logger.info('customer document. tag: %s' % tag)
                return return_value + 'supplier_document'
            except AttributeError:
                try:
                    tag = bsoup.RecepcionDTE.text
                    _logger.info('customer document. tag: %s' % tag)
                    if bsoup.EstadoRecepEnv.text == '0':
                        return return_value + 'acknowledge'
                except AttributeError:
                    try:
                        if bsoup.EstadoDTE.text == '0':
                            _logger.info('aceptacion comercial: %s' % tag)
                            return return_value + 'commercial_accept'
                        else:
                            _logger.info('rechazo comercial: %s' % tag)
                            return return_value + 'reject'
                            pass
                    except AttributeError:
                        try:
                            tag = bsoup.Declaracion.text
                            _logger.info('declaracion de recepcion de merc. tag: %s' % tag)
                            return return_value + 'merchandise_receive'
                        except AttributeError:
                            pass
            return ''

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        if custom_values is None:
            custom_values = {}
        defaults = {
            'origin_type':  self._get_origin_type(msg_dict.get('attachments')[0][1]),
            }
        defaults.update(custom_values)
        return super(ProcessMail, self).message_new(msg_dict, custom_values=defaults)

    #-@api.model
    #-def create(self, vals):
    #-    message_dte = super(ProcessMail, self).create(vals)
    #-    mail_obj = self.env['mail.message'].sudo()
    #-    mail_id = mail_obj.search(
    #-        [
    #-            ('res_id', '=', message_dte.id),
    #-            ('model', '=', 'mail.message.dte'), ], )
    #-    _logger.info("\n\n\n mail_obj: \n\n\n" % mail_obj)
    #-    message_dte.mail_id = mail_id.id
    #-    message_dte.process_message()
    #-    return message_dte

    def sender_data(self):
        # Preproceso
        # this is intended for a previous process, in order to check the basic sender data
        # and the company
        mail_obj = self.env['mail.message'].sudo()
        company_obj = self.env['res.company'].sudo()
        partner_obj = self.env['res.partner']
        for record in self:
            mail_id = mail_obj.search(
                [('res_id', '=', record.id),
                 ('model', '=', 'mail.message.dte'),
                 ('author_id', '=', False), ], )
            record.mail_id = mail_id.id
            for att in record.sudo().mail_id.attachment_ids:
                if not att.name:
                    _logger.info('No attachment found, att: %s' % att)
                    continue
                _logger.info('Attachment found, att: %s' % att)
                name = att.name.upper()
                if att.mimetype in ['text/plain'] and name.find('.XML') > -1:
                    read_xml = self._read_xml(att.datas, 'soup')
                    _logger.info('read xml: %s' % read_xml)
                    if True:  # try:
                        company_id = company_obj.search([
                            ('pointless_main_id_number', '=', read_xml.RUTRecep.text)])
                        record.company_id = company_id.id
                        record.origin_type = 'incoming_supplier_document'
                        _logger.info('Record: incoming supplier doc')
                        record.rut_issuer = read_xml.RUTEmisor.text
                        partner_ids = partner_obj.search([
                            ('pointless_main_id_number', '=', read_xml.RUTEmisor.text)], order='is_company desc')
                        if len(partner_ids) > 0:
                            for partner_id in partner_ids:
                                record.partner_id = partner_id.id
                        else:
                            _logger.info('Record: partner no encontrado: %s' % partner_ids)
                        record.inner_status = 'pre_processed'
                        continue
                    else:  # except AttributeError:
                        _logger.info('mail.py (250) no se encuentra el receptor (EnvioDTE)')
                    try:
                        company_id = company_obj.search([
                                ('pointless_main_id_number', '=', read_xml.RESULTADO_ENVIO.RUTEMISOR.text)])
                        record.company_id = company_id.id
                        record.origin_type = 'incoming_customer_acknowledge'
                        _logger.info('Record: acknowledge')
                        record.inner_status = 'pre_processed'
                    except AttributeError:
                        _logger.info('mail.py (275): no se encuentra rut emisor (resultado envio)')

    def pre_process(self):
        self.process_message(pre=True)

    @api.multi
    def process_message(self, pre=False, option=False):
        created = []
        for record in self:
            for att in record.sudo().mail_id.attachment_ids:
                if not att.name:
                    _logger.info('No attachment found, att: %s' % att)
                    continue
                name = att.name.upper()
                if att.mimetype in ['text/plain'] and name.find('.XML') > -1:
                    vals = {
                        'xml_file': att.datas,
                        'filename': att.name,
                        # 'pre_process': pre,
                        'dte_id': record.id,
                        'option': option, }
                    val = self.env['sii.dte.upload_xml.wizard'].create(vals)
                    record.inner_status = 'processed'
                    created.extend(val.confirm(ret=True))
        xml_id = 'l10n_cl_dte_incoming.action_dte_process'
        result = self.env.ref('%s' % xml_id).read()[0]
        if created:
            domain = eval(result['domain'])
            domain.append(('id', 'in', created))
            result['domain'] = domain
        return result


# noinspection PyTypeChecker
class ProcessMailsDocument(models.Model):
    _name = 'mail.message.dte.document'
    _inherit = ['mail.thread']

    _order = 'create_date DESC'

    dte_id = fields.Many2one(
        'mail.message.dte',
        string="DTE",
        readonly=True,
        ondelete='cascade',
    )
    new_partner = fields.Char(
        string="Proveedor Nuevo",
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Proveedor',
        domain=[('supplier', '=', True)],
    )
    date = fields.Date(
        string="Fecha Emisión",
        readonly=True,
    )
    number = fields.Char(
        string='Folio',
        readonly=True,
    )
    document_type_id = fields.Many2one(
        'account.document.type',
        string="Tipo de Documento",
        readonly=True,
    )
    amount = fields.Monetary(
        string="Monto",
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Moneda",
        readonly=True,
        default=lambda self: self.env.user.company_id.currency_id,
    )
    invoice_line_ids = fields.One2many(
        'mail.message.dte.document.line',
        'document_id',
        string="Líneas del Documento",
    )
    company_id = fields.Many2one(
        'res.company',
        string="Compañía",
        readonly=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Recibido'),
            ('accepted', 'Aceptado'),
            ('rejected', 'Rechazado'),
        ],
        default='draft',
    )
    invoice_id = fields.Many2one(
        'account.invoice',
        string="Factura",
        readonly=True,
    )
    xml = fields.Text(
        string="XML Documento",
        readonly=True,
    )
    purchase_to_done = fields.Many2many(
        'purchase.order',
        string="Ordenes de Compra a validar",
        domain=[('state', 'not in', ['accepted', 'rejected'])],
    )

    @api.model
    def auto_accept_documents(self):
        for old_invoice in self.search(
                [([('create_date', '<', datetime.strftime(datetime.now() - timedelta(days=8), '%Y-%m-%d'))])]):
            old_invoice.accept_document()
        """
        self.env.cr.execute(
            '''
            select
                id
            from
                mail_message_dte_document
            where
                create_date + interval '8 days' < now()
                and
                state = 'draft'
            '''
        )
        
        for d in self.browse([line.get('id') for line in self.env.cr.dictfetchall()]):
            d.accept_document()
        """

    @api.multi
    def accept_document(self):
        created = []  # type: List[Any]
        for r in self:
            if not r.xml:
                _logger.info('(402) No se encuentra un archivo XML vinculado a este registro.')
            vals = {
                'xml_file': r.xml.encode('ISO-8859-1'),
                'filename': r.dte_id.name,
                'pre_process': False,
                'document_id': r.id,
                'option': 'accept'
            }
            val = self.env['sii.dte.upload_xml.wizard'].create(vals)
            _logger.info('\n\n\nVALS: %s\n\n\n' % vals)
            _logger.info('\n\n\nVAL: %s\n\n\n' % val)
            created.extend(val.confirm(mail_message_dte_id=r.dte_id, ret=True))
            r.state = 'accepted'
        xml_id = 'account.action_invoice_tree2'
        result = self.env.ref('%s' % xml_id).read()[0]
        if created:
            domain = eval(result['domain'])
            domain.append(('id', 'in', created))
            result['domain'] = domain
        return result

    @api.multi
    def reject_document(self):
        for r in self:
            r.state = 'rejected'

        wiz_accept = self.env['dte.validate.wizard'].create(
            {
                'action': 'validate',
                'option': 'reject',
            }
        )
        wiz_accept.do_reject(self)


class ProcessMailsDocumentLines(models.Model):
    _name = 'mail.message.dte.document.line'

    document_id = fields.Many2one(
        'mail.message.dte.document',
        string="Documento",
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product',
        string="Producto",
    )
    new_product = fields.Char(
        string='Nuevo Producto',
        readonly=True,
    )
    description = fields.Char(
        string='Descripción',
        readonly=True,
    )
    product_description = fields.Char(
        string='Descripción Producto',
        readonly=True,
    )
    quantity = fields.Float(
        string="Cantidad",
        readonly=True,
    )
    price_unit = fields.Monetary(
        string="Precio Unitario",
        readonly=True,
    )
    price_subtotal = fields.Monetary(
        string="Total",
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Moneda",
        readonly=True,
        default=lambda self: self.env.user.company_id.currency_id,
    )
