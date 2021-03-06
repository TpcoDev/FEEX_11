# -*- coding: utf-8 -*-
# Part of Konos. See LICENSE file for full copyright and licensing details.
import tempfile
import binascii
import logging
from datetime import datetime
from odoo.exceptions import UserError
from odoo import models, fields, api, _
from odoo.osv import expression
# from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
_logger = logging.getLogger(__name__)
try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')
try:
    import xlrd
except ImportError:
    _logger.debug('Cannot `import xlrd`.')


class AccountBankStatementWizard(models.TransientModel):
    _name = "account.bank.statement.wizard"

    file = fields.Binary('File')
    file_opt = fields.Selection(
        [('excel', 'Excel'),
         ('csv', 'CSV')], default='excel')
    bank_opt = fields.Selection(
        [('santander', 'Santander'),
         ('estado', 'Banco Estado'),
         ('chile', 'Banco de Chile'),
         ('itau', 'Banco Itau'),
         ('bci', 'BCI'), ])

    @api.multi
    def import_file(self):
        if self.file_opt == 'csv':
            keys = ['date', 'ref', 'partner_id', 'name', 'amount']
            data = base64.b64decode(self.file)
            file_input = StringIO(data.decode("utf-8"))
            file_input.seek(0)
            reader_info = []
            reader = csv.reader(file_input, delimiter=',')
 
            try:
                reader_info.extend(reader)
            except Exception:
                raise UserError(_("Not a valid file!"))
            for i in range(len(reader_info)):
                field = list(map(str, reader_info[i]))
                values = dict(zip(keys, field))
                if values:
                    if i == 0:
                        continue
                    else:
                        res = self._create_statement_line(values)
        elif self.file_opt == 'excel':
            fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
            fp.write(binascii.a2b_base64(self.file))
            fp.seek(0)
            values = {}
            workbook = xlrd.open_workbook(fp.name)
            sheet = workbook.sheet_by_index(0)
            contador = 0
            
            if self.bank_opt == 'santander':
                for row_no in range(sheet.nrows):
                    if row_no <= 0:
                        fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
                    else:
                        line = list(
                            map(lambda row: isinstance(row.value, str) and row.value.encode('utf-8') or
                                str(row.value), sheet.row(row_no)))
                        try:
                            date_string = datetime.strptime(line[3], '%d/%m/%Y').strftime('%Y-%m-%d')
                        except:
                            date_string = '01-01-01'
                            contador = contador + 1
                        if date_string != '01-01-01' and contador <= 100:
                            contador = 100
                            values.update({
                                'date': date_string,
                                'ref': line[4].decode("utf-8"),
                                'partner_id': line[7],
                                'name': line[1].decode("utf-8"),
                                'amount': line[0], })
                            res = self._create_statement_line(values)
            elif self.bank_opt == 'chile':
                for row_no in range(sheet.nrows):
                    if row_no <= 1:
                        fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
                    else:
                        line = list(map(lambda row: isinstance(row.value, str) and row.value.encode('utf-8') or str(
                            row.value), sheet.row(row_no)))
                        data = line[0].decode("utf-8").split(";")
                        fecha = data[0]
                        date_string = datetime.strptime(fecha, '%d/%m/%Y').strftime('%Y-%m-%d')
                        if data[3] == '00000000000':
                            values.update({
                                'date': date_string,
                                'ref': data[1],
                                'partner_id': 'X',
                                'name': data[1],
                                'amount': int(data[2]) * (-1), })
                        else: 
                            values.update({
                                'date': date_string,
                                'ref': data[1],
                                'partner_id': 'X',
                                'name': data[1],
                                'amount': data[3], })
                        res = self._create_statement_line(values)
            elif self.bank_opt == 'estado':
                for row_no in range(sheet.nrows):

                    if row_no <= 0:
                        fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
                    else:
                        line = list(map(lambda row: isinstance(row.value, str) and row.value.encode('utf-8') or
                                    str(row.value), sheet.row(row_no)))
                        date_string = line[5]
                        date_string = date_string[:10]
                        try:
                            date_string = datetime.strptime(date_string, '%d/%m/%Y').strftime('%Y-%m-%d')
                        except:
                            date_string = '01-01-01'
                            contador = contador + 1
                        if date_string != '01-01-01' and contador <= 100:
                            contador = 100
                            # if line[3] in (None, "", 0, '0'):
                            if line[3] <= line[4] or (line[3] in (None, "", 0, '0', "0")): 
                                values.update({
                                    'date': date_string,
                                    'ref': line[0].decode("utf-8"),
                                    'partner_id': line[6],
                                    'name': line[1].decode("utf-8"),
                                    'amount': int(line[4].replace('.', '')) / 10, })
                            else:
                                values.update({
                                    'date': date_string,
                                    'ref': line[0].decode("utf-8"),
                                    'partner_id': line[6],
                                    'name': line[1].decode("utf-8"),
                                    # 'amount': line[3] * (-1),
                                    'amount': int(line[3].replace('.', '')) * (-1) / 10, })
                            res = self._create_statement_line(values)
            
            if self.bank_opt == 'bci':
                for row_no in range(sheet.nrows):
                    if row_no <= 0:
                        fields = map(lambda row: row.value.encode('utf-8'), sheet.row(row_no))
                    else:
                        line = list(
                            map(lambda row: isinstance(row.value, str) and row.value.encode('utf-8') or
                                str(row.value), sheet.row(row_no)))
                        try:
                            date_string = datetime.strptime(line[0].decode().split(' ')[0], '%d/%m/%Y').strftime(
                                '%Y-%m-%d')
                        except:
                            date_string = '01-01-01'
                        if line[3]:
                            cell_value = '-%s' % line[3]
                        else:
                            cell_value = line[4]
                        values.update({
                            'date': date_string,
                            'ref': line[2],
                            'partner_id': '',
                            'name': line[1].decode("utf-8"),
                            'amount': cell_value, })
                        res = self._create_statement_line(values)
            else:
                # Este es el fin y se recorre invertido
                ano = sheet.cell(11, 3).value
                ano = ano[-5:]
                for row_no in range(sheet.nrows-11):
                    if row_no > 26:
                        line = list(map(lambda row: isinstance(row.value, str) and row.value.encode('utf-8') or
                                        str(row.value), sheet.row(row_no)))
                        date_string = line[0].decode("utf-8")+ano
                        date_string = datetime.strptime(date_string, '%d/%m/%Y').strftime('%Y-%m-%d')
                        if line[4] <= line[5]: 
                            values.update({
                                'date': date_string,
                                'ref': line[1].decode("utf-8"),
                                'partner_id': line[6],
                                'name': line[3].decode("utf-8"),
                                'amount': int(line[5].replace('.0', ''))*(-1), })
                        else:
                            values.update({
                                'date': date_string,
                                'ref': line[1].decode("utf-8"),
                                'partner_id': line[6],
                                'name': line[3].decode("utf-8"),
                                'amount': line[4], })
                        res = self._create_statement_line(values)

        else:
            raise UserError('Please Select File Type')
        self.env['account.bank.statement'].browse(self._context.get('active_id'))._end_balance()
        return res

    def _find_partner(self, name):
        partner_id = self.env['res.partner'].search([
            ('name', '=', name), ])
        if partner_id:
            return partner_id.id
        else:
            return

    @api.multi
    def _create_statement_line(self, val):
        if not val.get('date'):
            raise UserError('Please Provide Date Field Value')
        if not val.get('name'):
            raise UserError('Please Provide Memo Field Value')
        val['partner_id'] = self._find_partner(val.get('partner_id'))
        val['statement_id'] = self._context.get('active_id')
        self.env['account.bank.statement.line'].create(val)


