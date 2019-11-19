# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

try:
    import xmltodict
except ImportError:
    pass

try:
    import base64
except ImportError:
    pass


class Caf(models.Model):
    _name = 'dte.caf'

    name = fields.Char('File Name', compute='_get_filename')

    filename = fields.Char('File Name')

    caf_file = fields.Binary(
        string='CAF XML File', filters='*.xml',
        store=True, help='Upload the CAF XML File in this holder')

    _sql_constraints = [(
        'filename_unique', 'unique(filename)',
        'Error! Filename Already Exist!')]

    issued_date = fields.Date('Issued Date')

    document_type_code = fields.Char('SII Document Type')

    start_nm = fields.Integer(
        string='Start Number', help='CAF Starts from this number')

    final_nm = fields.Integer(
        string='End Number', help='CAF Ends to this number')

    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_use', 'In Use'),
        ('spent', 'Spent'),
        ('cancelled', 'Cancelled')], string='Status',
        default='draft', help='''Draft: means it has not been used yet. \
You must put in in used in order to make it available for use.
Spent: means that the number interval has been exhausted.
Cancelled means it has been deprecated by hand.''')
    rut_n = fields.Char(string='RUT')
    company_id = fields.Many2one(
        'res.company', 'Company', required=False,
        default=lambda self: self.env.user.company_id)
    sequence_id = fields.Many2one(
        'ir.sequence', 'Sequence', required=False)
    use_level = fields.Float(string="Use Level", compute='_use_level')

    @api.depends('start_nm', 'final_nm', 'sequence_id', 'status')
    def _use_level(self):
        for r in self:
            if r.status not in ['draft', 'cancelled']:
                if r.sequence_id.number_next_actual > r.final_nm:
                    r.use_level = 100
                    if r.status == 'in_use':
                        self.env.cr.execute("UPDATE dte_caf SET status = \
                        'spent' WHERE filename = '%s'" % r.filename)
                elif r.sequence_id.number_next_actual < r.start_nm:
                    r.use_level = 0
                else:
                    r.use_level = 100 * float(
                        r.sequence_id.number_next_actual - r.start_nm) / float(
                        r.final_nm - r.start_nm + 1)
                    if r.status == 'spent':
                        self.env.cr.execute("UPDATE dte_caf SET status = \
                        'in_use' WHERE filename = '%s'" % r.filename)
            else:
                r.use_level = 0

    @api.multi
    def action_enable(self):
        if not self.caf_file:
            raise UserError('Debe Guardar el Caf primero')

        post = base64.b64decode(self.caf_file).decode('ISO-8859-1')
        post = xmltodict.parse(post.replace(
            '<?xml version="1.0"?>', '', 1))
        result = post['AUTORIZACION']['CAF']['DA']

        self.start_nm = result['RNG']['D']
        self.final_nm = result['RNG']['H']
        self.document_type_code = result['TD']
        self.issued_date = result['FA']
        rut = 'CL' + result['RE'].replace('-', '')
        self.rut_n = rut
        if not self.sequence_id:
            raise UserError(_(
                'You should select a DTE sequence before enabling this CAF \
record'))
        elif self.rut_n != self.company_id.vat.replace('L0', 'L'):
            raise UserError(_(
                'Company vat %s should be the same that assigned company\'s \
vat: %s!') % (self.rut_n, self.company_id.vat))
        elif self.document_type_code != self.sequence_id.document_type_code:
            raise UserError(_(
                '''SII Document Type for this CAF is %s and selected sequence \
associated document type is %s. This values should be equal for DTE Invoicing \
to work properly!''') % (
                self.document_type_code, self.sequence_id.document_type_code))
        #elif self.sequence_id.number_next_actual < self.start_nm or \
        #                self.sequence_id.number_next_actual > self.final_nm:
        #    raise UserError(_(
        #        'Folio Number %s should be between %s and %s CAF \
#Authorization Interval!') % (self.sequence_id.number_next_actual,
#                             self.start_nm, self.final_nm))
        else:
            self.sequence_id.number_next_actual = self.start_nm
            self.status = 'in_use'

    @api.multi
    def action_cancel(self):
        self.status = 'cancelled'

    @api.multi
    def _get_filename(self):
        for r in self:
            r.name = r.filename

    def decode_caf(self):
        post = base64.b64decode(self.caf_file).decode('ISO-8859-1')
        post = xmltodict.parse(post.replace(
            '<?xml version="1.0"?>','', 1))
        return post


