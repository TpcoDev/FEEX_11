# -*- coding: utf-8 -*-
from __future__ import print_function

import base64
import datetime
import logging
from M2Crypto import X509 as M2X509
from M2Crypto.EVP import MessageDigest
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
from OpenSSL.crypto import *

_logger = logging.getLogger(__name__)


type_ = FILETYPE_PEM

zero_values = {
    "filename": "",
    "key_file": False,
    "dec_pass": "",
    "not_before": False,
    "not_after": False,
    "status": "unverified",
    "final_date": False,
    "subject_title": "",
    "subject_c": "",
    "subject_serial_number": "",
    "subject_common_name": "",
    "subject_email_address": "",
    "issuer_country": "",
    "issuer_serial_number": "",
    "issuer_common_name": "",
    "issuer_email_address": "",
    "issuer_organization": "",
    "cert_serial_number": "",
    "cert_signature_algor": "",
    "cert_version": "",
    "cert_hash": "",
    "private_key_bits": "",
    "private_key_check": "",
    "private_key_type": "",
    "cacert": "",
    "cert": False,
    "priv_key": False,
    "authorized_users_ids": False,
    # "cert_owner_id": "",
}


class UserSignature(models.Model):
    _inherit = 'res.users'

    @api.model
    def default_status(self):
        return 'unverified'

    def check_cert_validity(self):
        """
        This function is to be used to validate the cert before using it.
        if invalid, the function passes the cert to expired status.
        :return: False if expired
        """
        for record in self:
            _logger.debug('Checking cert validity - id: %s, usuario: %s' % (record.id, record.login))
            if not record.not_after:
                return False
            if record.not_after < fields.Date.today():
                record.status = 'expired'
                return False
            else:
                return record.cert

    def load_cert_m2pem(self, *args, **kwargs):
        filecontent = base64.b64decode(self.key_file)
        cert = M2X509.load_cert(filecontent)
        issuer = cert.get_issuer()
        subject = cert.get_subject()

    def load_cert_pk12(self, filecontent):
        p12 = load_pkcs12(filecontent, self.dec_pass)
        cert = p12.get_certificate()
        privky = p12.get_privatekey()
        cacert = p12.get_ca_certificates()
        issuer = cert.get_issuer()
        subject = cert.get_subject()

        self.not_before = datetime.datetime.strptime(
            cert.get_notBefore().decode('ascii'), '%Y%m%d%H%M%SZ')
        self.not_after = datetime.datetime.strptime(
            cert.get_notAfter().decode('ascii'), '%Y%m%d%H%M%SZ')
        print('not before           ', datetime.datetime.strptime(
            cert.get_notBefore().decode('ascii'), '%Y%m%d%H%M%SZ'))
        print('not after            ', datetime.datetime.strptime(
            cert.get_notAfter().decode('ascii'), '%Y%m%d%H%M%SZ'))

        self.subject_c = subject.C
        self.subject_title = subject.title
        self.subject_common_name = subject.CN
        self.subject_serial_number = subject.serialNumber
        self.subject_email_address = subject.emailAddress
        self.issuer_country = issuer.C
        self.issuer_organization = issuer.O
        self.issuer_common_name = issuer.CN
        self.issuer_serial_number = issuer.serialNumber
        self.issuer_email_address = issuer.emailAddress
        self.status = 'expired' if cert.has_expired() else 'valid'

        self.cert_serial_number = cert.get_serial_number()
        self.cert_signature_algor = cert.get_signature_algorithm()
        self.cert_version = cert.get_version()
        self.cert_hash = cert.subject_name_hash()

        self.private_key_bits = privky.bits()
        self.private_key_check = privky.check()
        self.private_key_type = privky.type()

        certificate = p12.get_certificate()
        private_key = p12.get_privatekey()

        self.priv_key = dump_privatekey(type_, private_key)
        self.cert = dump_certificate(type_, certificate)

        pubkey = cert.get_pubkey()

        try:
            a = cert.sign(pubkey, 'sha1')
            print(a)
        except Exception as ex:
            print('Exception raised: %s' % ex)

    filename = fields.Char('File Name')
    key_file = fields.Binary(
        string='Signature File', required=False, store=True,
        help='Upload the Signature File')
    dec_pass = fields.Char('Pasword')
    # vigencia y estado
    not_before = fields.Date(
        string='Not Before', help='Not Before this Date', readonly=True)
    not_after = fields.Date(
        string='Not After', help='Not After this Date', readonly=True)
    status = fields.Selection(
        [('unverified', 'Unverified'), ('valid', 'Valid'),
         ('expired', 'Expired')],
        string='Status', default=default_status,
        help='''Draft: means it has not been checked yet.
You must press the "check" button.''')
    final_date = fields.Date(
        string='Last Date', help='Last Control Date', readonly=True)
    # sujeto
    subject_title = fields.Char('Subject Title', readonly=True)
    subject_c = fields.Char('Subject Country', readonly=True)
    subject_serial_number = fields.Char(
        'Subject Serial Number')
    subject_common_name = fields.Char(
        'Subject Common Name', readonly=True)
    subject_email_address = fields.Char(
        'Subject Email Address', readonly=True)
    # emisor
    issuer_country = fields.Char('Issuer Country', readonly=True)
    issuer_serial_number = fields.Char(
        'Issuer Serial Number', readonly=True)
    issuer_common_name = fields.Char(
        'Issuer Common Name', readonly=True)
    issuer_email_address = fields.Char(
        'Issuer Email Address', readonly=True)
    issuer_organization = fields.Char(
        'Issuer Organization', readonly=True)
    # data del certificado
    cert_serial_number = fields.Char('Serial Number', readonly=True)
    cert_signature_algor = fields.Char('Signature Algorithm', readonly=True)
    cert_version = fields.Char('Version', readonly=True)
    cert_hash = fields.Char('Hash', readonly=True)
    # data privad, readonly=True
    private_key_bits = fields.Char('Private Key Bits', readonly=True)
    private_key_check = fields.Char('Private Key Check', readonly=True)
    private_key_type = fields.Char('Private Key Type', readonly=True)
    # cacert = fields.Char('CA Cert', readonly=True)
    cert = fields.Text('Certificate', readonly=True)
    priv_key = fields.Text('Private Key', readonly=True)
    authorized_users_ids = fields.One2many(
        'res.users', 'cert_owner_id', string='Authorized Users')
    cert_owner_id = fields.Many2one(
        'res.users', 'Certificate Owner', ondelete='cascade')

    @api.multi
    def action_clean1(self):
        self.ensure_one()
        self.write(zero_values)

    @api.multi
    def action_process(self):
        self.ensure_one()
        filecontent = base64.b64decode(self.key_file)
        self.load_cert_pk12(filecontent)

    @api.multi
    @api.depends('key_file')
    def _get_date(self):
        self.ensure_one()
        old_date = self.issued_date
        if self.key_file is not None and self.status == 'unverified':
            self.issued_date = fields.datetime.now()
        else:
            self.issued_date = old_date

    def get_digital_signature(self, company_id):
        obj = self
        certificate = self.check_cert_validity()
        if not certificate:
            obj = self.env['res.users'].search([("authorized_users_ids", "=", self.id)])
            certificate = obj.check_cert_validity()
            if not certificate or self.id not in obj.authorized_users_ids.ids:
                message = _('''There is no Signer Person with an authorized signature for you in the system. \
Please make sure that 'user_signature_key' module has been installed and enable a digital signature, for you or \
make the signer to authorize you to use his signature. Also check expiration date of the users signature. certificate:\
 %s, object id: %s, authorized users: %s''' % (certificate, self.id, obj.authorized_users_ids.ids))
                raise UserError(message)
        signature_data = {
            'subject_name': obj.name,
            'subject_serial_number': obj.subject_serial_number,
            'priv_key': obj.priv_key,
            'cert': obj.cert, }
        return signature_data