class AccountBankStatementLine(models.Model):
    _name = "account.bank.statement.line"
    _inherit = 'account.bank.statement.line'

    def get_move_lines_for_reconciliation(
            self, partner_id=None, excluded_ids=None, str=False, offset=0, limit=None, additional_domain=None,
            overlook_partner=False):
        """
        Return account.move.line records which can be used for bank statement reconciliation.
        :param partner_id:
        :param excluded_ids:
        :param str:
        :param offset:
        :param limit:
        :param additional_domain:
        :param overlook_partner:
        """
        _logger.debug('Pasa por aquí')
        if partner_id is None:
            partner_id = self.partner_id.id

        # Blue lines = payment on bank account not assigned to a statement yet
        reconciliation_aml_accounts = [
            self.journal_id.default_credit_account_id.id, self.journal_id.default_debit_account_id.id]
        # domain_reconciliation = ['&', '&', ('statement_line_id', '=', False),
        # ('account_id', 'in', reconciliation_aml_accounts), ('payment_id','<>', False)]
        domain_reconciliation = ['&',  ('statement_line_id', '=', False), (
            'account_id', 'in', reconciliation_aml_accounts)]

        # Black lines = unreconciled & (not linked to a payment or open balance created by statement
        domain_matching = [('reconciled', '=', False)]
        if partner_id or overlook_partner:
            domain_matching = expression.AND([domain_matching, [
                ('account_id.internal_type', 'in', ['payable', 'receivable'])]])
        else:
            # TODO : find out what use case this permits (match a check payment, registered on a journal whose
            # account type is other instead of liquidity)
            domain_matching = expression.AND([domain_matching, [('account_id.reconcile', '=', True)]])

        # Let's add what applies to both
        domain = expression.OR([domain_reconciliation, domain_matching])
        if partner_id and not overlook_partner:
            domain = expression.AND([domain, [('partner_id', '=', partner_id)]])

        # Domain factorized for all reconciliation use cases
        if str:
            str_domain = self.env['account.move.line'].domain_move_lines_for_reconciliation(str=str)
            if not partner_id:
                str_domain = expression.OR([str_domain, [('partner_id.name', 'ilike', str)]])
            domain = expression.AND([domain, str_domain])
        if excluded_ids:
            domain = expression.AND([[('id', 'not in', excluded_ids)], domain])

        # Domain from caller
        if additional_domain is None:
            additional_domain = []
        else:
            additional_domain = expression.normalize_domain(additional_domain)
        domain = expression.AND([domain, additional_domain])
        # domain = expression.AND([additional_domain])
        _logger.debug('DOMAIN')
        _logger.debug(domain)
        return self.env['account.move.line'].search(
            domain, offset=offset, limit=limit, order="date_maturity desc, id desc")
