# -*- encoding: utf-8 -*-
import logging
from openerp import fields, models, api, _
from odoo.addons import decimal_precision as dp
from openerp.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class PickingChangeCurrency(models.TransientModel):
    _name = 'picking.change.currency'
    _description = 'Change Currency'

    currency_id = fields.Many2one(
        'res.currency',
        string='Change to',
        required=True,
        default=lambda self: self.env.user.company_id.currency_id,
        help="Select a currency to apply on the invoice"
    )
    currency_rate = fields.Float(
        'Currency Rate',
        required=True,
        help="Select a currency to apply on the invoice"
    )
    inverse_currency_rate = fields.Float(
        'Inverse Currency Rate',
    )
    currency_rate_readonly = fields.Float(
        related='currency_rate',
        readonly=True,
        digits=dp.get_precision('Currency')
    )

    @api.multi
    def get_picking(self):
        self.ensure_one()
        picking = self.env['stock.picking'].browse(
            self._context.get('active_id', False))
        if not picking:
            raise ValidationError(_('No Picking on context as "active_id"'))
        return picking

    @api.onchange('currency_id')
    def onchange_currency(self):
        picking = self.get_picking()
        currency = picking.currency_id
        if picking.company_id.currency_id == picking.currency_id:
            self.currency_rate = self.currency_id.rate
        else:
            self.currency_rate = currency.compute(1.0, self.currency_id, round=False)
        if self.currency_rate != 0.0:
            self.inverse_currency_rate = 1 / self.currency_rate

    @api.multi
    def change_currency(self, ):
        self.ensure_one()
        picking = self.get_picking()
        if self.currency_rate >= 1:
            for line in picking.move_lines:
                line.delivery_price_unit = self.currency_id.round(
                    line.delivery_price_unit * self.currency_rate)
            for line in picking.tax_line_ids.filtered(lambda x: x.manual):
                line.amount = self.currency_id.round(
                    line.amount * self.currency_rate)
            message = _("Currency changed from {0} to {1}. Rate: {1} {2} per {0}.").format(
                picking.currency_id.name, self.currency_id.name, round(self.currency_rate, 2))
            message2 = _("// Original quotation in {0}. Rate: {1} {2} per {0}.").format(
                picking.currency_id.name, self.currency_id.name, round(self.currency_rate, 2))
        else:
            for line in picking.move_lines:
                line.delivery_price_unit = self.currency_id.round(
                    line.delivery_price_unit / self.inverse_currency_rate)
            for line in picking.tax_line_ids.filtered(lambda x: x.manual):
                line.amount = self.currency_id.round(
                    line.amount / self.inverse_currency_rate)
            message = _("Currency changed from {0} to {1}. Rate: {0} {2} per {1}.").format(
                picking.currency_id.name, self.currency_id.name, round(self.inverse_currency_rate, 2))
            message2 = _("// Original quotation in {0}. Rate: {0} {2} per {1}.").format(
                picking.currency_id.name, self.currency_id.name, round(self.inverse_currency_rate, 2))
        picking.currency_id = self.currency_id.id
        picking.compute_taxes()
        try:
            picking.comment = picking.comment[:picking.comment.find('//')] + message2
        except AttributeError:
            picking.comment = message2
        picking.message_post(message)
        return {'type': 'ir.actions.act_window_close'}
