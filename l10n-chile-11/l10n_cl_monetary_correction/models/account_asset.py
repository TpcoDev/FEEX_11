# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
# from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class AssetMonetaryCorrectionCategory(models.Model):
    _name = 'account.asset.category'
    _inherit = 'account.asset.category'

    calculation_basis = fields.Selection(
        [('monthly', 'Monthly'),
         ('yearly', 'Yearly'), ], default='yearly', string='Calculation Basis', )
    monetary_correction_journal_id = fields.Many2one('account.journal', string='Monetary Correction Journal')
    counterpart_account_id = fields.Many2one(
        'account.account', string='Counterpart Order Account',
        help='Counterpart Account for Monetary Correction. Usually an order account or equity account. If you don\'t \
define this account the correction will impact directly over the monetary correction journal default account.')


class AssetMonetaryCorrection(models.Model):
    _name = 'account.asset.asset'
    _inherit = 'account.asset.asset'

    @staticmethod
    def month_year_iter(start_month, start_year, end_month, end_year):
        ym_start = 12 * start_year + start_month - 1
        ym_end = 12 * end_year + end_month - 1
        for ym in range(ym_start, ym_end):
            y, m = divmod(ym, 12)
            yield y, str(m + 1).zfill(2)

    @api.multi
    def _compute_monetary_correction(self, ipc_id, lines, basis):
        if len(lines) >= 1:
            _logger.info('###### ------ lines: %s' % lines)
            if basis == 'yearly':
                value = lines[len(lines)-1][2]['corrected_value']
            else:
                value = lines[len(lines) - 1].corrected_value
        else:
            value = self.value
        _logger.info('#######  ---   compute monetary corr... value: %s len monetary_correction: %s' % (
            value, len(self.monetary_correction_line_ids)))
        # if len(self.year_values_ids) >= 1:
        #     value = self.year_values_ids[len(self.year_values_ids)-1].year_value
        # else:
        #     value = self.value
        # raise UserError('value: %s' % value)
        line = {
            'name': self.name,
            'date_planned': fields.Date.today(),
            'ipc_id': ipc_id.id,
            'basis': basis,
            'book_value': self.value,
            'correction_value': value * (ipc_id.value / 100),
            'corrected_value': value * (1 + ipc_id.value / 100),
            'incremental_value': value * (1 + ipc_id.value / 100) - self.value,
            'move_check': False,
        }
        return line

    def _get_deprec_value(self, year_from, month_from, year_to, month_to):
        mm = {
            '01': 31,
            '02': 28,
            '03': 31,
            '04': 30,
            '05': 31,
            '06': 30,
            '07': 31,
            '08': 31,
            '09': 30,
            '10': 31,
            '11': 30,
            '12': 31,
        }
        #         query = """select depreciated_value - amount from account_asset_depreciation_line
        # where asset_id = {0} and depreciation_date between '{1}-{2}-01' and '{1}-{3}-31'""".format(
        #    self.id, year, month_from, end_month)
        # query = """select depreciated_value - amount as am from account_asset_depreciation_line
        # where asset_id = {0} and depreciation_date <= '{1}-{2}-{3}'""".format(
        #     self.id, year_to, month_to, mm[month_to])
        query = """select sum(amount) - max(amount) from account_asset_depreciation_line
        where asset_id = {0} and depreciation_date <= '{3}-{4}-{5}'""".format(
            self.id, year_from, month_from, year_to, month_to, mm[month_to])
        _logger.info('query:  %s' % query)
        self._cr.execute(query)
        depreciated_value = self._cr.fetchone()[0]
        if depreciated_value:
            return depreciated_value
        else:
            return 0.0

    def _get_sequence(self):
        try:
            return len(self.monetary_correction_line_ids)
        except:
            return 0

    def calculate_monetary_correction(self):
        ipc_obj = self.env['account.ipc']
        today = fields.Date.from_string(fields.Date.today())
        previous_month_to_year = 0
        for record in self:
            date = fields.Date.from_string(record.date)
            for i in range(2):
                if (record.calculation_basis == 'yearly' or date.year < today.year) and i == 0:
                    if date.year < today.year:
                        lines = []
                        year_values = []
                        purchase_year = date.year
                        sequence_add = 1
                        for year in range(date.year, today.year):
                            if year == purchase_year:
                                month_from = str(date.month + 1).zfill(2)
                                year_from = year
                            else:
                                month_from = '12'
                                year_from = year - 1
                            month_to = '11'
                            ipc_id = ipc_obj.search(
                                [
                                    ('year_from', '=', year_from),
                                    ('year_to', '=', year),
                                    ('month_from', '=', month_from),
                                    ('month_to', '=', month_to),
                                ]
                            )
                            depreciated_value = record._get_deprec_value(year_from, month_from, year, str(int(month_to) + 1))
                            _logger.info('where asset_id: %s' % depreciated_value)
                            if ipc_id:
                                _logger.info('ipc_id: %s, monetary_corr_line_ids: %s' % (
                                    ipc_id.id, [x.ipc_id.id for x in record.monetary_correction_line_ids]))
                                if ipc_id.id not in [x.ipc_id.id for x in record.monetary_correction_line_ids]:
                                    _logger.info('IPC found for %s basis: %s' % (record.calculation_basis, ipc_id.value))
                                    line = record._compute_monetary_correction(ipc_id, lines, 'yearly')
                                    # line['name']
                                    line['sequence'] = record._get_sequence() + sequence_add
                                    line['depreciated_value'] = depreciated_value
                                    line['month_to_year'] = 13 - int(month_from) if int(month_from) != 12 else int(
                                        month_from)
                                    line['month_to_total'] = len(
                                        record.depreciation_line_ids) - previous_month_to_year
                                    previous_month_to_year += line['month_to_year']
                                    lines.append((0, 0, line))
                                    sequence_add += 1
                                    year_value = {
                                        'name': year,
                                        'year_incremental_value': line['incremental_value'],
                                        'year_correction_value': line['correction_value'],
                                        'year_value': line['corrected_value'],
                                        'year_ipc_id': line['ipc_id'],
                                        'depreciated_value': depreciated_value,
                                    }
                                    year_values.append((0, 0, year_value))
                                else:
                                    _logger.info('value of IPC already computed')
                            else:
                                raise UserError('Valor de IPC faltante: %s-%s | %s-%s' % (
                                    year, month_from, year, month_to))

                        record.monetary_correction_line_ids = lines
                        _logger.info('Year values: %s' % year_values)
                        record.year_values_ids = year_values
                        date = fields.Date.from_string('%s-%s' % (today.year - 1, '12-31'))

                        continue
                    else:
                        pass
                        _logger.info('No se contemplan fechas futuras del indice (no existen)')
                else:
                    _logger.info('monthly basis %s, date: %s, today: %s' % (i, date, today))
                    year_values = []
                    purchase_year = date.year
                    purchase_month = date.month
                    previous_month_to_year = 0 if not previous_month_to_year else previous_month_to_year
                    end_month = 12
                    for year in [purchase_year, today.year]:
                        if year > purchase_year:
                            initial_month = 12
                        else:
                            initial_month = purchase_month
                        if year == today.year:
                            end_month = today.month
                        _logger.info('initial_month: %s, purchase_year: %s, end_month: %s, year: %s' % (
                            initial_month, purchase_year, end_month, today.year))
                        list_item = []
                        sequence_add = 1
                        line = {}
                        for mm in self.month_year_iter(initial_month, purchase_year, end_month, today.year):
                            if len(list_item) in [0, 1]:
                                list_item.append(mm)
                                if len(list_item) == 2:
                                    _logger.info('looking for list_item: %s' % list_item)
                                    ipc_id = ipc_obj.search(
                                        [
                                            ('year_from', '=', list_item[0][0]),
                                            ('month_from', '=', list_item[0][1]),
                                            ('year_to', '=', list_item[1][0]),
                                            ('month_to', '=', list_item[1][1]),
                                        ]
                                    )
                                    if not ipc_id:
                                        raise UserError('Valor de IPC faltante: %s' % list_item)
                                    _logger.info('ipc_id: %s, monetary_corr_line_ids: %s' % (
                                        ipc_id.id, [x.ipc_id.id for x in record.monetary_correction_line_ids]))
                                    depreciated_value = record._get_deprec_value(
                                        list_item[0][0], list_item[0][1], list_item[1][0], list_item[1][1])
                                    _logger.info('where asset_id: %s' % depreciated_value)
                                    if ipc_id.id not in [x.ipc_id.id for x in record.monetary_correction_line_ids]:
                                        _logger.info('IPC found for %s basis: %s' % (
                                            record.calculation_basis, ipc_id.value))
                                        line = record._compute_monetary_correction(
                                            ipc_id, record.monetary_correction_line_ids, 'monthly')
                                        _logger.info('line computed: %s, for ipc: %s' % (line, ipc_id.value))
                                        line['sequence'] = record._get_sequence() + sequence_add
                                        line['depreciated_value'] = depreciated_value
                                        line['month_to_year'] = int(list_item[0][1]) + 1 if int(list_item[0][1]) != 12 \
                                            else 1
                                        last_month_to_total_year = [x.month_to_total for x in record.monetary_correction_line_ids][
                                            len(record.monetary_correction_line_ids)-1]
                                        line['month_to_total'] = last_month_to_total_year - 1
                                        record.monetary_correction_line_ids = [(0, 0, line)]
                                        if year < today.year:
                                            year_value = {
                                                'name': year,
                                                'year_incremental_value': line['incremental_value'],
                                                'year_correction_value': line['correction_value'],
                                                'year_value': line['corrected_value'],
                                                'year_ipc_id': line['ipc_id'],
                                                'depreciated_value': depreciated_value,
                                            }
                                            year_values.append((0, 0, year_value))
                                        line = {}
                                    list_item = []
                                    list_item.append(mm)
                    # record.monetary_correction_line_ids = lines
                    # raise UserError('Corrección mensual no implementada')
                    # terminó de ingresar los valores, ahora recorre todas las lineas y decrementa el valor
                    previous_value = 0.0
                    for line in record.monetary_correction_line_ids:
                        if previous_value == 0.0:
                            _logger.info('previous value (0) %s, incremental: %s' % (
                                previous_value, line.incremental_value))
                            if line.basis == 'monthly':
                                line.correction_value = line.incremental_value
                        else:
                            _logger.info('previous value (else) %s' % previous_value)
                            if line.basis == 'monthly':
                                line.correction_value = line.incremental_value - previous_value
                        if line.basis == 'monthly':
                            previous_value = line.incremental_value
                            line.corrected_value = record.value + line.correction_value

    monetary_correction_line_ids = fields.One2many(
        'account.asset.monetary.correction.line', 'asset_id', string='Monetary Correction Lines', readonly=True,
        states={'draft': [('readonly', False)], 'open': [('readonly', False)]})
    calculation_basis = fields.Selection(
        [('monthly', 'Monthly'),
         ('yearly', 'Yearly'), ], related='category_id.calculation_basis', readonly=True, string='Calculation Basis', )
    monetary_correction_journal_id = fields.Many2one(
        'account.journal', string='Monetary Correction Journal', related='category_id.monetary_correction_journal_id',
        readonly=True)
    counterpart_account_id = fields.Many2one(
        'account.account', string='Counterpart Account', related='category_id.monetary_correction_journal_id',
        help='Counterpart Account for Monetary Correction. Usually an order account or equity account. If you don\'t \
define this account the correction will impact directly over the monetary correction journal default account.')
    year_values_ids = fields.One2many(
        'account.asset.monetary.correction.years', 'asset_id', string='Values in years of correction',
        help='Values of asset in each year')


