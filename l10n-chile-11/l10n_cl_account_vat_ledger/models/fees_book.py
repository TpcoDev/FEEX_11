# -*- coding: utf-8 -*-
import builtins
import collections
import json
import logging
import os
import textwrap
import xml.dom.minidom
from datetime import date, datetime, timedelta

import OpenSSL
import pysiidte
from bs4 import BeautifulSoup as bs
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from lxml import etree
from OpenSSL.crypto import *

from odoo import _, api, fields, models
from odoo.exceptions import UserError

try:
    from cStringIO import StringIO
except:
    from io import StringIO
try:
    from zeep.client import Client
except:
    pass
try:
    import urllib3
except:
    pass
pool = urllib3.PoolManager(timeout=30)

_logger = logging.getLogger(__name__)

try:
    import xmltodict
except ImportError:
    _logger.info('Cannot import xmltodict library')

try:
    import dicttoxml
except ImportError:
    _logger.info('Cannot import dicttoxml library')

try:
    from pdf417gen import encode, render_image
except ImportError:
    _logger.info('Cannot import pdf417gen library')

try:
    import M2Crypto
except ImportError:
    _logger.info('Cannot import M2Crypto library')

try:
    import base64
except ImportError:
    _logger.info('Cannot import base64 library')

try:
    import hashlib
except ImportError:
    _logger.info('Cannot import hashlib library')

try:
    import cchardet
except ImportError:
    _logger.info('Cannot import cchardet library')

try:
    #from SOAPpy import SOAPProxy
    from zeep.client import Client
except ImportError:
    _logger.info('Cannot import zeep.client')

try:
    from signxml import XMLSigner, XMLVerifier, methods
except ImportError:
    _logger.info('Cannot import signxml')

dicttoxml.LOG.setLevel(logging.ERROR)

type_ = FILETYPE_PEM

server_url = pysiidte.server_url
BC = pysiidte.BC
EC = pysiidte.EC
connection_status = pysiidte.connection_status
tag_replace01 = pysiidte.tag_replace01
tag_replace_1 = pysiidte.tag_replace_1
tag_replace02 = pysiidte.tag_replace02
tag_replace_2 = pysiidte.tag_replace_2
tag_round = pysiidte.tag_replace_2
all_tags = tag_round + tag_replace01 + tag_replace_1 + tag_replace02 + \
           tag_replace_2

operation_type_ = {'purchase': 'COMPRA',
                   'sale': 'VENTA'}

report_type_ = {'special': 'ESPECIAL',
                'monthly': 'MENSUAL',
                'amendment': 'RECTIFICA'}

sending_type_ = {'adjustment': 'AJUSTE',
                 'partial': 'PARCIAL',
                 'total': 'TOTAL',
                 'final': 'FINAL'}

xsdpath = os.path.dirname(os.path.realpath(__file__)).replace(
    '/models', '/../l10n_cl_dte/static/xsd/')

def to_json(colnames, rows):
    all_data = []
    for row in rows:
        each_row = collections.OrderedDict()
        i = 0
        for colname in colnames:
            each_row[colname] = pysiidte.char_replace(row[i])
            i += 1
        all_data.append(each_row)
    return all_data


def db_handler(method):
    def call(self, *args, **kwargs):
        _logger.info(args)
        query = method(self, *args, **kwargs)
        cursor = self.env.cr
        try:
            cursor.execute(query)
        except:
            return False
        rows = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        _logger.info('colnames: {}'.format(colnames))
        _logger.info('rows: {}'.format(rows))
        return to_json(colnames, rows)
    return call


