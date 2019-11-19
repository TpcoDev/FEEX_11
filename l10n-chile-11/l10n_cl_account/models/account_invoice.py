##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import logging
import re

from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare, pycompat

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice', 'l10n.cl.localization.filter']

    def _default_journal_document_type_id(self, default=None):
        ids = self._get_available_journal_document_type()
        document_types = self.env['account.journal.document.type'].browse(ids)
        if default:
            for dt in document_types:
                if dt.document_type_id.id == default:
                    self.journal_document_type_id = dt.id
        elif document_types:
            default = self.get_document_type_default(document_types)
        return default

    main_id_number = fields.Char(
        related='commercial_partner_id.main_id_number',
        readonly=True,
    )
    state_id = fields.Many2one(
        # related='commercial_partner_id.state_id',
        # al final lo hacemos por contacto (y no commercial) para poder usar
        # direcciones distintas
        related='partner_id.state_id',
        store=True,
        readonly=True,
    )
    currency_rate = fields.Float(
        string='Currency Rate',
        compute='_compute_currency_rate',
        copy=False,
        digits=(16, 4),
        store=True,
        readonly=True,
    )
    document_letter_id = fields.Many2one(
        related='document_type_id.document_letter_id',
        readonly=True,
    )
    document_letter_name = fields.Char(
        related='document_letter_id.name',
        readonly=True,
    )
    taxes_included = fields.Boolean(
        related='document_letter_id.taxes_included',
        readonly=True,
    )
    # mostly used on reports
    taxpayer_type_id = fields.Many2one(
        'account.taxpayer.type',
        string='Tax Payer Type',
        readonly=True,
        help='Tax Payer type from journal entry where it is stored and '
        'it never change',
        related='move_id.taxpayer_type_id',
    )
    invoice_number = fields.Float(
        compute='_get_invoice_number',
        string="Invoice Number",
        store=True,
        size=10,
        digits=(10, 0),
    )

    # point_of_sale_number = fields.Integer(
    #     compute='_get_invoice_number',
    #     string="Point Of Sale",
    # )

    vat_tax_ids = fields.One2many(
        compute="_get_chile_amounts",
        comodel_name='account.invoice.tax',
        string='VAT Taxes'
    )
    # todos los impuestos iva que componen base imponible (no se incluyen 0,
    # 1, 2 que no son impuesto en si)
    vat_taxable_ids = fields.One2many(
        compute="_get_chile_amounts",
        comodel_name='account.invoice.tax',
        string='VAT Taxes'
    )
    # todos los impuestos menos los tipo iva vat_tax_ids
    not_vat_tax_ids = fields.One2many(
        compute="_get_chile_amounts",
        comodel_name='account.invoice.tax',
        string='Not VAT Taxes'
    )
    # suma de base para todos los impuestos tipo iva
    vat_base_amount = fields.Monetary(
        compute="_get_chile_amounts",
        string='VAT Base Amount'
    )
    # base imponible (no se incluyen 0, exento y no gravado)
    vat_taxable_amount = fields.Monetary(
        compute="_get_chile_amounts",
        string='VAT Taxable Amount'
    )
    # base iva exento
    vat_exempt_base_amount = fields.Monetary(
        compute="_get_chile_amounts",
        string='VAT Exempt Base Amount'
    )
    # base iva no gravado
    vat_untaxed_base_amount = fields.Monetary(
        compute="_get_chile_amounts",
        string='VAT Untaxed Base Amount'
    )
    # importe de iva
    vat_amount = fields.Monetary(
        compute="_get_chile_amounts",
        string='VAT Amount'
    )
    # importe de otros impuestos
    other_taxes_amount = fields.Monetary(
        compute="_get_chile_amounts",
        string='Other Taxes Amount'
    )
    sii_incoterms_id = fields.Many2one(
        'stock.incoterms',
        'Incoterms',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    point_of_sale_type = fields.Selection(
        related='journal_id.point_of_sale_type',
        readonly=True,
    )
    # estos campos los agregamos en este modulo pero en realidad los usa FE
    # pero entendemos que podrian ser necesarios para otros tipos, por ahora
    # solo lo vamos a hacer requerido si el punto de venta es del tipo
    # electronico
    # TODO mejorar, este concepto deberia quedar fijo y no poder modificarse
    # TODO: creo que es innecesario manejar este concepto. Validar.
    # una vez validada, cosa que pasaria por ej si cambias el producto
    reference_ids = fields.One2many(
            'account.invoice.reference',
            'invoice_id',
            readonly=True,
            states={'draft': [('readonly', False)]}, )
    sii_concept = fields.Selection(
        compute='_get_concept',
        # store=True,
        selection=[('1', 'Producto / Exportación definitiva de bienes'),
                   ('2', 'Servicios'),
                   ('3', 'Productos y Servicios'),
                   ('4', '4-Otros (exportación)'), ],
        string="SII concept",
    )
    sii_service_start = fields.Date(
        string='Service Start Date',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    sii_service_end = fields.Date(
        string='Service End Date',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    vat_for_common_use = fields.Boolean(
        string="Common Use",
        readonly=True, oldname='iva_uso_comun', store=True,
        related='fiscal_position_id.vat_for_common_use', )

    @api.multi
    @api.constrains('type', 'document_type_id')
    def check_invoice_type_document_type(self):
        """
        This method replaces the default validation in account_document
        considering 'debit_note' as a rectification of the invoice
        (using the same treatment made to refunds => credit_note, since
        there is a similar document relationship in both)
        :return:
        """
        for rec in self:
            internal_type = rec.document_type_internal_type
            invoice_type = rec.type
            _logger.info('internal type: %s, invoice_type: %s' % (internal_type, invoice_type))
            """
            if not internal_type:
                continue
            elif internal_type in [
                    'debit_note', 'invoice'] and invoice_type in [
                    'out_refund', 'in_refund']:
                raise Warning(_(
                    'You can not use a %s document type with a refund '
                    'invoice') % internal_type)
            elif internal_type == 'credit_note' and invoice_type in [
                    'out_invoice', 'in_invoice']:
                raise Warning(_(
                    'You can not use a %s document type with a invoice') % (
                    internal_type))
            """

    @api.onchange('fiscal_position_id')
    def _compute_taxes(self):
        """
        Agregada por Daniel Blanco para intentar el recalculo de impuestos al cambiar la posicion fiscal
        :return:
        """
        _logger.info('set taxes h')
        for line in self.invoice_line_ids:
            line._set_taxes()

    @api.one
    def _get_chile_amounts(self):
        """
        """
        vat_taxes = self.tax_line_ids.filtered(
            lambda r: (
                r.tax_id.tax_group_id.type == 'tax' and
                r.tax_id.tax_group_id.tax == 'vat'))
        # we add and "r.base" because only if a there is a base amount it is
        # considered taxable, this is used for eg to validate invoices on sii
        vat_taxables = vat_taxes.filtered(
            lambda r: (
                r.tax_id.tax_group_id.sii_code not in [0, 1, 2]) and r.base)

        vat_amount = sum(vat_taxes.mapped('amount'))
        self.vat_tax_ids = vat_taxes
        self.vat_taxable_ids = vat_taxables
        self.vat_amount = vat_amount
        self.vat_taxable_amount = sum(vat_taxables.mapped('base'))
        self.vat_base_amount = sum(vat_taxes.mapped('base'))

        vat_exempt_taxes = self.tax_line_ids.filtered(
            lambda r: (
                r.tax_id.tax_group_id.type == 'tax' and
                r.tax_id.tax_group_id.tax == 'vat' and
                r.tax_id.tax_group_id.sii_code == 2))
        self.vat_exempt_base_amount = sum(
            vat_exempt_taxes.mapped('base'))
        vat_untaxed_taxes = self.tax_line_ids.filtered(
            lambda r: (
                r.tax_id.tax_group_id.type == 'tax' and
                r.tax_id.tax_group_id.tax == 'vat' and
                r.tax_id.tax_group_id.sii_code == 1))
        self.vat_untaxed_base_amount = sum(
            vat_untaxed_taxes.mapped('base'))
        not_vat_taxes = self.tax_line_ids - vat_taxes
        other_taxes_amount = sum(not_vat_taxes.mapped('amount'))
        self.not_vat_tax_ids = not_vat_taxes
        self.other_taxes_amount = other_taxes_amount

    @api.multi
    @api.depends('document_number', 'number')
    def _get_invoice_number(self):
        """ Funcion que calcula numero de punto de venta y numero de factura
        a partir del document number.
        """
        for rec in self:
            str_number = rec.document_number or False
            if str_number:
                if rec.document_type_id.code:  # in ['33', '99', '331', '332']:
                    # point_of_sale = '0'
                    invoice_number = str_number
                # revisar esta linea
                rec.invoice_number = int(
                    re.sub("[^0-9]", "", invoice_number))
                # rec.point_of_sale_number = int(
                #     re.sub("[^0-9]", "", point_of_sale))

    @api.one
    @api.depends(
        'invoice_line_ids',
        'invoice_line_ids.product_id',
        'invoice_line_ids.product_id.type',
        'localization',
    )
    def _get_concept(self):
        sii_concept = False
        if self.point_of_sale_type in ['online', 'electronic']:
            # exportaciones
            invoice_lines = self.invoice_line_ids
            product_types = set(
                [x.product_id.type for x in invoice_lines if x.product_id])
            consumible = set(['consu', 'product'])
            service = set(['service'])
            mixed = set(['consu', 'service', 'product'])
            # default value "product"
            sii_concept = '1'
            if product_types.issubset(mixed):
                sii_concept = '3'
            if product_types.issubset(service):
                sii_concept = '2'
            if product_types.issubset(consumible):
                sii_concept = '1'
            if self.document_type_id.code in ['19', '20', '21']:
                # TODO verificar esto, como par expo no existe 3 y existe 4
                # (otros), considermaos que un mixto seria el otros
                if sii_concept == '3':
                    sii_concept = '4'
        self.sii_concept = sii_concept

    @api.depends('currency_id')
    def _compute_currency_rate(self):
        for record in self:
            if record.company_id.currency_id == record.currency_id:
                record.currency_rate = 1.0
            else:
                currency = record.currency_id
                record.currency_rate = currency.compute(1., record.company_id.currency_id, round=False)

    @api.model
    def _get_available_journal_document_types(
            self, journal, invoice_type, partner):
        """
        This function search for available document types regarding:
        * Journal
        * Partner
        * Company
        * Documents configuration
        If needed, we can make this funcion inheritable and customizable per
        localization
        """
        if journal.localization != 'chile':
            return super(AccountInvoice, self)._get_available_journal_document_types(journal, invoice_type, partner)

        commercial_partner = partner.commercial_partner_id

        journal_document_types = journal_document_type = self.env[
            'account.journal.document.type']

        if invoice_type in [
                'out_invoice', 'in_invoice', 'out_refund', 'in_refund']:

            if journal.use_documents:
                letters = journal.get_journal_letter(
                    counterpart_partner=commercial_partner)

                domain = [
                    ('journal_id', '=', journal.id),
                    '|',
                    ('document_type_id.document_letter_id', 'in', letters.ids),
                    ('document_type_id.document_letter_id', '=', False),
                ]

                # if invoice_type is refund, only credit notes
                if invoice_type in ['out_refund', 'in_refund']:
                    domain += [
                        ('document_type_id.internal_type',
                            # '=', 'credit_note')]
                            # TODO, check if we need to add tickets and others
                            # also
                            'in', ['credit_note', 'in_document'])]
                # else, none credit notes
                else:
                    domain += [
                        ('document_type_id.internal_type',
                            '!=', 'credit_note')]

                # If internal_type in context we try to serch specific document
                # for eg used on debit notes
                internal_type = self._context.get('internal_type', False)
                if internal_type:
                    journal_document_type = journal_document_type.search(
                        domain + [
                            ('document_type_id.internal_type',
                                '=', internal_type)], limit=1)
                # For domain, we search all documents
                journal_document_types = journal_document_types.search(domain)

                # If not specific document type found, we choose another one
                if not journal_document_type and journal_document_types:
                    journal_document_type = journal_document_types[0]

        if invoice_type == 'in_invoice':
            other_document_types = commercial_partner.other_document_type_ids
            domain = [
                ('journal_id', '=', journal.id),
                ('document_type_id',
                    'in', other_document_types.ids),
            ]
            other_journal_document_types = self.env['account.journal.document.type'].search(domain)
            journal_document_types += other_journal_document_types
            # if we have some document sepecific for the partner, we choose it
            if other_journal_document_types:
                journal_document_type = other_journal_document_types[0]

        return {
            'available_journal_document_types': journal_document_types,
            'journal_document_type': journal_document_type,
        }

    @api.multi
    @api.constrains('document_number', 'partner_id', 'company_id')
    def _check_document_number_unique(self):
        for rec in self.filtered(lambda x: x.localization == 'chile'):
            if rec.document_number:
                domain = [
                    ('type', '=', rec.type),
                    ('document_number', '=', rec.document_number),
                    ('document_type_id', '=', rec.document_type_id.id),
                    ('company_id', '=', rec.company_id.id),
                    ('id', '!=', rec.id)
                ]
                msg = (
                    'Error en factura con id %s: El numero de comprobante (%s)'
                    ' debe ser unico por tipo de documento')
                if rec.type in ['out_invoice', 'out_refund']:
                    # si es factura de cliente entonces tiene que ser numero
                    # unico por compania y tipo de documento
                    rec.search(domain)
                else:
                    # si es factura de proveedor debe ser unica por proveedor
                    domain += [
                        ('partner_id.commercial_partner_id', '=',
                            rec.commercial_partner_id.id)]
                    msg += ' y proveedor'
                if rec.search(domain):
                    raise ValidationError(msg % (rec.id, rec.document_number))

    @api.multi
    def action_move_create(self):
        """
        We add currency rate on move creation so it can be used by electronic
        invoice later on action_number
        """
        self.check_chile_invoice_taxes()
        return super(AccountInvoice, self).action_move_create()

    @api.multi
    def check_chile_invoice_taxes(self):
        """
        We make theis function to be used as a constraint but also to be called
        from other models like vat citi
        """
        # only check for chile localization companies
        _logger.info('Running checks related to chile documents')

        # we consider chile invoices the ones from companies with
        # localization localization and that belongs to a journal with
        # use_documents
        chile_invoices = self.filtered(
            lambda r: (
                r.localization == 'chile' and r.use_documents))
        if not chile_invoices:
            return True

        # check partner has tax payer type so it will be assigned on invoice
        # validate
        without_taxpayer_type = chile_invoices.filtered(
            lambda x: not x.commercial_partner_id.taxpayer_type_id)
        if without_taxpayer_type:
            raise ValidationError(_(
                'The following invoices has a partner without SII '
                'tax payer type: %s' % without_taxpayer_type.ids))

        # we check all invoice tax lines has tax_id related
        # we exclude exempt vats and untaxed (no gravados)
        wihtout_tax_id = chile_invoices.mapped('tax_line_ids').filtered(
            lambda r: not r.tax_id)
        if wihtout_tax_id:
            raise ValidationError(_(
                "Some Invoice Tax Lines don't have a tax_id asociated, please "
                "correct them or try to refresh invoice. Tax lines: %s") % (
                ', '.join(wihtout_tax_id.mapped('name'))))

        # check codes has chile tax attributes configured
        tax_groups = chile_invoices.mapped(
            'tax_line_ids.tax_id.tax_group_id')
        unconfigured_tax_groups = tax_groups.filtered(
            lambda r: not r.type or not r.tax or not r.application)
        if unconfigured_tax_groups:
            raise ValidationError(_(
                "You are using chile localization and there are some tax"
                " groups that are not configured. Tax Groups (id): %s" % (
                    ', '.join(unconfigured_tax_groups.mapped(
                        lambda x: '%s (%s)' % (x.name, x.id))))))

        vat_taxes = self.env['account.tax'].search([
            ('tax_group_id.type', '=', 'tax'),
            ('tax_group_id.tax', '=', 'vat')])
        lines_without_vat = self.env['account.invoice.line'].search([
            ('invoice_id', 'in', chile_invoices.ids),
            ('invoice_line_tax_ids', 'not in', vat_taxes.ids),
            ('company_id.company_requires_vat', '=', True),
        ])
        if lines_without_vat:
            raise ValidationError(_(
                "Invoice with ID %s has some lines without vat Tax ") % (
                    lines_without_vat.mapped('invoice_id').ids))

        # Check except vat invoice
        sii_exempt_codes = ['Z', 'X', 'E', 'N', 'C']
        for invoice in chile_invoices:
            special_vat_taxes = invoice.tax_line_ids.filtered(
                lambda r: r.tax_id.tax_group_id.sii_code in [1, 2, 3])
            if (
                    special_vat_taxes and
                    invoice.fiscal_position_id.sii_code
                    not in sii_exempt_codes):
                raise ValidationError(_(
                    "If you have choose a 0, exempt or untaxed 'tax', or "
                    "you must choose a fiscal position with sii code in %s.\n"
                    "* Invoice id %i" % (sii_exempt_codes, invoice.id))
                )
            # esto es, por eje, si hay un producto con 100% de descuento para
            # única alicuota, entonces el impuesto liquidado da cero y se
            # obliga reportar con alicuota 0, entonces se exige tmb cod de op.
            # esta restriccion no es de FE si no de aplicativo citi
            # todo: esta situación no aplica ni es exigencia legal.
            zero_vat_lines = invoice.tax_line_ids.filtered(
                lambda r: ((
                    r.tax_id.tax_group_id.sii_code in [4, 5, 6, 8, 9] and
                    r.currency_id.is_zero(r.amount))))
            if (
                    zero_vat_lines and
                    invoice.fiscal_position_id.sii_code
                    not in sii_exempt_codes):
                raise ValidationError(_(
                    "Si hay líneas con IVA declarado 0, entonces debe elegir "
                    "una posición fiscal con código de sii '%s'.\n"
                    "* Invoice id %i" % (sii_exempt_codes, invoice.id))
                )

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountInvoice, self)._onchange_partner_id()
        fiscal_position = self.env[
            'account.fiscal.position'].with_context(
                force_company=self.company_id.id).get_fiscal_position(
                self.partner_id.id)
        if fiscal_position:
            self.fiscal_position_id = fiscal_position
        return res

    @api.onchange('journal_document_type_id')
    def _onchange_journal_document_type_id(self):
        if self.journal_document_type_id:
            self.fiscal_position_id = self.journal_document_type_id.document_type_id.document_letter_id.fiscal_position_id

    @api.one
    @api.constrains('date_invoice')
    def set_date_sii(self):
        if self.date_invoice:
            date_invoice = fields.Datetime.from_string(self.date_invoice)
            if not self.sii_service_start:
                self.sii_service_start = date_invoice + relativedelta(day=1)
            if not self.sii_service_end:
                self.sii_service_end = date_invoice + \
                    relativedelta(day=1, days=-1, months=+1)

    @api.model
    def _prepare_refund(
            self, invoice, date_invoice=None, date=None, description=None, journal_id=None, mode='1'):
        values = super(AccountInvoice, self)._prepare_refund(invoice, date_invoice, date, description, journal_id)
        document_type = self.env['account.journal.document.type'].search(
                [('document_type_id.code', '=', 61),
                 ('journal_id', '=', invoice.journal_id.id), ], limit=1, )
        if invoice.type == 'out_invoice':
            type = 'out_refund'
        elif invoice.type == 'out_refund':
            type = 'out_invoice'
        elif invoice.type == 'in_invoice':
            type = 'in_refund'
        elif invoice.type == 'in_refund':
            type = 'in_invoice'
        values.update({
            'type': type,
            'journal_document_type_id': document_type.id,
            'invoice_turn': invoice.invoice_turn.id,
            'reference_ids': [[0, 0, {
                'origin': int(invoice.invoice_number),
                'reference_doc_type': invoice.document_type_id.id,
                'reference_doc_code': mode,
                'reason': description,
                'date': invoice.date_invoice, }, ], ], })
        return values

    @api.multi
    @api.returns('self')
    def refund(self, date_invoice=None, date=None, description=None, journal_id=None, mode='1'):
        new_invoices = self.browse()
        for invoice in self:
            # create the new invoice
            values = self._prepare_refund(
                invoice, date_invoice=date_invoice, date=date,
                description=description, journal_id=journal_id, mode=mode)
            refund_invoice = self.create(values)
            invoice_type = {'out_invoice': 'customer invoices credit note',
                            'out_refund': 'customer invoices debit note',
                            'in_invoice': 'vendor bill credit note',
                            'in_refund': 'vendor bill debit note'}
            message = _("This %s has been created from: \
<a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a>") % (
                invoice_type[invoice.type], invoice.id, invoice.number)
            refund_invoice.message_post(body=message)
            new_invoices += refund_invoice
        return new_invoices
