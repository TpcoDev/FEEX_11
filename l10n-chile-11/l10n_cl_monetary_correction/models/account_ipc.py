# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountIPC(models.Model):
    _name = 'account.ipc'

    def _default_year(self):
        month = str(int(fields.Date.today()[5:7]) - 1).zfill(2)
        year = int(fields.Date.today()[:4])
        return year if month != '00' else year - 1

    def _default_month(self):
        month = str(int(fields.Date.today()[5:7]) - 1).zfill(2)
        return month if month != '00' else '12'

    name = fields.Char('Name', compute='_create_name', store=True)
    year_from = fields.Integer(string='Year From', default=_default_year)
    month_from = fields.Selection(
        [
            ('01', 'January'),
            ('02', 'February'),
            ('03', 'March'),
            ('04', 'April'),
            ('05', 'May'),
            ('06', 'June'),
            ('07', 'July'),
            ('08', 'August'),
            ('09', 'September'),
            ('10', 'October'),
            ('11', 'November'),
            ('12', 'December'),
        ],
        string='Month From', default=_default_month, help='IPC Computation from first day of this month')
    year_to = fields.Integer(string='Year To', default=_default_year)
    month_to = fields.Selection(
        [
            ('01', 'January'),
            ('02', 'February'),
            ('03', 'March'),
            ('04', 'April'),
            ('05', 'May'),
            ('06', 'June'),
            ('07', 'July'),
            ('08', 'August'),
            ('09', 'September'),
            ('10', 'October'),
            ('11', 'November'),
            ('12', 'December'),
        ],
        string='Month To', default=_default_month, help='IPC Computation to last day of this month')
    value = fields.Float('Value')

    @api.depends('year_from', 'year_to', 'month_from', 'month_to')
    def _create_name(self):
        for record in self:
            record.name = str(record.year_from) + '-' + record.month_from + ' : ' + str(record.year_to) +\
                          '-' + record.month_to

    @api.constrains('name')
    def _name_unique(self):
        for record in self:
            if self.search([('name', '=', record.name), ('id', '!=', record.id)]):
                raise ValidationError('Index value already exists: %s' % record.name)
