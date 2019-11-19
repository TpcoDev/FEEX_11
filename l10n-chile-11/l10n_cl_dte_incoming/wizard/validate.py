# -*- coding: utf-8 -*-
import base64
import collections
import logging
import pysiidte

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

try:
    import dicttoxml

except:
    _logger.warning('No se ha podido cargar dicttoxml')

try:
    import xmltodict
except:
    _logger.warning('No se ha podido cargar xmltodict')

dicttoxml.LOG.setLevel(logging.ERROR)

BC = '''-----BEGIN CERTIFICATE-----\n'''
EC = '''\n-----END CERTIFICATE-----\n'''


class ValidateDTEWizard(models.TransientModel):
    _name = 'dte.validate.wizard'
    _description = 'SII XML from Provider'

    def _get_docs(self):
        context = dict(self._context or {})
        incoming_reject = context.get('incoming_reject', False) or []
        if not incoming_reject:
            active_ids = context.get('active_ids', []) or []
            return [(6, 0, active_ids)]

    action = fields.Selection(
        [
            ('receipt', 'Recibo de mercaderías'),
            ('validate', 'Aprobar comercialmente'),
        ],
        string="Acción",
        default="validate",
    )
    invoice_ids = fields.Many2many(
        'account.invoice',
        string="Facturas",
        default=_get_docs,
    )
    option = fields.Selection(
        [
            ('accept', 'Aceptar'),
            ('reject', 'Rechazar'),
        ],
        string="Opción",
    )

    @api.multi
    def confirm(self):
        # if self.action == 'validate':
        self.do_receipt()
        self.do_validate_comercial()
        #   _logger.info("ee")

    def send_message(self, message="RCT"):
        id = self.document_id.number or self.inv.ref
        document_type = self.document_id.document_type_id or self.inv.document_type_id.code

    def _create_attachment(self, xml, name, id=False, model='account.invoice'):
        data = base64.b64encode(xml.encode('ISO-8859-1'))
        filename = (name + '.xml').replace(' ','')
        url_path = '/web/binary/download_document?model=' + model + '\
    &field=sii_xml_request&id=%s&filename=%s' % (id, filename)
        att = self.env['ir.attachment'].search(
            [
                ('name', '=', filename),
                ('res_id', '=', id),
                ('res_model', '=', model)
            ],
            limit=1,
        )
        if att:
            return att
        values = dict(
            name=filename, datas_fname=filename, url=url_path, res_model=model, res_id=id, type='binary', datas=data)
        att = self.env['ir.attachment'].create(values)
        return att

    def _caratula_respuesta(self, RutResponde, RutRecibe, IdRespuesta="1", NroDetalles=0):
        caratula = collections.OrderedDict()
        caratula['RutResponde'] = RutResponde
        caratula['RutRecibe'] = RutRecibe
        caratula['IdRespuesta'] = IdRespuesta
        caratula['NroDetalles'] = NroDetalles
        caratula['NmbContacto'] = self.env.user.partner_id.name
        caratula['FonoContacto'] = self.env.user.partner_id.phone
        caratula['MailContacto'] = self.env.user.partner_id.email
        caratula['TmstFirmaResp'] = pysiidte.time_stamp()
        return caratula

    def _resultado(self, TipoDTE, Folio, FchEmis, RUTEmisor, RUTRecep, MntTotal, IdRespuesta):
        res = collections.OrderedDict()
        res['TipoDTE'] = TipoDTE
        res['Folio'] = Folio
        res['FchEmis'] = FchEmis
        res['RUTEmisor'] = RUTEmisor
        res['RUTRecep'] = RUTRecep
        res['MntTotal'] = MntTotal
        res['CodEnvio'] = str(IdRespuesta)
        res['EstadoDTE'] = 0
        res['EstadoDTEGlosa'] = 'DTE Aceptado OK'
        if self.option == "reject":
            res['EstadoDTE'] = 2
            res['EstadoDTEGlosa'] = 'DTE Rechazado'
            res['CodRchDsc'] = "-1"  # User Reject
        return {'ResultadoDTE': res}

    def _dte_result(self, Caratula, resultado):
        resp='''<?xml version="1.0" encoding="ISO-8859-1"?>
<RespuestaDTE version="1.0" xmlns="http://www.sii.cl/SiiDte" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sii.cl/SiiDte RespuestaEnvioDTE_v10.xsd" >
    <Resultado ID="Odoo_resp">
        <Caratula version="1.0">
            {0}
        </Caratula>
            {1}
    </Resultado>
</RespuestaDTE>'''.format(
            Caratula,
            resultado,
        )
        return resp

    def do_reject(self, document_ids):
        inv_obj = self.env['account.invoice']
        id_seq = self.env.ref('l10n_cl_dte.response_sequence').id
        IdRespuesta = self.env['ir.sequence'].browse(id_seq).next_by_id()
        NroDetalles = 1
        for doc in document_ids:
            try:
                signature_d = self.env.user.get_digital_signature(doc.company_id)
            except:
                return False
            #     raise UserError(_('''There is no Signer Person with an \
            # authorized signature for you in the system. Please make sure that \
            # 'user_signature_key' module has been installed and enable a digital \
            # signature, for you or make the signer to authorize you to use his \
            # signature.'''))
            certp = signature_d['cert'].replace(
                BC, '').replace(EC, '').replace('\n', '')
            xml = xmltodict.parse(doc.xml)['DTE']['Documento']
            dte = self._resultado(
                TipoDTE=xml['Encabezado']['IdDoc']['TipoDTE'],
                Folio=xml['Encabezado']['IdDoc']['Folio'],
                FchEmis=xml['Encabezado']['IdDoc']['FchEmis'],
                RUTEmisor=xml['Encabezado']['Emisor']['RUTEmisor'],
                RUTRecep=xml['Encabezado']['Receptor']['RUTRecep'],
                MntTotal=xml['Encabezado']['Totales']['MntTotal'],
                IdRespuesta=IdRespuesta,
            )
            ResultadoDTE = dicttoxml.dicttoxml(
                dte,
                root=False,
                attr_type=False,
            ).decode().replace('<item>', '\n').replace('</item>', '\n')
            RutRecibe = xml['Encabezado']['Emisor']['RUTEmisor']
            caratula_validacion_comercial = self._caratula_respuesta(
                xml['Encabezado']['Receptor']['RUTRecep'],
                RutRecibe,
                IdRespuesta,
                NroDetalles)
            caratula = dicttoxml.dicttoxml(
                caratula_validacion_comercial,
                root=False,
                attr_type=False).decode().replace('<item>','\n').replace('</item>','\n')
            resp = self._dte_result(
                caratula,
                ResultadoDTE,
            )
            respuesta = '<?xml version="1.0" encoding="ISO-8859-1"?>\n' + inv_obj.sign_full_xml(
                resp.replace('<?xml version="1.0" encoding="ISO-8859-1"?>\n', ''),
                signature_d['priv_key'],
                certp,
                'Odoo_resp',
                'env_resp', )
            att = self._create_attachment(
                respuesta,
                'rechazo_comercial_' + str(IdRespuesta),
                id=doc.id,
                model="mail.message.dte.document", )
            #partners = doc.partner_id.ids
            #if not doc.partner_id:
            #    if att:
            #        values = {
            #            'res_id': doc.id,
            #            'email_from': doc.company_id.dte_email,
            #            'email_to': doc.dte_id.sudo().mail_id.email_from,
            #            'auto_delete': False,
            #            'model': "mail.message.dte.document",
            #            'body': 'XML de Respuesta Envío, Estado: %s , Glosa: %s ' % (
            #                recep['EstadoRecepEnv'], recep['RecepEnvGlosa']),
            #            'subject': 'XML de Respuesta Envío',
            #            'attachment_ids': att.ids,
            #        }
            #        send_mail = self.env['mail.mail'].create(values)
            #        send_mail.send()
            #doc.message_post(
            #    body='XML de Rechazo Comercial, Estado: %s, Glosa: %s' % (
            #        dte['ResultadoDTE']['EstadoDTE'], dte['ResultadoDTE']['EstadoDTEGlosa']),
            #    subject='XML de Validación Comercial',
            #    partner_ids=partners,
            #    attachment_ids=[att.id],
            #    message_type='comment',
            #    subtype='mt_comment', )
            template = self.env.ref('l10n_cl_dte_incoming.email_template_commercial_reject', False)
            mail_id = template.send_mail(
                doc.dte_id.id,
                force_send=True,
                email_values={'attachment_ids': att.ids})
            doc.dte_id.reception_response_number = IdRespuesta

            context = dict(self._context or {})
            incoming_reject = context.get('incoming_reject', False) or []
            if not incoming_reject:
                inv_obj.set_dte_claim(
                    rut_emisor = xml['Encabezado']['Emisor']['RUTEmisor'],
                    company_id=doc.company_id,
                    sii_document_number=doc.number,
                    document_type_id=doc.document_type_id,
                    claim='RCD', )

    def do_validate_comercial(self):
        id_seq = self.env.ref('l10n_cl_dte.response_sequence').id
        IdRespuesta = self.env['ir.sequence'].browse(id_seq).next_by_id()
        NroDetalles = 1
        for inv in self.invoice_ids:
            if inv.claim in ['ACD', 'RCD']:
                continue
            try:
                signature_d = self.env.user.get_digital_signature(inv.company_id)
            except:
                return False
            #     raise UserError(_('''There is no Signer Person with an \
            # authorized signature for you in the system. Please make sure that \
            # 'user_signature_key' module has been installed and enable a digital \
            # signature, for you or make the signer to authorize you to use his \
            # signature.'''))
            certp = signature_d['cert'].replace(
                BC, '').replace(EC, '').replace('\n', '')
            dte = self._resultado(
                TipoDTE=inv.document_type_id.code,
                Folio=inv.document_number,
                FchEmis=inv.date_invoice,
                RUTEmisor=inv.format_vat(inv.partner_id.main_id_number),
                RUTRecep=inv.format_vat(inv.company_id.main_id_number),
                MntTotal=int(round(inv.amount_total, 0)),
                IdRespuesta=IdRespuesta,
            )
            ResultadoDTE = dicttoxml.dicttoxml(
                dte,
                root=False,
                attr_type=False,
            ).decode().replace('<item>','\n').replace('</item>','\n')
            RutRecibe = inv.format_vat(inv.partner_id.main_id_number)
            caratula_validacion_comercial = self._caratula_respuesta(
                inv.format_vat(inv.company_id.main_id_number),
                RutRecibe,
                IdRespuesta,
                NroDetalles,
            )
            caratula = dicttoxml.dicttoxml(
                caratula_validacion_comercial,
                root=False,
                attr_type=False,
            ).decode().replace('<item>','\n').replace('</item>','\n')
            resp = self._dte_result(
                caratula,
                ResultadoDTE,
            )
            respuesta = '<?xml version="1.0" encoding="ISO-8859-1"?>\n' + inv.sign_full_xml(
                resp.replace('<?xml version="1.0" encoding="ISO-8859-1"?>\n', ''),
                signature_d['priv_key'],
                certp,
                'Odoo_resp',
                'env_resp',
            )
            inv.sii_message = respuesta
            att = self._create_attachment(
                respuesta,
                'validacion_comercial_' + str(IdRespuesta),
            )
            template = self.env.ref('l10n_cl_dte_incoming.email_template_receipt_commercial_accept', False)
            mail_id = template.send_mail(
                inv.id,
                force_send=True,
                email_values={'attachment_ids': att.ids})
            inv.dte_reception_status = 'validate'
            
            inv.claim = 'ACD'
            try:
                inv.set_dte_claim(
                    rut_emisor=inv.format_vat(inv.partner_id.main_id_number),
                )
            except:
                _logger.warning("@TODO crear código que encole la respuesta")

    def _recep(self, inv, RutFirma):
        # raise UserError('document invoice: %s' % inv.document_type_id.code)
        receipt = collections.OrderedDict()
        receipt['TipoDoc'] = inv.document_type_id.code
        receipt['Folio'] = int(inv.document_number)
        receipt['FchEmis'] = inv.date_invoice
        receipt['RUTEmisor'] = inv.format_vat(inv.partner_id.main_id_number)
        receipt['RUTRecep'] = inv.format_vat(inv.company_id.main_id_number)
        receipt['MntTotal'] = int(round(inv.amount_total))
        receipt['Recinto'] = inv.company_id.street
        receipt['RutFirma'] = RutFirma
        receipt['Declaracion'] = 'El acuse de recibo que se declara en este acto, de acuerdo a lo dispuesto \
en la letra b) del Art. 4, y la letra c) del Art. 5 de la Ley 19.983, acredita que la entrega de mercaderias o \
servicio(s) prestado(s) ha(n) sido recibido(s).'
        receipt['TmstFirmaRecibo'] = pysiidte.time_stamp()
        return receipt

    def _envio_recep(self, caratula, recep):
        xml = '''<?xml version="1.0" encoding="ISO-8859-1"?>
<EnvioRecibos xmlns='http://www.sii.cl/SiiDte' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance' \
xsi:schemaLocation='http://www.sii.cl/SiiDte EnvioRecibos_v10.xsd' version="1.0">
    <SetRecibos ID="SetDteRecibidos">
        <Caratula version="1.0">
        {0}
        </Caratula>
        {1}
    </SetRecibos>
</EnvioRecibos>'''.format(caratula, recep)
        return xml

    def _caratula_recep(self, RutResponde, RutRecibe):
        caratula = collections.OrderedDict()
        caratula['RutResponde'] = RutResponde
        caratula['RutRecibe'] = RutRecibe
        caratula['NmbContacto'] = self.env.user.partner_id.name
        caratula['FonoContacto'] = self.env.user.partner_id.phone
        caratula['MailContacto'] = self.env.user.partner_id.email
        caratula['TmstFirmaEnv'] = pysiidte.time_stamp()
        return caratula

    @api.multi
    def do_receipt(self):
        message = ""
        for inv in self.invoice_ids:
            if inv.claim in ['ACD', 'RCD']:
                continue
            try:
                signature_d = self.env.user.get_digital_signature(inv.company_id)
            except:
                return False
            #     raise UserError(_('''There is no Signer Person with an \
            # authorized signature for you in the system. Please make sure that \
            # 'user_signature_key' module has been installed and enable a digital \
            # signature, for you or make the signer to authorize you to use his \
            # signature.'''))
            certp = signature_d['cert'].replace(
                BC,
                '',
            ).replace(EC, '').replace('\n', '')
            dict_recept = self._recep(
                inv,
                signature_d['subject_serial_number'],
            )
            id = "T" + str(inv.document_type_id.code) + "F" + str(inv.document_number)
            doc = '''
<Recibo version="1.0" xmlns="http://www.sii.cl/SiiDte" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte Recibos_v10.xsd" >
    <DocumentoRecibo ID="{0}" >
    {1}
    </DocumentoRecibo>
</Recibo>
            '''.format(
                id,
                dicttoxml.dicttoxml(
                    dict_recept,
                    root=False,
                    attr_type=False,
                ).decode(),
            )
            message += '\n ' + str(dict_recept['Folio']) + ' ' + dict_recept['Declaracion']
            receipt = '<?xml version="1.0" encoding="ISO-8859-1"?>\n' + inv.sign_full_xml(
                doc.replace('<?xml version="1.0" encoding="ISO-8859-1"?>\n', ''),
                signature_d['priv_key'], certp, 'Recibo', 'recep')
            RutRecibe = inv.format_vat(inv.partner_id.main_id_number)
            dict_caratula = self._caratula_recep(
                inv.format_vat(inv.company_id.main_id_number),
                RutRecibe,
            )
            caratula = dicttoxml.dicttoxml(
                dict_caratula,
                root=False,
                attr_type=False,
            ).decode()
            envio_dte = self._envio_recep(
                caratula,
                receipt,
            )
            envio_dte = '<?xml version="1.0" encoding="ISO-8859-1"?>\n' + inv.sign_full_xml(
                envio_dte.replace('<?xml version="1.0" encoding="ISO-8859-1"?>\n', ''),
                signature_d['priv_key'],
                certp,
                'SetDteRecibidos',
                'env_recep',
            )
            id_seq = self.env.ref('l10n_cl_dte.response_sequence').id
            IdRespuesta = self.env['ir.sequence'].browse(id_seq).next_by_id()
            att = self._create_attachment(
                envio_dte,
                'recepcion_mercaderias_' + str(IdRespuesta),
                )
            template = self.env.ref('l10n_cl_dte_incoming.email_template_receipt_of_goods', False)
            mail_id = template.send_mail(
                inv.id,
                force_send=True,
                email_values={'attachment_ids': att.ids})
            inv.dte_reception_status = 'mercaderias'
            inv.claim = 'ERM'
            try:
                inv.set_dte_claim(
                    rut_emisor=inv.format_vat(inv.partner_id.main_id_number),
                )
            except:
                _logger.warning("(mejora:) crear código que encole la respuesta")
