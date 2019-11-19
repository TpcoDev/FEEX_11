
[![License: AGPL-3](https://img.shields.io/badge/licence-AGPL--3-blue.png)](http://www.gnu.org/licenses/agpl-3.0-standalone.html)
   

# Chilean localization for Odoo

## Highlights

###### Provide compatibility with chilean regulations.

Includes:
- Commercial tax documents used in Chile
- Correct and legal identification of clients and suppliers and type of taxpayers
- Correlation and correct numbering of documents
- Electronic billing
- Easier document exchange
- Legal accounting reports (WIP)
- Ease to get billing data for customers.
- Ease to hand over invoices using Factoring

###### Seeks to achieve compatibility between localizations in a multicompany database (WIP)

To fulfill this:
- Based on other developements: (Ingeniería ADHOC and OCA) extending these modules.


### Dependencies

Check [oca_depenencies.txt](oca_dependencies.txt)

### Available addons

|addon                           |version    |summary|
|--------------------------------|-----------|-------|
|[base_state_ubication](base_state_ubication/)|11.0.3.0.0|Add parent state to standard state and transform the states on recursive ubication.|
|[batch_supplier_payments](batch_supplier_payments/)|11.0.1.0.0|Basement for bank payment mandates. We developed this instead of OCA's bank_payment_mandates, because of the better interfase for high volume of invoices to be paid.|
|[l10n_cl_account](l10n_cl_account/)|11.0.1.0.0|Accounting base for chile (doc types, etc)|
|[l10n_cl_account_vat_ledger](l10n_cl_account_vat_ledger/)|11.0.1.0.0|Sale/Purchase/Fees monthly report in XLS and PDF|
|[l10n_cl_account_voucher_report](l10n_cl_account_voucher_report/)|11.0.1.0.0|Allows to print account voucher as a proof for a payment (or any other account entry) to have been entered. Used instead of a receipt in Chile|
|[l10n_cl_banks_sbif](l10n_cl_banks_sbif/)|11.0.1.0.0|Official Bank Coding|
|[l10n_cl_base](l10n_cl_base/)|11.0.1.0.1|Localization Installation Wizard|
|[l10n_cl_bci_bank_batch_supplier_payments](l10n_cl_bci_bank_batch_supplier_payments/)|11.0.1.0.1|batch_supplier_payments must be installed - delivers an xls file to instruct BCI bank to make payments to suppliers (or employees). Performs only one bank entry and only one account entry for all the payments.|
|[l10n_cl_chart](l10n_cl_chart/)|11.0.1.0.0|Suggested Chart of Account (based on SVS)|
|[l10n_cl_clean_doc_number](l10n_cl_clean_doc_number/)|11.0.1.0.0|Clean numbers and transmission data for cancelled invoices|
|[l10n_cl_counties](l10n_cl_counties/)|11.0.1.0.0|Add the official regions and counties for Chile|
|[l10n_cl_docsonline_factoring](l10n_cl_docsonline_factoring/)|11.0.1.0.0|Provides factoring connection through [DocumentosOnline](https://www.documentsonline.cl)|
|[l10n_cl_docsonline_partner](l10n_cl_docsonline_partner/)|11.0.1.0.0|Provides invoicing info for customers from [DocumentosOnline](https://www.documentsonline.cl)|
|[l10n_cl_docsonline_print](l10n_cl_docsonline_print/)|11.0.1.0.0|Provides prettier invoices print and a common transmission point from [DocumentosOnline](https://www.documentsonline.cl) (WIP: premium backup service)|
|[l10n_cl_dte](l10n_cl_dte/)|11.0.5.0.0|XML forming, check and Webservice connections to DTE Services|
|[l10n_cl_dte_caf](l10n_cl_dte_caf/)|11.0.1.0.0|Electronic invoice stamp authorization|
|[l10n_cl_dte_exportacion](l10n_cl_dte_exportacion/)|11.0.1.0.0|Exports Electronic invoice. This is a refactored fork from third parties, to make exports invoice|
|[l10n_cl_dte_sale_order_ref](l10n_cl_dte_sale_order_ref/)|11.0.1.0.0|Allows to create a cross reference to customers purchase order and or to sale order in the invoice_reference module and in the XML invoiceExports Electronic invoice.|
|[l10n_cl_eight_columns](l10n_cl_eight_columns/)|11.0.1.0.0|Legal balance sheet with eight columns. Required by SII for yearly tax balances.|
|[l10n_cl_hide_refund_menu](l10n_cl_hide_refund_menu/)|11.0.1.0.0|Hides the refunds menu, in order to not get the users confused when they see de sales and purchase. Works in conjuction with l10n_cl_invoice_tree_view|
|[l10n_cl_import_bank_statement_line](l10n_cl_import_bank_statement_line/)|11.0.1.0.0|Refactored from third parties adds new banks to the xls mask to import bank statements|
|[l10n_cl_invoice_tree_view](l10n_cl_invoice_tree_view/)|11.0.1.0.0|Shows invoices and refunds in the same tree view, and put signed amounts in refunds so that you can see a correct addition of sales and purchase documents.|
|[l10n_cl_dte_localization_filter](l10n_cl_dte_localization_filter/)|--|[WIP] to filter attributes, methods and views in multicompany environment|
|[l10n_cl_monetary_correction](l10n_cl_monetary_correction/)|--|[WIP] allows to calculate monetary correction to assets, and other kind of monetary corrections in the future. Intended for annual correction (not monthly by now).|
|[l10n_cl_dte_financial_indicators](l10n_cl_dte_financial_indicators/)|11.0.1.0.0|Official connection to update currencies an indexes from Chile (UF, UTM, Dollar and Euro)|
|[l10n_cl_partner](l10n_cl_partner/)|11.0.1.2.0|Partner data (identification and tax payer types), and views. Validation of data|
|[l10n_cl_partner_activities](l10n_cl_partner_activities/)|11.0.1.0.0|Business official economic activities from SII and optional activity description|
|[user_signature_key](user_signature_key/)|11.0.1.0.0|This module can be used outside the localization and can store a pk12 signature for each user. Used to sign electronic documents|

### License:

Check [LICENSE](LICENSE)

### Credits

Check Credits or collaborations in each module.

#### Author

Blanco Martín & Asociados


[![Logo](https://blancomartin.cl/logo.png)](https://blancomartin.cl)

#### Maintainer

This repository is mantained by Blanco Martín & Asociados

#### Contributors

* BMyA Development Task Force: <dev@bmya.cl>
* Daniel Blanco <daniel@bmya.cl>

Note: see the contributions to each module in its own README.rst file

#### Sponsors

[![Logo](https://blancomartin.cl/logo.png)](https://blancomartin.cl) 
[![Logo](https://www.documentosonline.cl/logo.png)](https://www.documentsonline.cl) 
[![Logo](https://www.netquest.com/hubfs/Basic-icons/logo-ntq-home-blue.svg?t=1528466608764)](https://www.netquest.com)
