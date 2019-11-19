# -*- coding: utf-8 -*-
from datetime import date, datetime
from odoo import osv, models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import except_orm, UserError
import odoo.addons.decimal_precision as dp
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import logging
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = 'stock.picking'

    def get_document_class_default(self, document_classes):
        document_class_id = False
        if self.turn_issuer.vat_affected not in ['SI', 'ND']:
            exempt_ids = [
                self.env.ref('l10n_cl_fe.dc_y_f_dtn').id,
                self.env.ref('l10n_cl_fe.dc_y_f_dte').id]
            for document_class in document_classes:
                if document_class.document_type_id.id in exempt_ids:
                    document_class_id = document_class.id
                    break
                else:
                    document_class_id = document_classes.ids[0]
        else:
            document_class_id = document_classes.ids[0]
        return document_class_id

    @api.onchange('origin')
    def _set_delivery_guide_currency(self):
        for rec in self:
            if rec.origin:
                sale = self.env['sale.order'].search([('name', '=', rec.origin)])
                if len(sale) == 1:
                    rec.currency_id = sale[0].currency_id

    @api.onchange('company_id')
    def _set_available_issuer_turns(self):
        for rec in self:
            if rec.company_id:
                available_turn_ids = rec.company_id.company_activities_ids
                for turn in available_turn_ids:
                    rec.turn_issuer = turn
            if rec.origin:
                rec._set_delivery_guide_currency()

    @api.onchange('currency_id', 'move_lines', 'move_reason')
    def _compute_amount(self):
        for rec in self:
            if rec.move_reason not in ['5']:
                taxes = {}
                amount_untaxed = 0
                amount_tax = 0
                if rec.move_lines:
                    for move in rec.move_lines:
                        amount_untaxed += move.subtotal
                        if move.move_line_tax_ids:
                            for t in move.move_line_tax_ids:
                                taxes.setdefault(t.id, [t, 0])
                                taxes[t.id][1] += move.subtotal
                if taxes:
                    amount_untaxed = 0
                    for t, value in taxes.items():
                        amount_tax += value[0].compute_all(value[1], rec.currency_id, 1)['taxes'][0]['amount']
                        amount_untaxed += value[0].compute_all(value[1], rec.currency_id, 1)['total_excluded']
                rec.amount_tax = amount_tax
                rec.amount_untaxed = amount_untaxed
            rec.amount_total = rec.amount_untaxed + rec.amount_tax

    def set_use_document(self):
        return self.picking_type_id and self.picking_type_id.code != 'incoming'

    """
    def _is_product_pack_installed(self):
        module_obj = self.env['ir.module.module']
        module = module_obj.search([
            ('name', '=', 'product_pack'),
            ('state', '=', 'installed')
        ])
        return len(module) >= 1
    """

    amount_untaxed = fields.Monetary(
        compute='_compute_amount',
        digits=dp.get_precision('Account'),
        string='Untaxed Amount',
    )
    amount_tax = fields.Monetary(
        compute='_compute_amount',
        digits=dp.get_precision('Account'),
        string='Taxes',
    )
    amount_total = fields.Monetary(
        compute='_compute_amount',
        digits=dp.get_precision('Account'),
        string='Total',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env.user.company_id.currency_id.id,
        track_visibility='always',
    )
    sii_batch_number = fields.Integer(
        copy=False,
        string='Batch Number',
        readonly=True,
        help='Batch number for processing multiple invoices together',
    )
    turn_issuer = fields.Many2one(
        'partner.activities',
        string='Giro Emisor',
        store=True,
        invisible=True,
        readonly=True, states={'assigned': [('readonly', False)], 'draft': [('readonly', False)]},
    )
    partner_turn = fields.Many2one(
        'partner.activities',
        string='Actividades',
        store=True,
        readonly=True, states={'assigned': [('readonly', False)], 'draft': [('readonly', False)]},
    )
    activity_description = fields.Many2one(
        'sii.activity.description',
        string='Giro',
        related="partner_id.commercial_partner_id.activity_description",
        readonly=True, states={'assigned': [('readonly', False)], 'draft': [('readonly', False)]},
    )
    sii_document_number = fields.Char(
        string='Document Number',
        copy=False,
        readonly=True,
    )
    document_number = fields.Char(
        string='Full Document Number',
        copy=False,
        readonly=True,
    )
    taxpayer_type_id = fields.Many2one(
        'account.taxpayer.type',
        string='Tax Payer Type',
        related='partner_id.commercial_partner_id.taxpayer_type_id',
        store=True,
    )
    document_type_id = fields.Many2one(
        related='location_id.document_type_id',
        string='Document Type Id',
        readonly=True
    )
    document_code = fields.Char(
        related='location_id.document_type_id.code',
        string='Document Code'
    )
    document_sequence_id = fields.Many2one(
        related='location_id.sequence_id',
        readonly=True,
    )
    picking_document_type_id = fields.Integer(
        'Next Delivery Guide Number',
        related='document_sequence_id.number_next_actual',
        readonly=True
    )
    next_number = fields.Integer(
        related='document_sequence_id.number_next_actual',
        string='Next Document Number',
        readonly=True,
    )
    use_documents = fields.Boolean(
        string='Use Delivery Guide?',
        related='document_sequence_id.for_delivery_guide'
    )
    reference_ids = fields.One2many(
        'stock.picking.reference',
        'stock_picking_id',
        oldname='reference',
    )
    transport_type = fields.Selection(
        [
            ('2', 'Despacho por cuenta de empresa'),
            ('1', 'Despacho por cuenta del cliente'),
            ('3', 'Despacho Externo'),
            ('0', 'Sin Definir')
        ],
        string="Tipo de Despacho",
        default="2",
    )
    move_reason = fields.Selection(
        [
            ('1', '1. Operación constituye venta'),
            ('2', '2. Ventas por efectuar'),
            ('3', '3. Consignaciones'),
            ('4', '4. Entrega Gratuita'),
            ('5', '5. Traslados Internos'),
            ('6', '6. Otros traslados no venta'),
            ('7', '7. Guía de Devolución'),
            ('8', '8. Traslado para exportación'),
            ('9', '9. Ventas para exportación')
        ],
        string='Razón del traslado',
        default="1",
    )
    vehicle = fields.Many2one(
        'fleet.vehicle',
        string="Vehicle",
    )
    driver_id = fields.Many2one(
        'res.partner',
        string="Driver",
        oldname='chofer',
    )
    car_plate = fields.Char(
        string="Car Plate",
        oldname='patente',
    )
    contact_id = fields.Many2one(
        'res.partner',
        string="Contact Person",
    )
    invoiced = fields.Boolean(
        string='Invoiced?',
        readonly=True,
    )
    hide_kit_components = fields.Boolean('Hide Kit Components', default=False)

    @api.multi
    @api.constrains('document_type_id', 'document_number')
    @api.onchange('document_type_id', 'document_number')
    def validate_document_number(self):
        for rec in self:
            if rec.document_sequence_id:
                continue
            document_type = rec.document_type_id
            if rec.document_type_id:
                res = document_type.validate_document_number(
                    rec.document_number)
                if res and res != rec.document_number:
                    rec.document_number = res

    @api.onchange('picking_type_id')
    def onchange_picking_type(self,):
        if self.picking_type_id:
            self.use_documents = self.picking_type_id.code not in ["incoming"]

    @api.onchange('company_id')
    def _reload_lines(self):
        if self.move_lines:
            for m in self.move_lines:
                m.company_id = self.company_id.id

    @api.onchange('vehicle')
    def _set_driver(self):
        self.driver_id = self.vehicle.driver_id
        self.car_plate = self.vehicle.license_plate
