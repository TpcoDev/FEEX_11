import base64
import collections
import logging
from datetime import date, datetime, timedelta
from io import BytesIO

import dicttoxml
import xmltodict
from lxml import etree
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
from six import string_types

from . import pysiidte

_logger = logging.getLogger(__name__)

BC = pysiidte.BC
EC = pysiidte.EC

TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

dicttoxml.LOG.setLevel(logging.ERROR)
timbre = pysiidte.stamp
result = xmltodict.parse(timbre)


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity', 'product_id', 'invoice_id.partner_id',
                 'invoice_id.currency_id', 'invoice_id.company_id')
    def _compute_price(self):
        res = super(AccountInvoiceLine, self)._compute_price()
        for line in self.filtered(lambda x: x.company_id.localization == 'chile'):
            line.price_tax_included = line.price_total
        return res

    price_tax_included = fields.Monetary(string='Amount', readonly=True, compute='_compute_price')


class AccountInvoiceTax(models.Model):
    _inherit = "account.invoice.tax"

    def _get_net(self, currency):
        net = 0
        for tax in self:
            base = tax.base
            price_tax_included = 0
            for line in tax.invoice_id.invoice_line_ids:
                if tax.tax_id in line.invoice_line_tax_ids and tax.tax_id.price_include:
                    price_tax_included += line.price_tax_included
            if price_tax_included > 0 and tax.tax_id.sii_type in ["R"] and tax.tax_id.amount > 0:
                base = currency.round(price_tax_included)
            elif price_tax_included > 0 and tax.tax_id.amount > 0:
                base = currency.round(price_tax_included / (1 + tax.tax_id.amount / 100.0))
            net += base
        return net


