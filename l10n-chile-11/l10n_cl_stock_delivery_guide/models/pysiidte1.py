# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
from __future__ import print_function

import base64
import collections
import hashlib
import logging
import os
import ssl
import struct
import textwrap
import xml
from datetime import datetime

import cchardet
import pdf417gen
import pytz
import urllib3
from OpenSSL import crypto
from bs4 import BeautifulSoup as bs
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from lxml import etree
from lxml.etree import Element, SubElement
from signxml import XMLSigner, methods
from zeep import Settings
from zeep.client import Client

urllib3.disable_warnings()
pool = urllib3.PoolManager(cert_reqs='CERT_NONE')

"""
Módulo auxiliares y para realizar conexión, firma y servicios
relacionados don Documentos Tributarios Electrónicos del SII
(Servicio de Impuestos Internos) de Chile
"""
__author__ = "Daniel Blanco Martín (daniel@blancomartin.cl)"
__copyright__ = "Copyright (C) 2015-2017 Blanco Martín y Asoc. EIRL - BMyA S.A."
__license__ = "AGPL 3.0"

_logger = logging.getLogger(__name__)
ssl._create_default_https_context = ssl._create_unverified_context

SERVER_URL = {
    'SIIHOMO': 'https://maullin.sii.cl/DTEWS/',
    'SII': 'https://palena.sii.cl/DTEWS/',
}
CLAIM_URL = {
    'SIIHOMO': 'https://ws2.sii.cl/WSREGISTRORECLAMODTECERT/registroreclamodteservice',
    'SII': 'https://ws1.sii.cl/WSREGISTRORECLAMODTE/registroreclamodteservice',
}

BC = '''-----BEGIN CERTIFICATE-----\n'''
EC = '''\n-----END CERTIFICATE-----\n'''

stamp = """<TED version="1.0"><DD><RE/><TD/><F/>\
<FE/><RR/><RSR/><MNT/><IT1/><CAF version="1.0"><DA><RE/><RS/>\
<TD/><RNG><D/><H/></RNG><FA/><RSAPK><M/><E/></RSAPK>\
<IDK/></DA><FRMA algoritmo="SHA1withRSA"/></CAF><TSTED/></DD>\
<FRMT algoritmo="SHA1withRSA"/></TED>"""

connection_status = {
    '0': 'Upload OK',
    '1': 'El remitente no tiene permiso para enviar',
    '2': 'Error en tamaño del archivo (muy grande o muy chico)',
    '3': 'Archivo cortado (tamaño <> al parámetro size)',
    '5': 'No está autenticado',
    '6': 'Empresa no autorizada a enviar archivos',
    '7': 'Esquema Invalido',
    '8': 'Firma del Documento',
    '9': 'Sistema Bloqueado',
    'Otro': 'Error Interno.',
}
tag_replace01 = ['TotOpExe', 'TotOpIVARec', 'CodIVANoRec',
                 'TotOpIVARetTotal', 'TotIVARetTotal',
                 'TotOpIVARetParcial', 'TotIVARetParcial',
                 'TotOpIVANoRetenido', 'TotIVANoRetenido',
                 'TotOpIVANoRec', 'TotMntIVANoRec',
                 'TotOpIVAUsoComun', 'TotCredIVAUsoComun',
                 'TotIVAUsoComun', 'TotImpSinCredito', 'CodImp', 'TotMntImp',
                 'TpoImp', 'TasaImp']
tag_replace_1 = ['TpoImp', 'TotOpIVARec', 'TotIVANoRec', 'TotOtrosImp']
tag_replace02 = ['CodIVANoRec', 'MntIVANoRec', 'IVANoRetenido', 'IVARetTotal',
                 'IVARetParcial', 'OtrosImp', 'CodImp', 'MntImp', 'TasaImp',
                 'TpoImp', 'uTasaImp', 'MntIVA']
tag_replace_2 = ['TpoDocRef', 'FolioDocRef', 'TpoImp', 'TasaImp',
                 'IVANoRec', 'OtrosImp']
tag_round = ['MntExe', 'MntNeto', 'MntIva', 'MntImp']

xsdpath = os.path.dirname(os.path.realpath(__file__)).replace('/models', '/static/xsd/')

document_type = {
    'Liquidacion': [43],
    'Exportaciones': [110, 111, 112],
}

RETRIES = 1000


def xml_document_type(document_code, document_type):
    for k, v in document_type.items():
        if document_code in v:
            return k
    return


