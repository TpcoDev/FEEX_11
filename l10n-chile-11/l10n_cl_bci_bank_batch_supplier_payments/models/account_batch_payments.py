# -*- coding: utf-8 -*-
from odoo import fields, models, api

import logging
_logger = logging.getLogger(__name__)

class XLSCLPayments(models.Model):
    _inherit = 'account.batch.payments'

    @api.multi
    def action_export_xls(self):
        res = super(XLSCLPayments, self).action_export_xls()

        if self.journal_id.bank_xls_format == "generic":
            return res

        elif self.journal_id.bank_xls_format == "bci":
            report = self.env.ref('l10n_cl_bci_bank_batch_supplier_payments.nomina_bci_report_xls')
            return report.report_action(self)

    def xls_format_bci(self):
            
        cols = {
            "account_1": self.journal_id.bank_acc_number,
            "bank_partner": [],
            "destination_bank": [],
            "rut": [],
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
            invoices = []
            message = []

            for invoice in payment.invoice_ids:

                doc_type = invoice.journal_document_type_id.document_type_id.name
                doc_number = str(invoice.invoice_number)

                message.append("Pago de %s nro %s" % (doc_type, doc_number))
                invoices.append(doc_number)

            invoices = " : ".join(invoices)
            message = " : ".join(message)

            cols["name_partner"].append(payment.partner_id.name)
            cols["amount"].append(payment.amount)
            cols["email"].append(payment.partner_id.email or '')

            cols["message"].append(message)

            partner_bank = self.env["res.partner.bank"].search(
                [('partner_id', '=', payment.partner_id.id)], limit=1)
            partner_bank_code = partner_bank.bank_id.sbif_code or ''
            partner_bank_acc_number = partner_bank.acc_number or ''

            cols["destination_bank"].append(partner_bank_code)
            cols["bank_partner"].append(partner_bank_acc_number)

            cols["type"] = "PRV"

            cols["n_invoice"].append(invoices)

            cols["point"].append("292")
            
            rut = payment.partner_id.vat or ' '
            cols["rut"].append(rut[:-1].replace('CL', ''))
            cols["digit"].append(rut[-1])

            cols["account_3"].append("")
        
        return cols


class BatchSupplierPaymentBciXls(models.AbstractModel):
    _name = 'report.batch_supplier_payment.bci'
    _inherit = 'report.report_xlsx.abstract'

    @staticmethod
    def generate_xlsx_report(workbook, data, payments):

        xls_header = [
            "Nº Cuenta de Cargo",
            "Nº Cuenta de Destino",
            "Banco Destino",
            "Rut Beneficiario",
            "Dig. Verif. Beneficiario",
            "Nombre Beneficiario",
            "Monto Transferencia",
            "Nro.Factura Boleta (1)",
            "Nº Orden de Compra(1)",
            "Tipo de Pago(2)",
            "Mensaje Destinatario (3)",
            "Email Destinatario(3)",
            "Cuenta Destino inscrita como(4)",
            "."
        ]

        cell_format = {
            'decimal': workbook.add_format({'num_format': '#,##0.00'}),
        }

        sheet = workbook.add_worksheet()
        cols, rows = 0, 0

        for col in xls_header:
            if cols < 7 or cols == 9:
                sheet.write(
                    rows, cols, col, 
                    workbook.add_format({
                        'bold': True, 
                        "font_color": "white",
                        "bg_color": "#dd0806"
                    })
                )
            elif cols < 14:
                sheet.write(
                    rows, cols, col, 
                    workbook.add_format({
                        'bold': True, 
                        "font_color": "white",
                        "bg_color": "#548dd4"
                    })
                )

            sheet.set_column(rows, cols, 25)

            cols += 1
        
        data = payments.xls_format_bci()
        rows = 1
        for i in range(len(data["message"])):

            sheet.write_string(rows, 0, data["account_1"])
            sheet.write_string(rows, 1, data["bank_partner"][i-1])
            sheet.write_string(rows, 2, data["destination_bank"][i-1])
            sheet.write_string(rows, 3, data["rut"][i-1])
            sheet.write_string(rows, 4, data["digit"][i-1])
            sheet.write_string(rows, 5, data["name_partner"][i-1])
            sheet.write_number(rows, 6, data["amount"][i-1], workbook.add_format({'num_format': '#,##0.00'}))
            # Decimal
            sheet.write_string(rows, 7, data["n_invoice"][i-1])
            sheet.write_string(rows, 8, data["n_purchase_order"])
            sheet.write_string(rows, 9, data["type"])
            sheet.write_string(rows, 10, data["message"][i-1])
            sheet.write_string(rows, 11, data["email"][i-1])
            sheet.write_string(rows, 12, data["account_3"][i-1])
            sheet.write_string(rows, 13, data["point"][i-1])

            rows += 1