class AccountMoveBook(models.Model):
    _name = "account.move.book"

    sii_receipt = fields.Text(
        string='SII Message',
        copy=False)
    sii_message = fields.Text(
        string='SII Message',
        copy=False)
    sii_xml_request = fields.Text(
        string='SII XML Request',
        # compute='set_values',
        store=True,
        copy=False)
    sii_xml_response = fields.Text(
        string='SII XML Response',
        copy=False)
    sii_send_ident = fields.Text(
        string='SII Send Identification',
        copy=False)
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
        'Resultado'
        , index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=""" * The 'Draft' status is used when a user is encoding a new and\
unconfirmed Invoice.\n
* The 'Pro-forma' status is used the invoice does not have an invoice number.
* The 'Open' status is used when user create invoice, an invoice number is \
generated. Its in open status till user does not pay invoice.\n
* The 'Paid' status is set automatically when the invoice is paid. Its related
 journal entries may or may not be reconciled.\n
* The 'Cancelled' status is used when user cancel invoice.""")
    
    journal_ids = fields.Many2many('account.journal',
        string = 'Jornals',
        states={'draft': [('readonly', False)]})

    invoice_ids = fields.Many2many(
        'account.invoice', readonly=True, string="Invoices",
        states={'draft': [('readonly', False)]})

    report_type = fields.Selection([
                ('special', 'Especial'),
                ('monthly', 'Mensual'),
                ('amendment', 'Rectifica'), ], string="Book Type",
                default='monthly', required=True, readonly=True,
                states={'draft': [('readonly', False)]},
                help=u"""Mensual: corresponde a libros regulares.
Especial: corresponde a un libro solicitado vía una notificación.
Rectifica: Corresponde a un libro que reemplaza a uno ya recibido por el SII, \
requiere un Código de Autorización de Reemplazo de Libro Electrónico.""")
    operation_type = fields.Selection([
                ('purchase', 'Purchases'),
                ('sale', 'Sales'), ],
                string="Tipo de operación",
                default="purchase",
                required=True,
                readonly=True,
                states={'draft': [('readonly', False)]}
            )
    sending_type = fields.Selection([
        ('adjustment', 'Ajuste'),
        ('partial', 'Parcial'), 
        ('total', 'Total'),
        ('final', 'Final'),
        ],
        string="Tipo de Envío",
        default="total", required=True, readonly=True,
        states={'draft': [('readonly', False)], })
    notification_number = fields.Char(
        string="Notification invoice number", readonly=True,
        states={'draft': [('readonly', False)], })
    taxes = fields.One2many(
        'account.move.book.tax', 'book_id', string="Tax Detail")
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.user.company_id.currency_id,
        required=True, track_visibility='always')
    total_vat_affected = fields.Monetary(
        string="Total VAT Affected", readonly=True,
        #compute="set_values",
        store=True)
    total_exempt = fields.Monetary(
        string="Total Exempt", readonly=True,
        #compute='set_values',
        store=True)
    total_vat = fields.Monetary(
        string="Total VAT", readonly=True,
        #compute='set_values',
        store=True)
    total_other_taxes = fields.Monetary(
        string="Total Other Taxes", readonly=True,
        #compute='set_values',
        store=True)
    total = fields.Monetary(
        string="Total", readonly=True,
        #compute='set_values',
        store=True)
    fiscal_period = fields.Char(
        string='Fiscal Period', required=True, readonly=True,
        default=lambda x: date.today().strftime('%Y-%m'),
        states={'draft': [('readonly', False)], })
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.user.company_id.id, readonly=True,
        states={'draft': [('readonly', False)], })
    name = fields.Char(
        string="Detail", required=True, readonly=True,
        states={'draft': [('readonly', False)], })
    proportion_factor = fields.Float(
        string="Proportion Factor", readonly=True,
        states={'draft': [('readonly', False)], })
    nro_segmento = fields.Integer(
        string="Número de Segmento", readonly=True,
        states={'draft': [('readonly', False)], },
        help=u"""Sólo si el TIPO DE ENVIO es partial.""")
    date = fields.Date(
        string="Date", required=True, readonly=True,
        default=fields.Date.today(),
        states={'draft': [('readonly', False)], })
    receipts = fields.One2many(
        'account.move.book.receipts', 'book_id', string="receipts",
        readonly=True, states={'draft': [('readonly', False)]})
    amendment_code = fields.Char(string="Código de Rectificación")

    @staticmethod
    def line_tax_view():
        a = """
select 	invoice_id,
journal_id,
line_id,
/*company_id,*/
tax_amount,
price_subtotal,
tax_code,
no_rec_code,
vat_for_common_use,
no_rec,
amount_total,
"TpoDoc",
"NroDoc",
"TpoImp",
"TasaImp",
"FchDoc",
"RUTDoc",
"RznSoc",
"TpoDocRef",
"FolioDocRef",
(CASE
WHEN tax_amount is not null THEN 0
ELSE price_subtotal
END) as "MntExe",
(CASE
WHEN tax_amount is null THEN 0
ELSE price_subtotal
END) as "MntNeto",
coalesce(round(
(CASE WHEN tax_code = 15 then 0
ELSE tax_amount END)
- (case when a.no_rec_code != '0' then
tax_amount else
(case when a.no_rec = '1' then tax_amount
else 0 end)
end) -
(case when vat_for_common_use then tax_amount
else 0 end), 2), 0.0) as "MntIVA",
(CASE
WHEN a.tax_code != 14 then 1
ELSE 0
END) as "OtrosImp",
(CASE
WHEN a.tax_code != 14 then a.tax_code
ELSE 0 END) as "CodImp",
(CASE
WHEN a.tax_code != 14 then "TasaImp"
ELSE 0 END) as "aTasaImp",
round((CASE
WHEN a.tax_code = 15 THEN tax_amount
ELSE 0
END), 0) as "MntImp",
round((CASE
WHEN "TasaImp" = 19 AND a.tax_code = 15
THEN tax_amount ELSE 0 END), 2)
as "IVARetTotal",
(CASE
WHEN "TasaImp" < 19 AND a.tax_code = 15
THEN tax_amount ELSE 0 END)
as "IVARetParcial",
(case
when a.no_rec_code != '0'
then 1
else (case
when a.no_rec = '1' then 1 else 0
end)
end) as "IVANoRec",
(case when a.no_rec_code != '0' then
cast(a.no_rec_code as integer) else
(case when a.no_rec = '1' then 1
else 0 end)
end) as "CodIVANoRec",
round((case when a.no_rec_code != '0' then
tax_amount
else
(case when a.no_rec = '1' then tax_amount
else 0 end)
end), 2) as "MntIVANoRec",
round((case when vat_for_common_use then
tax_amount
else 0 end), 2) as "IVAUsoComun",
(case when a.no_rec then 0 else 0 end)
as "MntSinCred",
round(a.amount_total, 0) as "MntTotal",
(case when a.no_rec then 0 else 0 end)
as "IVANoRetenido"
from
(select
ai.id as invoice_id,
aj.id as journal_id,
/*ai.company_id,*/
al.id as line_id,
dcl.code as "TpoDoc",
cast(ai.invoice_number as integer) as "NroDoc",
(CASE WHEN at.sii_code in (14, 15) THEN 1 ELSE 0 END) as "TpoImp",
COALESCE(round(abs(at.amount), 0), 0) as "TasaImp",
ai.date_invoice as "FchDoc",
trim(leading '0' from substring(rp.vat from 3 for 8)) || '-' ||
right(rp.vat, 1) as "RUTDoc",
left(rp.name, 50) as "RznSoc",
ref.code as "TpoDocRef",
ref.origin as "FolioDocRef",
at.tax_group_id,
at.no_rec,
at.sii_code as tax_code,
ai.vat_for_common_use,
ai.no_rec_code,
al.price_subtotal,
abs(al.price_subtotal * at.amount / 100) as tax_amount,
ai.amount_untaxed,
ai.amount_total
from account_invoice_line_tax alt
join account_tax at
on alt.tax_id = at.id
right join account_invoice_line al
on al.id = alt.invoice_line_id
left join account_invoice ai
on ai.id = al.invoice_id
left join account_journal aj
on aj.id = ai.journal_id
left join account_document_type dcl
on dcl.id = ai.document_type_id
left join res_partner rp
on rp.id = ai.partner_id
left join
(select ar.invoice_id, ar.origin, dcl.code from
(select
invoice_id,
origin,
"reference_doc_type" as tipo
from account_invoice_reference) ar
left join account_document_type dcl
on ar.tipo = dcl.id) as ref
on ref.invoice_id = ai.id
order by ai.id, al.id, dcl.code, at.id) a
"""
        # raise UserError(a)
        return a

    @db_handler
    def _summary_by_period(self):
        try:
            account_invoice_ids = [str(x.id) for x in self.invoice_ids]
        except:
            return False
        a = """
select
"TpoDoc"
"TpoDoc",
max("TpoImp") as "TpoImp",
count("TpoDoc") as "TotDoc",
sum(case when "MntExe" > 0 then 1 else 0 end) as "TotOpExe",
sum(cast("MntExe" as integer)) as "TotMntExe",
sum(cast("MntNeto" as integer)) as "TotMntNeto",
sum(case when "IVANoRec" > 0 then 0 else
(case when "MntIVA" = 0 then 0 else
(case when "TpoDoc" = '46' then Null else 1 end)
end)
end) as "TotOpIVARec",
sum(cast("MntIVA" as integer)) as "TotMntIVA",
/* tot otros imp */
sum(case when "MntImp" > 0 then 1 else 0 end) as "TotOtrosImp",
sum(case when "MntImp" > 0 then 15 else 0 end) as "CodImp",
sum(case when "MntImp" > 0 then "MntImp" else 0 end) as "TotMntImp",
/*sum(case when "IVARetTotal" > 0 then 1 else 0 end)
as "TotOpIVARetTotal",*/
sum(case when "IVARetTotal" > 0 then "IVARetTotal" else 0 end)
as "TotIVARetTotal",
/*sum(case when "IVARetParcial" > 0 then 1 else 0 end)
as "TotOpIVARetParcial",*/
sum(case when "IVARetParcial" > 0 then "IVARetParcial" else 0 end)
as "TotIVARetParcial",
/* TotOpActivoFijo, TotMntActivoFijo, TotMntIVAActivoFijo */
sum("IVANoRec") as "TotIVANoRec",
/* El TOT da la cantidad de iteraciones dentro de
la matriz (normalmente 1)*/
/*max((case when "IVANoRec" > 0 then at_sii_code else 0 end))
as "CodIVANoRec",*/
/* revisar repeticion y revisar de donde obtener el codigo */
max((case when "IVANoRec" > 0 then
"CodIVANoRec" else '0' end)) as "CodIVANoRec",
sum((case when "IVANoRec" > 0 then 1 else 0 end)) as "TotOpIVANoRec",
sum(cast(round((case when "IVANoRec" > 0 then "MntIVANoRec" else 0 end),
0) as integer)) as "TotMntIVANoRec",
sum(cast(round((case when "IVAUsoComun" > 0 then 1 else 0 end),
0) as integer)) as "TotOpIVAUsoComun",
sum(cast(round((case when "IVAUsoComun" > 0 then "IVAUsoComun" else
0 end),
0) as integer)) as "TotIVAUsoComun",
sum(cast(round((case when "IVAUsoComun" > 0 then "IVAUsoComun"
* %s else 0 end),
0) as integer)) as "TotCredIVAUsoComun",
sum(cast(round((case when "IVANoRec" > 0 then 0 else 0 end), 0)
as integer)) as "TotImpSinCredito",
sum(cast("MntExe" + "MntNeto" + "MntIVA" + "MntIVANoRec"
+ "IVAUsoComun"
- (case when "IVARetTotal" > 0 then "IVARetTotal" else 0 end)
- (case when "IVARetParcial" > 0 then "IVARetParcial" else 0 end)
as integer)) as "TotMntTotal",
sum(case when "IVANoRetenido" > 0 then 1 else 0 end)
as "TotOpIVANoRetenido",
sum(case when "IVANoRetenido" > 0 then "IVANoRetenido" else 0 end)
as "TotIVANoRetenido"
from(
select "TpoDoc",
"NroDoc",
max("TpoImp") as "TpoImp",
max("TasaImp") as "TasaImp",
"FchDoc",
"RUTDoc",
"RznSoc",
"TpoDocRef",
"FolioDocRef",
round(sum("MntExe"), 0) as "MntExe",
round(
(CASE WHEN "TpoDoc" = '46' THEN max("MntNeto")
ELSE sum("MntNeto") END), 0)
as "MntNeto",
round(sum("MntIVA"), 0) as "MntIVA",
max("OtrosImp") as "OtrosImp",
max("CodImp") as "CodImp",
max("aTasaImp") as "TasaImp",
max("MntImp") as "MntImp",
round(sum("IVARetTotal"), 0) as "IVARetTotal",
sum("IVARetParcial") as "IVARetParcial",
max("IVANoRec") as "IVANoRec",
max("CodIVANoRec") as "CodIVANoRec",
sum("MntIVANoRec") as "MntIVANoRec",
round(sum("IVAUsoComun"), 0) as "IVAUsoComun",
sum("MntSinCred") as "MntSinCred",
max("MntTotal") as "MntTotal",
max("IVANoRetenido") as "IVANoRetenido"
from (%s
where invoice_id in (%s)
) a
group by "TpoDoc", "NroDoc",
"FchDoc", "RUTDoc", "RznSoc",
"TpoDocRef", "FolioDocRef"
order by "TpoDoc", "NroDoc") b
group by
"TpoDoc"
""" % (self.proportion_factor, self.line_tax_view(), ', '.join(
            account_invoice_ids))
        # raise UserError(a)
        return a

    @db_handler
    def _detail_by_period(self):
        if True:  # try:
            account_invoice_ids = [str(x.id) for x in self.invoice_ids]
        else:  # except:
            return False
        a = """
select "TpoDoc",
"NroDoc",
max("TpoImp") as "TpoImp",
max("TasaImp") as "uTasaImp",
"FchDoc",
"RUTDoc",
"RznSoc",
"TpoDocRef",
"FolioDocRef",
round(sum("MntExe"), 0) as "MntExe",
round(
(CASE WHEN "TpoDoc" = '46' THEN max("MntNeto")
ELSE sum("MntNeto") END), 0)
as "MntNeto",
round(sum("MntIVA"), 0) as "MntIVA",
max("OtrosImp") as "OtrosImp",
max("CodImp") as "CodImp",
max("aTasaImp") as "TasaImp",
max("MntImp") as "MntImp",
round(sum("IVARetTotal"), 0) as "IVARetTotal",
sum("IVARetParcial") as "IVARetParcial",
max("IVANoRec") as "IVANoRec",
max("CodIVANoRec") as "CodIVANoRec",
round(sum("MntIVANoRec"), 0) as "MntIVANoRec",
round(sum("IVAUsoComun"), 0) as "IVAUsoComun",
sum("MntSinCred") as "MntSinCred",
max("MntTotal") as "MntTotal",
max("IVANoRetenido") as "IVANoRetenido"
from (%s
where invoice_id in (%s)
) a
group by "TpoDoc", "NroDoc",
"FchDoc", "RUTDoc", "RznSoc",
"TpoDocRef", "FolioDocRef"
order by "TpoDoc", "NroDoc"
        """ % (self.line_tax_view(), ', '.join(account_invoice_ids))
        # raise UserError(a)
        return a

    def _record_totals(self, jvalue):
        _logger.info(json.dumps(jvalue))
        if jvalue:
            self.total_vat_affected = sum([x['TotMntNeto'] for x in jvalue])
            self.total_exempt = sum([x['TotMntExe'] for x in jvalue])
            self.total_vat = sum([x['TotMntIVA'] for x in jvalue])
            self.total_other_taxes = 0
            self.total = sum([x['TotMntIVA'] for x in jvalue])

    @staticmethod
    def _envelope_book(xml_pret):
        ''' Se comenta porque el xsd dice que la etiqueta va sola '''
        return """<?xml version="1.0" encoding="ISO-8859-1"?>
<LibroCompraVenta xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte LibroCV_v10.xsd" version="1.0">\
{}</LibroCompraVenta>""".format(xml_pret)
        '''
        return """<?xml version="1.0" encoding="ISO-8859-1"?>
<LibroCompraVenta >\
{}</LibroCompraVenta>""".format(xml_pret)
'''

    @staticmethod
    def insert_son_values(
            parent_dictionary, grand_parent_tag, parent_tag, son_tags):
        dict2n = collections.OrderedDict()
        dict2n[grand_parent_tag] = []
        for d2 in parent_dictionary[grand_parent_tag]:
            dict2nlist = collections.OrderedDict()
            for k, v in d2.items():
                if k == parent_tag:
                    dict2nlist[k] = collections.OrderedDict()
                    print(k, v)
                elif k in son_tags and int(v) != 0:
                    try:
                        dict2nlist[parent_tag][k] = v
                    except KeyError:
                        pass
                else:
                    dict2nlist[k] = v
                print(k, v)
            dict2n[grand_parent_tag].append(dict2nlist)
        return dict2n

    @staticmethod
    def replace_tags(xml_part, tag_list, zero):
        for tag in tag_list:
            xml_part = xml_part.replace('<{0}>{1}</{0}>'.format(tag, zero), '')
        return xml_part

    def _record_detail(self, dict1, dict2):
        if True:
            inv_obj = self.env['account.invoice']
            #-try:
            resol_data = inv_obj.get_resolution_data(self.company_id)
            signature_d = self.get_digital_signature_pem(self.company_id)
            #-except:
                #-_logger.info(u'First entry: unknown company')
                #-return False
            dict1n = self.insert_son_values(
                dict1, 'ResumenPeriodo', 'TotIVANoRec',
                ['CodIVANoRec', 'TotMntIVANoRec', 'TotOpIVANoRec'])
            dict1n = self.insert_son_values(
                dict1n, 'ResumenPeriodo', 'TotOtrosImp',
                ['CodImp', 'TotMntImp'])
            xml_detail1 = self.replace_tags(self.replace_tags(
                self.replace_tags(
                dicttoxml.dicttoxml(
                    dict1n, root=False, attr_type=False).decode().replace(
                    'item', 'TotalesPeriodo').replace('>0.0<', '>0<').replace(
                    '.0<', '<'), tag_replace01, '0'), tag_replace_1, ''),
                    tag_replace01, '0.0')
            dict2n = self.insert_son_values(
                dict2, 'Detalles', 'IVANoRec', ['CodIVANoRec', 'MntIVANoRec'])
            # raise UserError(json.dumps(dict2n))
            dict2n = self.insert_son_values(
                dict2n, 'Detalles', 'OtrosImp', ['CodImp', 'TasaImp', 'MntImp'])
            # print dict2n
            xml_detail2 = dicttoxml.dicttoxml(
                dict2n, root=False, attr_type=False).decode().replace(
                'item', 'Detalle').replace('<Detalles>', '').replace(
                '</Detalles>', '').replace('>0.0<', '>0<').replace(
                    '.0<', '<')
            xml_detail2 = self.replace_tags(
                self.replace_tags(xml_detail2.replace(
                    '<TpoDocRef/>', '').replace(
                    '<FolioDocRef/>', ''), tag_replace02, '0'),
                tag_replace_2, '').replace('uTasaImp', 'TasaImp')
            print(xml_detail2)
            # raise UserError('xml_detail2')
            xml_envio_report = """<EnvioLibro ID="{}">\
<Caratula>\
<RutEmisorLibro>{}</RutEmisorLibro>\
<RutEnvia>{}</RutEnvia>\
<PeriodoTributario>{}</PeriodoTributario>\
<FchResol>{}</FchResol>\
<NroResol>{}</NroResol>\
<TipoOperacion>{}</TipoOperacion>\
<TipoLibro>{}</TipoLibro>\
<TipoEnvio>{}</TipoEnvio>\
<FolioNotificacion>{}</FolioNotificacion>\
<CodAutRec>{}</CodAutRec>\
</Caratula>{}{}<TmstFirma>{}</TmstFirma></EnvioLibro>""".format(
                self.name.replace(' ', '_'),
                inv_obj.format_vat(self.company_id.vat),
                signature_d['subject_serial_number'],
                self.fiscal_period,
                resol_data['dte_resolution_date'],
                resol_data['dte_resolution_number'],
                operation_type_[self.operation_type],
                report_type_[self.report_type],
                sending_type_[self.sending_type],
                self.notification_number or '',
                self.amendment_code or '',
                xml_detail1, xml_detail2, pysiidte.time_stamp()).replace(
                '<FolioNotificacion></FolioNotificacion>', '', 1).replace(
                '<CodAutRec></CodAutRec>', '', 1)
            _logger.info(xml_envio_report)
            xml1 = xml.dom.minidom.parseString(xml_envio_report)
            xml_pret = xml1.toprettyxml()
            if True:  # try:
                xml_pret = pysiidte.convert_encoding(
                    xml_pret, 'ISO-8859-1').decode().replace(
                    '<?xml version="1.0" ?>', '')
            else:  # except:
                _logger.info(u'no pude decodificar algún caracter. La versión \
guardada del xml es la siguiente: {}'.format(xml_pret))
                # raise UserError('xml pret sin decodificar')
            certp = signature_d['cert'].replace(
                BC, '').replace(EC, '').replace('\n', '')
            _logger.info("\n\n\n Aqui el xml_pret antes del envelop %s \n\n\n" % xml_pret)
            xml_pret = self._envelope_book(xml_pret)
            _logger.info(xml_pret)
            xml_pret = self.sign_full_xml(
                xml_pret.replace('<?xml version="1.0" encoding="ISO-8859-1"?>\n', ''),
                signature_d['priv_key'], certp,
                self.name.replace(' ', '_'), type='book')
            _logger.info(xml_pret)
            return xml_pret
        else:  # except:
            _logger.info('Could not get files (first attempt)')
            return False

    def sign_full_xml(self, message, privkey, cert, uri, type='book'):
        doc = etree.fromstring(message)
        string = etree.tostring(doc[0])
        mess = etree.tostring(etree.fromstring(string), method="c14n")
        digest = base64.b64encode(self.digest(mess))
        reference_uri='#'+uri
        signed_info = etree.Element("SignedInfo")
        c14n_method = etree.SubElement(signed_info, "CanonicalizationMethod", Algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
        sign_method = etree.SubElement(signed_info, "SignatureMethod", Algorithm='http://www.w3.org/2000/09/xmldsig#rsa-sha1')
        reference = etree.SubElement(signed_info, "Reference", URI=reference_uri)
        transforms = etree.SubElement(reference, "Transforms")
        etree.SubElement(transforms, "Transform", Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        digest_method = etree.SubElement(reference, "DigestMethod", Algorithm="http://www.w3.org/2000/09/xmldsig#sha1")
        digest_value = etree.SubElement(reference, "DigestValue")
        digest_value.text = digest
        signed_info_c14n = etree.tostring(signed_info,method="c14n",exclusive=False,with_comments=False,inclusive_ns_prefixes=None)
        att = 'xmlns="http://www.w3.org/2000/09/xmldsig#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        #@TODO Find better way to add xmlns:xsi attrib
        signed_info_c14n = signed_info_c14n.decode().replace("<SignedInfo>","<SignedInfo " + att + ">")
        xmlns = 'http://www.w3.org/2000/09/xmldsig#'
        sig_root = etree.Element("Signature",attrib={'xmlns':xmlns})
        sig_root.append(etree.fromstring(signed_info_c14n))
        signature_value = etree.SubElement(sig_root, "SignatureValue")

        key=OpenSSL.crypto.load_privatekey(type_,privkey.encode('ascii'))
        signature= OpenSSL.crypto.sign(key,signed_info_c14n,'sha1')
        signature_value.text = textwrap.fill(base64.b64encode(signature).decode(),64)
        key_info = etree.SubElement(sig_root, "KeyInfo")
        key_value = etree.SubElement(key_info, "KeyValue")
        rsa_key_value = etree.SubElement(key_value, "RSAKeyValue")
        modulus = etree.SubElement(rsa_key_value, "Modulus")
        key = load_pem_private_key(privkey.encode('ascii'),password=None, backend=default_backend())
        modulus.text =  textwrap.fill(base64.b64encode(self.long_to_bytes(key.public_key().public_numbers().n)).decode(),64)
        exponent = etree.SubElement(rsa_key_value, "Exponent")
        exponent.text = self.ensure_str(base64.b64encode(self.long_to_bytes(key.public_key().public_numbers().e)))
        x509_data = etree.SubElement(key_info, "X509Data")
        x509_certificate = etree.SubElement(x509_data, "X509Certificate")
        x509_certificate.text = '\n'+textwrap.fill(cert,64)
        msg = etree.tostring(sig_root)
    
        if type != 'libro_boleta':
            msg = msg if self.xml_validator(msg, 'sig') else ''
        if type == 'book':
            fulldoc = message.replace('</LibroCompraVenta>',msg.decode('utf-8')+'\n</LibroCompraVenta>')
        elif type == 'libro_boleta':
            resp = fulldoc = message.replace('</LibroBoleta>',str(msg)+'\n</LibroBoleta>')
            xmlns = 'xmlns="http://www.w3.org/2000/09/xmldsig#"'
            xmlns_sii = 'xmlns="http://www.sii.cl/SiiDte"'
            msg = msg.replace(xmlns, xmlns_sii)
            fulldoc = message.replace('</LibroBoleta>',msg+'\n</LibroBoleta>')
        fulldoc = '<?xml version="1.0" encoding="ISO-8859-1"?>\n'+fulldoc
        fulldoc = fulldoc if self.xml_validator(fulldoc, type) else ''
        if type == 'libro_boleta':# es feo, pero repara el problema de validacion mla creada del sii
            return '<?xml version="1.0" encoding="ISO-8859-1"?>\n'+resp
        return fulldoc

    def digest(self, data):
        sha1 = hashlib.new('sha1', data)
        return sha1.digest()

    def long_to_bytes(self, n, blocksize=0):
        """long_to_bytes(n:long, blocksize:int) : string
        Convert a long integer to a byte string.
        If optional blocksize is given and greater than zero, pad the front of the
        byte string with binary zeros so that the length is a multiple of
        blocksize.
        """
        # after much testing, this algorithm was deemed to be the fastest
        s = b''
        n = int(n)  # noqa
        import struct
        pack = struct.pack
        while n > 0:
            s = pack(b'>I', n & 0xffffffff) + s
            n = n >> 32
        # strip off leading zeros
        for i in range(len(s)):
            if s[i] != b'\000'[0]:
                break
        else:
            # only happens when n == 0
            s = b'\000'
            i = 0
        s = s[i:]
        # add back some pad bytes.  this could be done more efficiently w.r.t. the
        # de-padding being done above, but sigh...
        if blocksize > 0 and len(s) % blocksize:
            s = (blocksize - len(s) % blocksize) * b'\000' + s
        return s

    def ensure_str(self,x, encoding="utf-8", none_ok=False):
        if none_ok is True and x is None:
            return x
        if not isinstance(x, str):
            x = x.decode(encoding)
        return x

    def xml_validator(self, some_xml_string, validacion='doc'):
        validacion_type = {
            'doc': 'DTE_v10.xsd',
            'env': 'EnvioDTE_v10.xsd',
            'sig': 'xmldsignature_v10.xsd',
            'book': 'LibroCV_v10.xsd',
            'libroS': 'LibroCVS_v10.xsd',
            'libro_boleta': 'LibroBOLETA_v10.xsd',
        }
        xsd_file = xsdpath+validacion_type[validacion]
        try:
            xmlschema_doc = etree.parse(xsd_file)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            if validacion == 'sig':
                xml_doc = etree.fromstring(some_xml_string)
            else:
                xml_doc = etree.fromstring(some_xml_string.replace('<?xml version="1.0" encoding="ISO-8859-1"?>', ''))
            result = xmlschema.validate(xml_doc)
            if not result:
                xmlschema.assert_(xml_doc)
            return result
        except AssertionError as e:
            raise UserError(_('XML Malformed Error:  %s') % e.args)

    @api.multi
    def get_invoices(self):
        
        self.invoice_ids = self.invoice_ids.search(
            [('journal_id', 'in', self.journal_ids.ids),
            ('state', 'not in', ['draft'])
            ])

    @api.depends('name', 'date', 'company_id', 'journal_ids','invoice_ids', 'fiscal_period',
                 'operation_type', 'report_type', 'sending_type',
                 'proportion_factor')
    def set_values(self):
        for rec in self:
            self.get_invoices()
            if not rec.name and not self.invoice_ids:
                return
            dict0 = rec._summary_by_period()
            rec._record_totals(dict0)
            dict1 = {'ResumenPeriodo': dict0}
            dict2 = {'Detalles': rec._detail_by_period()}
            xml_pret = rec._record_detail(dict1, dict2)
            rec.sii_xml_request = xml_pret

    @api.multi
    def validate_report(self):
        inv_obj = self.env['account.invoice']
        if self.state not in ['draft', 'NoEnviado', 'Rechazado']:
            raise UserError('El libro se encuentra en estado: {}'.format(
                self.state))
        company_id = self.company_id
        doc_id = self.operation_type + '_' + self.fiscal_period
        #result = inv_obj.send_xml_file(
        result = self.send_xml_file(
            self.sii_xml_request, doc_id + '.xml', company_id)
        self.write({
            'sii_xml_response': result['sii_xml_response'],
            'sii_send_ident': result['sii_send_ident'],
            'state': result['sii_result'],
            # 'sii_xml_request': envio_dte
        })

    @api.multi
    def send_xml_file(
            self, envio_dte=None, file_name="envio", company_id=False):
        if not company_id.dte_service_provider:
            raise UserError(_("Not Service provider selected!"))
        if True:  # try:
            signature_d = self.get_digital_signature_pem(
                company_id)
            seed = self.get_seed(company_id)
            template_string = self.create_template_seed(seed)
            seed_firmado = self.sign_seed(
                template_string, signature_d['priv_key'],
                signature_d['cert'])
            token = pysiidte.get_token(seed_firmado, company_id.dte_service_provider)
        else:  # except:
            _logger.info(connection_status)
            raise UserError(connection_status)

        url = 'https://palena.sii.cl'
        if company_id.dte_service_provider == 'SIIHOMO':
            url = 'https://maullin.sii.cl'
        post = '/cgi_dte/UPL/DTEUpload'
        headers = {
            'Accept': 'image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, application/vnd.ms-powerpoint, application/ms-excel, application/msword, */*',
            'Accept-Language': 'es-cl',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'Mozilla/4.0 (compatible; PROG 1.0; Windows NT 5.0; YComp 5.0.2.4)',
            'Referer': '{}'.format(company_id.website),
            'Connection': 'Keep-Alive',
            'Cache-Control': 'no-cache',
            'Cookie': 'TOKEN={}'.format(token),
        }
        params = collections.OrderedDict()
        params['rutSender'] = signature_d['subject_serial_number'][:8]
        params['dvSender'] = signature_d['subject_serial_number'][-1]
        params['rutCompany'] = company_id.vat[2:-1]
        params['dvCompany'] = company_id.vat[-1]
        file_name = file_name + '.xml'
        params['archivo'] = (file_name,envio_dte,"text/xml")
        multi  = urllib3.filepost.encode_multipart_formdata(params)
        headers.update({'Content-Length': '{}'.format(len(multi[0]))})
        response = pool.request_encode_body('POST', url+post, params, headers)
        result = {'sii_xml_response': response.data, 'sii_result': 'NoEnviado','sii_send_ident':''}
        if response.status != 200:
            return result
        respuesta_dict = xmltodict.parse(response.data)
        if respuesta_dict['RECEPCIONDTE']['STATUS'] != '0':
            _logger.info('l736-status no es 0')
            _logger.info(connection_status)
        else:
            result.update({'sii_result': 'Enviado','sii_send_ident':respuesta_dict['RECEPCIONDTE']['TRACKID']})
        return result

    def get_digital_signature_pem(self, comp_id):
        obj = user = False
        if 'responsable_envio' in self and self._ids:
            obj = user = self[0].responsable_envio
        if not obj:
            obj = user = self.env.user
        if not obj.cert:
            obj = self.env['res.users'].search(
                [("authorized_users_ids","=", user.id)])
            if not obj or not obj.cert:
                obj = self.env['res.company'].browse([comp_id.id])
                if not obj.cert or not user.id in obj.authorized_users_ids.ids:
                    return False
        signature_data = {
            'subject_name': obj.name,
            'subject_serial_number': obj.subject_serial_number,
            'priv_key': obj.priv_key,
            'cert': obj.cert,
            'rut_envia': obj.subject_serial_number
            }
        return signature_data

    def get_seed(self, company_id):
        # En caso de que haya un problema con la validación de certificado del
        #   sii ( por una mala implementación de ellos)
        # esto omite la validacion
        try:
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
        except:
            pass
        url = server_url[company_id.dte_service_provider] + 'CrSeed.jws?WSDL'
        ns = 'urn:'+server_url[company_id.dte_service_provider] + 'CrSeed.jws'
        # _server = Client(url, ns)
        _server = Client(url)
        root = etree.fromstring(_server.service.getSeed().replace(
            '<?xml version="1.0" encoding="UTF-8"?>', ''))
        seed = root[0][0].text
        return seed

    def _get_send_status(self, track_id, signature_d, token):
        url = server_url[
                  self.company_id.dte_service_provider] + 'QueryEstUp.jws?WSDL'
        ns = 'urn:' + server_url[
            self.company_id.dte_service_provider] + 'QueryEstUp.jws'
        # _server = Client(url, ns)
        _server = Client(url)
        respuesta = _server.getEstUp(
            self.company_id.vat[2:-1], self.company_id.vat[-1], track_id, token)
        self.sii_receipt = respuesta
        resp = xmltodict.parse(respuesta)
        status = False
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "-11":
            status = {
                'warning': {
                    'title': _('Error -11'),
                    'message': _("Error -11: Espere a que sea aceptado por el \
SII, intente en 5s más")}}
        if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "EPR":
            self.state = "Proceso"
            if 'SII:RESP_BODY' in resp['SII:RESPUESTA'] and resp[
                'SII:RESPUESTA']['SII:RESP_BODY']['RECHAZADOS'] == "1":
                self.sii_result = "Rechazado"
        elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == "RCT":
            self.state = "Rechazado"
            status = {
                'warning': {
                    'title': _('Error RCT'),
                    'message': _(resp['SII:RESPUESTA']['GLOSA'])}}
        return status

    def create_template_seed(self, seed):
        xml = u'''<getToken>
<item>
<Semilla>{}</Semilla>
</item>
</getToken>
'''.format(seed)
        return xml

    @staticmethod
    def sign_seed(message, privkey, cert):
        """
        @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
        @version: 2016-06-01
        """
        _logger.info('SIGNING WITH SIGN_SEED ##### ------ #####')
        doc = etree.fromstring(message)
        signed_node = XMLSigner(
            method=methods.enveloped, signature_algorithm=u'rsa-sha1',
            digest_algorithm=u'sha1').sign(
            doc, key=privkey.encode('ascii'), passphrase=None, cert=cert,
            key_name=None, key_info=None, id_attribute=None)
        msg = etree.tostring(
            signed_node, pretty_print=True).replace(b'ds:', b'')
        _logger.info('message: {}'.format(msg))
        return msg

    @api.multi
    def ask_for_dte_status(self):
        inv_obj = self.env['account.invoice']
        if True:  # try:
            signature_d = inv_obj.get_digital_signature_pem(
                self.company_id)
            token = pysiidte.sii_token(
                self.company_id.dte_service_provider, signature_d['priv_key'],
                signature_d['cert'])
        else:  # except:
            raise UserError('Connection error')
        xml_response = xmltodict.parse(self.sii_xml_response)
        _logger.info(xml_response)
        if self.state == 'Enviado':
            status = self._get_send_status(
                self.sii_send_ident, signature_d, token)
            if self.state != 'Proceso':
                return status


class Receipts(models.Model):
    _name = 'account.move.book.receipts'

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.user.company_id.currency_id,
        required=True,
        track_visibility='always')
    receipt_type = fields.Many2one('account.document.type',
        string="Receipt Type",
        required=True,
        domain=[('document_letter_id.name','in',['B','M'])])
    initial_range = fields.Integer(
        string="Initial Range", required=True)
    final_range = fields.Integer(
        string="Final Range", required=True)
    quantity_receipts = fields.Integer(
        string="Cantidad receipts", required=True)
    net_amount = fields.Monetary(string="Net Amount", required=True)
    tax = fields.Many2one(
        'account.tax', string="Tax", required=True,
        domain=[('type_tax_use', '!=', 'none'), '|', ('active', '=', False),
                ('active', '=', True)])
    amount_tax = fields.Monetary(
        compute='_amount_total', string="Tax Amount", required=True)
    amount_total = fields.Monetary(
        compute='_amount_total', string="Total Amount", required=True)
    book_id = fields.Many2one('account.move.book')


class BookTaxes(models.Model):
    _name = "account.move.book.tax"

    def get_monto(self):
        for t in self:
            t.amount = t.debit - t.credit
            if t.book_id.operation_type in ['sale']:
                t.amount = t.credit - t.debit

    tax_id = fields.Many2one('account.tax', string="Tax")
    credit = fields.Monetary(string="Créditos", default=0.00)
    debit = fields.Monetary(string="Débitos", default=0.00)
    amount = fields.Monetary(compute="get_monto", string="Amount")
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.user.company_id.currency_id,
        required=True, track_visibility='always')
    book_id = fields.Many2one('account.move.book', string="Book")