class SequenceCaf(models.Model):
    _inherit = "ir.sequence"

    document_type_id = fields.Many2one('account.document.type', 'Document Type',
        compute="_get_document_type")
    document_type_code = fields.Char('Document Type Code',
        related='document_type_id.code', readonly=True)
    is_dte = fields.Boolean('IS DTE?', related='document_type_id.dte', readonly=True)
    dte_caf_ids = fields.One2many('dte.caf', 'sequence_id', 'DTE Caf')
    qty_available = fields.Integer('Quantity Available', compute='_qty_available')
    forced_by_caf = fields.Boolean(string="Forced By CAF", default=True)
    for_delivery_guide = fields.Boolean(string="Delivery Guide", default=False)

    @api.multi
    def _get_document_type(self):
        for record in self:
            if record.for_delivery_guide:
                record.document_type_id = self.env.ref('l10n_cl_account.dc_gd_dte')
            else:
                obj = self.env['account.journal.document.type'].search(
                    [('sequence_id', '=', record.id)], limit=1)
                record.document_type_id = obj.document_type_id

    def get_qty_available(self, folio=None):
        folio = folio or self._get_folio()
        try:
            cafs = self.get_caf_files(folio)
        except:
            cafs = False
        available = 0
        folio = int(folio)
        if cafs:
            for c in cafs:
                if folio >= c.start_nm and folio <= c.final_nm:
                    available += c.final_nm - folio
                elif folio <= c.final_nm:
                    available += (c.final_nm - c.start_nm) + 1
                if folio > c.start_nm:
                    available +=1
        return available

    def _qty_available(self):
        for i in self:
            i.qty_available = i.get_qty_available()

    def _get_folio(self):
        return self.number_next_actual

    def get_caf_file(self, folio=False):
        folio = folio or self._get_folio()
        caffiles = self.get_caf_files(folio)
        if not caffiles:
            raise UserError(_('''No hay caf disponible para el documento %s folio %s. Por favor solicite suba un CAF o solicite uno en el SII.''' % (self.name, folio)))
        for caffile in caffiles:
            if int(folio) >= caffile.start_nm and int(folio) <= caffile.final_nm:
                return caffile.decode_caf()
        msg = '''No Hay caf para el documento: {}, está fuera de rango . Solicite un nuevo CAF en el sitio \
www.sii.cl'''.format(folio)
        raise UserError(_(msg))

    def get_caf_files(self, folio=None):
        '''
            Devuelvo caf actual y futuros
        '''
        folio = folio or self._get_folio()
        if not self.dte_caf_ids:
            raise UserError(_('''No hay CAFs disponibles para la secuencia de %s. Por favor suba un CAF o solicite uno en el SII.''' % (self.name)))
        cafs = self.dte_caf_ids
        sorted(cafs, key=lambda e: e.start_nm)
        result = []
        for caffile in cafs:
            if int(folio) <= caffile.final_nm:
                result.append(caffile)
        if result:
            return result
        return False

    def update_next_by_caf(self, folio=None):
        folio = folio or self._get_folio()
        menor = False
        cafs = self.get_caf_files(folio)
        if not cafs:
            raise UserError(_('No quedan CAFs para %s disponibles') % self.name)
        for c in cafs:
            if not menor or c.start_nm < menor.start_nm:
                menor = c
        if menor and int(folio) < menor.start_nm:
            self.sudo(SUPERUSER_ID).write({'number_next': menor.start_nm})

    def _next_do(self):
        number_next = self.number_next
        if self.implementation == 'standard':
            number_next = self.number_next_actual
        folio = super(SequenceCaf, self)._next_do()
        if self.forced_by_caf and self.dte_caf_ids:
            self.update_next_by_caf(folio)
            actual = self.number_next
            if self.implementation == 'standard':
                actual = self.number_next_actual
            if number_next + 1 != actual: #Fue actualizado
                number_next = actual
            folio = self.get_next_char(number_next)
        return folio