def set_headers(token, referer):
    headers = {
        'Accept': 'image/gif, image/x-xbitmap, image/jpeg, \
image/pjpeg, application/vnd.ms-powerpoint, application/ms-excel, \
application/msword, */*',
        'Accept-Language': 'es-cl',
        'Accept-Encoding': 'gzip, deflate',
        'User-Agent': 'Mozilla/4.0 (compatible; PROG 1.0; Windows NT 5.0; \
YComp 5.0.2.4)',
        'Referer': '{}'.format(referer),
        'Connection': 'Keep-Alive',
        'Cache-Control': 'no-cache',
        'Cookie': 'TOKEN={}'.format(token), }
    return headers


def str_shorten(text, text_len):
    return text[:text_len]


def time_stamp(date_format='%Y-%m-%dT%H:%M:%S'):
    tz = pytz.timezone('America/Santiago')
    return datetime.now(tz).strftime(date_format)


def xml_validator(xml_to_validate, validation_type='doc'):
    """
    Funcion para validar los xml generados contra el esquema que le
    corresponda segun el tipo de documento.
    @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
    @version: 2016-06-01. Se agregó validación para boletas
    Modificada por Daniel Santibañez 2016-08-01
    """
    if validation_type == 'bol':
        return True
    validation_types = {
        'doc': 'DTE_v10.xsd',
        'env': 'EnvioDTE_v10.xsd',
        'env_boleta': 'EnvioBOLETA_v11.xsd',
        'recep': 'Recibos_v10.xsd',
        'env_recep': 'EnvioRecibos_v10.xsd',
        'env_resp': 'RespuestaEnvioDTE_v10.xsd',
        'sig': 'xmldsignature_v10.xsd',
        'book': 'LibroCV_v10.xsd',
        'consu': 'ConsumoFolio_v10.xsd',
        'bol': 'EnvioBOLETA_v11.xsd',
    }
    xsd_file = xsdpath + validation_types[validation_type]
    try:
        xmlschema_doc = etree.parse(xsd_file)
        xmlschema = etree.XMLSchema(xmlschema_doc)
        xml_doc = etree.fromstring(xml_to_validate)
        result = xmlschema.validate(xml_doc)
        if not result:
            xmlschema.assert_(xml_doc)
        return result
    except AssertionError as error:
        raise AssertionError(error)


def convert_encoding(data, new_coding='UTF-8'):
    """
    Funcion auxiliar para conversion de codificacion de strings
    @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
    @version: 2014-12-01 - actualizada 2017-08-20
    """
    try:
        encoding = cchardet.detect(data)['encoding']
    except:
        encoding = 'ascii'
    if new_coding.upper() != encoding.upper():
        try:
            data = data.decode(encoding=encoding, errors='ignore')
        except:
            try:
                data = data.decode(encoding='UTF-8', errors='ignore')
            except:
                try:
                    data = data.decode(encoding='ISO-8859-9', errors='replace')
                except:
                    pass
        data = data.encode(encoding=new_coding, errors='ignore')
    return data


def long_to_bytes(n, blocksize=0):
    s = b''
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


def soup_text(xml, type_tag):
    """
    :param xml: xml obtenido
    :param type_tag: TOKEN o SEMILLA
    :return:
    """
    try:
        soup = bs(xml, 'xml')
        tag = soup.find(type_tag).text
        return tag
    except Exception as error:
        raise ValueError('No se pudo obtener el %s - error %s' % (type_tag, error))


def char_replace(text):
    """
    Funcion para reemplazar caracteres especiales
    Esta funcion sirve para salvar bug en libreDTE con los recortes de
    giros que están codificados en utf8 (cuando trunca, trunca la
    codificacion)
    @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
    @version: 2016-07-31
    """
    special_chars = [
        [u'á', 'a'],
        [u'é', 'e'],
        [u'í', 'i'],
        [u'ó', 'o'],
        [u'ú', 'u'],
        [u'ñ', 'n'],
        [u'Á', 'A'],
        [u'É', 'E'],
        [u'Í', 'I'],
        [u'Ó', 'O'],
        [u'Ú', 'U'],
        [u'Ñ', 'N']]
    for char in special_chars:
        try:
            text = text.replace(char[0], char[1])
        except:
            pass
    return text


def get_sha1_digest(data):
    """
    Funcion para obtener digest en la firma
    @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
    @version: 2015-03-01
    """
    sha1 = hashlib.new('sha1', data)
    return sha1.digest()