# noinspection PyTypeChecker
class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice', 'l10n.cl.localization.filter']

    def _domain_journal_document_type_id(self):
        domain = self._get_available_journal_document_type()
        return [('id', 'in', domain)]

    def _get_barcode_img(self):
        for r in self:
            if r.sii_barcode:
                barcode_file = BytesIO()
                image = pysiidte.pdf417bc(r.sii_barcode)
                image.save(barcode_file, 'PNG')
                data = barcode_file.getvalue()
                r.sii_barcode_img = base64.b64encode(data)

    def _pretty_xml_dte(self):
        for record in self:
            if record.sii_xml_dte:
                record.sii_pretty_xml_dte = pysiidte.pretty_xml_dte(record.sii_xml_dte)

    taxes_included = fields.Boolean(
        'Discriminate VAT?',
        compute="get_taxes_included",
        store=True,
        readonly=False,
        help="Discriminate VAT on Quotations and Sale Orders?", )
    available_journal_document_type_ids = fields.Many2many(
        'account.journal.document.type',
        string='Available Journal Document Classes', )
    journal_document_type_id = fields.Many2one(
        'account.journal.document.type',
        string='Documents Type',
        default=lambda self: self._default_journal_document_type_id(),
        domain=_domain_journal_document_type_id,
        readonly=True,
        store=True,
        states={'draft': [('readonly', False)]}, )
    document_type_id = fields.Many2one(
        'account.document.type',
        related='journal_document_type_id.document_type_id',
        string='Document Type',
        copy=False,
        readonly=True,
        store=True, )
    sii_document_number = fields.Char(
        string='Document Number',
        copy=False,
        readonly=True, )
    taxpayer_type_id = fields.Many2one(
        'account.taxpayer.type',
        string='Tax Payer Type',
        related='commercial_partner_id.taxpayer_type_id',
        store=True, )
    no_rec_code = fields.Selection(
        [
            ('1', 'Compras destinadas a IVA a generar operaciones no gravados o exentas.'),
            ('2', 'Facturas de proveedores registrados fuera de plazo.'),
            ('3', 'Gastos rechazados.'),
            ('4', 'Entregas gratuitas (premios, bonificaciones, etc.) recibidos.'),
            ('9', 'Otros.')
        ],
        string="Non recoverable code",
        readonly=True, )
    next_invoice_number = fields.Integer(
        related='journal_document_type_id.sequence_id.number_next_actual',
        string='Next Document Number',
        readonly=True, )
    use_documents = fields.Boolean(
        related='journal_id.use_documents',
        string='Use Documents?',
        readonly=True, )
    contact_id = fields.Many2one(
        'res.partner',
        string="Contacto", )
    sii_batch_number = fields.Integer(
        copy=False,
        string='Batch Number',
        readonly=True,
        help='Batch number for processing multiple invoices together', )
    sii_barcode = fields.Char(
        copy=False,
        string=_('SII Barcode'),
        help='SII Barcode Name',
        readonly=True,
        states={'draft': [('readonly', False)]}, )
    sii_barcode_img = fields.Binary(
        string=_('SII Barcode Image'),
        help='SII Barcode Image in PDF417 format',
        compute="_get_barcode_img", )
    sii_message = fields.Text(
        string='SII Message',
        copy=False, )
    sii_xml_dte = fields.Text(
        string='SII XML DTE',
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]}, )
    sii_pretty_xml_dte = fields.Text(
        compute='_pretty_xml_dte',
        string='DTE XML',
    )
    sii_xml_request = fields.Many2one(
        'sii.xml.envio',
        string='SII XML Request',
        copy=False, )
    sii_result = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('NoEnviado', 'No Enviado'),
            ('EnCola', 'En cola de envío'),
            ('Enviado', 'Enviado'),
            ('Aceptado', 'Aceptado'),
            ('Rechazado', 'Rechazado'),
            ('Reparo', 'Reparo'),
            ('Proceso', 'Procesado'),
            ('Anulado', 'Anulado'), ],
        string='Resultado',
        copy=False,
        help="SII request result", )
    canceled = fields.Boolean(
        string="Canceled?",
        copy=False, )
    dte_reception_status = fields.Selection(
        [
            ('recibido', 'Recibido en DTE'),
            ('mercaderias', 'Recibido mercaderias'),
            ('validate', 'Validación Comercial')
        ],
        string="Estado de Recepcion del Envio",
        default='recibido',
        copy=False, oldname='estado_recep_dte')
    estado_recep_glosa = fields.Char(
        string="Información Adicional del Estado de Recepción",
        copy=False, )
    ticket = fields.Boolean(
        string="Formato Ticket",
        default=False,
        readonly=True,
        states={'draft': [('readonly', False)]}, )
    claim = fields.Selection(
        [
            ('ACD', 'Acepta Contenido del Documento'),
            ('RCD', 'Reclamo al  Contenido del Documento '),
            ('ERM', ' Otorga  Recibo  de  Mercaderías  o Servicios'),
            ('RFP', 'Reclamo por Falta Parcial de Mercaderías'),
            ('RFT', 'Reclamo por Falta Total de Mercaderías'),
        ],
        string="Reclamo",
        copy=False, )
    claim_description = fields.Char(
        string="Detalle Reclamo",
        readonly=True, )
    purchase_to_done = fields.Many2many(
        'purchase.order',
        string="Ordenes de Compra a validar",
        domain=[('state', 'not in', ['done', 'cancel'])],
        readonly=True,
        states={'draft': [('readonly', False)]}, )
    amount_untaxed_global_discount = fields.Float(
        string="Global Discount Amount",
        store=True,
        default=0.00, )
    amount_untaxed_global_recargo = fields.Float(
        string="Global Recargo Amount",
        store=True,
        default=0.00, )
    global_descuentos_recargos = fields.One2many(
        'account.invoice.gdr',
        'invoice_id',
        string="Descuentos / Recargos globales",
        readonly=True,
        states={'draft': [('readonly', False)]}, )
    send_queue_id = fields.Many2one('sii.send_queue', copy=False)
    sii_send_file_name = fields.Char('SII Send Filename')
    email_sent = fields.Boolean('Email Sent')
    journal_point_of_sale_type = fields.Selection(related='journal_id.point_of_sale_type')
    hide_kit_components = fields.Boolean('Hide Kit Components', default=False)

    @api.multi
    def compute_invoice_totals(self, company_currency, invoice_move_lines):
        """
        :param company_currency:
        :param invoice_move_lines:
        :return:
        """
        if self.env.user.company_id.localization != 'chile':
            return super(AccountInvoice, self).compute_invoice_totals(company_currency, invoice_move_lines)
        total = 0
        total_currency = 0
        amount_diff = self.amount_total
        amount_diff_currency = 0
        gdr = self.discount_charges_percent()
        if self.currency_id != company_currency:
            currency = self.currency_id.with_context(date=self.date_invoice or fields.Date.context_today(self))
            amount_diff = currency.compute(self.amount_total, company_currency)
            amount_diff_currency = self.amount_total
        for line in invoice_move_lines:
            exento = False
            if line.get('tax_ids'):
                exento = self.env['account.tax'].search([('id', 'in', line.get('tax_ids')[0][2]), ('amount', '=', 0)])
            if not line.get('tax_line_id') and not exento:
                line['price'] *= gdr
            if line.get('amount_currency', False) and not line.get('tax_line_id'):
                if not exento:
                    line['amount_currency'] *= gdr
            if self.currency_id != company_currency:
                if not (line.get('currency_id') and line.get('amount_currency')):
                    line['currency_id'] = currency.id
                    line['amount_currency'] = currency.round(line['price'])
                    line['price'] = currency.compute(line['price'], company_currency)
            else:
                line['currency_id'] = False
                line['amount_currency'] = False
                line['price'] = self.currency_id.round(line['price'])
            amount_diff -= line['price']
            if line.get('amount_currency', False):
                amount_diff_currency -= line['amount_currency']
            if self.type in ('out_invoice', 'in_refund'):
                total += line['price']
                total_currency += line['amount_currency'] or line['price']
                line['price'] = - line['price']
            else:
                total -= line['price']
                total_currency -= line['amount_currency'] or line['price']
        if amount_diff != 0:
            if self.type in ('out_invoice', 'in_refund'):
                invoice_move_lines[0]['price'] -= amount_diff
            else:
                invoice_move_lines[0]['price'] += amount_diff
            total += amount_diff
        if amount_diff_currency != 0:
            invoice_move_lines[0]['amount_currency'] += amount_diff_currency
            total_currency += amount_diff_currency
        return total, total_currency, invoice_move_lines

    def discount_charges_percent(self):
        if not self.global_descuentos_recargos:
            return 1
        taxes = super(AccountInvoice, self).get_taxes_values()
        affected = exempt = total = 0.00
        for id, t in taxes.items():
            tax = self.env['account.tax'].browse(t['tax_id'])
            total += t['base']
            if tax.amount > 0:
                affected += t['base']
            else:
                exempt += t['base']
        grouped_discount_charges = self.global_descuentos_recargos.gather_groups()
        discount_charges_amount = grouped_discount_charges['R'] - grouped_discount_charges['D']
        if discount_charges_amount == 0:
            return 1
        return 1 + (((100.0 * discount_charges_amount) / affected) / 100.0)

    def _get_grouped_taxes(self, line, taxes, tax_grouped={}):
        for tax in taxes:
            val = self._prepare_tax_line_vals(line, tax)
            # If the taxes generate moves on the same financial account as the invoice line,
            # propagate the analytic account from the invoice line to the tax line.
            # This is necessary in situations were (part of) the taxes cannot be reclaimed,
            # to ensure the tax move is allocated to the proper analytic account.
            if not val.get('account_analytic_id') and line.account_analytic_id and \
                    val['account_id'] == line.account_id.id:
                val['account_analytic_id'] = line.account_analytic_id.id
            key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)
            if key not in tax_grouped:
                tax_grouped[key] = val
            else:
                tax_grouped[key]['amount'] += val['amount']
                tax_grouped[key]['base'] += val['base']
        return tax_grouped

    @api.multi
    def get_taxes_values(self):
        if not self.filtered(lambda x: x.company_id.localization == 'chile'):
            return super(AccountInvoice, self).get_taxes_values()
        tax_grouped = {}
        totales = {}
        for line in self.invoice_line_ids:
            if line.invoice_line_tax_ids and line.invoice_line_tax_ids[0].price_include:
                # se asume todos los productos vienen con precio incluido o no (no hay mixes)
                for t in line.invoice_line_tax_ids:
                    if t not in totales:
                        totales[t] = 0
                    totales[t] += (self.currency_id.round(line.price_unit * line.quantity) * line.discount)
            taxes = line.invoice_line_tax_ids.compute_all(
                line.price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id,
                discount=line.discount)['taxes']
            tax_grouped = self._get_grouped_taxes(line, taxes, tax_grouped)
        if totales:
            for line in self.invoice_line_ids:
                for t in line.invoice_line_tax_ids:
                    taxes = t.compute_all(totales[t], self.currency_id, 1)['taxes']
                    tax_grouped = self._get_grouped_taxes(line, taxes, tax_grouped)
        if not self.global_descuentos_recargos:
            return tax_grouped
        gdr = self.discount_charges_percent()
        taxes = {}
        for t, group in tax_grouped.items():
            if t not in taxes:
                taxes[t] = group
            tax = self.env['account.tax'].browse(group['tax_id'])
            if tax.amount > 0:
                taxes[t]['amount'] *= gdr
                taxes[t]['base'] *= gdr
        return taxes

    @api.onchange('global_descuentos_recargos')
    def _onchange_discounts(self):
        self._onchange_invoice_line_ids()

    @staticmethod
    def get_document_type_default(document_types):
        document_type_id = document_types.ids[0]
        return document_type_id

    @api.onchange('journal_id', 'company_id')
    def _set_available_issuer_turns(self):
        # usamos la misma funcion para chequear la actividad del receptor
        for rec in self:
            if rec.company_id and rec.company_id.localization == 'chile':
                available_turn_ids = rec.company_id.company_activities_ids
                for turn in available_turn_ids:
                    if not turn.new_activity:
                        raise UserError(
                            _("""Your company as a DTE issuer, has old economic activities assigned. Please, \
check that your company\'s economic activities are in accordance with new codes, effective from November 1st 2018
(CIIU4 codification)."""))
                available_turn_ids = rec.partner_id.partner_activities_ids
                for turn in available_turn_ids:
                    # aca no interesa si la actividad es codigo antiguo
                    if turn:
                        # con la primer actividad que encuentra, sale
                        rec.invoice_turn = turn.id
                        break

    @api.multi
    def name_get(self):
        types = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Supplier Invoice'),
            'out_refund': _('Refund'),
            'in_refund': _('Supplier Refund'), }
        result_name = []
        for inv in self:
            result_name.append(
                (inv.id, "%s %s" % (inv.document_number or types[inv.type], inv.name or '')))
        return result_name

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search(
                [('document_number', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    def _search_equivalent_tax(self, tax):
        tax_n = self.env['account.tax'].search(
            [
                ('sii_code', '=', tax.sii_code),
                ('sii_type', '=', tax.sii_type),
                ('retencion', '=', tax.retencion),
                ('type_tax_use', '=', tax.type_tax_use),
                ('no_rec', '=', tax.no_rec),
                ('company_id', '=', self.company_id.id),
                ('price_include', '=', tax.price_include),
                ('amount', '=', tax.amount),
                ('amount_type', '=', tax.amount_type), ])
        return tax_n

    def _create_equivalent_tax(self, tax):
        tax_n = self.env['account.tax'].create({
            'sii_code': tax.sii_code,
            'sii_type': tax.sii_type,
            'retencion': tax.retencion,
            'type_tax_use': tax.type_tax_use,
            'no_rec': tax.no_rec,
            'name': tax.name,
            'description': tax.description,
            'tax_group_id': tax.tax_group_id.id,
            'company_id': self.company_id.id,
            'price_include': tax.price_include,
            'amount': tax.amount,
            'amount_type': tax.amount_type,
            'account_id': tax.account_id.id,
            'refund_account_id': tax.refund_account_id.id, })
        return tax_n

    @api.onchange('partner_id')
    def update_journal(self):
        self.journal_id = self._default_journal()
        self.set_default_journal()
        return self.update_domain_journal()

    def _get_available_journal_document_type(self):
        context = dict(self._context or {})
        journal_id = self.journal_id
        if not journal_id and 'default_journal_id' in context:
            journal_id = self.env['account.journal'].browse(context['default_journal_id'])
        if not journal_id:
            journal_id = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        invoice_type = self.type or context.get('default_type', False)
        if not invoice_type:
            invoice_type = 'in_invoice' if journal_id.type == 'purchase' else 'out_invoice'
        document_type_ids = []
        nd = False
        for ref in self.reference_ids:
            if not nd:
                nd = ref.reference_doc_code
        if invoice_type in ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']:
            if journal_id:
                domain = [
                    ('journal_id', '=', journal_id.id),
                ]
            else:
                operation_type = self.get_operation_type(invoice_type)
                domain = [
                    ('journal_id.type', '=', operation_type),
                ]
            if invoice_type in ['in_refund', 'out_refund']:
                domain += [('document_type_id.internal_type', 'in', ['credit_note'])]
            else:
                options = ['invoice', 'invoice_in']
                if nd:
                    options.append('debit_note')
                domain += [('document_type_id.internal_type', 'in', options)]
            document_types = self.env[
                'account.journal.document.type'].search(domain)
            document_type_ids = document_types.ids
        return document_type_ids

    @api.onchange('journal_id', 'partner_id')
    def update_domain_journal(self):
        document_types = self._get_available_journal_document_type()
        return {
            'domain': {
                'journal_document_type_id': [('id', 'in', document_types)], }, }

    @api.depends('journal_id')
    @api.onchange('journal_id', 'partner_id')
    def set_default_journal(self, default=None):
        if not self.journal_document_type_id or self.journal_document_type_id.journal_id != self.journal_id:
            domain = []
            if not default and not self.journal_document_type_id:
                domain.append(
                    ('document_type_id', '=', self.journal_document_type_id.document_type_id.id),
                )
            if self.journal_document_type_id.journal_id != self.journal_id or not default:
                domain.append(
                    ('journal_id', '=', self.journal_id.id)
                )
            if domain:
                default = self.env['account.journal.document.type'].search(
                    domain,
                    order='sequence asc',
                    limit=1,
                ).id
            self.journal_document_type_id = self._default_journal_document_type_id(default)

    @api.onchange('document_type_id', 'partner_id')
    def _check_vat(self):
        if self.partner_id and not self._check_doc_type() and not \
                self.partner_id.commercial_partner_id.main_id_number and self.taxes_included:
            raise UserError(_("""The customer/supplier does not have a VAT \
defined. The type of invoicing document you selected requires you tu settle \
a VAT."""))

    @api.depends(
        'document_type_id',
        'document_type_id.document_letter_id',
        'document_type_id.document_letter_id.taxes_included',
        'company_id',
        'company_id.invoice_vat_discrimination_default', )
    def get_taxes_included(self):
        for inv in self:
            inv.taxes_included = (inv.document_type_id.document_letter_id.taxes_included or
                                  inv.company_id.invoice_vat_discrimination_default == 'discriminate_default')

    @api.one
    @api.constrains('reference', 'partner_id', 'company_id', 'type', 'journal_document_type_id')
    def _check_reference_in_invoice(self):
        if self.type in ['in_invoice', 'in_refund'] and self.reference:
            domain = [('type', '=', self.type),
                      ('reference', '=', self.reference),
                      ('partner_id', '=', self.partner_id.id),
                      ('journal_document_type_id.document_type_id', '=',
                       self.journal_document_type_id.document_type_id.id),
                      ('company_id', '=', self.company_id.id),
                      ('id', '!=', self.id)]
            invoice_ids = self.search(domain)
            if invoice_ids:
                raise UserError(u'''El numero de factura debe ser unico por Proveedor. Ya existe otro documento con 
el numero: %s para el proveedor: %s''' % (self.reference, self.partner_id.display_name))

    @staticmethod
    def get_operation_type(invoice_type):
        if invoice_type in ['in_invoice', 'in_refund']:
            operation_type = 'purchase'
        elif invoice_type in ['out_invoice', 'out_refund']:
            operation_type = 'sale'
        else:
            operation_type = False
        return operation_type

    def get_valid_document_letters(self, partner_id, operation_type='sale', company=False, vat_affected='SI',
                                   invoice_type='out_invoice', nd=False):
        document_letter_obj = self.env['sii.document_letter']
        partner = self.partner_id

        if not partner_id or not company or not operation_type:
            return []

        partner = partner.commercial_partner_id
        if operation_type == 'sale':
            issuer_taxpayer_type_id = company.partner_id.taxpayer_type_id.id
            receptor_taxpayer_type_id = partner.taxpayer_type_id.id
            domain = [
                ('issuer_ids', '=', issuer_taxpayer_type_id),
                ('receptor_ids', '=', receptor_taxpayer_type_id), ]
            if invoice_type == 'out_invoice' and not nd:
                if vat_affected == 'SI':
                    domain.append(('name', '!=', 'C'))
                else:
                    domain.append(('name', '=', 'C'))
        elif operation_type == 'purchase':
            issuer_taxpayer_type_id = partner.taxpayer_type_id.id
            domain = [('issuer_ids', '=', issuer_taxpayer_type_id)]
        else:
            raise UserError(
                _('Operation Type Error'), _('Operation Type Must be "Sale" or "Purchase"'))
        document_letter_ids = document_letter_obj.search(domain)
        return document_letter_ids

    @api.multi
    def _check_duplicate_supplier_reference(self):
        for invoice in self:
            if invoice.type in ('in_invoice', 'in_refund') and invoice.reference:
                if self.search([
                    ('reference', '=', invoice.reference),
                    ('journal_document_type_id', '=', invoice.journal_document_type_id.id),
                    ('partner_id', '=', invoice.partner_id.id),
                    ('type', '=', invoice.type),
                    ('id', '!=', invoice.id),
                ]):
                    raise UserError('El documento %s, Folio %s de la Empresa %s ya se en cuentra registrado' % (
                        invoice.journal_document_type_id.document_type_id.name,
                        invoice.reference, invoice.partner_id.name))

    @api.multi
    def invoice_validate(self):
        if self.env.user.company_id.localization != 'chile' or self.env.user.company_id.dte_service_provider not in [
            'SII', 'SIIHOMO'
        ]:
            return super(AccountInvoice, self).invoice_validate()
        for inv in self:
            if not inv.journal_id.use_documents or not inv.document_type_id.dte:
                continue
            if (inv.currency_id != self.env.user.company_id.currency_id) and not (inv._check_doc_type(['E'])):
                raise UserError('El documento %s, Número %s tiene definida la moneda %s. Para continuar debe cambiar '
                                'la moneda a %s ' % (
                                    inv.journal_document_type_id.document_type_id.name,
                                    inv.document_number,
                                    inv.currency_id.name,
                                    inv.company_id.currency_id.name)
                                )
            inv.sii_result = 'NoEnviado'
            inv.responsable_envio = self.env.user.id
            if inv.type in ['out_invoice', 'out_refund']:
                if inv.journal_id.point_of_sale_type not in ['online']:
                    inv.sii_result = 'Proceso'
                else:
                    inv._stamp()
                    if inv._check_doc_type() and not inv._nc_doc_type_b():
                        # acá si es boleta, debe envolver con envio boleta
                        inv.sii_xml_dte = inv.create_exchange()
                        # hasta acá agregado.
                        inv.sii_result = 'Proceso'
                        continue
                    passive_time = datetime.now() + timedelta(minutes=int(
                        self.env['ir.config_parameter'].sudo().get_param('account.auto_send_dte', default=60)))
                    auto_send_email = self.env['ir.config_parameter'].sudo().get_param(
                        'account.auto_send_email', default=True)
                    self.env['sii.send_queue'].create({
                        'doc_ids': [inv.id],
                        'model': 'account.invoice',
                        'model_selection': 'account.invoice',
                        'invoice_ids': [(6, 0, [inv.id])],
                        'user_id': self.env.user.id,
                        'tipo_trabajo': 'pasivo',
                        'date_time': passive_time,
                        'send_email': auto_send_email, })
        return super(AccountInvoice, self).invoice_validate()

    @api.model
    def create(self, vals):
        inv = super(AccountInvoice, self).create(vals)
        inv.update_domain_journal()
        inv.set_default_journal()
        return inv

    @api.model
    def _default_journal(self):
        res = super(AccountInvoice, self)._default_journal()
        if self.company_id.localization != 'chile':
            return res
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        company_id = self._context.get('company_id', self.company_id or self.env.user.company_id)
        if self._context.get('honorarios', False):
            inv_type = self._context.get('type', 'out_invoice')
            inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
            # TODO: review this domain syntax
            domain = [
                ('journal_document_type_ids.document_type_id.document_letter_id.name', '=', 'M'),
                ('type', 'in', [TYPE2JOURNAL[ty] for ty in inv_types if ty in TYPE2JOURNAL]),
                ('company_id', '=', company_id.id), ]
            journal_id = self.env['account.journal'].search(domain, limit=1)
            return journal_id

        return res

    @staticmethod
    def get_resolution_data(comp_id):
        resolution_data = {
            'dte_resolution_date': comp_id.dte_resolution_date,
            'dte_resolution_number': comp_id.dte_resolution_number}
        return resolution_data

    def create_exchange(self):
        rut = self.format_vat(self.partner_id.commercial_partner_id.main_id_number)
        xml_envio, file_name = self._create_envelope(RUTRecep=rut)
        return xml_envio

    def _read_xml(self, mode="text"):
        """
        Código para realizar migración de la versión 9.0.5.2.0, a la 9.0.5.3.0
        :param mode:
        :return:
        """
        if self.sii_xml_request.xml_envio:
            xml_read = self.sii_xml_request.xml_envio.decode('ISO-8859-1').replace(
                '<?xml version="1.0" encoding="ISO-8859-1"?>', '')
        if mode == "etree":
            return etree.fromstring(xml_read)
        if mode == "parse":
            return xmltodict.parse(xml_read)
        return xml_read

    def _create_attachment(self, ):
        if self.document_code not in {'39', '41'}:
            try:
                exchange_xml = self.create_exchange()
            except:
                # Código compatibilidad
                if self.sii_xml_request and not self.sii_xml_dte:
                    xml = self._read_xml("etree")
                    envio = xml.find("{http://www.sii.cl/SiiDte}SetDTE")
                    if envio:
                        sii_xml_dte = etree.tostring(envio.findall("{http://www.sii.cl/SiiDte}DTE")[0])
                        self.sii_xml_dte = sii_xml_dte
                        self.sii_pretty_xml_dte = pysiidte.pretty_xml_dte(sii_xml_dte)
                exchange_xml = self.create_exchange()
        else:
            exchange_xml = 'aca va'
        url_path = '/download/xml/invoice/%s' % self.id
        filename = ('%s.xml' % self.display_name).replace(' ', '_')
        att = self.env['ir.attachment'].search(
            [('name', '=', filename), ('res_id', '=', self.id), ('res_model', '=', 'account.invoice')], limit=1)
        if att:
            return att
        data = base64.b64encode(exchange_xml.encode())
        values = dict(
            name=filename,
            datas_fname=filename,
            url=url_path,
            res_model='account.invoice',
            res_id=self.id,
            type='binary',
            datas=data, )
        att = self.env['ir.attachment'].create(values)
        return att

    @api.multi
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        if not self.filtered(lambda x: x.company_id.localization == 'chile'):
            return super(AccountInvoice, self).action_invoice_sent()
        self.ensure_one()
        template = self.env.ref('account.email_template_edi_invoice', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        att = self._create_attachment()
        atts = []
        if template.attachment_ids:
            for a in template.attachment_ids:
                atts.append(a.id)
        atts.append((6, 0, [att.id]))
        template.attachment_ids = atts
        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def get_xml_file(self):
        url_path = '/download/xml/%s/%s' % (self._context['kind'], self.id)
        return {
            'type': 'ir.actions.act_url',
            'url': url_path,
            'target': 'new',
        }

    def get_folio(self):
        return int(self.document_number)

    @staticmethod
    def format_vat(value, with_zero=False):
        if not value or value == '' or value == 0:
            value = "CL666666666"
        if 'CL' in value:
            # argument is vat
            rut = value[:10] + '-' + value[10:]
            if not with_zero:
                rut = rut.replace('CL0', '')
            rut = rut.replace('CL', '')
        else:
            # argument is other (main_id_number for example)
            rut = value.replace('.', '')
        return rut

    @api.multi
    def get_related_invoices_data(self):
        """
        List related invoice information to fill CbtesAsoc.
        """
        self.ensure_one()
        rel_invoices = self.search([
            ('number', '=', self.origin),
            ('state', 'not in',
             ['draft', 'proforma', 'proforma2', 'cancel'])])
        return rel_invoices

    @api.multi
    def do_dte_send_invoice(self, n_atencion=None):
        ids = []
        for inv in self.with_context(lang='es_CL'):
            if inv.sii_result in ['', 'NoEnviado', 'Rechazado'] and not inv._check_doc_type() and not \
                    inv._nc_doc_type_b():
                if inv.sii_result in ['Rechazado']:
                    inv._stamp()
                inv.sii_result = 'EnCola'
                ids.append(inv.id)
        if not isinstance(n_atencion, string_types):
            n_atencion = ''
        if ids:
            # notación antigua sii.send_queue
            self.env['sii.send_queue'].create(
                {
                    'doc_ids': ids,
                    'model': 'account.invoice',
                    'model_selection': 'account.invoice',
                    'user_id': self.env.user.id,
                    'tipo_trabajo': 'envio',
                    'n_atencion': n_atencion,
                    'send_email': True,
                    'invoice_ids': [(6, 0, ids)],
                })

    def _check_doc_type(self, types={'B', 'M'}):
        if self.document_type_id.document_letter_id.name:
            return self.document_type_id.document_letter_id.name in types
        else:
            return False

    def _nc_doc_type_b(self):
        if not self.reference_ids or self.type != "out_refund":
            return False
        for r in self.reference_ids:
            if r.reference_doc_type.code in [35, 38, 39, 41, 70, 71]:
                return True
        return False

    def _check_foreign_partner(self):
        # si se dan todas las condiciones, es extranjero, caso contrario es un problema de validación
        if self.partner_id.main_id_number in ['55.555.555-5', '55555555-5'] and \
                self.partner_id.taxpayer_type_id == self.env.ref('l10n_cl_account.res_EXT') and \
                self.partner_id.country_id != self.env.ref('base.cl'):
            return True
        else:
            return False

    def _giros_emisor(self):
        giros_emisor = []
        for turn in self.env.user.company_id.company_activities_ids:
            giros_emisor.extend([{'Acteco': turn.code}])
        return giros_emisor

    def _turn_recipient(self):
        """
        Función para forzar a que de algun lado obtenga el giro del emisor en caso que el mismo no se haya fijado
        (se puede mejorar)
        :return:
        """
        turn_recipient = self.invoice_turn.name
        if not turn_recipient:
            try:
                turn_recipient = self.partner_id.partner_activities_ids[0].name
            except:
                turn_recipient = self.partner_id.activity_description.name
        if not turn_recipient:
            try:
                turn_recipient = self.commercial_partner_id.partner_activities_ids[0].name
            except:
                turn_recipient = self.commercial_partner_id.activity_description.name
        if not turn_recipient:
            raise UserError('Please set the turn or economical activity for this recipient partner')
        else:
            return turn_recipient

    def _id_doc(self, tax_include=False, exempt_amount=0):
        id_doc = collections.OrderedDict()
        id_doc['TipoDTE'] = self.document_type_id.code
        id_doc['Folio'] = self.get_folio()
        id_doc['FchEmis'] = self.date_invoice
        if self._check_doc_type():
            id_doc['IndServicio'] = 3
            """
            1 Boletas de servicios periódicos
            2 Boletas de servicios periódicos domiciliarios
            3 Boletas de venta y servicios
            4 Boleta de Espectáculo emitida por cuenta de Terceros
            """
        if self.ticket:
            id_doc['TpoImpresion'] = "T"
        if tax_include and exempt_amount == 0 and not self._check_doc_type():
            id_doc['MntBruto'] = 1
        if not self._check_doc_type():
            id_doc['FmaPago'] = self.payment_term_id.dte_sii_code or 2
            if self.payment_term_id.name:
                # esto podría ser una tabla con varios pagos, pero se implementa una solución
                # intermedia, poniendo un medios de pago
                id_doc['MntPagos'] = collections.OrderedDict()
                id_doc['MntPagos']['FchPago'] = self.date_due
                id_doc['MntPagos']['MntPago'] = int(self._currency_decimals(self.amount_total))
                id_doc['MntPagos']['GlosaPagos'] = self.payment_term_id.name
        if not tax_include and self._check_doc_type():
            # prefiero forzar a que el tax include sea true cuando es check_doc_type
            # id_doc['IndMntNeto'] = 2
            """
            Este indicador se utiliza para expresar que el precio unitario y el valor de todas las líneas de
            detalles corresponden a Montos netos, es decir no incluyen el IVA. Sólo se aplica para empresas que
            tienen autorización para emitir las boletas desglosando el IVA.
            No aplica en boleta exenta
            """
        if not self._check_doc_type():
            id_doc['FchVenc'] = self.date_due or datetime.strftime(datetime.now(), '%Y-%m-%d')
        return id_doc

    def _emisor(self):
        issuer = collections.OrderedDict()
        issuer['RUTEmisor'] = self.format_vat(self.company_id.vat)
        if self._check_doc_type():
            ## revisar esta parte porque decia RzonSocissuer y Giroissuer
            issuer['RznSocEmisor'] = pysiidte.str_shorten(self.company_id.partner_id.name, 100)
            issuer['GiroEmisor'] = pysiidte.str_shorten(self.company_id.activity_description.name, 80)
            if self.journal_id.point_of_sale_number:
                issuer['CdgSIISucur'] = pysiidte.str_shorten(self.journal_id.point_of_sale_number, 9)
        else:
            issuer['RznSoc'] = pysiidte.str_shorten(self.company_id.partner_id.name, 100)
            issuer['GiroEmis'] = pysiidte.str_shorten(
                self.company_id.activity_description.name or self.company_id.company_activities_ids[0].name, 80)
            issuer['Telefono'] = pysiidte.str_shorten(self.company_id.phone, 20)
            if self.company_id.dte_email:
                issuer['CorreoEmisor'] = self.company_id.dte_email
            issuer['item'] = self._giros_emisor()
            if self.journal_id.point_of_sale_name:
                issuer['Sucursal'] = pysiidte.str_shorten(self.journal_id.point_of_sale_name, 20)
        issuer['DirOrigen'] = pysiidte.str_shorten(self.company_id.street + ' ' + (self.company_id.street2 or ''), 70)
        issuer['CmnaOrigen'] = self.company_id.city_id.name or ''
        issuer['CiudadOrigen'] = self.company_id.city or ''
        # este no va aca para las boletas  issuer['CodVndor'] = pysiidte.str_shorten(self.user_id.name, 60)
        if not self._check_doc_type() and self.user_id:
            issuer['CdgVendedor'] = pysiidte.str_shorten(self.user_id.name, 60)
        return issuer

    def _turn_recipient(self):
        """
        Función para forzar a que de algun lado obtenga el giro del emisor en caso que el mismo no se haya fijado
        (se puede mejorar)
        :return:
        """
        turn_recipient = self.invoice_turn.name
        # transformar turn_recipient en fields.Related
        if not turn_recipient:
            if self.partner_id.taxpayer_type_id.tp_sii_code == 0:
                turn_recipient = self.partner_id.activity_description.name
            elif len(self.partner_id.partner_activities_ids) > 0:
                turn_recipient = self.partner_id.partner_activities_ids[0].name
        if not turn_recipient:
            raise UserError('Please set the turn or economical activity for this recipient partner')
        else:
            return turn_recipient

    def _recipient(self):
        recipient = collections.OrderedDict()
        if not self.commercial_partner_id.main_id_number and not self._check_doc_type():
            raise UserError("Debe Ingresar RUT receptor")
        recipient['RUTRecep'] = self.format_vat(self.commercial_partner_id.main_id_number)
        if self.commercial_partner_id.ref and not self._check_doc_type():
            recipient['CdgIntRecep'] = pysiidte.str_shorten(self.commercial_partner_id.ref, 20)
        recipient['RznSocRecep'] = pysiidte.str_shorten(self.commercial_partner_id.name, 100)
        # tabla de paises de aduana
        # se usa IdAdicRecep para identificar el pais con el dato que aparece en Odoo (es libre para el SII)
        if self._check_foreign_partner():
            recipient['Extranjero'] = collections.OrderedDict()
            recipient['Extranjero']['NumId'] = self.partner_id.vat
            # Opcional: agregar ['Nacionalidad'] de extranjero (no implementado) debe provenir de
            recipient['Extranjero']['IdAdicRecep'] = pysiidte.str_shorten(
                self.partner_id.country_id.name or self.commercial_partner_id.country_id.name, 20)
        if not self._check_foreign_partner():
            if not self._check_doc_type():
                recipient['GiroRecep'] = pysiidte.str_shorten(self._turn_recipient(), 40)
        if self.contact_id:
            recipient['Contacto'] = pysiidte.str_shorten(
                '%s - %s' % (self.contact_id.name, self.contact_id.phone or ''), 80)
        elif self.partner_id.phone or self.commercial_partner_id.phone:
            recipient['Contacto'] = pysiidte.str_shorten(
                self.partner_id.phone or self.commercial_partner_id.phone or self.partner_id.email, 80)
        if not self._check_doc_type():
            if self.commercial_partner_id.email or self.commercial_partner_id.dte_email or self.partner_id.email or \
                    self.partner_id.dte_email:
                recipient['CorreoRecep'] = self.commercial_partner_id.dte_email or self.partner_id.dte_email or \
                                           self.commercial_partner_id.email or self.partner_id.email
        street_recep = self.partner_id.street or self.commercial_partner_id.street or False
        if not street_recep and not self._check_doc_type():
            raise UserError('Debe Ingresar dirección del cliente')
        street2_recep = self.partner_id.street2 or self.commercial_partner_id.street2 or False
        recipient['DirRecep'] = pysiidte.str_shorten((street_recep or '') + ' ' + (street2_recep or ''), 70)
        recipient['CmnaRecep'] = self.partner_id.city_id.name or self.commercial_partner_id.city_id.name
        if not self._check_foreign_partner() and not self._check_doc_type():
            if not recipient['CmnaRecep']:
                raise UserError('Debe Ingresar Comuna del cliente')
        else:
            recipient['CmnaRecep'] = pysiidte.str_shorten(
                self.partner_id.state_id.name or '' or self.commercial_partner_id.state_id.name or 'N-A', 20)
        recipient['CiudadRecep'] = pysiidte.str_shorten(self.partner_id.city or self.commercial_partner_id.city or '',
                                                        20)
        return recipient

    def _totals_otra_moneda(self, currency_id, MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal=0):
        total_amounts = collections.OrderedDict()
        total_amounts['TpoMoneda'] = pysiidte.str_shorten(self.company_currency_id.short_name, 15)
        total_amounts['TpoCambio'] = round(
            self.company_currency_id._get_conversion_rate(
                self.company_currency_id, currency_id), 4)
        if MntNeto:
            if currency_id:
                MntNeto = currency_id.compute(MntNeto, self.company_currency_id)
            total_amounts['MntNetoOtrMnda'] = MntNeto
        if MntExe:
            if currency_id:
                MntExe = currency_id.compute(MntExe, self.company_currency_id)
            total_amounts['MntExeOtrMnda'] = MntExe
        if TasaIVA:
            if currency_id:
                IVA = currency_id.compute(IVA, self.company_currency_id)
            total_amounts['IVAOtrMnda'] = IVA
        if ImptoReten:
            total_amounts['ImptRetOtrMnda'] = collections.OrderedDict()
            total_amounts['ImptRetOtrMnda']['TipoImpOtrMnda'] = ImptoReten['TpoImp']
            total_amounts['ImptRetOtrMnda']['TasaImpOtrMnda'] = ImptoReten['TasaImp']
            if currency_id:
                ImptoReten['MontoImp'] = currency_id.compute(ImptoReten['MontoImp'], self.company_currency_id)
            total_amounts['ImptRetOtrMnda']['ValorImpOtrMnda'] = ImptoReten['MontoImp']
        if currency_id:
            MntTotal = currency_id.compute(MntTotal, self.company_currency_id)
        total_amounts['MntTotOtrMnda'] = MntTotal
        return total_amounts

    @staticmethod
    def _totals_boletas(MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal=0):
        total_amounts = collections.OrderedDict()
        if MntExe:
            total_amounts['MntExe'] = MntExe
        # if ImptoReten:
        #     total_amounts['ImptoReten'] = ImptoReten
        total_amounts['MntTotal'] = MntTotal
        return total_amounts

    def _totals_normal(self, MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal=0):
        total_amounts = collections.OrderedDict()
        if MntNeto:
            total_amounts['MntNeto'] = MntNeto
        if MntExe:
            total_amounts['MntExe'] = MntExe
        if TasaIVA:
            total_amounts['TasaIVA'] = TasaIVA
            total_amounts['IVA'] = IVA
        if ImptoReten:
            total_amounts['ImptoReten'] = ImptoReten
        total_amounts['MntTotal'] = MntTotal
        return total_amounts

    def _totals(self, exempt_amount=0, no_product=False, tax_include=False):
        net_amount = False
        vat_obj = False
        tax_withholding = False
        vat_tax = False
        vat_amount = 0
        if self.document_type_id.code == 34 or (
                self.reference_ids and self.reference_ids[0].reference_doc_type.code == '34'):
            exempt_amount = self.currency_id.round(self.amount_total)
            if no_product:
                exempt_amount = 0
        elif self.amount_untaxed and self.amount_untaxed != 0:
            if not self._check_doc_type() or not tax_include:
                vat_obj = False
                for t in self.tax_line_ids:
                    if t.tax_id.sii_code in [14, 15]:
                        vat_obj = t
                if vat_obj and vat_obj.base > 0:
                    net_amount = self.currency_id.round(vat_obj.base)
        if exempt_amount > 0:
            exempt_amount = self.currency_id.round(exempt_amount)
        if not self._check_doc_type() or not tax_include:
            if vat_obj:
                if not self._check_doc_type():
                    vat_tax = round(vat_obj.tax_id.amount, 2)
                vat_amount = self.currency_id.round(vat_obj.amount)
            if no_product:
                net_amount = 0
                if not self._check_doc_type():
                    vat_tax = 0
                vat_amount = 0
        if vat_obj and vat_obj.tax_id.sii_code in [15]:
            tax_withholding = collections.OrderedDict()
            tax_withholding['TpoImp'] = vat_obj.tax_id.sii_code
            tax_withholding['TasaImp'] = round(vat_obj.tax_id.amount, 2)
            tax_withholding['MontoImp'] = self.currency_id.round(vat_obj.amount)

        total_amount = self.currency_id.round(self.amount_total)
        if self.company_currency_id == self.currency_id:
            exempt_amount = int(exempt_amount)
            net_amount = int(net_amount)
            vat_amount = int(vat_amount)
            total_amount = int(total_amount)
        if no_product:
            total_amount = 0
        return exempt_amount, net_amount, vat_amount, vat_tax, tax_withholding, total_amount

    def _xml_header(self, exempt_amount=0, no_product=False, tax_include=False):
        xml_header = collections.OrderedDict()
        xml_header['IdDoc'] = self._id_doc(tax_include, exempt_amount)
        xml_header['Emisor'] = self._emisor()
        xml_header['Receptor'] = self._recipient()
        currency_id = self.currency_id
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
        exempt_amount, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal = self._totals(
            exempt_amount, no_product, tax_include)
        if self._check_doc_type():
            xml_header['Totales'] = self._totals_boletas(exempt_amount, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal)
        else:
            xml_header['Totales'] = self._totals_normal(exempt_amount, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal)

        if self._check_doc_type('E'):
            xml_header['OtraMoneda'] = self._totals_otra_moneda(
                currency_id, exempt_amount, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal)

        return xml_header

    @api.multi
    def get_barcode(self, no_product=False):
        folio = self.get_folio()
        result['TED']['DD']['RE'] = self.format_vat(self.company_id.main_id_number)
        result['TED']['DD']['TD'] = self.document_type_id.code
        result['TED']['DD']['F'] = folio
        result['TED']['DD']['FE'] = self.date_invoice
        if not self.commercial_partner_id.main_id_number:
            raise UserError(_("Fill Partner VAT"))
        result['TED']['DD']['RR'] = self.format_vat(self.commercial_partner_id.main_id_number)
        result['TED']['DD']['RSR'] = pysiidte.str_shorten(self.commercial_partner_id.name, 40)
        result['TED']['DD']['MNT'] = self._currency_decimals(self.amount_total)

        if no_product:
            result['TED']['DD']['MNT'] = 0
        for line in self.invoice_line_ids:
            result['TED']['DD']['IT1'] = pysiidte.str_shorten(line.product_id.name, 40)
            if line.product_id.default_code:
                result['TED']['DD']['IT1'] = pysiidte.str_shorten(line.product_id.name.replace(
                    '[' + line.product_id.default_code + '] ', ''), 40)
            break

        resultcaf = self.journal_document_type_id.sequence_id.get_caf_file(self.get_folio())
        result['TED']['DD']['CAF'] = resultcaf['AUTORIZACION']['CAF']
        dte = result['TED']['DD']
        timestamp = pysiidte.time_stamp()
        if date(int(timestamp[:4]), int(timestamp[5:7]), int(timestamp[8:10])) < date(int(self.date[:4]), int(
                self.date[5:7]), int(self.date[8:10])):
            raise UserError("La fecha de timbraje no puede ser menor a la fecha de emisión del documento")
        dte['TSTED'] = timestamp
        ddxml = '<DD>' + dicttoxml.dicttoxml(
            dte, root=False, attr_type=False).decode().replace(
            '<key name="@version">1.0</key>', '', 1).replace(
            '><key name="@version">1.0</key>', ' version="1.0">', 1).replace(
            '><key name="@algoritmo">SHA1withRSA</key>',
            ' algoritmo="SHA1withRSA">').replace(
            '<key name="#text">', '').replace(
            '</key>', '').replace('<CAF>', '<CAF version="1.0">') + '</DD>'
        keypriv = resultcaf['AUTORIZACION']['RSASK'].replace('\t', '')
        root = etree.XML(ddxml)
        ddxml = etree.tostring(root)
        frmt = pysiidte.signmessage(ddxml, keypriv)
        ted = '<TED version="1.0">{}<FRMT algoritmo="SHA1withRSA">{}</FRMT></TED>'.format(ddxml.decode(), frmt)
        self.sii_barcode = ted
        ted += '<TmstFirma>{}</TmstFirma>'.format(timestamp)
        return ted

    def _currency_decimals(self, value):
        return self.currency_id.round(value) \
            if self.currency_id != self.company_currency_id else int(self.currency_id.round(value))

    def _document_lines(self):
        line_number = 1
        invoice_lines = []
        no_product = False
        MntExe = 0
        currency_id = False
        if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
        for line in self.invoice_line_ids:
            if line.name.startswith('>') and self.hide_kit_components:
                continue
            if line.product_id.default_code == 'NO_PRODUCT' or line.product_id.default_code == 'CORRIGE':
                no_product = True
            lines = collections.OrderedDict()
            lines['NroLinDet'] = line_number
            if line.product_id.default_code and not no_product:
                lines['CdgItem'] = collections.OrderedDict()
                lines['CdgItem']['TpoCodigo'] = 'INT1'
                lines['CdgItem']['VlrCodigo'] = line.product_id.default_code
            # tax_include = False
            tax_include = line.invoice_id._check_doc_type()
            if not line.invoice_line_tax_ids and not tax_include:
                lines['IndExe'] = 1
                price_exe = line.price_tax_included
                MntExe += self.currency_id.round(price_exe)
            # else:
            elif line.invoice_line_tax_ids and not tax_include:
                for t in line.invoice_line_tax_ids:
                    tax_include = t.price_include
                    if t.amount == 0 or t.sii_code in [0]:  # TODO mejor manera de identificar exento de afecto
                        lines['IndExe'] = 1
                        price_exe = line.price_tax_included
                        MntExe += self.currency_id.round(price_exe)
            lines['NmbItem'] = pysiidte.str_shorten(line.product_id.name, 80)
            lines['DscItem'] = pysiidte.str_shorten(line.name, 1000)  # descripción más extensa
            qty = round(line.quantity, 4)
            if not no_product:
                lines['QtyItem'] = qty
            if qty == 0 and not no_product:
                lines['QtyItem'] = 1
            elif qty < 0:
                raise UserError("The quantity amount cannot be less than zero. If you need to deduct a previous "
                                "product or payment from the customer you should generate a credit note later.")
            if not no_product:
                lines['UnmdItem'] = line.uom_id.name[:4]
                if line.invoice_id._check_doc_type():
                    # esto es para el caso estándar hardcodeo el impuesto para tener urgente la solucion
                    lines['PrcItem'] = round(line.price_unit * 1.19, 6)
                else:
                    lines['PrcItem'] = round(line.price_unit, 6)
                if currency_id:
                    lines['OtrMnda'] = collections.OrderedDict()
                    lines['OtrMnda']['PrcOtrMon'] = round(currency_id.compute(
                        line.price_unit, self.company_id.currency_id, round=False), 4)
                    lines['OtrMnda']['Moneda'] = pysiidte.str_shorten(self.company_id.currency_id.name, 3)
                    lines['OtrMnda']['FctConv'] = round(currency_id.rate, 4)
            if line.discount > 0:
                if currency_id:
                    lines['OtrMnda']['DctoOtrMnda'] = line.discount
                lines['DescuentoPct'] = line.discount
                DescMonto = (line.discount / 100) * lines['PrcItem'] * qty
                lines['DescuentoMonto'] = self._currency_decimals(DescMonto)
                if currency_id:
                    lines['OtrMnda']['DctoOtrMnda'] = currency_id.compute(DescMonto, self.company_id.currency_id)
            if not no_product and not tax_include:
                if currency_id:
                    lines['OtrMnda']['MontoItemOtrMnda'] = currency_id.compute(
                        line.price_subtotal, self.company_id.currency_id)
                lines['MontoItem'] = self._currency_decimals(line.price_subtotal)
            elif not no_product:
                if currency_id:
                    lines['OtrMnda']['MontoItemOtrMnda'] = currency_id.compute(
                        line.price_tax_included, self.company_id.currency_id)
                lines['MontoItem'] = self._currency_decimals(line.price_tax_included)
            if no_product:
                lines['MontoItem'] = 0
            line_number += 1
            invoice_lines.extend([{'Detalle': lines}])
            if 'IndExe' in lines:
                tax_include = False
            if self.company_currency_id == self.currency_id:
                MntExe = int(MntExe)
        return {
            'invoice_lines': invoice_lines,
            'MntExe': MntExe,
            'no_product': no_product,
            'tax_include': tax_include,
        }

    def _gdr(self):
        result = []
        lin_dr = 1
        for dr in self.global_descuentos_recargos:
            dr_line = collections.OrderedDict()
            dr_line['NroLinDR'] = lin_dr
            dr_line['TpoMov'] = dr.type
            if dr.gdr_dtail:
                dr_line['GlosaDR'] = dr.gdr_dtail
            disc_type = "%"
            if dr.gdr_type == "amount":
                disc_type = "$"
            dr_line['TpoValor'] = disc_type
            dr_line['ValorDR'] = self.currency_id.round(dr.valor)
            if self.currency_id and self.company_id and self.currency_id != self.company_id.currency_id:
                currency_id = self.currency_id.with_context(date=self.date_invoice)
                dr_line['ValorDROtrMnda'] = currency_id.compute(dr.valor, self.company_id.currency_id)
            if self.document_type_id.code in [34] and (
                    self.reference_ids and self.reference_ids[0].reference_doc_type.code == '34'):
                # solamente si es exento
                dr_line['IndExeDR'] = 1
            dr_lines = [{'DscRcgGlobal': dr_line}]
            result.append(dr_lines)
            lin_dr += 1
        return result

    def _dte(self, n_atencion=None):
        dte = collections.OrderedDict()
        invoice_lines = self._document_lines()
        dte['Encabezado'] = self._xml_header(
            invoice_lines['MntExe'], invoice_lines['no_product'], invoice_lines['tax_include'])
        lin_ref = 1
        ref_lines = []
        if self.company_id.dte_service_provider == 'SIIHOMO' and isinstance(n_atencion, string_types) and \
                n_atencion != '' and not self._check_doc_type():
            ref_line = collections.OrderedDict()
            ref_line['NroLinRef'] = lin_ref
            ref_line['TpoDocRef'] = "SET"
            ref_line['FolioRef'] = self.get_folio()
            ref_line['FchRef'] = datetime.strftime(datetime.now(), '%Y-%m-%d')
            ref_line['RazonRef'] = "CASO " + n_atencion + "-" + str(self.sii_batch_number)
            lin_ref = 2
            ref_lines.extend([{'Referencia': ref_line}])
        if self.reference_ids:
            for ref in self.reference_ids:
                ref_line = collections.OrderedDict()
                ref_line['NroLinRef'] = lin_ref
                if not self._check_doc_type():
                    if ref.reference_doc_type:
                        ref_line['TpoDocRef'] = pysiidte.str_shorten(
                            ref.reference_doc_type.doc_code_prefix, 3) if \
                            ref.reference_doc_type.use_prefix else ref.reference_doc_type.code
                        ref_line['FolioRef'] = ref.origin
                    ref_line['FchRef'] = ref.date or datetime.strftime(datetime.now(), '%Y-%m-%d')
                if ref.reference_doc_code not in ['', 'none', False]:
                    ref_line['CodRef'] = ref.reference_doc_code
                ref_line['RazonRef'] = ref.reason or ''
                if self._check_doc_type():
                    ref_line['CodVndor'] = self.seller_id.id  # revisar la definición de este valor
                    ref_lines['CodCaja'] = self.journal_id.point_of_sale_cashier_code
                ref_lines.extend([{'Referencia': ref_line}])
                lin_ref += 1
        dte['item'] = invoice_lines['invoice_lines']
        if self.global_descuentos_recargos:
            dte['drlines'] = self._gdr()
        dte['reflines'] = ref_lines
        dte['TEDd'] = self.get_barcode(invoice_lines['no_product'])
        return dte

    @staticmethod
    def _dte_to_xml(dte, tpo_dte="Documento"):
        ted = dte[tpo_dte + ' ID']['TEDd']
        dte[(tpo_dte + ' ID')]['TEDd'] = ''
        xml_return = dicttoxml.dicttoxml(
            dte, root=False, attr_type=False).decode() \
            .replace('<item >', '').replace('<item>', '').replace('</item>', '') \
            .replace('<reflines>', '').replace('</reflines>', '') \
            .replace('<TEDd>', '').replace('</TEDd>', '') \
            .replace('</' + tpo_dte + '_ID>', '\n' + ted + '\n</' + tpo_dte + '_ID>') \
            .replace('<drlines>', '').replace('</drlines>', '')
        return xml_return

    def _tpo_dte(self):
        tpo_dte = "Documento"
        if self.document_type_id.code == 43:
            tpo_dte = 'Liquidacion'
        return tpo_dte

    def _stamp(self, n_atencion=None):
        signature_d = self.env.user.get_digital_signature(self.company_id)
        certp = signature_d['cert'].replace(BC, '').replace(EC, '').replace('\n', '')
        folio = self.get_folio()
        tpo_dte = self._tpo_dte()
        doc_id_number = "F{}T{}".format(folio, self.document_type_id.code)
        doc_id = '<' + tpo_dte + ' ID="{}">'.format(doc_id_number)
        dte = collections.OrderedDict()
        dte[(tpo_dte + ' ID')] = self._dte(n_atencion)
        xml = self._dte_to_xml(dte, tpo_dte)
        root = etree.XML(xml)
        xml_pret = etree.tostring(
            root,
            pretty_print=True
        ).decode().replace(
            '<' + tpo_dte + '_ID>',
            doc_id
        ).replace('</' + tpo_dte + '_ID>', '</' + tpo_dte + '>')
        envelope_efact = pysiidte.create_template_doc(xml_pret)
        type = 'doc'
        if self._check_doc_type():
            # todo: revisar aca... si lo que estoy verificando es el dte no hace falta poner el tipo en 'bol'
            type = 'bol'
        einvoice = pysiidte.sign_full_xml(
            envelope_efact,
            signature_d['priv_key'],
            pysiidte.split_cert(certp),
            doc_id_number,
            type,
        )
        self.sii_xml_dte = einvoice
        self.sii_pretty_xml_dte = pysiidte.pretty_xml_dte(einvoice)

    def _create_envelope(self, n_atencion=None, RUTRecep="60803000-K"):
        dte_s = {}
        clases = {}
        company_id = False
        es_boleta = False
        batch = 0
        for inv in self.with_context(lang='es_CL'):
            if not inv.sii_batch_number or inv.sii_batch_number == 0:
                batch += 1
                inv.sii_batch_number = batch
                # si viene una guía/nota regferenciando una factura, que por numeración viene a continuación de la
                # guia/nota, será recahazada laguía porque debe estar declarada la factura primero
            es_boleta = inv._check_doc_type()
            signature_d = self.env.user.get_digital_signature(inv.company_id)
            certp = signature_d['cert'].replace(BC, '').replace(EC, '').replace('\n', '')
            if inv.company_id.dte_service_provider == 'SIIHOMO':  # Retimbrar con número de atención y envío
                inv._stamp(n_atencion)
            if not inv.document_type_id.code in clases:
                clases[inv.document_type_id.code] = []
            clases[inv.document_type_id.code].extend(
                [{
                    'id': inv.id,
                    'envio': inv.sii_xml_dte,
                    'sii_batch_number': inv.sii_batch_number,
                    'sii_document_number': inv.sii_document_number, }])
            dte_s.update(clases)
            if not company_id:
                company_id = inv.company_id
            elif company_id.id != inv.company_id.id:
                raise UserError("Está combinando compañías, no está permitido hacer eso en un envío")
            company_id = inv.company_id
        file_name = ""
        dtes = {}
        SubTotDTE = ''
        resol_data = self.get_resolution_data(company_id)
        RUTEmisor = self.format_vat(company_id.vat)
        for id_class_doc, classes in clases.items():
            NroDte = 0
            for documento in classes:
                if documento['sii_batch_number'] in dtes.keys():
                    raise UserError("No se puede repetir el mismo número de orden")
                dtes.update({str(documento['sii_batch_number']): documento['envio']})
                NroDte += 1
                file_name += 'F' + str(int(documento['sii_document_number'])) + 'T' + str(id_class_doc)
            SubTotDTE += '<SubTotDTE>\n<TpoDTE>' + str(id_class_doc) + '</TpoDTE>\n<NroDTE>' + str(NroDte) + \
                         '</NroDTE>\n</SubTotDTE>\n'
        file_name += ".xml"
        documentos = ""
        for key in sorted(dtes.keys(), key=lambda r: int(r[0])):
            documentos += '\n' + dtes[key]
        # firma del sobre
        dtes = pysiidte.create_template_envio(
            RUTEmisor,
            RUTRecep,
            resol_data['dte_resolution_date'],
            resol_data['dte_resolution_number'],
            pysiidte.time_stamp(),
            documentos,
            signature_d,
            SubTotDTE, )
        env = 'env'
        if es_boleta:
            envio_dte = pysiidte.create_template_env_boleta(dtes)
            env = 'env_boleta'
        else:
            envio_dte = pysiidte.create_template_env(dtes)
        envio_dte = pysiidte.sign_full_xml(
            envio_dte.replace('<?xml version="1.0" encoding="ISO-8859-1"?>\n', ''),
            signature_d['priv_key'],
            certp,
            'SetDoc',
            env
        )
        return envio_dte, file_name

    @api.multi
    def do_dte_send(self, n_atencion=None):
        if not self[0].sii_xml_request or self[0].sii_result in ['Rechazado'] or \
                (self[0].company_id.dte_service_provider == 'SIIHOMO' and self[0].sii_xml_request.state in
                 ['', 'NoEnviado']):
            for r in self:
                if r.sii_xml_request:
                    r.sii_xml_request.unlink()
            xml_envio, file_name = self._create_envelope(n_atencion, RUTRecep="60803000-K")
            envio_id = self.env['sii.xml.envio'].create({
                    'xml_envio': xml_envio,
                    'name': file_name,
                    'company_id': self.company_id.id,
                    'user_id': self.env.uid,
                })
            for r in self:
                r.sii_xml_request = envio_id.id
            resp = envio_id.send_xml()
            return envio_id
        self[0].sii_xml_request.send_xml()
        return self[0].sii_xml_request

    @api.onchange('sii_message')  # no me doy cuenta para qué es este onchange, si el sii_message
    # no se actualiza por interfase
    def get_sii_result(self):
        for r in self:
            if not r.sii_result:
                r.sii_result = r.sii_xml_request.state  # puede no ser igual al sii_xml_request.state
            if r.sii_message:
                # r.sii_result = pysiidte.process_response_xml(xmltodict.parse(r.sii_message))
                r.sii_result = pysiidte.analyze_sii_result(r.sii_result, r.sii_message, r.sii_xml_request.sii_receipt)
                if r.sii_result in {'Proceso', 'Rechazado', 'Reparo', 'Aceptado'}:
                    r.send_queue_id.active = False
                continue
            if r.sii_xml_request.state == 'NoEnviado':
                r.sii_result = 'EnCola'
                continue
            r.sii_result = r.sii_xml_request.state  # puede no ser igual al sii_xml_request.state

    @api.multi
    def cron_process_queue(self):
        """
        this job process all messages.
        we remove type of work from pasivo to envio if we want to action it manually
        """
        for record in self:
            if record.send_queue_id.active:
                if record.send_queue_id.tipo_trabajo == 'pasivo':
                    record.send_queue_id.tipo_trabajo = 'envio'
                    _logger.info('invoice id: %s passed to sending state and processing queue' % record.id)
                    record.send_queue_id._process_job_type()
                elif record.send_queue_id.tipo_trabajo in ['envio', 'consulta']:
                    _logger.info('invoice id: %s already in sending state. processing queue NOW...' % record.id)
                    record.send_queue_id._process_job_type()
                else:
                    _logger.info(
                        'processing queue done nothing over invoice id: %s because type of job is %s' % (
                            record.id, record.send_queue_id.tipo_trabajo))
            else:
                _logger.info(
                    'processing queue done nothing over invoice id: %s because queue job is inactive' % record.id)

    def _get_dte_status(self):
        for r in self:
            signature_d = r.user_id.get_digital_signature(r.company_id)
            data = {
                'rut': str(signature_d['subject_serial_number']),
                'company_vat': r.company_id.vat,
                'receptor': r.format_vat(r.commercial_partner_id.main_id_number),
                'document_type_code': str(r.document_type_id.code),
                'sii_document_number': str(r.sii_document_number),
                'invoice_date': datetime.strptime(r.date_invoice, "%Y-%m-%d").strftime("%d-%m-%Y"),
                'amount_total': str(self._currency_decimals(r.amount_total)),
            }
            response = pysiidte.get_dte_status(
                signature_d,
                service_provider=r.company_id.dte_service_provider,
                **data,
            )
            r.sii_message = response

    @api.multi
    def ask_for_dte_status(self):
        for r in self:
            if r.sii_xml_request.state in {'Aceptado', 'Rechazado'}:
                _logger.info('sii_xml_request.state - Ask for DTE Status')
                r.sii_result = r.sii_xml_request.state
                return
            if not r.sii_xml_request and not r.sii_xml_request.sii_send_ident:
                raise UserError(_('The document has not been sent yet. It is in internal queue'))
            if r.sii_xml_request.state not in {'Aceptado', 'Rechazado'}:
                r.sii_xml_request.get_send_status(r.env.user)
        self._get_dte_status()  # esta funcion actualiza el sii_message, que por ahora no está sirviendo para nada
        self.get_sii_result()   # esta función hace algo redundante parecido a lo de la linea 1557

    def set_dte_claim(self, rut_emisor=False, company_id=False, sii_document_number=False, document_type_id=False,
                      claim=False):
        response = pysiidte.set_dte_claim(
            token=self.sii_xml_request.get_token(self.env.user, self.company_id),
            dte_service_provide=company_id.dte_service_provider,
            rut_emisor=rut_emisor or self.format_vat(self.company_id.partner_id.main_id_number),
            sii_document_number=sii_document_number or self.sii_document_number or self.reference,
            document_type_id=document_type_id or self.document_type_id,
            claim=claim or self.claim,
        )
        if self.id:
            self.claim_description = response

    @api.multi
    def get_dte_claim(self):
        response = pysiidte.get_dte_claim(
            token=self.sii_xml_request.get_token(self.env.user, self.company_id),
            dte_service_provider=self.company_id.dte_service_provider,
            company_vat=self.company_id.vat,
            document_type_code=str(self.document_type_id.code),
            sii_document_number=str(self.sii_document_number)

        )
        self.claim_description = response

    @api.multi
    def wizard_upload(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sii.dte.upload_xml.wizard',
            'src_model': 'account.invoice',
            'view_mode': 'form',
            'view_type': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'tag': 'action_upload_xml_wizard', }

    @api.multi
    def invoice_print(self):
        self.ensure_one()
        self.sent = True
        if self.ticket:
            return self.env.ref('l10n_cl_dte.action_print_ticket').report_action(self)
        return self.env.ref('account.account_invoices').report_action(self)

    @api.multi
    def print_cedible(self):
        raise UserError('Para impresión de DTE cedible debe utilizar l10n_cl_docsonline_print')

    @api.multi
    def get_total_discount(self):
        total_discount = 0
        for l in self.invoice_line_ids:
            total_discount += (((l.discount or 0.00) / 100) * l.price_unit * l.quantity)
        return self.currency_id.round(total_discount)

    # TODO should be removed when pysiidte migration is finished
    def sign_full_xml(self, message, privkey, cert, uri, type='doc'):
        return pysiidte.sign_full_xml(message, privkey, cert, uri, type)

    # TODO should be removed when pysiidte migration is finished
    @staticmethod
    def pdf417bc(ted):
        return pysiidte.pdf417bc(ted)

    # TODO should be removed when pysiidte migration is finished
    @staticmethod
    def long_to_bytes(n, blocksize=0):
        return pysiidte.long_to_bytes(n, blocksize)

    # TODO should be removed when pysiidte migration is finished
    @staticmethod
    def signmessage(message, key):
        return pysiidte.signmessage(message, key)
