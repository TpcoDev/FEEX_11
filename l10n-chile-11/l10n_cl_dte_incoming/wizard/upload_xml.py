# -*- coding: utf-8 -*-
import base64
import collections
import logging
import re
import pysiidte

from lxml import etree

import dicttoxml
import xmltodict
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

dicttoxml.LOG.setLevel(logging.ERROR)
try:
    from io import BytesIO
except:
    _logger.warning("no se ha cargado io")

BC = '''-----BEGIN CERTIFICATE-----\n'''
EC = '''\n-----END CERTIFICATE-----\n'''

regex = re.compile('([a-z0-9!#$%&\'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&\'*+\/=?^_`'
                   '{|}~-]+)*(@|\sat\s)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|'
                   '\sdot\s))+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)')


class UploadXMLWizard(models.TransientModel):
    _name = 'sii.dte.upload_xml.wizard'
    _description = 'SII XML from Supplier'

    @staticmethod
    def get_emails(s):
        if s == False:
            return False
        _logger.info('get_emails: %s' % s)
        return (email[0] for email in re.findall(regex, s) if not email[0].startswith('//'))

    def _clean_email(self, s):
        clean_email = False
        for email in self.get_emails(s):
            clean_email = email
            break
        return clean_email

    def gather_partner_from_email(self, email_from):
        partner_obj = self.env['res.partner']
        if not email_from:
            email_from = self.env.user.company_id.partner_id.email
            if not email_from:
                raise UserError('Debe definir como mínimo un email para su compañía')
            _logger.info('No se encuentra email para responder. Se usará el email de la compañía')
        _logger.info('\n\n email_from: %s\n\n' % email_from)
        clean_email = self._clean_email(email_from)
        _logger.info('\n\n clean_email: %s\n\n' % clean_email)
        try:
            partner_id = partner_obj.search([
                '|', ('dte_email', '=', clean_email),
                ('email', '=', clean_email)])
        except ValueError:
            _logger.info('\n\n no se encuentra partner con el email: %s\n\n' % clean_email)
            partner_id = False
        return clean_email, partner_id

    action = fields.Selection(
        [
            ('create_po', 'Crear Orden de Pedido y Factura'),
            ('create', 'Crear Solamente Factura'),
        ],
        string="Acción",
        default="create",
    )
    xml_file = fields.Binary(
        string='XML File',
        filters='*.xml',
        store=True,
        help='Upload the XML File in this holder',
    )
    filename = fields.Char(
        string='File Name',
    )
    pre_process = fields.Boolean(
        default=True,
    )
    dte_id = fields.Many2one(
        'mail.message.dte',
        string="DTE",
    )
    document_id = fields.Many2one(
        'mail.message.dte.document',
        string="Documento",
    )
    option = fields.Selection(
        [
            ('upload', 'Solo Subir'),
            ('accept', 'Aceptar'),
            ('reject', 'Rechazar'),
        ],
        string="Opción",
    )
    response = fields.Text('Response', readonly=True)

    @api.multi
    def confirm(self, mail_message_dte_id=False, ret=False):
        # context = dict(self._context or {})
        # active_id = context.get('active_id', []) or []
        created = []
        _logger.info('\n\n\ ANTES DE CREAR EL DTE ID dte_id = %s \n\n' % self.dte_id)
        if not self.dte_id:
            _logger.info(
                '\n\n\ ENTRA EN EL QUE NO HAY dte_id = %s, filename: %s \n\n\n' % (
                    self.dte_id, self.filename))
            dte_id = self.env['mail.message.dte'].search(
                [
                    ('name', '=', self.filename),
                ]
            )
            if len(dte_id) > 1:
                dte_id = mail_message_dte_id
            if not dte_id:
                _logger.info('\n\n\n busca y no lo encuentra (lo crea) \n\n\n')
                dte = {
                    'name': self.filename,
                }
                dte_id = self.env['mail.message.dte'].create(dte)
            self.dte_id = dte_id
        if self.pre_process or self.action == 'upload':
            created = self.do_create_pre()
            xml_id = 'l10n_cl_dte_incoming.action_dte_process'
        elif self.option == 'reject':
            self.do_reject()
            return
        elif self.action == 'create':
            created = self.do_create_inv()
            xml_id = 'account.action_invoice_tree2'
        if self.action == 'create_po':
            self.do_create_po()
            xml_id = 'purchase.purchase_order_tree'
        if ret:
            return created
        result = self.env.ref('%s' % xml_id).read()[0]
        if created:
            domain = eval(result['domain'])
            domain.append(('id', 'in', created))
            result['domain'] = domain
        return result

    def format_rut(self, RUTEmisor=None):
        rut = RUTEmisor.replace('.', '')
        # rut = RUTEmisor.replace('-', '')
        # if int(rut[:-1]) < 10000000:
        #     rut = '0' + str(int(rut))
        # rut = 'CL' + rut
        return rut

    def search_partner_by_rut(self, rut):
        domain = [
            ('active', '=', True),
            ('parent_id', '=', False),
            ('main_id_number', '=', self.format_rut(rut)),
        ]
        partner_id = self.env['res.partner'].search(domain)

    def _read_xml(self, mode="text"):
        if self.document_id:
            xml = self.document_id.xml
        elif self.xml_file:
            xml = base64.b64decode(self.xml_file).decode('ISO-8859-1').replace(
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
        return xml

    def _check_digest_caratula(self):
        xml = etree.fromstring(self._read_xml(False))
        string = etree.tostring(xml[0])
        mess = etree.tostring(etree.fromstring(string), method="c14n")
        # our = base64.b64encode(inv_obj.digest(mess))
        our = base64.b64encode(pysiidte.digest(mess))
        # if our != xml.find("{http://www.w3.org/2000/09/xmldsig#}Signature/{http://www.w3.org/2000/09/\
        # xmldsig#}SignedInfo/{http://www.w3.org/2000/09/xmldsig#}Reference/{http://www.w3.org/2000/09/xmldsig#}\
        # DigestValue").text:
        #    return 2, 'Envio Rechazado - Error de Firma'
        return 0, 'Envio Ok'

    def _check_digest_dte(self, dte):
        xml = self._read_xml("etree")
        envio = xml.find("{http://www.sii.cl/SiiDte}SetDTE")
        # "{http://www.w3.org/2000/09/xmldsig#}Signature/{http://www.w3.org/2000/09/xmldsig#}SignedInfo/\
        # {http://www.w3.org/2000/09/xmldsig#}Reference/{http://www.w3.org/2000/09/xmldsig#}DigestValue").text
        for e in envio.findall("{http://www.sii.cl/SiiDte}DTE"):
            string = etree.tostring(e.find("{http://www.sii.cl/SiiDte}Documento"))  # doc
            mess = etree.tostring(etree.fromstring(string), method="c14n").decode('iso-8859-1').replace(
                ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"','').encode('iso-8859-1')
            # el replace es necesario debido a que python lo agrega solo
            # our = base64.b64encode(self.env['account.invoice'].digest(mess))
            our = base64.b64encode(pysiidte.digest(mess))
            their = e.find("{http://www.w3.org/2000/09/xmldsig#}Signature/{http://www.w3.org/2000/09/xmldsig#}\
SignedInfo/{http://www.w3.org/2000/09/xmldsig#}Reference/{http://www.w3.org/2000/09/xmldsig#}DigestValue").text
            if our != their:
                _logger.warning('DTE No Recibido - Error de Firma: our = %s their=%s' % (our, their))
                #return 1, 'DTE No Recibido - Error de Firma'
        return 0, 'DTE Recibido OK'

    def _validate_caratula(self, cara):
        try:
            self.env['account.invoice'].xml_validator(
                self._read_xml(False),
                'env',
            )
        except:
               return 1, 'Envio Rechazado - Error de Schema'
        self.dte_id.company_id = self.env['res.company'].search([
                ('main_id_number', '=', self.format_rut(cara['RutReceptor']))
            ])
        if not self.dte_id.company_id:
            return 3, 'Rut no corresponde a nuestra empresa'
        partner_id = self.env['res.partner'].search(
            [
                ('active', '=', True),
                ('parent_id', '=', False),
                ('main_id_number', '=', self.format_rut(cara['RutEmisor']))
            ]
        )
        # if not partner_id :
        #     return 2, 'Rut no coincide con los registros'
        # for SubTotDTE in cara['SubTotDTE']:
        #    document_type = self.env['account.document.type'].search([('code','=', str(SubTotDTE['TipoDTE']))])
        #    if not document_type:
        #        return  99, 'Tipo de documento desconocido'
        return 0, 'Envío Ok'

    def _validar(self, doc):
        cara, glosa = self._validate_caratula(doc[0][0]['Caratula'])
        return cara, glosa

    def _validate_dte(self, doc):
        res = collections.OrderedDict()
        res['TipoDTE'] = doc['Encabezado']['IdDoc']['TipoDTE']
        res['Folio'] = doc['Encabezado']['IdDoc']['Folio']
        res['FchEmis'] = doc['Encabezado']['IdDoc']['FchEmis']
        res['RUTEmisor'] = doc['Encabezado']['Emisor']['RUTEmisor']
        res['RUTRecep'] = doc['Encabezado']['Receptor']['RUTRecep']
        res['MntTotal'] = doc['Encabezado']['Totales']['MntTotal']
        partner_id = self.env['res.partner'].search([
            ('active', '=', True),
            ('parent_id', '=', False),
            ('main_id_number', '=', self.format_rut(doc['Encabezado']['Emisor']['RUTEmisor']))
        ], limit=1)
        document_type = self.env['account.document.type'].search(
            [('code', '=', str(doc['Encabezado']['IdDoc']['TipoDTE']))])
        res['EstadoRecepDTE'] = 0
        res['RecepDTEGlosa'] = 'DTE Recibido OK'
        res['EstadoRecepDTE'], res['RecepDTEGlosa'] = self._check_digest_dte(doc)
        if not document_type:
            res['EstadoRecepDTE'] = 99
            res['RecepDTEGlosa'] = 'Tipo de documento desconocido'
            return res
        docu = self.env['account.invoice'].search(
            [
                ('reference', '=', doc['Encabezado']['IdDoc']['Folio']),
                ('partner_id', '=', partner_id.id),
                ('document_type_id', '=', document_type.id), ])
        company_id = self.env['res.company'].search([
                ('pointless_main_id_number', '=', self.format_rut(doc['Encabezado']['Receptor']['RUTRecep']))
            ])
        if not company_id and (not docu or doc['Encabezado']['Receptor']['RUTRecep'] != self.env[
                'account.invoice'].format_vat(docu.company_id.vat)):
            res['EstadoRecepDTE'] = 3
            res['RecepDTEGlosa'] = 'Rut no corresponde a la empresa esperada'
            return res
        return res

    def _validate_dtes(self):
        envio = self._read_xml('parse')
        if 'Documento' in envio['SetDTE']['DTE']:
            res = {'RecepcionDTE': self._validate_dte(envio['SetDTE']['DTE']['Documento'])}
        else:
            res = []
            for doc in envio['SetDTE']['DTE']:
                res.extend([{'RecepcionDTE': self._validate_dte(doc['Documento'])}])
        return res

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

    def _receipt(self, IdRespuesta):
        envio = self._read_xml('parse')
        xml = self._read_xml('etree')
        resp = collections.OrderedDict()
        inv_obj = self.env['account.invoice']
        resp['NmbEnvio'] = self.filename
        resp['FchRecep'] = pysiidte.time_stamp()
        resp['CodEnvio'] = pysiidte.str_shorten(IdRespuesta, 10)
        resp['EnvioDTEID'] = xml[0].attrib['ID']
        resp['Digest'] = xml.find("{http://www.w3.org/2000/09/xmldsig#}Signature/{http://www.w3.org/2000/09/\
xmldsig#}SignedInfo/{http://www.w3.org/2000/09/xmldsig#}Reference/{http://www.w3.org/2000/09/xmldsig#}DigestValue").text
        EstadoRecepEnv, RecepEnvGlosa = self._validate_caratula(envio['SetDTE']['Caratula'])
        if EstadoRecepEnv == 0:
            EstadoRecepEnv, RecepEnvGlosa = self._check_digest_caratula()
        resp['RutEmisor'] = envio['SetDTE']['Caratula']['RutEmisor']
        resp['RutReceptor'] = envio['SetDTE']['Caratula']['RutReceptor']
        resp['EstadoRecepEnv'] = EstadoRecepEnv
        resp['RecepEnvGlosa'] = RecepEnvGlosa
        NroDte = len(envio['SetDTE']['DTE'])
        if 'Documento' in envio['SetDTE']['DTE']:
            NroDte = 1
        resp['NroDTE'] = NroDte
        resp['item'] = self._validate_dtes()
        return resp

    def _RecepcionEnvio(self, Caratula, resultado):
        resp='''<?xml version="1.0" encoding="ISO-8859-1"?>
<RespuestaDTE version="1.0" xmlns="http://www.sii.cl/SiiDte" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte RespuestaEnvioDTE_v10.xsd" >
    <Resultado ID="Odoo_resp">
        <Caratula version="1.0">
            {0}
        </Caratula>
            {1}
    </Resultado>
</RespuestaDTE>'''.format(Caratula,resultado)
        return resp

    def _create_attachment(self, xml, name, id=False, model='account.invoice'):
        data = base64.b64encode(xml.encode('ISO-8859-1'))
        filename = (name + '.xml').replace(' ', '')
        url_path = '/download/xml/resp/%s' % id
        att = self.env['ir.attachment'].search([
            ('name', '=', filename),
            ('res_id', '=', id),
            ('res_model', '=', model), ], limit=1)
        if att:
            return att
        values = dict(
            name=filename,
            datas_fname=filename,
            url=url_path,
            res_model=model,
            res_id=id,
            type='binary',
            datas=data, )
        att = self.env['ir.attachment'].create(values)
        return att

    @api.one
    def do_receipt_deliver(self):
        envio = self._read_xml('parse')
        try:
            if 'Caratula' not in envio['SetDTE']:
                return True
        except KeyError:
            _logger.info('keyerror: setdte (continua el proceso hacia resultado envio)')
            return True
        company_id = self.env['res.company'].search(
            [
                ('pointless_main_id_number', '=', self.format_rut(envio['SetDTE']['Caratula']['RutReceptor']))
            ], limit=1)
        id_seq = self.env.ref('l10n_cl_dte.response_sequence').id
        IdRespuesta = self.env['ir.sequence'].browse(id_seq).next_by_id()
        try:
            signature_d = self.env.user.get_digital_signature(company_id)
        except:
            return False
            # raise UserError(_('''There is no Signer Person with an \
            # authorized signature for you in the system. Please make sure that \
            # 'user_signature_key' module has been installed and enable a digital \
            # signature, for you or make the signer to authorize you to use his \
            # signature.'''))
        certp = signature_d['cert'].replace(
            BC, '').replace(EC, '').replace('\n', '')
        recep = self._receipt(IdRespuesta)
        NroDetalles = len(envio['SetDTE']['DTE'])
        resp_dtes = dicttoxml.dicttoxml(recep, root=False, attr_type=False).decode().replace(
            '<item>', '\n').replace('</item>', '\n')
        RecepcionEnvio = '''
<RecepcionEnvio>
    {0}
</RecepcionEnvio>
        '''.format(resp_dtes)
        RutRecibe = envio['SetDTE']['Caratula']['RutEmisor']
        caratula_recepcion_envio = self._caratula_respuesta(
            self.env.user.company_id.pointless_main_id_number,
            RutRecibe,
            IdRespuesta,
            NroDetalles,
        )
        caratula = dicttoxml.dicttoxml(
            caratula_recepcion_envio,
            root=False,
            attr_type=False,
        ).decode().replace('<item>', '\n').replace('</item>', '\n')
        resp = self._RecepcionEnvio(caratula, RecepcionEnvio)
        respuesta = '<?xml version="1.0" encoding="ISO-8859-1"?>\n'+self.env['account.invoice'].sign_full_xml(
            resp.replace('<?xml version="1.0" encoding="ISO-8859-1"?>\n', ''),
            signature_d['priv_key'],
            certp,
            'Odoo_resp',
            'env_resp')
        self.response = respuesta
        # ubicacion anterior de if self.dte_id and not self.dte_id.reception_response_number:
        email_and_partner = []
        if self.dte_id and not self.dte_id.reception_response_number:
            if not self.dte_id.partner_id:
                email_and_partner = self.gather_partner_from_email(self.dte_id.mail_id.email_from)
                _logger.info('(421) email_and_partner 0: %s' % email_and_partner[0])
                _logger.info('(422) email_and_partner 1: %s' % email_and_partner[1])
            else:
                email_and_partner.append(self._clean_email(self.dte_id.email_from))  # Este dato proviene del preproceso
                email_and_partner.append(self.dte_id.partner_id)  # Este dato proviene del preproceso
            try:
                self.dte_id.mail_id.email_from = email_and_partner[0]
                if email_and_partner[1]:
                    self.dte_id.message_subscribe(partner_ids=[email_and_partner[1]])
                att = self._create_attachment(
                    respuesta,
                    'recepcion_envio_' + (self.filename or self.dte_id.name) + '_' + str(IdRespuesta),
                    self.dte_id.id,
                    'mail.message.dte')
                template = self.env.ref('l10n_cl_dte_incoming.email_template_receipt_ack', False)
                _logger.info('\n\n attachment(s) %s\n\n' % att.ids)
                mail_id = template.send_mail(
                    self.dte_id.id,
                    force_send=True,
                    email_values={'attachment_ids': att.ids})
                _logger.info('se envio email con template (se puede mejorar el tema de attachment para adjuntar \
    directo en la plantilla)')
                self.dte_id.reception_response_number = IdRespuesta
            except:
                _logger.info('(445) email not sent')

    def _create_partner(self, data):
        if self.pre_process:
            return False
        giro_id = self.env['sii.activity.description'].search([('name','=', data['GiroEmis'])])
        if not giro_id:
            giro_id = self.env['sii.activity.description'].create({
                'name': data['GiroEmis'],
            })
        rut = self.format_rut(data['RUTEmisor'])
        partner_id = self.env['res.partner'].create(
            {
                'name': data['RznSoc'],
                'activity_description': giro_id.id,
                'vat': rut,
                'main_id_category_id': self.env.ref('l10n_cl_partner.dt_RUT').id,
                'taxpayer_type_id': self.env.ref('l10n_cl_account.res_IVARI').id,
                'main_id_number': data['RUTEmisor'],
                'street': data['DirOrigen'],
                'city': data['CiudadOrigen'] if 'CiudadOrigen' in data else '',
                'company_type': 'company',
                'supplier': True, }, )
        return partner_id

    def _default_category(self,):
        md = self.env['ir.model.data']
        res = False
        try:
            res = md.get_object_reference('product', 'product_category_all')[1]
        except ValueError:
            res = False
        return res

    def _search_taxes(self, name="Impuesto", amount=0, sii_code=0, sii_type=False, IndExe=False):
        query = [
            ('amount', '=', amount),
            ('sii_code', '=', sii_code),
            ('type_tax_use', '=', 'purchase'),
            ('activo_fijo', '=', False),
            ('company_id', '=', self.env.user.company_id.id)
        ]
        if IndExe:
            query.append(
                    ('sii_type', '=', False)
            )
        if amount == 0 and sii_code == 0 and not IndExe:
            query.append(
                ('name', '=', name)
            )
        if sii_type:
            query.extend([
                ('sii_type', '=', sii_type),
            ])
        imp = self.env['account.tax'].search(query)
        _logger.info('search taxes: %s - %s' % (query, imp))
        if not imp:
            imp = self.env['account.tax'].sudo().create({
                'amount': amount,
                'name': name,
                'sii_code': sii_code,
                'sii_type': sii_type,
                'type_tax_use': 'purchase',
            }, )
        return imp

    def get_product_values(self, line, price_included=False):
        IndExe = line.find("{http://www.sii.cl/SiiDte}IndExe")
        amount = 0
        sii_code = 0
        sii_type = False
        if not IndExe:
            amount = 19
            sii_code = 14
            sii_type = False
        imp = self._search_taxes(amount=amount, sii_code=sii_code, sii_type=sii_type, IndExe=IndExe)
        price = float(line.find("{http://www.sii.cl/SiiDte}PrcItem").text if line.find(
            "{http://www.sii.cl/SiiDte}PrcItem") is not None else line.find("{http://www.sii.cl/SiiDte}MontoItem").text)
        if price_included:
            price = imp.compute_all(price, self.env.user.company_id.currency_id, 1)['total_excluded']
        values = {
            'sale_ok': False,
            'name': line.find("{http://www.sii.cl/SiiDte}NmbItem").text,
            'lst_price': price,
            'categ_id': self._default_category(),
            'supplier_taxes_id': [(6, 0, imp.ids)],
        }
        for c in line.findall("{http://www.sii.cl/SiiDte}CdgItem"):
            VlrCodigo = c.find("{http://www.sii.cl/SiiDte}VlrCodigo").text
            if c.find("{http://www.sii.cl/SiiDte}TpoCodigo").text == 'ean13':
                values['barcode'] = VlrCodigo
            else:
                values['default_code'] = VlrCodigo
        return values

    def _create_prod(self, data, price_included=False):
        product_id = self.env['product.product'].create(self.get_product_values(data, price_included))
        return product_id

    def _buscar_producto(self, document_id, line, price_included=False):
        # agregado daniel blanco
        # imp = self._search_taxes(name="OtrosImps_" + str(i['TipoImp']), sii_code=i['TipoImp'])
        default_code = False
        CdgItem = line.find("{http://www.sii.cl/SiiDte}CdgItem")
        NmbItem = line.find("{http://www.sii.cl/SiiDte}NmbItem").text
        VlrCodigo = line.find("{http://www.sii.cl/SiiDte}VlrCodigo")
        # TpoCodigo = line.find("{http://www.sii.cl/SiiDte}TpoCodigo").text
        if document_id:
            # code = ' ' + etree.tostring(CdgItem) if CdgItem is not None else ''
            try:
                code = ' ' + VlrCodigo.text if VlrCodigo is not None else ''
            except:
                code = ''
            line_id = self.env['mail.message.dte.document.line'].search(
                [
                    '|',
                    ('new_product', '=', NmbItem + code),
                    ('product_description', '=', line.find("{http://www.sii.cl/SiiDte}DescItem").text if line.find(
                        "{http://www.sii.cl/SiiDte}DescItem") is not None else NmbItem),
                    ('document_id', '=', document_id.id)
                ], limit=1
            )
            if line_id:
                if line_id.product_id:
                    return line_id.product_id.id
            else:
                return False
        query = False
        product_id = False
        if CdgItem is not None:
            for c in line.findall("{http://www.sii.cl/SiiDte}CdgItem"):
                VlrCodigo = c.find("{http://www.sii.cl/SiiDte}VlrCodigo")
                TpoCodigo = c.find("{http://www.sii.cl/SiiDte}TpoCodigo").text
                if TpoCodigo == 'ean13':
                    query = [('barcode', '=', VlrCodigo.text)]
                elif TpoCodigo == 'INT1':
                    query = [('default_code', '=', VlrCodigo.text)]
                default_code = VlrCodigo.text
        if not query:
            query = [('name', '=', NmbItem)]
        product_id = self.env['product.product'].search(query)
        query2 = [('name', '=', document_id.partner_id.id)]
        if default_code:
            query2.append(('product_code', '=', default_code))
        else:
            query2.append(('product_name', '=', NmbItem))
        product_supplier = self.env['product.supplierinfo'].search(query2)
        product_id = product_supplier.product_id or self.env['product.product'].search(
            [
                ('product_tmpl_id', '=', product_supplier.product_tmpl_id.id),
            ],
                limit=1)
        if not product_id:
            return
            # modificado para evitar el agregado de productos
            """
            if not product_supplier and not self.pre_process:
                product_id = self._create_prod(line, price_included)
            else:
                try:
                    code = ' ' + VlrCodigo.text
                except:
                    code = ''
                return NmbItem + code
            """
        if not product_supplier and document_id.partner_id:
            price = float(line.find("{http://www.sii.cl/SiiDte}PrcItem").text if line.find(
                "{http://www.sii.cl/SiiDte}PrcItem") is not None else line.find(
                "{http://www.sii.cl/SiiDte}MontoItem").text)
            # commented by Daniel Blanco: imp is not present as an object in this function. Price included is only
            # probable with receipts (boletas) and not regular invoices
            # if price_included:
            #     price = imp.compute_all(price, self.env.user.company_id.currency_id, 1)['total_excluded']
            supplier_info = {
                'name': document_id.partner_id.id,
                'product_name': NmbItem,
                'product_code': default_code,
                'product_tmpl_id': product_id.product_tmpl_id.id,
                'price': price,
            }
            self.env['product.supplierinfo'].create(supplier_info)

        return product_id.id

    def _prepare_line(self, line, document_id, journal, type, price_included=False):
        data = {}
        product_id = self._buscar_producto(document_id, line, price_included)
        if isinstance(product_id, int):
            data.update(
                {
                    'product_id': product_id,
                }
            )
        elif not product_id:
            return False
        account_id = journal.default_debit_account_id.id
        if type in ('out_invoice', 'in_refund'):
                account_id = journal.default_credit_account_id.id
        if line.find("{http://www.sii.cl/SiiDte}MntExe") is not None:
            price_subtotal = float(line.find("{http://www.sii.cl/SiiDte}MntExe").text)
        else:
            price_subtotal = float(line.find("{http://www.sii.cl/SiiDte}MontoItem").text)
        discount = 0
        if line.find("{http://www.sii.cl/SiiDte}DescuentoPct") is not None:
            discount = float(line.find("{http://www.sii.cl/SiiDte}DescuentoPct").text)
        price = float(line.find("{http://www.sii.cl/SiiDte}PrcItem").text) if line.find(
            "{http://www.sii.cl/SiiDte}PrcItem") is not None else price_subtotal
        DescItem = line.find("{http://www.sii.cl/SiiDte}DescItem")
        data.update({
            'name':  DescItem.text if DescItem is not None else line.find("{http://www.sii.cl/SiiDte}NmbItem").text,
            'price_unit': price,
            'discount': discount,
            'quantity': line.find("{http://www.sii.cl/SiiDte}QtyItem").text if line.find(
                "{http://www.sii.cl/SiiDte}QtyItem") is not None else 1,
            'account_id': account_id,
            'price_subtotal': price_subtotal,
        })
        if self.pre_process:
            _logger.info('\n\n(653) pre_process\n\n')
            data.update({
                'new_product': product_id,
                'product_description': DescItem.text if DescItem is not None else '',
            })
        else:
            _logger.info('\n\n(659) not pre_process\n\n')
            product_id = self.env['product.product'].browse(product_id)
            if price_included:
                price = product_id.supplier_taxes_id.compute_all(
                    price, self.env.user.company_id.currency_id, 1)['total_excluded']
                price_subtotal = product_id.supplier_taxes_id.compute_all(
                    price_subtotal, self.env.user.company_id.currency_id, 1)['total_excluded']
            data.update({
                'invoice_line_tax_ids': [(6, 0, product_id.supplier_taxes_id.ids)],
                'uom_id': product_id.uom_id.id,
                'price_unit': price,
                'price_subtotal': price_subtotal,
            })

        return [0,0, data]

    def _create_tpo_doc(self, TpoDocRef, RazonRef=''):
        vals = {
                'name': RazonRef + ' ' + str(TpoDocRef)
            }
        if str(TpoDocRef).isdigit():
            vals.update({
                    'sii_code': TpoDocRef,
                })
        else:
            vals.update({
                    'doc_code_prefix': TpoDocRef,
                    'sii_code': 801,
                    'use_prefix': True,
                })
        return self.env['account.document.type'].create(vals)

    def _prepare_ref(self, ref):
        query = []
        TpoDocRef = ref.find("{http://www.sii.cl/SiiDte}TpoDocRef").text
        RazonRef = ref.find("{http://www.sii.cl/SiiDte}RazonRef")
        if str(TpoDocRef).isdigit():
            query.append(('code', '=', TpoDocRef))
            query.append(('use_prefix', '=', False))
        else:
            query.append(('doc_code_prefix', '=', TpoDocRef))
        _logger.info('(709) query: %s' % query)
        tpo = self.env['account.document.type'].search(query, limit=1)
        if not tpo:
            _logger.info('el tipo de documento de referencia es desconocido. Asume 801')
            # tpo = self._create_tpo_doc(TpoDocRef, RazonRef)
            tpo = self.env.ref('l10n_cl_account.dc_oc')
        return [0, 0, {
            'origin': ref.find("{http://www.sii.cl/SiiDte}FolioRef").text,
            'reference_doc_type': tpo.id,
            'reference_doc_code': ref.find("{http://www.sii.cl/SiiDte}CodRef").text if ref.find(
                "{http://www.sii.cl/SiiDte}CodRef") is not None else None,
            'reason': RazonRef.text if RazonRef is not None else None,
            'date': ref.find("{http://www.sii.cl/SiiDte}FchRef").text if ref.find(
                "{http://www.sii.cl/SiiDte}FchRef") is not None else None,
        }]

    def process_dr(self, dr):
        data = {
                    'type': dr.find("{http://www.sii.cl/SiiDte}TpoMov").text,
                }
        disc_type = "percent"
        if dr.find("{http://www.sii.cl/SiiDte}TpoValor").text == '$':
            disc_type = "amount"
        data['gdr_type'] = disc_type
        data['valor'] = dr.find("{http://www.sii.cl/SiiDte}ValorDR").text
        data['gdr_dtail'] = dr.find("{http://www.sii.cl/SiiDte}GlosaDR").text if dr.find(
            "{http://www.sii.cl/SiiDte}GlosaDR") is not None else 'Descuento global'
        return data

    def _prepare_invoice(self, documento, company_id, journal_document_type_id):
        Encabezado = documento.find("{http://www.sii.cl/SiiDte}Encabezado")
        IdDoc = Encabezado.find("{http://www.sii.cl/SiiDte}IdDoc")
        Emisor = Encabezado.find("{http://www.sii.cl/SiiDte}Emisor")
        RUTEmisor = Emisor.find("{http://www.sii.cl/SiiDte}RUTEmisor").text
        string = etree.tostring(documento)
        dte = xmltodict.parse(string)['Documento']
        invoice = {}
        partner_id = self.env['res.partner'].search(
            [
                ('active', '=', True),
                ('parent_id', '=', False),
                ('main_id_number', '=', self.format_rut(RUTEmisor))
            ], limit=1)
        if not partner_id:
            partner_id = self._create_partner(dte['Encabezado']['Emisor'])
        elif not partner_id.supplier:
            partner_id.supplier = True
        if partner_id:
            invoice.update(
            {
                'account_id': partner_id.property_account_payable_id.id,
                'partner_id': partner_id.id,
            })
            partner_id = partner_id.id
        try:
            name = self.filename.decode('ISO-8859-1').encode('UTF-8')
        except:
            name = self.filename.encode('UTF-8')
        image = False
        barcodefile = BytesIO()
        ted_string = etree.tostring(documento.find("{http://www.sii.cl/SiiDte}TED"), method="c14n", pretty_print=False)
        image = self.env['account.invoice'].pdf417bc(ted_string.decode().replace(
            'xmlns="http://www.sii.cl/SiiDte" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ', '').replace(
            ' xmlns=""', ''))
        image.save(barcodefile, 'PNG')
        data = barcodefile.getvalue()
        sii_barcode_img = base64.b64encode(data)
        FchEmis = IdDoc.find("{http://www.sii.cl/SiiDte}FchEmis").text
        sii_xml_request = self.env['sii.xml.envio'].create({
            'xml_envio': string,
            'name': name,
            'sii_barcode': ted_string,
            'sii_barcode_img': sii_barcode_img,
            })
        # verificación de la compañía para saber si es coincidente
        if self.env.user.company_id != company_id:
            raise UserError(
                'La compañía %s es diferente a la compañía corriente: %s. \
                Cambie de compañía para procesar recepción' % (self.env.user.company_id.name, company_id.name))
        # comprobación de actividades económicas.
        turn_issuer = False
        for turn in company_id.company_activities_ids:
            if turn:
                turn_issuer = turn.id
                break
        if not turn_issuer:
            raise UserError('La compañía %s, no tiene actividades económicas definidas' % company_id.name)
        invoice.update({
            'origin': 'XML Envío: ' + name.decode(),
            'date_invoice': FchEmis,
            'partner_id': partner_id,
            'company_id': company_id.id,
            'journal_id': journal_document_type_id.journal_id.id,
            'turn_issuer': turn_issuer,
            'sii_xml_request': sii_xml_request.id,
            'sii_send_file_name': name,
        })
        DscRcgGlobal = documento.findall("{http://www.sii.cl/SiiDte}DscRcgGlobal")
        if DscRcgGlobal:
            drs = [(5,)]
            for dr in DscRcgGlobal:
                drs.append((0,0,self.process_dr(dr)))
            invoice.update({
                    'global_descuentos_recargos': drs,
                })
        Folio = IdDoc.find("{http://www.sii.cl/SiiDte}Folio").text
        if partner_id and not self.pre_process:
            invoice.update({
                'reference': Folio,
                'journal_document_type_id': journal_document_type_id.id,
            })
        else:
            invoice.update({
                'number': Folio,
                'date': FchEmis,
                'new_partner': RUTEmisor + ' ' + Emisor.find("{http://www.sii.cl/SiiDte}RznSoc").text,
                'document_type_id': journal_document_type_id.document_type_id.id,
                'amount': dte['Encabezado']['Totales']['MntTotal'],
            })
        return invoice

    def _get_journal(self, code, company_id):
        journal_sii = self.env['account.journal.document.type'].search(
            [
                ('document_type_id.code', '=', code),
                ('journal_id.type','=','purchase'),
                ('journal_id.company_id', '=', company_id.id)
            ],
            limit=1,
        )
        return journal_sii

    def _get_data(self, documento, company_id):
        string = etree.tostring(documento)
        dte = xmltodict.parse(string)['Documento']
        Encabezado = documento.find("{http://www.sii.cl/SiiDte}Encabezado")
        IdDoc = Encabezado.find("{http://www.sii.cl/SiiDte}IdDoc")
        price_included = Encabezado.find("{http://www.sii.cl/SiiDte}MntBruto")
        _logger.info('(807), _get_data. price_included: %s' % price_included)
        journal_document_type_id = self._get_journal(IdDoc.find("{http://www.sii.cl/SiiDte}TipoDTE").text, company_id)
        if not journal_document_type_id:
            document_type = self.env['account.document.type'].search([('code', '=', IdDoc.find(
                "{http://www.sii.cl/SiiDte}TipoDTE").text)])
            raise UserError('No existe Diario para el tipo de documento %s, por favor añada uno primero, o \
ignore el documento' % document_type.name.encode('UTF-8'))
        data = self._prepare_invoice(documento, company_id, journal_document_type_id)
        data['type'] = 'in_invoice'
        if dte['Encabezado']['IdDoc']['TipoDTE'] in ['61']:
            # document type 54 not found in sii catalog!!!
            data['type'] = 'in_refund'
        # agregado Daniel Blanco:
        data['document_number'] = dte['Encabezado']['IdDoc']['Folio']
        lines = [(5, )]
        document_id = self._dte_exist(documento)
        for line in documento.findall("{http://www.sii.cl/SiiDte}Detalle"):
            new_line = self._prepare_line(
                line, document_id=document_id, journal=journal_document_type_id.journal_id, type=data['type'],
                price_included=price_included)
            if new_line:
                lines.append(new_line)
        product_id = self.env['product.product'].search([
                ('product_tmpl_id', '=', self.env.ref('l10n_cl_dte.product_imp').id), ]).id
        if 'ImptoReten' in dte['Encabezado']['Totales']:
            Totales = dte['Encabezado']['Totales']
            if 'TipoImp' in Totales['ImptoReten']:
                Totales = [Totales['ImptoReten']['TipoImp']]
            else:
                Totales = Totales['ImptoReten']
            for i in Totales:
                imp = self._search_taxes(name="OtrosImps_" + str(i['TipoImp']), sii_code=i['TipoImp'])
                price = float(i['MontoImp'])
                price_subtotal = float(i['MontoImp'])
                if price_included:
                    price = imp.compute_all(price, self.env.user.company_id.currency_id, 1)['total_excluded']
                    price_subtotal = imp.compute_all(
                        price_subtotal, self.env.user.company_id.currency_id, 1)['total_excluded']
                lines.append([0, 0, {
                    'invoice_line_tax_ids': ((6, 0, imp.ids)),
                    'product_id': product_id,
                    'name': 'MontoImpuesto %s' % str(i['TipoImp']),
                    'price_unit': price,
                    'quantity': 1,
                    'price_subtotal': price_subtotal,
                    'account_id':  journal_document_type_id.journal_id.default_debit_account_id.id
                    }]
                )
        Referencias = documento.findall("{http://www.sii.cl/SiiDte}Referencia")
        if not self.pre_process and Referencias:
            refs = [(5,)]
            for ref in Referencias:
                refs.append(self._prepare_ref(ref))
            data['referencias'] = refs
        data['invoice_line_ids'] = lines
        mnt_neto = int(dte['Encabezado']['Totales']['MntNeto']) if 'MntNeto' in dte['Encabezado']['Totales'] else 0
        mnt_neto += int(dte['Encabezado']['Totales']['MntExe']) if 'MntExe' in dte['Encabezado']['Totales'] else 0
        data['amount_untaxed'] = mnt_neto
        data['amount_total'] = dte['Encabezado']['Totales']['MntTotal']
        if document_id:
            purchase_to_done = False
            if document_id.purchase_to_done:
                purchase_to_done = document_id.purchase_to_done.ids
            if purchase_to_done:
                data['purchase_to_done'] = purchase_to_done
        return data

    def _inv_exist(self, documento):
        encabezado = documento.find("{http://www.sii.cl/SiiDte}Encabezado")
        Emisor= encabezado.find("{http://www.sii.cl/SiiDte}Emisor")
        IdDoc = encabezado.find("{http://www.sii.cl/SiiDte}IdDoc")
        return self.env['account.invoice'].search(
            [
                ('reference', '=', IdDoc.find("{http://www.sii.cl/SiiDte}Folio").text),
                ('type', 'in', ['in_invoice', 'in_refund']),
                ('document_type_id.code', '=', IdDoc.find("{http://www.sii.cl/SiiDte}TipoDTE").text),
                ('partner_id.main_id_number', '=', self.format_rut(
                    Emisor.find("{http://www.sii.cl/SiiDte}RUTEmisor").text)),
            ])

    def _create_inv(self, documento, company_id):
        _logger.info('create inv. Documento: %s' % documento)  # <Element {http://www.sii.cl/SiiDte}Documento at 0x7f5abc1c43c8>
        inv = self._inv_exist(documento)
        if inv:
            return inv
        Totales = documento.find("{http://www.sii.cl/SiiDte}Encabezado/{http://www.sii.cl/SiiDte}Totales")
        _logger.info('create inv. Totales: %s' % Totales)
        data = self._get_data(documento, company_id)
        _logger.info('create inv. data: %s' % data)
        inv = self.env['account.invoice'].create(data)
        monto_xml = float(Totales.find('{http://www.sii.cl/SiiDte}MntTotal').text)
        if inv.amount_total == monto_xml:
            return inv
        inv.amount_total = monto_xml
        for t in inv.tax_line_ids:
            _logger.info('upload_xml (898) taxes: %s' % inv.tax_line_ids)
            if Totales.find('{http://www.sii.cl/SiiDte}TasaIVA') is not None and t.tax_id.amount == float(
                    Totales.find('{http://www.sii.cl/SiiDte}TasaIVA').text):
                t.amount = float(Totales.find('{http://www.sii.cl/SiiDte}IVA').text)
                t.base = float(Totales.find('{http://www.sii.cl/SiiDte}MntNeto').text)
            else:
                t.base = float(Totales.find('{http://www.sii.cl/SiiDte}MntExe').text)
        return inv

    def _dte_exist(self, documento):
        encabezado = documento.find("{http://www.sii.cl/SiiDte}Encabezado")
        Emisor= encabezado.find("{http://www.sii.cl/SiiDte}Emisor")
        IdDoc = encabezado.find("{http://www.sii.cl/SiiDte}IdDoc")
        return self.env['mail.message.dte.document'].search(
            [
                ('number', '=', IdDoc.find("{http://www.sii.cl/SiiDte}Folio").text),
                ('document_type_id.code', '=', IdDoc.find("{http://www.sii.cl/SiiDte}TipoDTE").text),
                '|',
                ('partner_id.main_id_number', '=', self.format_rut(Emisor.find(
                    "{http://www.sii.cl/SiiDte}RUTEmisor").text)),
                ('new_partner', '=', Emisor.find("{http://www.sii.cl/SiiDte}RUTEmisor").text + ' ' + Emisor.find(
                    "{http://www.sii.cl/SiiDte}RznSoc").text),
            ]
        )

    def _create_pre(self, documento, company_id):
        dte = self._dte_exist(documento)
        if dte:
            _logger.warning(_('The document is already registered'))
            return dte
        data = self._get_data(documento, company_id)
        data.update({
            'dte_id': self.dte_id.id,
        })
        return self.env['mail.message.dte.document'].create(data)

    def _get_dtes(self):
        xml = self._read_xml('etree')
        envio = xml.find("{http://www.sii.cl/SiiDte}SetDTE")
        if envio is None:
            if xml.tag == "{http://www.sii.cl/SiiDte}DTE":
                return [xml]
            return []
        return envio.findall("{http://www.sii.cl/SiiDte}DTE")

    def do_create_pre(self):
        created = []
        resp = self.do_receipt_deliver()
        dtes = self._get_dtes()
        for dte in dtes:
            if True:  # try:
                document = dte.find("{http://www.sii.cl/SiiDte}Documento")
                company_id = self.env['res.company'].search(
                        [
                            ('pointless_main_id_number', '=', self.format_rut(
                                document.find("{http://www.sii.cl/SiiDte}Encabezado/{http://www.sii.cl/SiiDte}\
Receptor/{http://www.sii.cl/SiiDte}RUTRecep").text)),
                        ],
                        limit=1,
                    )
                if not company_id:
                    _logger.warning("No existe compañia para %s" % document.find("{http://www.sii.cl/\
SiiDte}Encabezado/{http://www.sii.cl/SiiDte}Receptor/{http://www.sii.cl/SiiDte}RUTRecep").text)
                    continue
                pre = self._create_pre(
                    document,
                    company_id,
                )
                if pre:
                    inv = self._inv_exist(document)
                    pre.write({
                        'xml': etree.tostring(dte),
                        'invoice_id': inv.id,
                        }
                    )
                    created.append(pre.id)
            else:  # except Exception as e:
                _logger.warning('(964) Error en 1 factura con error:  %s' % str(e))
        return created

    def do_create_inv(self):
        created = []
        dtes = self._get_dtes()
        _logger.info('(974) do_create_inv: get dtes: %s' % dtes)
        for dte in dtes:
            if True:  # try:
                company_id = self.document_id.company_id
                documento = dte.find("{http://www.sii.cl/SiiDte}Documento")
                company_id = self.env['res.company'].search(
                        [
                            ('pointless_main_id_number', '=', self.format_rut(documento.find(
"{http://www.sii.cl/SiiDte}Encabezado/{http://www.sii.cl/SiiDte}Receptor/{http://www.sii.cl/SiiDte}RUTRecep").text)),
                        ],
                        limit=1,
                    )
                inv = self._create_inv(
                    documento,
                    company_id,
                )
                _logger.info('(1002) documento. inv %s' % inv)
                if self.document_id:
                    self.document_id.invoice_id = inv.id
                if inv:
                    created.append(inv.id)
                if not inv:
                    raise UserError('El archivo XML no contiene documentos para alguna empresa registrada en Odoo, \
o ya ha sido procesado anteriormente ')
            else:  # except Exception as e:
                _logger.warning('(997) Error en 1 factura con error:  %s' % str(e))
        if created and self.option not in [False, 'upload']:
            wiz_accept = self.env['dte.validate.wizard'].create(
                {
                    'invoice_ids': [(6, 0, created)],
                    'action': 'validate',
                    'option': self.option,
                }
            )
            wiz_accept.confirm()
        return created

    def prepare_purchase_line(self, line, date_planned):
        product = self.env['product.product'].search([('name','=', line['NmbItem'])], limit=1)
        if not product:
            # product = self._create_prod(line)
            return
        values = {
            'name': line['DescItem'] if 'DescItem' in line else line['NmbItem'],
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'taxes_id': [(6, 0, product.supplier_taxes_id.ids)],
            'price_unit': float(line['PrcItem'] if 'PrcItem' in line else line['MontoItem']),
            'product_qty': line['QtyItem'],
            'date_planned': date_planned,
        }
        return values

    def _create_po(self, dte):
        purchase_model = self.env['purchase.order']
        partner_id = self.env['res.partner'].search([
            ('active','=', True),
            ('parent_id', '=', False),
            ('main_id_number', '=', self.format_rut(dte['Encabezado']['Emisor']['RUTEmisor'])),
        ])
        if not partner_id:
            partner_id = self._create_partner(dte['Encabezado']['Emisor'])
        elif not partner_id.supplier:
            partner_id.supplier = True
        company_id = self.env['res.company'].search(
            [
                ('pointless_main_id_number', '=', self.format_rut(dte['Encabezado']['Receptor']['RUTRecep'])),
            ],
        )
        data = {
            'partner_ref': dte['Encabezado']['IdDoc']['Folio'],
            'date_order': dte['Encabezado']['IdDoc']['FchEmis'],
            'partner_id': partner_id.id,
            'company_id': company_id.id,
        }
        # antes de crear la OC, verificar que no exista otro documento con los mismos datos
        other_orders = purchase_model.search([
            ('partner_id', '=', data['partner_id']),
            ('partner_ref', '=', data['partner_ref']),
            ('company_id', '=', data['company_id']),
            ])
        if other_orders:
            raise UserError("Ya existe un Pedido de compra con Referencia: %s para el Proveedor: %s.\n" \
                            "No se puede crear nuevamente, por favor verifique." %
                            (data['partner_ref'], partner_id.name))
        lines =[(5,)]
        vals_line = {}
        detalles = dte['Detalle']
        # cuando es un solo producto, no viene una lista sino un diccionario
        # asi que tratarlo como una lista de un solo elemento
        # para evitar error en la esructura que siempre espera una lista
        if isinstance(dte['Detalle'], dict):
            detalles = [dte['Detalle']]
        for line in detalles:
            vals_line = self.prepare_purchase_line(line, dte['Encabezado']['IdDoc']['FchEmis'])
            if vals_line:
                lines.append([0, 0, vals_line])

        data['order_line'] = lines
        po = purchase_model.create(data)
        po.button_confirm()
        inv = self.env['account.invoice'].search([('purchase_id', '=', po.id)])
        # inv.document_type_id = dte['Encabezado']['IdDoc']['TipoDTE']
        return po

    def do_create_po(self):
        # self.validate()
        dtes = self._get_dtes()
        for dte in dtes:
            if dte['Documento']['Encabezado']['IdDoc']['TipoDTE'] in ['34', '33']:
                self._create_po(dte['Documento'])
            elif dte['Documento']['Encabezado']['IdDoc']['TipoDTE'] in ['56', '61']:  # es una nota
                self._create_inv(dte['Documento'])