def sign_seed(message, privkey, cert):
    """
    Funcion usada en autenticacion en SII
    Firma de la semilla utilizando biblioteca signxml
    De autoria de Andrei Kislyuk https://github.com/kislyuk/signxml
    (en este caso particular esta probada la efectividad de la libreria)
    @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
    @version: 2016-06-01
    :param message:
    :param privkey:
    :param cert:
    :return:
    """
    doc = etree.fromstring(message)
    signed_node = XMLSigner(method=methods.enveloped, digest_algorithm='sha1').sign(
        doc, key=privkey.encode('ascii'), cert=cert)
    msg = etree.tostring(signed_node, pretty_print=True).decode().replace('ds:', '')
    return msg


def get_seed(mode):
    url = SERVER_URL[mode] + 'CrSeed.jws?WSDL'
    _server = Client(wsdl=url)
    seed = None
    retry = 0
    while seed is None and retry < 1000:
        try:
            resp = _server.service.getSeed().replace('<?xml version="1.0" encoding="UTF-8"?>', '')
            root = etree.fromstring(resp)
            seed = root[0][0].text
        except Exception:
            continue
        finally:
            retry += 1
    return seed


def get_token(mode, private_key, cert, seed):
    template_string = u'''<getToken>
    <item>
    <Semilla>{}</Semilla>
    </item>
    </getToken>
    '''.format(seed)
    doc = etree.fromstring(template_string)
    signed_node = XMLSigner(method=methods.enveloped, digest_algorithm='sha1').sign(doc, key=private_key.encode(
        'ascii'), cert=cert)
    seed_file = etree.tostring(signed_node, pretty_print=True).decode().replace('ds:', '')
    _logger.debug('######------- seed file %s' % seed_file)
    resp = None
    retry = 0
    while resp is None and retry < 1000:
        try:
            url = SERVER_URL[mode] + 'GetTokenFromSeed.jws?WSDL'
            _server = Client(wsdl=url)
            tree = etree.fromstring(seed_file)
            ss = etree.tostring(tree, pretty_print=True, encoding='iso-8859-1').decode()
            resp = _server.service.getToken(ss)
        except:
            continue
        finally:
            retry += 1
    try:
        response = etree.fromstring(resp.replace('<?xml version="1.0" encoding="UTF-8"?>', ''))
    except AttributeError:
        raise UserError('El servidor del SII no está disponible. Intente nuevamente')
    return response[0][0].text


def sii_token(mode, private_key, cert):
    seed = get_seed(mode)
    token = get_token(mode, private_key, cert, seed)
    _logger.debug('### ---- token: {}'.format(token))
    return token


# def sii_token(mode, privkey, cert):
#     @sign_seed(privkey, cert)
#     @create_template_seed
#     def get_seed(mode):
#         """
#         Funcion usada en autenticacion en SII, obtención de la semilla
#         se discontinúa el método usado con SOAPPy por poco eficiente y
#         con existencia de muchos errores (2015-04-01)
#         @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
#         @version: 2017-05-10
#         """
#         url = server_url[mode] + 'CrSeed.jws?WSDL'
#         seed_xml, i = None, retries
#         client = Client(url)
#         while seed_xml is None and i > 0:
#             _logger.info('getSeed: Intento {}'.format(retries + 1 - i))
#             try:
#                 seed_xml = client.service.getSeed()
#             except:
#                 continue
#             finally:
#                 i -= 1
#         return soup_text(seed_xml, 'SEMILLA')
#
#     return get_token(get_seed(mode), mode)


def split_cert(cert):
    certf, j = '', 0
    for i in range(0, 29):
        certf += cert[76 * i:76 * (i + 1)] + '\n'
    return certf


def pdf417bc(ted):
    """
    Funcion creacion de imagen pdf417 basada en biblioteca elaphe
     @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
     @version: 2016-05-01
    """
    bc = pdf417gen.encode(
        ted,
        security_level=5,
        columns=13, )
    image = pdf417gen.render_image(
        bc,
        padding=15,
        scale=1, )
    return image


