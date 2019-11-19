import collections
import dicttoxml
import logging
import os
import pytz
import urllib3
import xmltodict
from datetime import datetime, timedelta

from jinja2 import Environment, FileSystemLoader

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_cl_dte.models import pysiidte

urllib3.disable_warnings()
pool = urllib3.PoolManager(cert_reqs='CERT_NONE')

_logger = logging.getLogger(__name__)

dicttoxml.LOG.setLevel(logging.ERROR)

xsdpath = os.path.dirname(os.path.realpath(__file__)).replace('/models', '/static/xsd/')


class L10nClDteConsumoFolios(models.Model):
    _name = "l10n.cl.dte.consumo.folios"

    sii_message = fields.Text(
        string='SII Message',
        copy=False,
        readony=True,
        states={'draft': [('readonly', False)]},)
    sii_xml_request = fields.Text(
        string='SII XML Request',
        copy=False,
        readony=True,
        states={'draft': [('readonly', False)]},)
    sii_xml_response = fields.Text(
        string='SII XML Response',
        copy=False,
        readony=True,
        states={'draft': [('readonly', False)]},)
    sii_send_ident = fields.Text(
        string='SII Send Identification',
        copy=False,
        readony=True,
        states={'draft': [('readonly', False)]},)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('NoEnviado', 'No Enviado'),
        ('Enviado', 'Enviado'),
        ('Aceptado', 'Aceptado'),
        ('Rechazado', 'Rechazado'),
        ('Reparo', 'Reparo'),
        ('Proceso', 'Proceso'),
        ('Reenviar', 'Reenviar'),
        ('Anulado', 'Anulado')],
        'Resultado', index=True, readonly=True, default='draft', track_visibility='onchange', copy=False,
        help='''* The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.
* The 'Pro-forma' status is used the invoice does not have an invoice number.
* The 'Open' status is used when user create invoice, an invoice number is generated. \
Its in open status till user does not pay invoice.
* The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be \
reconciled.
* The 'Cancelled' status is used when user cancel invoice.''')
    move_ids = fields.Many2many(
        'account.move', readony=True, states={'draft': [('readonly', False)]})
    fecha_inicio = fields.Date(
        string="Fecha Inicio", default=fields.Date.today(), readony=True, states={'draft': [('readonly', False)]},)
    fecha_final = fields.Date(
        string="Fecha Final", default=fields.Date.today(), readony=True, states={'draft': [('readonly', False)]},)
    correlativo = fields.Integer(string="Correlativo", readony=True, states={'draft': [('readonly', False)]},)
    sec_envio = fields.Integer(string="Secuencia de Envío", readony=True, states={'draft': [('readonly', False)]},)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.user.company_id.id, readony=True,
        states={'draft': [('readonly', False)]},)
    name = fields.Char(
        string="Detalle", required=True, readony=True, states={'draft': [('readonly', False)]},)
    date = fields.Date(
        string="Date", required=True, default=fields.Date.today(), readony=True,
        states={'draft': [('readonly', False)]},)

    def _get_move_ids(self, start_date=None, company_id=None):
        if start_date is None:
            start_date = self.fecha_inicio
        if company_id is None:
            company_id = self.company_id.id
        return self.env['account.move'].search([
            ('document_type_id.code', 'in', [39, 41]),
            ('date', '=', start_date),
            ('company_id', '=', company_id),
            ]).ids

    @api.onchange('fecha_inicio', 'company_id')
    def set_data(self):
        self.name = self.fecha_inicio
        self.fecha_final = self.fecha_inicio
        self.move_ids = self._get_move_ids()
        consumos = self.search_count([
            ('fecha_inicio', '=', self.fecha_inicio),
            ('state', 'not in', ['draft', 'Rechazado']),
            ('company_id', '=', self.company_id.id),
            ])
        if consumos > 0:
            self.correlativo = (consumos + 1)

    @api.multi
    def unlink(self):
        for libro in self:
            if libro.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete a Validated book.'))
        return super().unlink()

    @api.multi
    def send_xml_file(self, envio_dte=None, file_name="envio"):
        return_value = {'state': 'NoEnviado'}
        signature_d = self.env.user.get_digital_signature(self.company_id)
        try:
            response = pysiidte.send_xml(
                mode=self.company_id.dte_service_provider,
                signature_d=signature_d,
                company_website=self.company_id.website,
                company_vat=self.company_id.vat,
                file_name=file_name,
                xml_message=envio_dte
            )
        except Exception as error:
            _logger.error(error)
            return return_value
        return_value.update({'sii_xml_response': response.data})
        if response.status != 200:
            return return_value
        parse_response = xmltodict.parse(response.data)
        return_value = pysiidte.procesar_recepcion(return_value, parse_response)
        return return_value

    '''
    Funcion para descargar el xml en el sistema local del usuario
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-05-01
    '''
    @api.multi
    def get_xml_file(self):
        file_name = self.name.replace(' ', '_')
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=account.move.consumo_folios\
&field=sii_xml_request&id=%s&filename=%s.xml' % (self.id, file_name),
            'target': 'new',
        }

    @staticmethod
    def format_vat(value):
        if not value or value == '' or value == 0:
            value = "CL666666666"
        rut = value[:10] + '-' + value[10:]
        rut = rut.replace('CL0', '').replace('CL', '')
        return rut

    @api.onchange('fiscal_period', 'tipo_operacion')
    def set_name(self):
        if self.name:
            return
        self.name = self.tipo_operacion
        if self.fiscal_period:
            self.name += " " + self.fiscal_period

    @api.multi
    def validar_consumo_folios(self):
        self._validar()
        return self.write({'state': 'NoEnviado'})

    @staticmethod
    def _process_imps(tax_line_id, totales=0, currency=None, neto=0, tax_mnt=0, mnt_exe=0, taxes=None, imp=None):
        if taxes is None:
            taxes = dict()
        if imp is None:
            imp = dict()
        mnt = tax_line_id.compute_all(totales,  currency, 1)['taxes'][0]
        if mnt['amount'] < 0:
            mnt['amount'] *= -1
            mnt['base'] *= -1
        if tax_line_id.sii_code in [14, 15, 17, 18, 19, 30, 31, 32, 33, 34, 36, 37, 38, 39, 41, 47, 48]:
            # diferentes tipos de IVA retenidos o no
            taxes.setdefault(tax_line_id.id, [tax_line_id, 0])
            taxes[tax_line_id.id][1] += mnt['amount']
            tax_mnt += mnt['amount']
            neto += mnt['base']
        else:
            imp.setdefault(tax_line_id.id, [tax_line_id, 0])
            imp[tax_line_id.id][1] += mnt['amount']
            if tax_line_id.amount == 0:
                mnt_exe += mnt['base']
        return neto, tax_mnt, mnt_exe, taxes, imp

    def get_resumen(self, rec):
        det = dict()
        det['TpoDoc'] = rec.document_type_id.code
        det['NroDoc'] = int(rec.document_number)
        neto = 0
        mnt_exe = 0
        tax_mnt = 0
        ivas = imp = impuestos = {}
        if 'lines' in rec:
            for line in rec.lines:
                if line.tax_ids:
                    for t in line.tax_ids:
                        impuestos.setdefault(t.id, [t, 0])
                        impuestos[t.id][1] += line.price_subtotal_incl
            for key, t in impuestos.items():
                neto, tax_mnt, mnt_exe, ivas, imp = self._process_imps(
                    t[0], t[1], rec.pricelist_id.currency_id, neto, tax_mnt, mnt_exe, ivas, imp)
        else:  # si la boleta fue hecha por contabilidad
            for l in rec.line_ids:
                if l.tax_line_id:
                    if l.tax_line_id and l.tax_line_id.amount > 0:  # supuesto iva único
                        if l.tax_line_id.sii_code in [14, 15, 17, 18, 19, 30, 31, 32, 33, 34, 36, 37, 38, 39, 41,
                                                      47, 48]:
                            # diferentes tipos de IVA retenidos o no
                            if l.tax_line_id.id not in ivas:
                                ivas[l.tax_line_id.id] = [l.tax_line_id, 0]
                            ivas[l.tax_line_id.id][1] += l.credit > 0 and l.credit or l.debit
                            tax_mnt += l.credit > 0 and l.credit or l.debit
                        else:
                            if l.tax_line_id.id not in imp:
                                imp[l.tax_line_id.id] = [l.tax_line_id, 0]
                            imp[l.tax_line_id.id][1] += l.credit > 0 and l.credit or l.debit
                            tax_mnt += l.credit > 0 and l.credit or l.debit
                elif l.tax_ids and l.tax_ids[0].amount > 0:
                    neto += l.credit > 0 and l.credit or l.debit
                elif not l.tax_line_id and rec.document_type_id.code == '41':  # caso monto exento
                    mnt_exe += l.credit
        if mnt_exe > 0:
            det['MntExe'] = int(round(mnt_exe, 0))
        if tax_mnt > 0:
            det['MntIVA'] = int(round(tax_mnt))
            for key, t in ivas.items():
                det['TasaIVA'] = t[0].amount
        monto_total = int(round((neto + mnt_exe + tax_mnt), 0))
        det['MntNeto'] = int(round(neto))
        det['MntTotal'] = monto_total
        return det

    @staticmethod
    def _last(folio, items):  # se asumen que vienen ordenados de menor a mayor
        for c in items:
            if folio > c['Final'] and folio > c['Inicial']:
                return c
        return False

    def _nuevo_rango(self, folio, f_contrario, contrarios):
        last = self._last(folio, contrarios)  # obtengo el último tramo de los contrarios
        if last and last['Inicial'] > f_contrario:
            return True
        return False

    def _orden(self, folio, rangos, contrarios, continuado=True):
        last = self._last(folio, rangos)
        if not continuado or not last or self._nuevo_rango(folio, last['Final'], contrarios):
            r = collections.OrderedDict()
            r['Inicial'] = folio
            r['Final'] = folio
            rangos.append(r)
            return rangos
        result = []
        for r in rangos:
            if r['Final'] == last['Final'] and folio > last['Final']:
                r['Final'] = folio
            result.append(r)
        return result

    def _rangosU(self, resumen, rangos, continuado=True):
        if not rangos:
            rangos = collections.OrderedDict()
        folio = resumen['NroDoc']
        if 'A' in resumen:
            utilizados = rangos['itemUtilizados'] if 'itemUtilizados' in rangos else []
            if 'itemAnulados' not in rangos:
                rangos['itemAnulados'] = []
                r = collections.OrderedDict()
                r['Inicial'] = folio
                r['Final'] = folio
                rangos['itemAnulados'].append(r)
            else:
                rangos['itemAnulados'] = self._orden(resumen['NroDoc'], rangos['itemAnulados'], utilizados, continuado)
                return rangos
        anulados = rangos['itemAnulados'] if 'itemAnulados' in rangos else []
        if 'itemUtilizados' not in rangos:
            rangos['itemUtilizados'] = []
            r = collections.OrderedDict()
            r['Inicial'] = folio
            r['Final'] = folio
            rangos['itemUtilizados'].append(r)
        else:
            rangos['itemUtilizados'] = self._orden(resumen['NroDoc'], rangos['itemUtilizados'], anulados, continuado)
        return rangos

    def _setResumen(self, resumen, resumenP, continuado=True):
        resumenP['TipoDocumento'] = resumen['TpoDoc']
        if 'MntNeto' in resumen and 'MntNeto' not in resumenP:
            resumenP['MntNeto'] = resumen['MntNeto']
        elif 'MntNeto' in resumen:
            resumenP['MntNeto'] += resumen['MntNeto']
        elif 'MntNeto' not in resumenP:
            resumenP['MntNeto'] = 0
        if 'MntIVA' in resumen and 'MntIva' not in resumenP:
            resumenP['MntIva'] = resumen['MntIVA']
        elif 'MntIVA' in resumen:
            resumenP['MntIva'] += resumen['MntIVA']
        elif 'MntIva' not in resumenP:
            resumenP['MntIva'] = 0
        if 'TasaIVA' in resumen and 'TasaIVA' not in resumenP:
            resumenP['TasaIVA'] = resumen['TasaIVA']
        if 'MntExe' in resumen and 'MntExento' not in resumenP:
            resumenP['MntExento'] = resumen['MntExe']
        elif 'MntExe' in resumen:
            resumenP['MntExento'] += resumen['MntExe']
        elif 'MntExento' not in resumenP:
            resumenP['MntExento'] = 0
        if 'MntTotal' not in resumenP:
            resumenP['MntTotal'] = resumen['MntTotal']
        else:
            resumenP['MntTotal'] += resumen['MntTotal']
        if 'FoliosEmitidos' in resumenP:
            resumenP['FoliosEmitidos'] += 1
        else:
            resumenP['FoliosEmitidos'] = 1

        if 'FoliosAnulados' not in resumenP:
            resumenP['FoliosAnulados'] = 0
        if 'Anulado' in resumen:  # opción de indicar de que está anulado por panel SII no por nota
            resumenP['FoliosAnulados'] += 1
        elif 'FoliosUtilizados' in resumenP:
            resumenP['FoliosUtilizados'] += 1
        else:
            resumenP['FoliosUtilizados'] = 1
        if str(resumen['TpoDoc'])+'_folios' not in resumenP:
            resumenP[str(resumen['TpoDoc'])+'_folios'] = dict()
        resumenP[str(resumen['TpoDoc'])+'_folios'] = self._rangosU(
            resumen, resumenP[str(resumen['TpoDoc'])+'_folios'], continuado)
        return resumenP

    @staticmethod
    def _get_default_resume_values():
        default_values = dict()
        default_values['TipoDocumento'] = '39'
        default_values['MntNeto'] = 0
        default_values['MntIva'] = 0
        default_values['MntExento'] = 0
        default_values['MntTotal'] = 0
        default_values['FoliosEmitidos'] = 0
        default_values['FoliosAnulados'] = 0
        default_values['FoliosUtilizados'] = 0
        return default_values

    @staticmethod
    def _get_template_xml(values, template_name):
        base_path = os.path.dirname(os.path.dirname(__file__))
        env = Environment(loader=FileSystemLoader(os.path.join(base_path, 'template')))
        template = env.get_template('{}.xml'.format(template_name))
        xml = template.render(values)
        xml = xml.replace('&', '&amp;')
        return xml

    def _validar(self):
        company_id = self.company_id
        try:
            signature_d = self.env.user.get_digital_signature(company_id)
        except:
            raise Warning(_('''There is no Signer Person with an \
        authorized signature for you in the system. Please make sure that \
        'user_signature_key' module has been installed and enable a digital \
        signature, for you or make the signer to authorize you to use his \
        signature.'''))
        certp = signature_d['cert'].replace(pysiidte.BC, '').replace(pysiidte.EC, '').replace('\n', '')
        resumenes = {}
        TpoDocs = []
        orders = []
        recs = sorted(self.with_context(lang='es_CL').move_ids, key=lambda t: t.document_number)
        for rec in recs:
            if not rec.document_type_id or rec.document_type_id.code not in {'39', '41', '61'}:
                raise UserError("Por este medio solamente se pueden declarar Boletas o "
                                "Notas de crédito Electrónicas, Por favor elimine el documento %s del listado"
                                % rec.name)
            rec.sended = True
            if not rec.document_number:
                orders += self.env['pos.order'].search([
                    ('account_move', '=', rec.id),
                    ('invoice_id', '=', False),
                    ('document_number', 'not in', [False, '0']),
                    ('document_type_id.code', 'in', [39, 41, 61]),
                ]).ids
            else:
                resumen = self.get_resumen(rec)
                TpoDoc = resumen['TpoDoc']
                TpoDocs.append(TpoDoc)
                if TpoDoc not in resumenes:
                    resumenes[TpoDoc] = dict()
                resumenes[TpoDoc] = self._setResumen(resumen, resumenes[TpoDoc])
        if orders:
            orders_array = sorted(
                self.env['pos.order'].browse(orders).with_context(lang='es_CL'), key=lambda t: t.document_number)
            ant = 0
            for order in orders_array:
                resumen = self.get_resumen(order)
                TpoDoc = resumen['TpoDoc']
                TpoDocs.append(TpoDoc)
                if TpoDoc not in resumenes:
                    resumenes[TpoDoc] = dict()
                resumenes[TpoDoc] = self._setResumen(resumen, resumenes[TpoDoc], ((ant+1) == order.document_number))
                ant = order.document_number
        resumen = []
        for r, value in resumenes.items():
            if str(r)+'_folios' in value:
                folios = value[str(r)+'_folios']
                if 'itemUtilizados' in folios:
                    utilizados = []
                    for rango in folios['itemUtilizados']:
                        utilizados.append({'RangoUtilizados': rango})
                    folios['itemUtilizados'] = utilizados
                if 'itemAnulados' in folios:
                    anulados = []
                    for rango in folios['itemAnulados']:
                        anulados.append({'RangoAnulados': rango})
                    folios['itemAnulados'] = anulados
                value[str(r)+'_folios'] = folios
            resumen.extend([{'Resumen': value}])
        if not resumen:
            default_value = self._get_default_resume_values()
            resumen.extend([{'Resumen': default_value}])
        resol_data = self.env['account.invoice'].get_resolution_data(company_id)
        doc_id = 'CF_'+self.date
        xml_timestamp = pysiidte.time_stamp()
        values = {
            'id': doc_id,
            'RutEmisor': self.format_vat(company_id.vat),
            'RutEnvia': signature_d['subject_serial_number'],
            'FchResol': resol_data['dte_resolution_date'],
            'NroResol': resol_data['dte_resolution_number'],
            'FchInicio': self.fecha_inicio,
            'FchFinal': self.fecha_final,
            'Correlativo': self.correlativo,
            'SecEnvio': self.sec_envio,
            'TmstFirmaEnv': xml_timestamp,
            'items': resumen,
        }
        xml = self._get_template_xml(values, 'template_consumo_folios')
        envio_dte = pysiidte.sign_full_xml(xml, signature_d['priv_key'], certp, doc_id, 'consu')
        doc_id += '.xml'
        self.sii_xml_request = envio_dte
        return envio_dte, doc_id

    @api.multi
    def do_dte_send_consumo_folios(self):
        if self.state not in ['NoEnviado', 'Rechazado']:
            raise UserError("El libro ya ha sido enviado")
        envio_dte, doc_id = self._validar()
        result = self.send_xml_file(envio_dte, doc_id)
        self.write({
            'sii_xml_response': result.get('sii_xml_response'),
            'sii_send_ident': result.get('sii_send_ident'),
            'state': result.get('state'),
            'sii_xml_request': envio_dte,
        })

    @api.multi
    def ask_for_dte_status(self):
        if self.state == 'Enviado':
            signature_d = self.env.user.get_digital_signature(self.company_id)
            token = pysiidte.sii_token(
                self.company_id.dte_service_provider,
                signature_d['priv_key'],
                signature_d['cert']
            )
            response = pysiidte.get_send_status(token, self.company_id.dte_service_provider, self.sii_send_ident,
                                                self.company_id.vat)
            parsed_response = xmltodict.parse(response)
            state = pysiidte.process_response_xml(parsed_response)
            self.write({
                'sii_message': response,
                'state': state,
            })

    @api.model
    def _create_new_folio(self):
        yesterday = (datetime.now(tz=pytz.timezone('America/Santiago')) - timedelta(days=1)).strftime('%Y-%m-%d')
        move_ids = self._get_move_ids(yesterday, self.env.user.company_id.id)
        folio = self.create({
            'state': 'NoEnviado',
            'name': yesterday,
            'fecha_inicio': yesterday,
            'fecha_final': yesterday,
            'date': yesterday,
            'move_ids': [(6, 0, move_ids)],
        })
        return folio

    @api.model
    def _cron_process_queue(self):
        folio = self._create_new_folio()
        try:
            folio.do_dte_send_consumo_folios()
            folio.ask_for_dte_status()
        except Exception as error:
            _logger.info('Send consumo folios by cron fail: %s' % error)
            folio.update({'state': 'draft'})