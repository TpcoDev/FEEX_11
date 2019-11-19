from odoo import fields, models, api
from openerp.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class OpenInvoicesWizard(models.TransientModel):
    _name = 'account.batch.payments.open_inv_wizard'

    invoice_ids = fields.Many2many(
        'account.invoice', string="Invoices", )
    previous_invoice_ids = fields.Many2many(
        'account.invoice',
        'batch_payments_prev_invoices_rel',
        string="Previous Invoices",
        default=lambda self: self._get_previous_invoices(), )

    @api.model
    def _get_previous_invoices(self):
        batch_id = self.env['account.batch.payments'].browse(
            self.env.context.get('active_id'))
        return batch_id.line_ids.mapped('invoice_id.id')

    @api.multi
    def get_invoices(self):
        batch_id = self.env['account.batch.payments'].browse(
            self.env.context.get('active_id'))

        vals = []
        inv_result = list(set(self.invoice_ids.ids) - set(self._get_previous_invoices()))
        invoice_ids = self.invoice_ids.browse(inv_result)
        
        for inv in invoice_ids:
            vals.append(
                (0, 0, {'invoice_id': inv.id, 'balance_amount': inv.residual, }))
        
        if vals:
            batch_id.write({'line_ids': vals, })
