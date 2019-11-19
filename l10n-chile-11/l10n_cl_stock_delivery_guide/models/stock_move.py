# -*- coding: utf-8 -*-
from odoo import osv, models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _name = 'stock.move'
    _inherit = 'stock.move'

    @api.model
    def create(self, vals):
        if 'picking_id' in vals:
            picking = self.env['stock.picking'].browse(vals['picking_id'])
            if picking and picking.company_id:
                vals['company_id'] = picking.company_id.id
                vals['currency_id'] = picking.currency_id.id
        return super(StockMove, self).create(vals)

    def _set_price_from(self):
        if self.picking_id.reference_ids:
            for ref in self.picking_id.reference_ids:
                if ref.reference_doc_type.code in [33]:  # factura venta
                    il = self.env['account.invoice'].search(
                        [
                            ('sii_document_number', '=', ref.origin),
                            ('document_type_id.code', '=', ref.reference_doc_type.code),
                            ('product_id', '=', self.product_id.id),
                        ]
                    )
                    if il:
                        self.delivery_price_unit = il.delivery_price_unit
                        self.subtotal = il.subtotal
                        self.discount = il.discount
                        self.move_line_tax_ids = il.invoice_line_tax_ids

    @api.depends('picking_id.reference_ids')
    @api.onchange('name')
    def _sale_prices(self):
        # prevent to recalculate prices
        _logger.info('_sale_prices: ')
        for rec in self:
            if rec.delivery_price_unit <= 0:
                rec._set_price_from()
            if rec.delivery_price_unit <= 0:
                rec.delivery_price_unit = rec.product_id.lst_price
                rec.move_line_tax_ids = rec.product_id.taxes_id  # TODO mejorar asignación
            if not rec.name:
                rec.name = rec.product_id.name

    @api.onchange('name', 'product_id', 'move_line_tax_ids', 'product_uom_qty', 'delivery_price_unit', 'quantity_done')
    def _compute_amount(self):
        for rec in self:
            price = rec.delivery_price_unit * (1 - (rec.discount or 0.0) / 100.0)
            qty = rec.quantity_done
            if qty <= 0:
                qty = rec.product_uom_qty
            rec.subtotal = qty * price

    name = fields.Char(
        string="Nombre",
    )
    subtotal = fields.Float(
        compute='_compute_amount',
        string='Subtotal',
    )
    delivery_price_unit = fields.Float(
        string='Precio Unitario',
        oldname='precio_unitario',
    )
    price_untaxed = fields.Float(
        compute='_sale_prices',
        string='Price Untaxed',
    )
    move_line_tax_ids = fields.Many2many(
        'account.tax',
        'move_line_tax_ids',
        'move_line_id',
        'tax_id',
        string='Taxes',
        domain=lambda self: [
            ('type_tax_use', '!=', 'none'),
            ('company_id', '=', self.env.user.company_id.id),
            '|', ('active', '=', False), ('active', '=', True)
        ],
        oldname='invoice_line_tax_id',
    )
    discount = fields.Float(
        digits=dp.get_precision('Discount'),
        string='Discount (%)',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user.company_id.currency_id.id,
        track_visibility='always',
    )