def analyze_sii_result(sii_result, sii_message, sii_receipt):
    result_dict = {
        'Proceso': ['DOK', 'SOK', 'CRT', 'PDR', 'FOK', '-11'],
        'Rechazado': ['RCH', 'RFR', 'RSC', 'RCT'],
        'Reparo': ['RLV'],
        'check_receipt': ['EPR', 'DNK'],
        'check_glosa': ['2'], }
    status = False
    try:
        soup_message = bs(sii_message, 'xml')
        _logger.info(soup_message)
        for key, values in result_dict.items():
            if soup_message.ESTADO.text in values:
                status = key
                break
        _logger.info('status: %s' % status)
        if status in {'Proceso', 'Rechazado', 'Reparo'}:
            return status
        elif status == 'check_receipt':
            if True:
                soup_receipt = bs(sii_receipt, 'xml')
                _logger.info(soup_receipt)
                if soup_receipt.ACEPTADOS.text == soup_receipt.INFORMADOS.text:
                    _logger.info('sale por Aceptado')
                    return 'Aceptado'
                if soup_receipt.REPAROS.text >= '1':
                    _logger.info('sale por Reparo')
                    return 'Reparo'
                if soup_receipt.RECHAZADOS.text >= '1':
                    _logger.info('sale por Rechazado')
                    return 'Rechazado'
            else:  # except:
                pass
        elif status == 'check_glosa':
            _logger.info('soup message: %s' % soup_message)
            try:
                raise ValueError('Error code: 2: %s' % soup_message.GLOSA_ERR.text)
            except ValueError:
                _logger.info('status check_glosa: el mensaje no posee tag de error')
        return sii_result
    except TypeError:
        _logger.info('pysiidte.analyze_sii_result: sii_message Retornando Valor Original')
        return sii_result


def remove_plurals_xml(xml):
    pluralizeds = ['Actecos', 'Detalles', 'Referencias', 'DscRcgGlobals', 'ImptoRetens']
    for k in pluralizeds:
        xml = xml.replace('<%s>' % k, '').replace('</%s>' % k, '')
    return xml


def create_template_env(doc):
    xml = '''<?xml version="1.0" encoding="ISO-8859-1"?>
<EnvioDTE xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte EnvioDTE_v10.xsd" \
version="1.0">
    {}
</EnvioDTE>'''.format(doc)
    return xml


def create_template_doc(doc):
    """
    Creacion de plantilla xml para envolver el DTE
    Previo a realizar su firma (1)
    @author: Daniel Blanco Martin (daniel[at]blancomartin.cl)
    """
    doc_soup = bs(doc, 'xml')
    if doc_soup.TipoDTE.text in {'39', '41'}:
        return '''<DTE version="1.0">
{}</DTE>'''.format(doc)
    else:
        return '''<DTE xmlns="http://www.sii.cl/SiiDte" version="1.0">
{}</DTE>'''.format(doc)


def create_template_env_boleta(doc):
    return '''<?xml version="1.0" encoding="ISO-8859-1"?>
<EnvioBOLETA xmlns="http://www.sii.cl/SiiDte" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.sii.cl/SiiDte EnvioBOLETA_v11.xsd" \
version="1.0">
{}</EnvioBOLETA>'''.format(doc)


def pretty_xml_dte(sii_xml_dte):
    x = xml.dom.minidom.parseString(sii_xml_dte)
    return x.toprettyxml().replace('\n\n\n\n', '\n').replace('\n\n\n', '\n').replace('\n\n', '\n')


def process_response_xml(resp):
    if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == '2':
        return 'Enviado'
    if resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] in ['EPR', 'MMC', 'DOK']:
        return 'Proceso'
    elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] == '1':
        return 'Reparo'
    elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] in ['DNK', 'FAU', 'RCT', 'RCH']:
        return 'Rechazado'
    elif resp['SII:RESPUESTA']['SII:RESP_HDR']['ESTADO'] in ['FAN']:
        return 'Anulado'


def get_dte_status(signature_d, service_provider, **kwargs):
    response = None
    retry = 0
    token = sii_token(service_provider, signature_d['priv_key'], signature_d['cert'])
    url = SERVER_URL[service_provider] + 'QueryEstDte.jws?WSDL'
    _server = Client(url)
    while response is None and retry < RETRIES:
        try:
            response = _server.service.getEstDte(
                kwargs.get('rut')[:8],
                kwargs.get('rut')[-1],
                kwargs.get('company_vat')[2:-1],
                kwargs.get('company_vat')[-1],
                kwargs.get('receptor')[:8],
                kwargs.get('receptor')[-1],
                kwargs.get('document_type_code'),
                kwargs.get('sii_document_number'),
                kwargs.get('invoice_date'),
                kwargs.get('amount_total'),
                token
            )
        except Exception as error:
            continue
        finally:
            retry += 1
    return response


