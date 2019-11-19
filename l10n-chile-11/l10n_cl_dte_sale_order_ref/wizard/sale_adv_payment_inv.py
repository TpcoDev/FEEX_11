# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleAdvPaymentInvoice(models.TransientModel):
    _name = 'sale.advance.payment.inv'
    _inherit = 'sale.advance.payment.inv'
    _description = 'Inherited Invoice Creation Wizard with reference to sale order'

    refer_to_so = fields.Boolean('Refer to Sale Order')
    sale_order_no = fields.Char('Sale Order', compute='_get_sale_order', readonly=True)
    refer_to_po = fields.Boolean('Refer to Purchase Order')
    customer_po = fields.Char('Customer purchase order number')
    date_po = fields.Date('Customer purchase order date')

    def _get_sale_order(self):
        for record in self:
            sale_order_obj = self.env['sale.order'].browse(self._context['active_id'])
            record.sale_order_no = sale_order_obj.name

    @api.onchange('refer_to_po')
    def _refer_to_po(self):
        sale_order_obj = self.env['sale.order'].browse(self._context['active_id'])
        self.customer_po = sale_order_obj.client_order_ref or sale_order_obj.origin
        self.date_po = sale_order_obj.date_order

    @api.multi
    def create_invoices(self):
        super(SaleAdvPaymentInvoice, self).create_invoices()
        localization = self.env.user.company_id.localization
        sale_order_obj = self.env['sale.order']
        sale_order_id = sale_order_obj.browse(self._context['active_id'])
        if localization == 'chile' and (self.refer_to_so or self.refer_to_po) and len(self._context['active_ids']) == 1:
            invoice_obj = self.env['account.invoice'].search(
                [('origin', '=', sale_order_id.name)], order='id desc', limit=1)
            references = [[5, 0, ]]
            if self.refer_to_so:
                reference = {
                    'origin': sale_order_id.name,
                    'reference_doc_type': self.env.ref('l10n_cl_account.dc_ndp'),
                    'reason': 'Nota de Venta',
                    'date': sale_order_id.confirmation_date, }
                references.append([0, 0, reference])
            if self.refer_to_po:
                reference = {
                    'origin': self.customer_po,
                    'reference_doc_type': self.env.ref('l10n_cl_account.dc_oc'),
                    'reason': 'Orden de Compra',
                    'date': self.date_po, }
                references.append([0, 0, reference])
            _logger.info('references: %s' % references)
            invoice_obj.reference_ids = references
        if self._context.get('open_invoices', False):
            return sale_order_id.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}
