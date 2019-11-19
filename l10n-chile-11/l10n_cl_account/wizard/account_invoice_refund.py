# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.tools.translate import _


class AccountInvoiceRefund(models.TransientModel):
    """Refund Documents"""
    _name = 'account.invoice.refund'
    _inherit = ['account.invoice.refund', 'l10n.cl.localization.filter']

    # todo: improve the domain (search only in journal)
    document_type_id = fields.Many2one(
        'account.document.type',
        string="Document Type",
        domain=[
            ('internal_type', 'in', ['debit_note', 'credit_note']),
            ('dte', '=', True),
            ('localization', '=', 'chile'), ])
    filter_refund_cl = fields.Selection(
        [
            ('1', '1. Anula Documento de Referencia'),
            ('2', '2. Corrige texto Documento Referencia'),
            ('3', '3. Corrige montos'),
        ],
        default='1',
        string='Refund Method',
        help='Refund base on this type. You can not Modify and Cancel if the invoice is already reconciled', )

    @api.multi
    def compute_refund(self, mode='1'):
        if self.env.user.company_id.localization != 'chile':
            return super(AccountInvoiceRefund, self).compute_refund(mode)
        inv_obj = self.env['account.invoice']
        context = dict(self._context or {})
        xml_id = False
        for form in self:
            created_inv = []
            date = False
            description = False
            refund_type_id = form.document_type_id
            for inv in inv_obj.browse(context.get('active_ids')):
                if inv.state in ['draft', 'proforma2', 'cancel']:
                    raise UserError(_('Cannot refund draft/proforma/cancelled invoice.'))
                if inv.reconciled and inv.amount_total > 0:
                    raise UserError(_(
                        'Cannot refund invoice which is already reconciled, invoice should be unreconciled first. \
You can only refund this invoice.'))

                date = form.date_invoice or False
                description = '%s (%s)' % (form.description or inv.name, inv.display_name)
                rectification_type = form.document_type_id.internal_type
                if inv.type == 'out_invoice':
                    refund_type = 'out_refund' if rectification_type == 'credit_note' else 'out_invoice'
                elif inv.type == 'out_refund':
                    refund_type = 'out_invoice'
                elif inv.type == 'in_invoice':
                    refund_type = 'in_refund' if rectification_type == 'credit_note' else 'in_invoice'
                else:  # if inv.type == 'in_refund':
                    refund_type = 'in_invoice' if rectification_type == 'debit_note' else 'in_refund'
                document_type = self.env['account.journal.document.type'].search(
                    [('document_type_id.code', '=', self.document_type_id.code),
                     ('journal_id', '=', inv.journal_id.id), ], limit=1, )
                if mode in {'2', '3'}:
                    invoice = inv.read(inv_obj._get_refund_modify_read_fields())
                    invoice = invoice[0]
                    del invoice['id']
                    prod = self.env['product.product'].search(
                        [('product_tmpl_id', '=', self.env.ref(
                            'l10n_cl_account.cn_correct').id), ])
                    account = inv.invoice_line_ids.get_invoice_line_account(
                        inv.type, prod, inv.fiscal_position_id, inv.company_id)
                    if not account.id:
                        if rectification_type == 'credit_note':
                            account = inv.journal_id.default_debit_account_id
                        else:
                            account = inv.journal_id.default_credit_account_id
                    if not account.id:
                        raise UserError('You must configure default account in journals')
                    if mode == '2':
                        invoice_lines = [[0, 0, {
                            'product_id': prod.id,
                            'uom_id': prod.uom_id.id,
                            'account_id': account.id,
                            'name': 'Donde dice:    debe decir:',
                            'quantity': 0,
                            'price_unit': 0, }, ], ]
                    else:
                        invoice_lines = [(5, )]
                    references = [[0, 0, {
                        'origin': int(inv.invoice_number),
                        'reference_doc_type': inv.document_type_id.id,
                        'reference_doc_code': mode,
                        'reason': description,
                        'date': inv.date_invoice, }, ], ]
                    invoice.update({
                        'date_invoice': date,
                        'state': 'draft',
                        'number': False,
                        'date': date,
                        'name': description,
                        'origin': inv.display_name,
                        'fiscal_position_id': inv.fiscal_position_id.id,
                        'type': refund_type,
                        'journal_document_type_id': document_type.id,
                        'invoice_turn': inv.invoice_turn.id,
                        'reference_ids': references,
                        'invoice_line_ids': invoice_lines,
                        'tax_line_ids': False,
                        'refund_invoice_id': inv.id,
                    })
                    for field in inv_obj._get_refund_common_fields():
                        if inv_obj._fields[field].type == 'many2one':
                            invoice[field] = invoice[field] and invoice[field][0]
                        else:
                            invoice[field] = invoice[field] or False
                    refund = inv_obj.create(invoice)
                    if refund.payment_term_id.id:
                        refund._onchange_payment_term_date_invoice()
                if mode in {'1', '3'}:
                    refund = inv.refund(
                        form.date_invoice, date, description, inv.journal_id.id, mode)
                    # document_type=self.document_type_id.code, mode=mode)
                refund.origin = inv.display_name
                refund.journal_id = inv.journal_id
                refund.type = refund_type
                created_inv.append(refund.id)
                xml_id = (inv.type in ['out_refund', 'out_invoice']) and \
                    'action_invoice_tree1' or (inv.type in ['in_refund', 'in_invoice']) and \
                    'action_invoice_tree2'
                subject = self.document_type_id.name
                body = description
                refund.message_post(body=body, subject=subject)
        if xml_id:
            result = self.env.ref('account.%s' % xml_id).read()[0]
            invoice_domain = safe_eval(result['domain'])
            refund.journal_document_type_id = document_type
            invoice_domain.append(('id', 'in', created_inv))
            result['domain'] = invoice_domain
            return result
        return True

    @api.multi
    def invoice_refund(self):
        localization = self.env.user.company_id.localization
        if localization == 'chile':
            data_refund = self.read(['filter_refund_cl'])[0]['filter_refund_cl']
            return self.compute_refund(data_refund)
        else:
            return super(AccountInvoiceRefund, self).invoice_refund()
