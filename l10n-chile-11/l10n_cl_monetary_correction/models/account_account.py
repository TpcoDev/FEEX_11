# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountAccount(models.Model):
    _name = 'account.account'
    _inherit = 'account.account'

    monetary_correction = fields.Selection(
        [('yes', 'Yes'), ('no', 'No'), ],
        string='Monetary Correction', help='Correct Account Entries in this Journal Using IPC Values')
    counterpart_account_id = fields.Many2one(
        'account.account', string='Counterpart',
        help='Counterpart Account for Monetary Correction. Usually an order account or equity account. If you don\'t \
define this account the correction will impact directly over the monetary correction journal default account.')


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = 'account.move'

    monetary_correction_line_ids = fields.One2many(
        'account.asset.monetary.correction.line', 'move_made_id',
        string='Assets Monetary Correction Lines', ondelete="restrict")

    @api.multi
    def button_cancel(self):
        for move in self:
            for line in move.monetary_correction_line_ids:
                line.move_posted_check = False
        return super(AccountMove, self).button_cancel()

    @api.multi
    def post(self):
        super(AccountMove, self).post()
        for move in self:
            for monetary_correction_line in move.monetary_correction_line_ids:
                monetary_correction_line.post_correction_lines_on_asset()


class EntryMonetaryCorrectionLine(models.Model):
    _name = 'account.move.monetary.correction.line'
    _description = 'Monetary Correction Line for Account Moves'
    _order = 'origin_move_id, sequence, id'

    @api.depends('ipc_id', 'book_value')
    def _compute_correction(self):
        for line in self:
            line.update({
                'correction_value': line.ipc_id.value,
                'corrected_value': line.book_value * (1 + line.ipc_id.value / 100),
            })

    name = fields.Text(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    date_planned = fields.Date(string='Scheduled Date', required=True, index=True)
    ipc_id = fields.Many2one(
        'account.ipc', string='IPC Index', domain=[], change_default=True, required=True)
    origin_move_id = fields.Many2one(
        'account.move', string='Origin Move', index=True, required=True, ondelete='cascade')
    origin_move_line_id = fields.Many2one(
        'account.move', string='Origin Move Line', index=True, required=True, ondelete='cascade')
    book_value = fields.Float(string='Book Value', required=True)
    correction_value = fields.Float(compute='_compute_correction', string='Correction', store=True)
    corrected_value = fields.Float(compute='_compute_correction', string='Corrected Val', store=True)
    company_id = fields.Many2one(
        'res.company', related='origin_move_id.company_id', string='Company', store=True, readonly=True)
    move_made_id = fields.Many2one(
        'account.move', string='Account Entry Gen', readonly=True, ondelete='set null', copy=False)
    state = fields.Selection(related='move_made_id.state', store=True)
    date_entry = fields.Date(related='move_made_id.date', string='Move Date', readonly=True)