class AssetMonetaryCorrectionYears(models.Model):
    _name = 'account.asset.monetary.correction.years'
    _description = 'Values in years of correction'
    _order = 'asset_id, id'

    name = fields.Char('Year')
    asset_id = fields.Many2one('account.asset.asset', string='Values')
    year_incremental_value = fields.Float('Incremental Value', digits=(25, 0))
    year_correction_value = fields.Float('Correction Value', digits=(25, 0))
    year_ipc_id = fields.Many2one(
        'account.ipc', string='Year IPC', domain=[], change_default=True, required=True)
    year_ipc_value = fields.Float(related='year_ipc_id.value', string='Year IPC Value')
    year_value = fields.Float('Gross Asset Value - year', digits=(25, 0))
    depreciated_value = fields.Float('Year Deprec.', digits=(25, 0))


class AssetMonetaryCorrectionLine(models.Model):
    _name = 'account.asset.monetary.correction.line'
    _description = 'Monetary Correction Line for Assets'
    _order = 'asset_id, sequence, id'

    @api.multi
    @api.depends('move_made_id')
    def _get_move_check(self):
        for line in self:
            line.move_check = bool(line.move_made_id)

    @api.multi
    @api.depends('move_made_id.state')
    def _get_move_posted_check(self):
        for line in self:
            line.move_posted_check = True if line.move_made_id and line.move_made_id.state == 'posted' else False

    @api.multi
    def create_move(self, post_move=True):
        created_moves = self.env['account.move']
        prec = self.env['decimal.precision'].precision_get('Account')
        for line in self:
            if line.move_made_id:
                raise UserError(_(
                    'This monetary correction is already linked to a journal entry! Please post or delete it.'))
            category_id = line.asset_id.category_id
            date_planned = self.env.context.get(
                'date_planned') or line.date_planned or fields.Date.context_today(self)
            company_currency = line.asset_id.company_id.currency_id
            current_currency = line.asset_id.currency_id
            amount = current_currency.with_context(date=date_planned).compute(line.correction_value, company_currency)
            asset_name = line.asset_id.name + ' (%s/%s)' % (line.sequence, len(
                line.asset_id.monetary_correction_line_ids))
            # agregar cuenta de depreciacion. Secuencia:
            # 1. busca en la categoria
            # 2. busca en la cuenta contable a usar como contrapartida
            # 3. busca en el cuenta contable a usar como cuenta de activo (impacta directamente en el activo)
            debit = 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount
            credit = amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0
            # define the main correction account (increment => credit)
            if category_id.counterpart_account_id:
                main_account_id = category_id.counterpart_account_id
            elif category_id.account_asset_id.counterpart_account_id:
                main_account_id = category_id.counterpart_account_id
            else:
                main_account_id = category_id.account_asset_id
            # define the counterpart account
            counterpart_account_id = line.asset_id.monetary_correction_journal_id.default_debit_account_id \
                if credit > 0.0 else line.asset_id.monetary_correction_journal_id.default_credit_account_id
            move_line_1 = {
                'name': asset_name,
                'account_id': counterpart_account_id.id,
                'debit': debit,
                'credit': credit,
                'journal_id': category_id.monetary_correction_journal_id.id,
                'partner_id': line.asset_id.partner_id.id,
                'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
            }
            move_line_2 = {
                'name': asset_name,
                'account_id': main_account_id.id,
                'credit': debit,
                'debit': credit,
                'journal_id': category_id.monetary_correction_journal_id.id,
                'partner_id': line.asset_id.partner_id.id,
                'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'purchase' else False,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and line.amount or 0.0,
            }
            move_vals = {
                'ref': line.asset_id.code,
                'date': date_planned or False,
                'journal_id': category_id.monetary_correction_journal_id.id,
                'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
            }
            move = self.env['account.move'].create(move_vals)
            line.write(
                {'move_made_id': move.id, 'move_check': True})
            created_moves |= move

        if post_move and created_moves:
            created_moves.filtered(
                lambda m: any(m.monetary_correction_line_ids.mapped('asset_id.category_id.open_asset'))).post()
        return [x.id for x in created_moves]

    @api.multi
    def post_correction_lines_on_asset(self):
        for line in self:
            asset = line.asset_id
            asset.message_post(body=_("Document %s registered for monetary correction line %s with IPC index %s." % (
                line.move_made_id.name,
                line.name,
                line.ipc_value
            )))

    name = fields.Text(string='Name', required=True)
    sequence = fields.Integer(string='Seq.', default=10)
    date_planned = fields.Date(string='Calc. Date', required=True, index=True)
    ipc_id = fields.Many2one(
        'account.ipc', string='IPC Index', domain=[], change_default=True, required=True)
    ipc_value = fields.Float(related='ipc_id.value', string='IPC')
    basis = fields.Selection([('yearly', 'Yearly'), ('monthly', 'Monthly')], string='Basis')
    asset_id = fields.Many2one(
        'account.asset.asset', string='Asset', index=True, required=True, ondelete='cascade')
    book_value = fields.Float(
        related='asset_id.value_residual', string='Book Val.', required=True, digits=(25, 0))
    correction_value = fields.Float(string='Corr. Before Deprec.', digits=(25, 0))
    corrected_value = fields.Float(string='Corrected Val', digits=(25, 0))
    incremental_value = fields.Float(string='Incremental Value')
    company_id = fields.Many2one(
        'res.company', related='asset_id.company_id', string='Company', store=True, readonly=True)
    move_made_id = fields.Many2one(
        'account.move', string='Account Entry Gen', readonly=True, ondelete='set null', copy=False)
    parent_state = fields.Selection(related='asset_id.state', store=True)
    date_entry = fields.Date(related='move_made_id.date', string='Move Date', readonly=True)
    move_check = fields.Boolean(compute='_get_move_check', string='Linked', track_visibility='always', store=True)
    move_posted_check = fields.Boolean(
        compute='_get_move_posted_check', string='Posted', track_visibility='always', store=True)
    depreciated_value = fields.Float('Deprec. Val.')
    month_to_year = fields.Integer('Month to Year')
    month_to_total = fields.Integer('Month to Total')
    rate_to_adjust = fields.Float(compute='_compute_rate', string='Rate')

    @api.depends('month_to_year', 'month_to_total')
    def _compute_rate(self):
        for record in self:
            if record.month_to_total != 0 and record.month_to_total:
                record.rate_to_adjust = record.month_to_year / record.month_to_total