def get_send_status(token, dte_service_provider, track_id, company_vat):
    url = SERVER_URL[dte_service_provider] + 'QueryEstUp.jws?WSDL'
    _server = Client(url)
    status = None
    retry = 0
    while status is None and retry < RETRIES:
        try:
            status = _server.service.getEstUp(company_vat[2:-1], company_vat[-1], track_id, token)
        except Exception:
            continue
        finally:
            retry += 1
    return status


def create_template_envio(RutEmisor, RutReceptor, FchResol, NroResol, TmstFirmaEnv, EnvioDTE, signature_d, SubTotDTE):
    return '''<SetDTE ID="SetDoc">
<Caratula version="1.0">
<RutEmisor>{0}</RutEmisor>
<RutEnvia>{1}</RutEnvia>
<RutReceptor>{2}</RutReceptor>
<FchResol>{3}</FchResol>
<NroResol>{4}</NroResol>
<TmstFirmaEnv>{5}</TmstFirmaEnv>
{6}</Caratula>{7}
</SetDTE>
'''.format(RutEmisor, signature_d['subject_serial_number'], RutReceptor, FchResol, NroResol, TmstFirmaEnv,
           SubTotDTE, EnvioDTE)


def _get_xsd_types():
    return {
        'doc': 'DTE_v10.xsd',
        'env': 'EnvioDTE_v10.xsd',
        'env_boleta': 'EnvioBOLETA_v11.xsd',
        'recep': 'Recibos_v10.xsd',
        'env_recep': 'EnvioRecibos_v10.xsd',
        'env_resp': 'RespuestaEnvioDTE_v10.xsd',
        'sig': 'xmldsignature_v10.xsd'
    }


def ensure_str(x, encoding="utf-8", none_ok=False):
    if none_ok and x is None:
        return x
    if not isinstance(x, str):
        x = x.decode(encoding)
    return x


def _append_sig(xml_type, sign, message):
    tag_to_replace = {
        'doc': '</DTE>',
        'bol': '</DTE>',
        'env': '</EnvioDTE>',
        'recep': '</Recibo>',
        'env_recep': '</EnvioRecibos>',
        'env_resp': '</RespuestaDTE>',
        'consu': '</ConsumoFolios>',
    }
    tag = tag_to_replace.get(xml_type, '</EnvioBOLETA>')
    return message.replace(tag, sign + tag)


