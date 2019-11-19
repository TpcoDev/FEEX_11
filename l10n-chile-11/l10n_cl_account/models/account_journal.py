##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _name = 'account.journal'
    _inherit = ['account.journal', 'l10n.cl.localization.filter']

    _point_of_sale_types_selection = [
        ('', 'Undefined'),
        ('manual', 'Manual'),
        ('preprinted', 'Preprinted'),
        ('online', 'Online'),
    ]
    point_of_sale_type = fields.Selection(
        _point_of_sale_types_selection,
        'Point Of Sale Type',
        default='manual', )
    bank_sbif = fields.Char(
        related='bank_account_id.bank_id.sbif_code', )
    point_of_sale_number = fields.Integer('Point Of Sale Number', help='This number is needed only if provided by SII.')
    point_of_sale_name = fields.Char('Point Of Sale Name', help='This is the name that you want to assign to your \
point of sale. It is not mandatory.')
    point_of_sale_cashier_code = fields.Char('Point Of Sale Cashier Code', help='This code is suitable to be used when \
you have more than one cashier in your point of sale.')
    no_documents = fields.Boolean(compute='_compute_documents_and_sequence')
    no_sequence = fields.Boolean(compute='_compute_documents_and_sequence')
    no_caf = fields.Boolean(compute='_compute_documents_and_sequence')

    @api.depends('type', 'journal_document_type_ids')
    def _compute_documents_and_sequence(self):
        for record in self:
            if record.type != 'sale':
                record.no_documents = record.no_sequence = record.no_caf = False
                return
            document_qty = len(record.journal_document_type_ids)
            if document_qty == 0:
                record.no_documents = True
                record.no_sequence = record.no_caf = False
            else:
                record.no_documents = record.no_sequence = record.no_caf = False
                sequences = cafs_used = document_qty
                for document in record.journal_document_type_ids:
                    if not document.sequence_id:
                        sequences -= 1
                    else:
                        caf_in_use = 0
                        try:
                            for caf in document.sequence_id.dte_caf_ids:
                                if caf.status == 'in_use':
                                    caf_in_use = 1
                                    break
                        except:
                            _logger.info('Exception during caf in use check')
                        if caf_in_use == 0:
                            cafs_used -= 1
                if sequences < document_qty:
                    record.no_sequence = True
                if cafs_used < document_qty and record.point_of_sale_type == 'online':
                    record.no_caf = True

    @api.onchange('name', 'type')
    def _default_point_of_sale_name(self):
        if self.type == 'sale' and not self.point_of_sale_name:
            self.point_of_sale_name = self.name

    def set_bank_account(self, acc_number, bank_id=None):
        return super(AccountJournal, self.with_context(
            default_sbif_code=self.bank_sbif)).set_bank_account(
            acc_number, bank_id=bank_id)

    @api.onchange(
        'type', 'localization', 'use_documents', 'point_of_sale_type', 'sequence_id')
    def change_to_set_name_and_code(self):
        """
        We only set name and code if not sequence_id
        """
        if not self._context.get('set_point_of_sale_name'):
            return {}
        if self.type == 'sale' and not self.sequence_id:
            self.name, self.code = self.get_name_and_code()

    @api.multi
    def get_name_and_code_suffix(self):
        self.ensure_one()
        point_of_sale_type = {
            'manual': 'Manual',
            'preprinted': 'Preimpresa',
            'online': 'Online',
            'electronic': 'Electronica',
        }
        name = point_of_sale_type[self.point_of_sale_type]
        return name

    @api.multi
    def get_name_and_code(self):
        self.ensure_one()
        point_of_sale_number = 0
        name = 'Ventas'
        sufix = self.get_name_and_code_suffix()
        if sufix:
            name += ' ' + sufix
        if point_of_sale_number:
            name += ' %04d' % point_of_sale_number
        code = 'V%04d' % point_of_sale_number
        return name, code

    @api.multi
    def get_journal_letter(self, counterpart_partner=False):
        """Function to be inherited by others"""
        self.ensure_one()
        return self._get_journal_letter(
            journal_type=self.type,
            company=self.company_id,
            counterpart_partner=counterpart_partner)

    @api.model
    def _get_journal_letter(
            self, journal_type, company, counterpart_partner=False):
        taxpayer_type_id = company.taxpayer_type_id
        if journal_type == 'sale':
            taxpayer_field = 'issuer_ids'
        elif journal_type == 'purchase':
            taxpayer_field = 'receptor_ids'
        else:
            raise UserError('Letters not implemented for journal type %s' % (
                journal_type))
        letters = self.env['account.document.letter'].search([
            '|', (taxpayer_field, '=', taxpayer_type_id.id),
            (taxpayer_field, '=', False)])

        if counterpart_partner:
            counterpart_resp = counterpart_partner.taxpayer_type_id
            if journal_type == 'sale':
                letters = letters.filtered(
                    lambda x: not x.receptor_ids or
                    counterpart_resp in x.receptor_ids)
            else:
                letters = letters.filtered(
                    lambda x: not x.issuer_ids or
                    counterpart_resp in x.issuer_ids)
        return letters

    @api.multi
    def _get_excluded_document_types(self,vals=False):
        _logger.info("\n\n\n  vals: %s  \n\n\n" % vals)
        if vals:
            if_zf = [] if vals['free_tax_zone'] else [901, 906, 907]
            if_lf = [] if vals['settlement_invoice'] else [40, 43]
            if_tr = [] if vals['weird_documents'] else [29, 108, 914, 911, 904, 905]
            if_exp = [] if vals['dte_export'] else [110, 111, 112]
            # if_pr = [] if self.purchase_invoices else [45, 46]
            if_na = [] if self.excempt_documents else [32, 34]
            excluding_list = if_zf + if_lf + if_tr + if_exp + if_na
            return excluding_list
        else:
            return []

    @api.multi
    def _update_journal_document_types(self,vals=False):
        """
        It creates, for journal of type:
            * sale: documents of internal types 'invoice', 'debit_note',
                'credit_note' if there is a match for document letter
        TODO complete here
        """
        self.ensure_one()
        if self.localization != 'chile':
            return super(AccountJournal, self)._update_journal_document_types()

        if not self.use_documents:
            return True

        letters = self.get_journal_letter()

        other_purchase_internal_types = ['in_document', 'ticket']

        if self.type in ['purchase', 'sale']:
            internal_types = ['invoice', 'debit_note', 'credit_note']
            # for purchase we add other documents with letter
            if self.type == 'purchase':
                internal_types += other_purchase_internal_types
        else:
            raise UserError(_('Type %s not implemented yet' % self.type))

        domain = []

        if vals['dte_register'] and vals['non_dte_register']:
            pass
        elif vals['dte_register']:
            domain = [('dte', '=', True)]
        else:
            domain = [('dte', '=', False)]
        
        domain.extend(
            [('internal_type', 'in', internal_types),
            ('localization', '=', self.localization),
            '|', ('document_letter_id', 'in', letters.ids),
            ('document_letter_id', '=', False),
            ('code','not in', self._get_excluded_document_types(vals)),], )

        document_types = self.env['account.document.type'].search(domain)

        _logger.info("\n\n\n 1)cantidad de documentos: %s \n\n\n" % len(document_types))
        _logger.info("\n\n\n 1)codigos de documentos: %s \n\n\n" % document_types.mapped('code'))
        _logger.info("\n\n\n mapped: %s \n\n\n" % document_types)
        _logger.info("\n\n\n mapped: %s \n\n\n" % self.mapped('journal_document_type_ids.document_type_id'))

        document_types = document_types - self.mapped(
            'journal_document_type_ids.document_type_id')

        _logger.info("\n\n\n 2)cantidad de documentos: %s \n\n\n" % len(document_types))
        _logger.info("\n\n\n 2)codigos de documentos: %s \n\n\n" % document_types.mapped('code'))

        sequence = 10
        for document_type in document_types:
            _logger.info("\n\n\n document_type: %s \n\n\n" % document_type)
            sequence_id = False
            if self.type == 'sale':
                if (
                        document_type.internal_type in [
                        'debit_note', 'credit_note'] and
                        self.document_sequence_type == 'same_sequence'
                ):
                    journal_document = self.journal_document_type_ids.search([
                        ('document_type_id.document_letter_id', '=',
                            document_type.document_letter_id.id),
                        ('journal_id', '=', self.id)], limit=1)
                    sequence_id = journal_document.sequence_id.id
                elif document_type.dte:
                    try:
                        sequence_id = self.env['dte.caf'].search([
                            ('document_type_code', '=', document_type.code),
                            ('status', '=', 'in_use'),
                            ('company_id', '=', self.env.user.company_id.id)
                        ], limit=1).sequence_id.id
                    except:
                        # the object dte.caf is not defined because the module may be not installed
                        _logger.info('Exception while looking for CAF object')
                        sequence_id = False
            if not sequence_id:
                sequence_id = self.env['ir.sequence'].create(
                    document_type.get_document_sequence_vals(self)).id
            self.journal_document_type_ids.create({
                'document_type_id': document_type.id,
                'sequence_id': sequence_id,
                'journal_id': self.id,
                'sequence': sequence, })
            sequence += 10
