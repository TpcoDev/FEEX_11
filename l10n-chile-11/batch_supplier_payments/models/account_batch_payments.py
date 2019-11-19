from odoo import fields, models, api
from openerp.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountBatchPaymentsLines(models.Model):
    _name = 'account.batch.payments.line'

    batch_payment_id = fields.Many2one('account.batch.payments',
        'Payment', ondelete='cascade',
    )
    invoice_id = fields.Many2one('account.invoice', 'Invoice',
        domain=[('state', 'not in', ('draft', 'paid', 'cancelled')),
                ('type', 'in', ('in_invoice', 'in_refund'))],
        readonly = True,
    )
    partner_id = fields.Many2one('res.partner', 'Partner',
        related="invoice_id.partner_id",
        readonly = True,
    )
    balance_amount = fields.Float('Amount to Pay',
    )
    state = fields.Selection([
            ('draft', 'Draft'),
            ('open', 'Open'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled')],
            'State',
            related="invoice_id.state",
    )

    @api.constrains('invoice_id')
    def _check_invoice_unique(self):
        for rec in self:
            # Search for duplicated invoices in this list
            result = self.search([('invoice_id', '=', rec.invoice_id.id),
                                  ('batch_payment_id', '=', rec.batch_payment_id.id), ])
            if len(result) > 1:
                raise ValidationError('There are duplicated invoices in THIS \
                    list. Please check this invoice: %s' % rec.invoice_id.display_name)

            # Search for duplicated invoices in this another list
            result = self.search([('invoice_id', '=', rec.invoice_id.id),
                                  ('batch_payment_id.state', 'in', ['draft', 'wait'])])
            if len(result) > 1:
                raise ValidationError('There are duplicated invoices in ANOTHER \
                    list. Please check this invoice: %s in the list: %s (ID: %s)' % (
                    rec.invoice_id.display_name, result.mapped('batch_payment_id.display_name')[0],
                    result.mapped('batch_payment_id.id')[0]))


class AccountBatchPayments(models.Model):
    _name = 'account.batch.payments'

    date = fields.Date('Payment Date')
    journal_id = fields.Many2one('account.journal', 'Journal')
    # format_xls = el formato se debe elegir es desde el diario (por implementar)
    total_amount = fields.Float('Total', compute='_compute_total')
    line_ids = fields.One2many(
        'account.batch.payments.line', 'batch_payment_id', 'Invoices', help="Invoices to Pay", )
    payment_ids = fields.One2many(
        'account.payment', 'batch_id', 'Payments')
    state = fields.Selection(
        [('draft', 'Draft'), ('wait', 'Waiting for Approval'), ('approved', 'Approved'), ('cancelled', 'Cancelado')],
        default='draft', )

    def name_get(self):
        result = []
        for record in self:
            result.append(
                (record.id, "%s (%s)" % (record.date, record.journal_id.name)))
        return result

    @api.depends('line_ids.balance_amount')
    def _compute_total(self):
        for rec in self:
            total_amount = 0.0
            for line in rec.line_ids:
                total_amount += line.balance_amount
            rec.total_amount = total_amount

    @api.multi
    def action_wait(self):
        self.state = 'wait'

    @api.multi
    def action_approve(self):
        self.make_payments()
        self.state = 'approved'

    @api.multi
    def action_cancel(self):
        self.state = 'cancelled'

    @api.multi
    def action_draft(self):
        self.state = 'draft'


    @api.multi
    def make_payments(self):
        for line in self.line_ids:
            payment = self.env['account.payment'].create(self.get_payment_batch_vals(line))
            # payment_ids.append(payment.id)
            payment.post()
        move = payment.move_line_ids[0].move_id
        move.post()

    def get_payment_batch_vals(self, line):
        res = {
            'journal_id': self.journal_id.id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
            'payment_date': self.date,
            # 'communication': group_data['memo'],
            'invoice_ids': [(4, line.invoice_id.id, None)],
            'payment_type': 'outbound',
            'amount': line.balance_amount,
            # 'currency_id': self.currency_id.id,
            'partner_id': line.partner_id.id,
            'partner_type': 'supplier',
            'batch_id': line.batch_payment_id.id,
        }
        return res

    @api.multi
    def _check_mandatory_values(self):
        if not self.journal_id.bank_xls_format:
            raise ValidationError("Verify if the Bank XLS Format in your journal is correctly configured")
        if not self.journal_id.bank_acc_number:
            raise ValidationError("Verify if the bank account number in your journal is correctly configured")
        for line in self.line_ids:
            partner_bank = self.env["res.partner.bank"].search([('partner_id', '=', line.partner_id.id)])
            if not partner_bank:
                raise ValidationError("""Verify if the bank account number for your
                    supplier \" %s \" are correctly configured""" % line.partner_id.name)
    
    @api.multi
    def action_export_xls(self):
        """ This is the method you have to inherit with super just adding
        a new if block calling a new format method.
        Please do not override this generic format method"""
        self._check_mandatory_values()
        if self.journal_id.bank_xls_format == 'generic':
            report = self.env.ref('batch_supplier_payments.generic_report_xls')
            return report.report_action(self)

    def xls_format_generic(self):

        cols = {
            "account_1": self.journal_id.bank_acc_number,
            "bank_partner": [],
            "destination_bank": [],
            "vat": [],
            "digit": [],
            "name_partner": [],
            "amount": [],
            "n_invoice": [],
            "n_purchase_order": '',
            "type": "PRV",
            "message": [],
            "email": [],
            "account_3": [],
            "point": [],
        }

        for payment in self.payment_ids:
            cols["name_partner"].append(payment.partner_id.name)
            cols["amount"].append(payment.amount)
            cols["email"].append(payment.partner_id.email or '')
            cols["message"].append(payment.communication or '')

            partner_bank = self.env["res.partner.bank"].search([('partner_id', '=', payment.partner_id.id)])
            
            cols["destination_bank"].append(partner_bank[0].bank_id.name)
            cols["bank_partner"].append(partner_bank[0].acc_number)

            cols["type"] = "PRV"
            cols["n_invoice"].append(payment.invoice_ids[0].number or 1)
            cols["point"].append("292")
            
            vat = payment.partner_id.vat or ' '
            cols["vat"].append(vat[:-1])
            cols["digit"].append(vat[-1])

            cols["account_3"].append("")

        return cols


class BatchSupplierPayment(models.AbstractModel):
    _name = 'report.batch_supplier_payment'
    _inherit = 'report.report_xlsx.abstract'

    @staticmethod
    def generate_xlsx_report(workbook, data, payments):
        xls_header = [
            "Charge Account",
            "Destination Account",
            "Destination Bank",
            "VAT",
            "Beneficiary",
            "Total Amount",
            "Invoice Number",
            "Purchase Order Number",
            "Payment Type",
            "Addressee Message",
            "Beneficiary Email",
        ]
        # cell_format = workbook.add_format()
        cell_formats = {
            "bold": workbook.add_format({'bold': True}),
            'decimal': workbook.add_format({'num_format': '#,##0.00'}),
        }
        sheet = workbook.add_worksheet()
        cols, rows = 0, 0
        for col in xls_header:
            sheet.write(rows, cols, col, cell_formats["bold"])
            cols += 1
            sheet.set_column(rows, cols, 25)

        data = data = payments.xls_format_generic()
        rows = 1
        for i in range(len(data["message"])):

            sheet.write(rows, 0, data["account_1"])
            sheet.write(rows, 1, data["bank_partner"][i-1])
            sheet.write(rows, 2, data["destination_bank"][i-1])
            sheet.write(rows, 3, data["vat"][i-1])
            sheet.write(rows, 4, data["name_partner"][i-1])
            sheet.write(rows, 5, data["amount"][i-1], cell_formats["decimal"])
            sheet.write(rows, 6, data["n_invoice"][i-1])
            sheet.write(rows, 7, data["n_purchase_order"])
            sheet.write(rows, 8, data["type"])
            sheet.write(rows, 9, data["message"][i-1])
            sheet.write(rows, 10, data["email"][i-1])
            rows += 1