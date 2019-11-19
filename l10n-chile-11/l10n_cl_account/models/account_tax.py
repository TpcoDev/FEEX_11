##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = ['account.tax', 'l10n.cl.localization.filter']

    sii_code = fields.Integer(
        'SII Code'
    )

    # jurisdiction_code = fields.Char(
    #     compute='_compute_jurisdiction_code',
    # )

    sii_type = fields.Selection(
            [
                ('A', 'Anticipado'),
                ('R', 'Retención'),
            ],
            string="Tipo de impuesto para el SII",
        )
    retencion = fields.Float(
            string="Valor retención",
            default=0.00,
        )
    no_rec = fields.Boolean(
            string="Es No Recuperable",
            default=False,
        )
    activo_fijo = fields.Boolean(
            string="Activo Fijo",
            default=False,
        )

    # @api.multi
    # def _compute_jurisdiction_code(self):
    #     for rec in self:
    #         tag = rec.tag_ids.filtered('jurisdiction_code')
    #         rec.jurisdiction_code = tag and tag[0].jurisdiction_code


class AccountTaxTemplate(models.Model):
    _name = 'account.tax.template'
    _inherit = ['account.tax.template', 'l10n.cl.localization.filter']

    tax_group_id = fields.Many2one(
        'account.tax.group',
        string="Tax Group",
    )
    sii_code = fields.Integer(
        'SII Code'
    )
    sii_type = fields.Selection(
            [
                ('A', 'Anticipado'),
                ('R', 'Retención'),
            ],
            string="Tipo de impuesto para el SII",
        )
    retencion = fields.Float(
            string="Valor retención",
            default=0.00,
        )
    no_rec = fields.Boolean(
            string="Es No Recuperable",
            default=False,
        )
    activo_fijo = fields.Boolean(
            string="Activo Fijo",
            default=False,
        )

    def _get_tax_vals(self, company, tax_template_to_tax):
        """ This method generates a dictionary of all the values for the tax that will be created.
        """
        self.ensure_one()
        vals = super(AccountTaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)
        vals.update({
            'sii_code': self.sii_code,
            'sii_type': self.sii_type,
            'retencion': self.retencion,
            'no_rec': self.no_rec,
            'activo_fijo': self.activo_fijo,
        })
        if self.tax_group_id:
            vals['tax_group_id'] = self.tax_group_id.id
        return vals


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    sii_code = fields.Integer(
        'SII Code'
    )
    type = fields.Selection([
        ('tax', 'TAX'),
        ('perception', 'Perception'),
        ('withholding', 'Withholding'),
        ('other', 'Other'),
        # ('view', 'View'),
    ])
    tax = fields.Selection([
        ('vat', 'VAT'),
        ('profits', 'Profits'),
        ('gross_income', 'Gross Income'),
        ('other', 'Other')],
    )
    application = fields.Selection([
        ('national_taxes', 'National Taxes'),
        ('provincial_taxes', 'Provincial Taxes'),
        ('municipal_taxes', 'Municipal Taxes'),
        ('internal_taxes', 'Internal Taxes'),
        ('others', 'Others')],
        help='Other Taxes According to SII',
    )
    application_code = fields.Char(
        'Application Code',
        compute='get_application_code',
    )
    # added to avoid warning
    amount = fields.Float(
        'Amount'
    )

    @api.one
    @api.depends('application')
    def get_application_code(self):
        if self.application == 'national_taxes':
            application_code = '01'
        elif self.application == 'provincial_taxes':
            application_code = '02'
        elif self.application == 'municipal_taxes':
            application_code = '03'
        elif self.application == 'internal_taxes':
            application_code = '04'
        else:
            application_code = '99'
        self.application_code = application_code