def sign_full_xml(message, private_key, cert, uri, xml_type='doc'):
    doc = etree.fromstring(message)
    string = etree.tostring(doc[0])
    mess = etree.tostring(etree.fromstring(string), method="c14n")  # agregado el pretty print
    signed_info = Element("SignedInfo")
    SubElement(signed_info, "CanonicalizationMethod", Algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315')
    SubElement(signed_info, "SignatureMethod", Algorithm='http://www.w3.org/2000/09/xmldsig#rsa-sha1')
    reference = SubElement(signed_info, "Reference", URI='#' + uri)
    transforms = SubElement(reference, "Transforms")
    SubElement(transforms, "Transform", Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
    SubElement(reference, "DigestMethod", Algorithm="http://www.w3.org/2000/09/xmldsig#sha1")
    digest_value = SubElement(reference, "DigestValue")
    digest_value.text = base64.b64encode(get_sha1_digest(mess))
    signed_info_c14n = etree.tostring(signed_info, method="c14n", exclusive=False, with_comments=False,
                                      inclusive_ns_prefixes=None).decode('utf-8')
    if xml_type in ['doc', 'recep']:
        att = 'xmlns="http://www.w3.org/2000/09/xmldsig#"'
    else:
        att = 'xmlns="http://www.w3.org/2000/09/xmldsig#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
    signed_info_c14n = signed_info_c14n.replace("<SignedInfo>", "<SignedInfo %s>" % att)
    sig_root = Element("Signature", attrib={'xmlns': 'http://www.w3.org/2000/09/xmldsig#'})
    sig_root.append(etree.fromstring(signed_info_c14n))
    signature_value = SubElement(sig_root, "SignatureValue")
    key = crypto.load_privatekey(crypto.FILETYPE_PEM, private_key.encode('ascii'))
    signature = crypto.sign(key, signed_info_c14n, 'sha1')
    signature_value.text = base64.b64encode(signature)
    key_info = SubElement(sig_root, "KeyInfo")
    key_value = SubElement(key_info, "KeyValue")
    rsa_key_value = SubElement(key_value, "RSAKeyValue")
    modulus = SubElement(rsa_key_value, "Modulus")
    key = load_pem_private_key(private_key.encode('ascii'), password=None, backend=default_backend())
    modulus.text = base64.b64encode(long_to_bytes(key.public_key().public_numbers().n))
    exponent = SubElement(rsa_key_value, "Exponent")
    exponent.text = ensure_str(base64.b64encode(long_to_bytes(key.public_key().public_numbers().e)))
    x509_data = SubElement(key_info, "X509Data")
    x509_certificate = SubElement(x509_data, "X509Certificate")
    x509_certificate.text = '\n' + textwrap.fill(cert, 64)
    msg = etree.tostring(sig_root)
    msg = msg if xml_validator(msg, 'sig') else ''
    fulldoc = _append_sig(xml_type, msg.decode('utf-8'), message)
    _logger.info('##################  --------- ##################')
    _logger.info(fulldoc)
    return '<?xml version="1.0" encoding="ISO-8859-1"?>\n' + fulldoc if xml_validator(fulldoc, xml_type) else ''


def signmessage(message, key):
    key = crypto.load_privatekey(crypto.FILETYPE_PEM, key)
    signature = crypto.sign(key, message, 'sha1')
    text = base64.b64encode(signature).decode()
    return textwrap.fill(text, 64)


def set_dte_claim(token, dte_service_provider, rut_emisor, sii_document_number, document_type_id, claim):
    url = CLAIM_URL[dte_service_provider] + '?wsdl'
    settings = Settings(strict=False, extra_http_headers={'Cookie': 'TOKEN=' + token})
    _server = Client(url, settings=settings)
    retry = 0
    response = None
    while response is None and retry < RETRIES:
        try:
            response = _server.service.ingresarAceptacionReclamoDoc(
                rut_emisor[:-2],
                rut_emisor[-1],
                str(document_type_id.code),
                str(sii_document_number),
                claim)
        except:
            continue
        finally:
            retry += 1
    return response


def get_dte_claim(token, dte_service_provider, company_vat, document_type_code, sii_document_number):
    url = CLAIM_URL[dte_service_provider] + '?wsdl'
    settings = Settings(strict=False, extra_http_headers={'Cookie': 'TOKEN=' + token})
    retry = 0
    response = None
    _server = Client(url, settings=settings)
    while response is None and retry < RETRIES:
        try:
            response = _server.service.listarEventosHistDoc(
                company_vat[2:-1],
                company_vat[-1],
                str(document_type_code),
                str(sii_document_number)
            )
        except:
            continue
        finally:
            retry += 1
    return response


def procesar_recepcion(response_value, respuesta_dict):
    _logger.debug('### ---- respuesta dict %s \n' % respuesta_dict)
    if respuesta_dict['RECEPCIONDTE']['STATUS'] != '0':
        _logger.warning(connection_status[respuesta_dict['RECEPCIONDTE']['STATUS']])
    else:
        response_value.update({'state': 'Enviado', 'sii_send_ident': respuesta_dict['RECEPCIONDTE']['TRACKID']})
    return response_value


def send_xml(mode, signature_d, company_website, company_vat, file_name, xml_message, post='/cgi_dte/UPL/DTEUpload'):
    token = sii_token(mode, signature_d['priv_key'], signature_d['cert'])
    url = SERVER_URL[mode].replace('/DTEWS/', '')
    headers = {
        'Accept': 'image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, application/vnd.ms-powerpoint, \
application/ms-excel, application/msword, */*',
        'Accept-Language': 'es-cl',
        'Accept-Encoding': 'gzip, deflate',
        'User-Agent': 'Mozilla/4.0 (compatible; PROG 1.0; Windows NT 5.0; YComp 5.0.2.4)',
        'Referer': '{}'.format(company_website),
        'Connection': 'Keep-Alive',
        'Cache-Control': 'no-cache',
        'Cookie': 'TOKEN={}'.format(token),
    }
    params = collections.OrderedDict()
    params['rutSender'] = signature_d['subject_serial_number'][:8]
    params['dvSender'] = signature_d['subject_serial_number'][-1]
    params['rutCompany'] = company_vat[2:-1]
    params['dvCompany'] = company_vat[-1]
    params['archivo'] = (file_name, xml_message, "text/xml")
    multi = urllib3.filepost.encode_multipart_formdata(params)
    headers.update({'Content-Length': '{}'.format(len(multi[0]))})
    try:
        response = pool.request_encode_body('POST', url+post, params, headers)
    except Exception as error:
        raise error
    return response