# -*- coding: utf-8 -*-
import base64
import collections
import logging
import os
import sys
from datetime import date, datetime, timedelta
from io import BytesIO

import dicttoxml
import urllib3
from lxml import etree
from six import string_types
from zeep.client import Client

import pdf417gen
import pysiidte
import xmltodict
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from . import pysiidte1

_logger = logging.getLogger(__name__)


try:
    urllib3.disable_warnings()
except ImportError:
    _logger.info('Cannot urllib3 disable warnings')
try:
    pool = urllib3.PoolManager()
except:
    _logger.info('Cannot instance urllib3 pool manager')




timbre = pysiidte.stamp
try:
    result = xmltodict.parse(timbre)
except ImportError:
    _logger.warning('Cannot parse stamp')

dicttoxml.LOG.setLevel(logging.ERROR)

server_url = pysiidte.server_url
BC = pysiidte.BC
EC = pysiidte.EC

# hardcodeamos este valor por ahora

USING_PYTHON2 = True if sys.version_info < (3, 0) else False
xsdpath = os.path.dirname(os.path.realpath(__file__)).replace('/models', '/static/xsd/')

connection_status = {
    '0': 'Upload OK',
    '1': 'El Sender no tiene permiso para enviar',
    '2': 'Error en tamaño del archivo (muy grande o muy chico)',
    '3': 'Archivo cortado (tamaño <> al parámetro size)',
    '5': 'No está autenticado',
    '6': 'Empresa no autorizada a enviar archivos',
    '7': 'Esquema Invalido',
    '8': 'Firma del Documento',
    '9': 'Sistema Bloqueado',
    'Otro': 'Error Interno.',
}


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @staticmethod
    def create_template_envio(
            RutEmisor, RutReceptor, FchResol, NroResol, TmstFirmaEnv, EnvioDTE, signature_d, SubTotDTE):
        xml = '''<SetDTE ID="SetDoc">
    <Caratula version="1.0">
        <RutEmisor>{0}</RutEmisor>
        <RutEnvia>{1}</RutEnvia>
        <RutReceptor>{2}</RutReceptor>
        <FchResol>{3}</FchResol>
        <NroResol>{4}</NroResol>
        <TmstFirmaEnv>{5}</TmstFirmaEnv>
        {6}
    </Caratula>
    {7}
</SetDTE>
'''.format(RutEmisor, signature_d['subject_serial_number'], RutReceptor,
           FchResol, NroResol, TmstFirmaEnv, SubTotDTE, EnvioDTE)
        return xml

    @staticmethod
    def xml_validator(some_xml_string, validacion='doc'):
        validacion_type = {
            'doc': 'DTE_v10.xsd',
            'env': 'EnvioDTE_v10.xsd',
            'recep': 'Recibos_v10.xsd',
            'env_recep': 'EnvioRecibos_v10.xsd',
            'env_resp': 'RespuestaEnvioDTE_v10.xsd',
            'sig': 'xmldsignature_v10.xsd'
        }
        xsd_file = xsdpath+validacion_type[validacion]
        try:
            xmlschema_doc = etree.parse(xsd_file)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            xml_doc = etree.fromstring(some_xml_string)
            result = xmlschema.validate(xml_doc)
            if not result:
                xmlschema.assert_(xml_doc)
            return result
        except AssertionError as e:
            raise UserError(_('XML Malformed Error:  %s') % e.args)

    @staticmethod
    def create_template_doc1(doc, sign):
        xml = doc.replace('</DTE>',  sign.decode() + '</DTE>')
        return xml

    @staticmethod
    def create_template_env1(doc, sign):
        xml = doc.replace('</EnvioDTE>', sign.decode() + '</EnvioDTE>')
        return xml

    # estos métodos hay que arreglarlos ya que fueron reemplazados.
    def create_template_seed(self, seed):
        return self.env['account.invoice'].create_template_seed(seed)

    def get_seed(self, company_id):
        return self.env['account.invoice'].get_seed(company_id)

    def sign_seed(self, message, privkey, cert):
        return self.env['account.invoice'].sign_seed(message, privkey, cert)

    def get_token(self, seed_file, company_id):
        return self.env['account.invoice'].get_token(seed_file, company_id)

    def ensure_str(self, x, encoding="utf-8", none_ok=False):
        if none_ok is True and x is None:
            return x
        if not isinstance(x, str):
            x = x.decode(encoding)
        return x

    @api.multi
    def get_xml_file(self):
        url_path = '/download/xml/%s/%s' % (self._context['kind'], self.id)
        return {
            'type': 'ir.actions.act_url',
            'url': url_path,
            'target': 'new',
        }

    """
    @api.multi
    def get_xml_file(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/download/xml/guia/%s' % self.id,
            'target': 'self', }
    """

    def get_folio(self):
        # saca el folio directamente de la secuencia
        return int(self.sii_document_number)

    @staticmethod
    def format_rut(rut):
        rut = rut.replace('.', '')
        return rut

    @staticmethod
    def format_vat(value, con_cero=False):
        """
        Se Elimina el 0 para prevenir problemas con el sii, ya que las muestras no las toma si va con
        el 0 , y tambien internamente se generan problemas, se mantiene el 0 delante, para cosultas, o sino retorna
        "error de datos"
        :param value:
        :param con_cero:
        :return:
        """
        if not value or value == '' or value == 0:
            value = "CL666666666"
            # TODO opción de crear código de cliente en vez de rut genérico
        rut = value[:10] + '-' + value[10:]
        if not con_cero:
            rut = rut.replace('CL0', '')
        rut = rut.replace('CL', '')
        return rut

    @staticmethod
    def pdf417bc(ted):
        bc = pdf417gen.encode(
            ted,
            security_level=5,
            columns=13, )
        image = pdf417gen.render_image(
            bc,
            padding=15,
            scale=1, )
        return image

    def signmessage(self, texto, key):
        return self.env['account.invoice'].signmessage(texto, key)

    sii_batch_number = fields.Integer(
        copy=False,
        string='Batch Number',
        readonly=True,
        help='Batch number for processing multiple invoices together')
    sii_barcode = fields.Char(
        copy=False,
        string=_('SII Barcode'),
        readonly=True,
        help='SII Barcode Name')
    sii_barcode_img = fields.Binary(
        copy=False,
        string=_('SII Barcode Image'),
        help='SII Barcode Image in PDF417 format')
    sii_message = fields.Text(
            string='SII Message',
            copy=False,
        )
    sii_xml_dte = fields.Text(
            string='SII XML DTE',
            copy=False,
        )
    sii_xml_request = fields.Many2one(
            'sii.xml.envio',
            string='SII XML Request',
            copy=False,
        )
    sii_result = fields.Selection(
            [
                ('', 'n/a'),
                ('NoEnviado', 'No Enviado'),
                ('EnCola', 'En cola de envío'),
                ('Enviado', 'Enviado'),
                ('Aceptado', 'Aceptado'),
                ('Rechazado', 'Rechazado'),
                ('Reparo', 'Reparo'),
                ('Proceso', 'Proceso'),
                ('Anulado', 'Anulado'),
            ],
            string='Resultado',
            copy=False,
            help="SII request result",
            default='',
        )
    canceled = fields.Boolean(string="Is Canceled?")
    dte_reception_status = fields.Selection(
        [
            ('no_revisado', 'No Revisado'),
            ('0', 'Conforme'),
            ('1', 'Error de Schema'),
            ('2', 'Error de Firma'),
            ('3', 'RUT Receptor No Corresponde'),
            ('90', 'Archivo Repetido'),
            ('91', 'Archivo Ilegible'),
            ('99', 'Envio Rechazado - Otros')
        ], string="Estado de Recepcion del Envio", oldname='estado_recep_dte')
    estado_recep_glosa = fields.Char(string="Información Adicional del Estado de Recepción")
    responsable_envio = fields.Many2one('res.users')
    picking_send_queue_id = fields.Many2one('sii.send_queue', copy=False)

    @api.multi
    def action_done_delivery_guide(self):
        # former def action_done(self):
        # res = super(StockPicking, self).action_done()
        for s in self:
            if not s.use_documents:
                continue
            if not s.sii_document_number and s.location_id.sequence_id.is_dte:
                s.sii_document_number = s.location_id.sequence_id.next_by_id()
                document_number = (s.location_id.document_type_id.doc_code_prefix or '') + s.sii_document_number
                s.document_number = document_number
            if s.picking_type_id.code in {'outgoing', 'internal'}:
                # TODO diferenciar si es de salida o entrada para internal
                s.responsable_envio = self.env.uid
                s.sii_result = 'NoEnviado'
                s._stamp()
                self.env['sii.send_queue'].create(
                    {
                        'doc_ids': [s.id],
                         'model': 'stock.picking',
                         'model_selection': 'stock.picking',
                         'picking_ids': [(6, 0, [s.id])],
                         'user_id': self.env.user.id,
                         'tipo_trabajo': 'pasivo',
                         'date_time': (datetime.now() + timedelta(hours=12)),
                     }
                )

        # return res

    @api.multi
    def do_dte_send_picking(self, n_atencion=None):
        ids = []
        if not isinstance(n_atencion, string_types):
            n_atencion = ''
        for rec in self:
            rec.responsable_envio = self.env.uid
            if rec.sii_result in ['', 'NoEnviado', 'Rechazado']:
                if not rec.sii_xml_request or rec.sii_result in ['Rechazado']:
                    rec._stamp(n_atencion)
                rec.sii_result = "EnCola"
                ids.append(rec.id)
        if ids:
            self.env['sii.send_queue'].create(
                {
                    'doc_ids': ids,
                    'model': 'stock.picking',
                    'model_selection': 'stock.picking',
                    # 'user_id': self.env.uid,
                    'user_id': self.env.user.id,
                    'tipo_trabajo': 'envio',
                    'n_atencion': n_atencion,
                    'picking_ids': [(6, 0, ids)],
                },
            )

    def _giros_emisor(self):
        giros_emisor = []
        for turn in self.company_id.company_activities_ids:
            giros_emisor.extend([{'Acteco': turn.code}])
        return giros_emisor

    def _id_doc(self, tax_include=False, MntExe=0):
        IdDoc = collections.OrderedDict()
        IdDoc['TipoDTE'] = self.location_id.document_type_id.code
        IdDoc['Folio'] = self.get_folio()
        # IdDoc['FchEmis'] = self.scheduled_date[:10]
        # IdDoc['FchEmis'] = fields.Date.context_today(self)
        IdDoc['FchEmis'] = datetime.strftime(datetime.now(), '%Y-%m-%d')
        if self.transport_type and self.transport_type not in ['0']:
            IdDoc['TipoDespacho'] = self.transport_type
        IdDoc['IndTraslado'] = self.move_reason
        # if self.print_ticket:
        #    IdDoc['TpoImpresion'] = "N" #@TODO crear opcion de ticket
        if tax_include and MntExe == 0:
            IdDoc['MntBruto'] = 1
        # IdDoc['FmaPago'] = self.forma_pago or 1
        # IdDoc['FchVenc'] = self.date_due or datetime.strftime(datetime.now(), '%Y-%m-%d')
        return IdDoc

    def _emisor(self):
        issuer = collections.OrderedDict()
        issuer['RUTEmisor'] = self.format_rut(self.company_id.main_id_number)
        issuer['RznSoc'] = self.company_id.partner_id.name
        issuer['GiroEmis'] = pysiidte.str_shorten(self.company_id.activity_description.name, 80)
        issuer['Telefono'] = pysiidte.str_shorten(self.company_id.phone or '', 20)
        issuer['CorreoEmisor'] = self.company_id.dte_email
        issuer['item'] = self._giros_emisor()
        if self.location_id.sii_code:
            issuer['CdgSIISucur'] = self.location_id.sii_code
        issuer['DirOrigen'] = self.company_id.street + ' ' + (self.company_id.street2 or '')
        issuer['CmnaOrigen'] = self.company_id.city_id.name or ''
        issuer['CiudadOrigen'] = self.company_id.city or ''
        return issuer

    def _receptor(self):
        recipient = collections.OrderedDict()
        partner_id = self.partner_id or self.company_id.partner_id
        if not partner_id.commercial_partner_id.main_id_number:
            raise UserError("Must include recipient RUT (VAT)")
        recipient['RUTRecep'] = self.format_rut(partner_id.commercial_partner_id.main_id_number)
        recipient['RznSocRecep'] = pysiidte.str_shorten(partner_id.commercial_partner_id.name, 100)
        activity_description = self.activity_description or partner_id.activity_description
        if not activity_description:
            raise UserError(_('Seleccione giro del partner'))
        recipient['GiroRecep'] = pysiidte.str_shorten(activity_description.name, 40)
        if partner_id.commercial_partner_id.phone:
            recipient['Contacto'] = partner_id.commercial_partner_id.phone
        if partner_id.commercial_partner_id.dte_email:
            recipient['CorreoRecep'] = partner_id.commercial_partner_id.dte_email
        recipient['DirRecep'] = pysiidte.str_shorten(
            partner_id.commercial_partner_id.street + ' ' + (partner_id.commercial_partner_id.street2 or ''), 70)
        recipient['CmnaRecep'] = partner_id.commercial_partner_id.city_id.name
        recipient['CiudadRecep'] = partner_id.commercial_partner_id.city
        return recipient

    def _transporte(self):
        Transporte = collections.OrderedDict()
        if self.car_plate:
            Transporte['Patente'] = self.car_plate[:8]
        elif self.vehicle:
            Transporte['Patente'] = self.vehicle.matricula or ''
        if self.transport_type in ['2','3'] and self.driver_id:
            if not self.driver_id.vat:
                raise UserError("Debe llenar los datos del chofer")
            if self.transport_type == '2':
                Transporte['RUTTrans'] = self.format_rut(self.company_id.main_id_number)
            else:
                if not self.carrier_id.partner_id.main_id_number:
                    raise UserError("Debe especificar el RUT del transportista, en su ficha de partner")
                Transporte['RUTTrans'] = self.format_rut(self.carrier_id.partner_id.main_id_number)
            if self.driver_id:
                Transporte['Chofer'] = collections.OrderedDict()
                Transporte['Chofer']['RUTChofer'] = self.format_rut(self.driver_id.main_id_number)
                Transporte['Chofer']['NombreChofer'] = self.driver_id.name[:30]
        partner_id = self.partner_id or self.company_id.partner_id
        Transporte['DirDest'] = (partner_id.street or '')+ ' '+ (partner_id.street2 or '')
        Transporte['CmnaDest'] = partner_id.state_id.name or ''
        Transporte['CiudadDest'] = partner_id.city or ''
        # TODO SUb Area Aduana
        return Transporte

    def _totales(self, MntExe=0, no_product=False, tax_include=False):
        Totales = collections.OrderedDict()
        IVA = 19
        for line in self.move_lines:
            if line.move_line_tax_ids:
                for t in line.move_line_tax_ids:
                    IVA = t.amount
        if IVA > 0 and not no_product:
            Totales['MntNeto'] = int(round(self.amount_untaxed, 0))
            Totales['TasaIVA'] = round(IVA,2)
            Totales['IVA'] = int(round(self.amount_tax, 0))

        monto_total = int(round(self.amount_total, 0))
        if no_product:
            monto_total = 0
        Totales['MntTotal'] = monto_total
        return Totales

    def _encabezado(self, MntExe=0, no_product=False, tax_include=False):
        xml_header = collections.OrderedDict()
        xml_header['IdDoc'] = self._id_doc(tax_include, MntExe)
        xml_header['Emisor'] = self._emisor()
        xml_header['Receptor'] = self._receptor()
        xml_header['Transporte'] = self._transporte()
        xml_header['Totales'] = self._totales(MntExe, no_product)
        return xml_header

    @api.multi
    def get_barcode(self, no_product=False):
        partner_id = self.partner_id or self.company_id.partner_id
        ted = False
        RutEmisor = self.format_rut(self.company_id.main_id_number)
        result['TED']['DD']['RE'] = RutEmisor
        result['TED']['DD']['TD'] = self.location_id.document_type_id.code
        result['TED']['DD']['F'] = self.get_folio()
        result['TED']['DD']['FE'] = datetime.strftime(datetime.now(), '%Y-%m-%d')
        if not partner_id.commercial_partner_id.main_id_number:
            raise UserError(_("Fill Partner VAT"))
        result['TED']['DD']['RR'] = self.format_rut(partner_id.commercial_partner_id.main_id_number)
        result['TED']['DD']['RSR'] = pysiidte.str_shorten(partner_id.commercial_partner_id.name, 40)
        result['TED']['DD']['MNT'] = int(round(self.amount_total))
        if no_product:
            result['TED']['DD']['MNT'] = 0
        for line in self.move_lines:
            result['TED']['DD']['IT1'] = pysiidte.str_shorten(line.product_id.name,40)
            if line.product_id.default_code:
                result['TED']['DD']['IT1'] = pysiidte.str_shorten(line.product_id.name.replace(
                    '['+line.product_id.default_code+'] ', ''), 40)
            break

        resultcaf = self.location_id.sequence_id.get_caf_file()
        result['TED']['DD']['CAF'] = resultcaf['AUTORIZACION']['CAF']
        if RutEmisor != result['TED']['DD']['CAF']['DA']['RE']:
            raise UserError(_('NO coincide el Dueño del CAF : %s con el emisor Seleccionado: %s' % (
                result['TED']['DD']['CAF']['DA']['RE'], RutEmisor)))
        dte = result['TED']['DD']
        timestamp = pysiidte.time_stamp()
        if date(int(timestamp[:4]), int(timestamp[5:7]), int(timestamp[8:10])) < date(
                int(self.date[:4]), int(self.date[5:7]), int(self.date[8:10])):
            raise UserError("La fecha de timbraje no puede ser menor a la fecha de emisión del documento")
        dte['TSTED'] = timestamp
        ddxml = '<DD>'+dicttoxml.dicttoxml(
            dte, root=False, attr_type=False).decode().replace(
            '<key name="@version">1.0</key>', '', 1).replace(
            '><key name="@version">1.0</key>', ' version="1.0">', 1).replace(
            '><key name="@algoritmo">SHA1withRSA</key>',
            ' algoritmo="SHA1withRSA">').replace(
            '<key name="#text">', '').replace(
            '</key>', '').replace('<CAF>', '<CAF version="1.0">')+'</DD>'
        keypriv = resultcaf['AUTORIZACION']['RSASK'].replace('\t', '')
        # parser = etree.XMLParser(remove_blank_text=True)
        root = etree.XML(ddxml)  # Daniel Blanco: se instancia el parser
        # root = etree.fromstring(ddxml, parser=parser)  # Daniel Blanco: se instancia el parser
        ddxml = etree.tostring(root)  # Daniel Blanco: test pretty_print: la mayoría no lo formatea
        frmt = self.signmessage(ddxml, keypriv)
        ted = '<TED version="1.0">{}<FRMT algoritmo="SHA1withRSA">{}</FRMT></TED>'.format(ddxml.decode(), frmt)
        self.sii_barcode = ted
        image = False
        if ted:
            barcodefile = BytesIO()
            image = self.pdf417bc(ted)
            image.save(barcodefile, 'PNG')
            data = barcodefile.getvalue()
            self.sii_barcode_img = base64.b64encode(data)
        ted += '''
<TmstFirma>{}</TmstFirma>'''.format(timestamp)
        return ted

    def _document_lines(self):
        line_number = 1
        picking_lines = []
        MntExe = 0
        for line in self.move_lines:
            if line.name.startswith('>') and self.hide_kit_components:
                continue
            no_product = False
            if line.product_id.default_code == 'NO_PRODUCT':
                no_product = True
            lines = collections.OrderedDict()
            lines['NroLinDet'] = line_number
            if line.product_id.default_code and not no_product:
                lines['CdgItem'] = collections.OrderedDict()
                lines['CdgItem']['TpoCodigo'] = 'INT1'
                lines['CdgItem']['VlrCodigo'] = line.product_id.default_code
            tax_include = False
            if line.move_line_tax_ids:
                for t in line.move_line_tax_ids:
                    tax_include = t.price_include
                    if t.amount == 0 or t.sii_code in [0]:  # mejor manera de identificar exento de afecto
                        lines['IndExe'] = 1
                        MntExe += int(round(line.subtotal, 0))
            lines['NmbItem'] = pysiidte.str_shorten(line.product_id.name, 80)
            lines['DscItem'] = pysiidte.str_shorten(line.name, 1000)  # descripción más extenza
            if line.product_id.default_code:
                lines['NmbItem'] = pysiidte.str_shorten(
                    line.product_id.name.replace('['+line.product_id.default_code+'] ', ''), 80)
            qty = round(line.quantity_done, 4)
            if qty <= 0:
                qty = round(line.product_uom_qty, 4)
                if qty <=0:
                    raise UserError("¡No puede ser menor o igual que 0!, tiene líneas con cantidad realiada 0")
            if not no_product:
                lines['QtyItem'] = qty
            if self.move_reason in ['5']:
                no_product = True
            if not no_product:
                lines['UnmdItem'] = line.product_uom.name[:4]
                if line.delivery_price_unit > 0:
                    lines['PrcItem'] = round(line.delivery_price_unit, 4)
            if line.discount > 0:
                lines['DescuentoPct'] = line.discount
                lines['DescuentoMonto'] = int(round((((line.discount / 100) * lines['PrcItem']) * qty)))
            if not no_product:
                lines['MontoItem'] = int(round(line.subtotal, 0))
            if no_product:
                lines['MontoItem'] = 0
            line_number += 1
            picking_lines.extend([{'Detalle': lines}])
            if 'IndExe' in lines:
                tax_include = False
        if len(picking_lines) == 0:
            raise UserError(_('No se puede emitir una guía sin líneas'))
        return {
                'picking_lines': picking_lines,
                'MntExe': MntExe,
                'no_product': no_product,
                'tax_include': tax_include, }

    def _dte(self, n_atencion=None):
        dte = collections.OrderedDict()
        picking_lines = self._document_lines()
        dte['Encabezado'] = self._encabezado(
            picking_lines['MntExe'], picking_lines['no_product'], picking_lines['tax_include'])
        count = 0
        lin_ref = 1
        ref_lines = []
        if self.company_id.dte_service_provider == 'SIIHOMO' and isinstance(n_atencion, string_types):
            ref_line = {}
            ref_line = collections.OrderedDict()
            ref_line['NroLinRef'] = lin_ref
            count += 1
            ref_line['TpoDocRef'] = "SET"
            ref_line['FolioRef'] = self.get_folio()
            ref_line['FchRef'] = datetime.strftime(datetime.now(), '%Y-%m-%d')
            ref_line['RazonRef'] = "CASO "+n_atencion+"-" + str(self.sii_batch_number)
            lin_ref = 2
            ref_lines.extend([{'Referencia': ref_line}])
        for ref in self.reference_ids:
            if ref.reference_doc_type.code in ['33', '34']:  # TODO Mejorar Búsqueda
                inv = self.env["account.invoice"].search([('sii_document_number', '=', str(ref.origin))])
            ref_line = {}
            ref_line = collections.OrderedDict()
            ref_line['NroLinRef'] = lin_ref
            if ref.reference_doc_type:
                ref_line['TpoDocRef'] = ref.reference_doc_type.code
                ref_line['FolioRef'] = ref.origin
                ref_line['FchRef'] = datetime.strftime(datetime.now(), '%Y-%m-%d')
                if ref.date:
                    ref_line['FchRef'] = ref.date
            ref_lines.extend([{'Referencia':ref_line}])
        dte['item'] = picking_lines['picking_lines']
        dte['reflines'] = ref_lines
        dte['TEDd'] = self.get_barcode(picking_lines['no_product'])
        return dte

    def _tpo_dte(self):
        tpo_dte = "Documento"
        return tpo_dte

    def _stamp(self, n_atencion=None):
        signature_d = self.env.user.get_digital_signature(self.company_id)
        certp = signature_d['cert'].replace(
            BC, '').replace(EC, '').replace('\n', '')
        folio = self.get_folio()
        tpo_dte = self._tpo_dte()
        doc_id_number = "F{}T{}".format(folio, self.location_id.document_type_id.code)
        doc_id = '<' + tpo_dte + ' ID="{}">'.format(doc_id_number)
        dte = collections.OrderedDict()
        dte[(tpo_dte + ' ID')] = self._dte(n_atencion)
        xml = self.env['account.invoice']._dte_to_xml(dte, tpo_dte)
        root = etree.XML(xml)
        xml_pret = etree.tostring(
                root,
                pretty_print=True
            ).decode().replace(
                    '<' + tpo_dte + '_ID>',
                    doc_id
                ).replace('</' + tpo_dte + '_ID>', '</' + tpo_dte + '>')
        envelope_efact = pysiidte.create_template_doc(xml_pret)
        einvoice = self.env['account.invoice'].sign_full_xml(
            envelope_efact,
            signature_d['priv_key'],
            pysiidte.split_cert(certp),
            doc_id_number, )
        self.sii_xml_dte = einvoice

    def _create_envelope(self, n_atencion=False, RUTRecep="60803000-K"):
        DTEs = {}
        count = 0
        company_id = False
        for rec in self.with_context(lang='es_CL'):
            if rec.company_id.dte_service_provider == 'SIIHOMO':
                # si ha sido timbrado offline, no se puede volver a timbrar
                rec._stamp(n_atencion)
            DTEs.update({str(rec.sii_document_number): rec.sii_xml_dte})
            if not company_id:
                company_id = rec.company_id
            elif company_id.id != rec.company_id.id:
                raise UserError("Está combinando compañías")
            company_id = rec.company_id
        file_name = 'T52'
        dtes=""
        SubTotDTE = ''
        resol_data = self.env['account.invoice'].get_resolution_data(company_id)
        signature_d = self.env.user.get_digital_signature(company_id)
        RUTEmisor = self.format_rut(company_id.main_id_number)
        NroDte = 0
        for rec_id, documento in DTEs.items():
            dtes += '\n' + documento
            NroDte += 1
            file_name += 'F' + rec_id
        SubTotDTE += '''<SubTotDTE>
    <TpoDTE>52</TpoDTE>
    <NroDTE>''' + str(NroDte) + '''</NroDTE>
</SubTotDTE>'''
        RUTRecep = "60803000-K"  # RUT SII
        dtes = self.create_template_envio(
                RUTEmisor,
                RUTRecep,
                resol_data['dte_resolution_date'],
                resol_data['dte_resolution_number'],
                pysiidte.time_stamp(),
                dtes,
                signature_d, SubTotDTE, )
        envio_dte = pysiidte.create_template_env(dtes)
        certp = signature_d['cert'].replace(BC, '').replace(EC, '').replace('\n', '')
        envio_dte = self.env['account.invoice'].sudo(self.env.user.id).with_context(
            {'company_id': company_id.id}).sign_full_xml(
                envio_dte.replace('<?xml version="1.0" encoding="ISO-8859-1"?>\n', ''),
                signature_d['priv_key'],
                pysiidte.split_cert(certp),
                'SetDoc',
                'env'
            )

        return {
                # 'xml_envio': '<?xml version="1.0" encoding="ISO-8859-1"?>\n' + envio_dte,
                'xml_envio': envio_dte,
                'name': file_name,
                'company_id': company_id.id,
                'user_id': self.env.uid, }

    @api.multi
    def do_dte_send(self, n_atencion=False):
        if not self[0].sii_xml_request or self[0].sii_result in ['Rechazado'] or (self[0].company_id.dte_service_provider == 'SIIHOMO' and self[0].sii_xml_request.state in ['', 'NoEnviado']):
            for r in self:
                if r.sii_xml_request:
                    r.sii_xml_request.unlink()
            envio = self._create_envelope(n_atencion, RUTRecep="60803000-K")
            envio_id = self.env['sii.xml.envio'].create(envio)
            for r in self:
                r.sii_xml_request = envio_id.id
            resp = envio_id.send_xml()
            return envio_id
        self[0].sii_xml_request.send_xml()
        return self[0].sii_xml_request

    @api.onchange('sii_message')
    def get_sii_result(self):
        for r in self:
            if r.sii_message:
                # r.sii_result = pysiidte.process_response_xml(xmltodict.parse(r.sii_message))
                r.sii_result = pysiidte1.analyze_sii_result(r.sii_result, r.sii_message, r.sii_xml_request.sii_receipt)
                if r.sii_result in {'Proceso', 'Rechazado', 'Reparo', 'Aceptado'}:
                    r.picking_send_queue_id.active = False
                continue
            if r.sii_xml_request.state == 'NoEnviado':
                r.sii_result = 'EnCola'
                continue
            r.sii_result = r.sii_xml_request.state

    def _get_dte_status(self):
        for r in self:
            if not r.sii_xml_request or r.sii_xml_request.state not in ['Aceptado', 'Reparo']:
                continue
            partner_id = r.partner_id or r.company_id.partner_id
            token = r.sii_xml_request.get_token(self.env.user, r.company_id)
            signature_d = self.env.user.get_digital_signature(r.company_id)
            url = server_url[r.company_id.dte_service_provider] + 'QueryEstDte.jws?WSDL'
            _server = Client(url)
            receptor = r.format_rut(partner_id.commercial_partner_id.main_id_number)
            scheduled_date = datetime.strptime(r.scheduled_date[:10], "%Y-%m-%d").strftime("%d-%m-%Y")
            total = str(int(round(r.amount_total,0)))
            sii_code = str(r.location_id.document_type_id.code)
            response = None
            retry = 0
            while response is None and retry < 1000:
                try:
                    response = _server.service.getEstDte(signature_d['subject_serial_number'][:8],
                                      str(signature_d['subject_serial_number'][-1]),
                                      r.company_id.vat[2:-1],
                                      r.company_id.vat[-1],
                                      receptor[:8],
                                      receptor[-1],
                                      sii_code,
                                      str(r.sii_document_number),
                                      scheduled_date,
                                      total,token)
                    r.sii_message = response
                except Exception:
                    continue
                finally:
                    retry += 1

    @api.multi
    def ask_for_dte_status(self):
        for r in self:
            if not r.sii_xml_request and not r.sii_xml_request.sii_send_ident:
                raise UserError('No se ha enviado aún el documento, aún está en cola de envío interna en odoo')
            if r.sii_xml_request.state not in {'Aceptado', 'Rechazado'}:
                r.sii_xml_request.get_send_status(r.env.user)
        self._get_dte_status()
        self.get_sii_result()

    @api.multi
    def cron_process_queue(self):
        """
        this job process all messages.
        we remove type of work from pasivo to envio if we want to action it manually
        """
        for record in self:
            if record.picking_send_queue_id.active:
                if record.picking_send_queue_id.tipo_trabajo == 'pasivo':
                    record.picking_send_queue_id.tipo_trabajo = 'envio'
                    _logger.info('picking id: %s passed to sending state and processing queue' % record.id)
                    record.picking_send_queue_id._process_job_type()
                elif record.picking_send_queue_id.tipo_trabajo in {'envio', 'consulta'}:
                    _logger.info('picking id: %s already in sending state. processing queue NOW...' % record.id)
                    record.picking_send_queue_id._process_job_type()
                else:
                    _logger.info(
                        'processing queue done nothing over picking id: %s because type of job is %s' % (
                            record.id, record.picking_send_queue_id.tipo_trabajo))
            else:
                _logger.info(
                    'processing queue done nothing over picking id: %s because queue job is inactive' % record.id)