class AccountFiscalPositionTemplate(models.Model):
    _inherit = 'account.fiscal.position.template'

    sii_code = fields.Char(
        'SII Code',
        help='For eg. This code will be used on electronic invoice'
        'reports'
    )
    # TODO borrar si no lo usamos, por ahora lo resolivmos de manera nativa
    taxpayer_type_ids = fields.Many2many(
        'account.taxpayer.type',
        'taxpayer_account_fiscal_pos_temp_rel',
        'position_id', 'taxpayer_type_id',
        'Tax Payer Types',
        help='Add this fiscalposition if partner has one of this '
        'tax payer types'
    )
    # TODO this fields should be added on odoo core
    auto_apply = fields.Boolean(
        string='Detect Automatically',
        help="Apply automatically this fiscal position.")
    country_id = fields.Many2one(
        'res.country', string='Country',
        help="Apply only if delivery or invoicing country match.")
    country_group_id = fields.Many2one(
        'res.country.group', string='Country Group',
        help="Apply only if delivery or invocing country match the group.")
    state_ids = fields.Many2many(
        'res.country.state', string='Federal States')
    zip_from = fields.Integer(
        string='Zip Range From', default=0)
    zip_to = fields.Integer(
        string='Zip Range To', default=0)
    vat_for_common_use = fields.Boolean(
        string="Common Use",
        readonly=True, oldname='iva_uso_comun',
    )
    no_rec_code = fields.Selection(
        [
            ('1', 'Compras destinadas a IVA a generar operaciones no gravados o exentas.'),
            ('2', 'Facturas de proveedores registrados fuera de plazo.'),
            ('3', 'Gastos rechazados.'),
            ('4', 'Entregas gratuitas (premios, bonificaciones, etc.) recibidos.'),
            ('9', 'Otros.')
        ],
        string="Non recoverable code",
        readonly=True,
    )
    active = fields.Boolean(
        'Active', default=True,
        help="If unchecked, it will allow you to hide the template without removing it.")


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    sii_code = fields.Char(
        'SII Code',
        help='For eg. This code will be used on electronic invoice.'
        'reports'
    )
    # TODO tal vez podriamos usar funcionalidad nativa con "vat subjected"
    taxpayer_type_ids = fields.Many2many(
        'account.taxpayer.type',
        'taxpayer_account_fiscal_pos_rel',
        'position_id', 'taxpayer_type_id',
        'Tax Payer Types',
        help='Add this fiscalposition if partner has one of this '
        'tax payer types'
    )
    vat_for_common_use = fields.Boolean(
        string="Common Use",
        readonly=True, oldname='iva_uso_comun',
    )
    no_rec_code = fields.Selection(
        [
            ('1', 'Compras destinadas a IVA a generar operaciones no gravados o exentas.'),
            ('2', 'Facturas de proveedores registrados fuera de plazo.'),
            ('3', 'Gastos rechazados.'),
            ('4', 'Entregas gratuitas (premios, bonificaciones, etc.) recibidos.'),
            ('9', 'Otros.')
        ],
        string="Non recoverable code",
        readonly=True,
    )
    active = fields.Boolean(
        'Active', default=True,
        help="If unchecked, it will allow you to hide the template without removing it.")

    @api.model
    def _get_fpos_by_region_and_taxpayer_type(
            self, country_id=False, state_id=False,
            zipcode=False, taxpayer_type_id=False):
        """
        We use similar code than _get_fpos_by_region but we use
        "taxpayer_type_id" insted of vat_required
        """

        base_domain = [
            ('auto_apply', '=', True),
            ('taxpayer_type_ids', '=', taxpayer_type_id)
        ]

        if self.env.context.get('force_company'):
            base_domain.append(
                ('company_id', '=', self.env.context.get('force_company')))

        null_state_dom = state_domain = [('state_ids', '=', False)]
        null_zip_dom = zip_domain = [
            ('zip_from', '=', 0), ('zip_to', '=', 0)]
        null_country_dom = [
            ('country_id', '=', False), ('country_group_id', '=', False)]

        if zipcode and zipcode.isdigit():
            zipcode = int(zipcode)
            zip_domain = [
                ('zip_from', '<=', zipcode), ('zip_to', '>=', zipcode)]
        else:
            zipcode = 0

        if state_id:
            state_domain = [('state_ids', '=', state_id)]

        domain_country = base_domain + [('country_id', '=', country_id)]
        domain_group = base_domain + [
            ('country_group_id.country_ids', '=', country_id)]

        # Build domain to search records with exact matching criteria
        fpos = self.search(
            domain_country + state_domain + zip_domain, limit=1)

        # return records that fit the most the criteria, and fallback on less
        # specific fiscal positions if any can be found
        if not fpos and state_id:
            fpos = self.search(
                domain_country + null_state_dom + zip_domain, limit=1)
        if not fpos and zipcode:
            fpos = self.search(
                domain_country + state_domain + null_zip_dom, limit=1)
        if not fpos and state_id and zipcode:
            fpos = self.search(
                domain_country + null_state_dom + null_zip_dom, limit=1)

        # fallback: country group with no state/zip range
        if not fpos:
            fpos = self.search(
                domain_group + null_state_dom + null_zip_dom, limit=1)

        if not fpos:
            # Fallback on catchall (no country, no group)
            fpos = self.search(
                base_domain + null_country_dom, limit=1)
        return fpos or False

    @api.model
    def get_fiscal_position(self, partner_id, delivery_id=None):
        """
        We overwrite original functionality and replace vat_required logic
        for taxpayer_type_ids
        """
        # we need to overwrite code (between #####) from original function
        #####
        if not partner_id:
            return False
        # This can be easily overriden to apply more complex fiscal rules
        partner_obj = self.env['res.partner']
        partner = partner_obj.browse(partner_id)

        # if no delivery use invoicing
        if delivery_id:
            delivery = partner_obj.browse(delivery_id)
        else:
            delivery = partner

        # partner manually set fiscal position always win
        if (
                delivery.property_account_position_id or
                partner.property_account_position_id):
            return (
                delivery.property_account_position_id.id or
                partner.property_account_position_id.id)
        #####

        taxpayer = (
            partner.commercial_partner_id.taxpayer_type_id)

        fpos = self._get_fpos_by_region_and_taxpayer_type(
            delivery.country_id.id, delivery.state_id.id, delivery.zip,
            taxpayer.id)
        if not fpos and taxpayer:
            fpos = self._get_fpos_by_region_and_taxpayer_type(
                delivery.country_id.id, delivery.state_id.id, delivery.zip,
                False)

        return fpos.id if fpos else False
