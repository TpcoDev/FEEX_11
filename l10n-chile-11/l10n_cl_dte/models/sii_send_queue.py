import ast
import logging
from datetime import datetime
from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF

_logger = logging.getLogger(__name__)


class SendQueue(models.Model):
    _name = "sii.send_queue"

    invoice_ids = fields.One2many(
        'account.invoice', 'send_queue_id', string='Invoices'
    )
    model_selection = fields.Selection(
        [('account.invoice', 'Invoices'), ('stock.picking', 'Pickings'), ],
        default='account.invoice', string='Refers To', )
    doc_ids = fields.Char(
            string="Id Documentos", )
    model = fields.Char(
            string="Model destino", )
    user_id = fields.Many2one(
            'res.users', )
    tipo_trabajo = fields.Selection(
        [('pasivo', 'pasivo'), ('envio', 'Envío'), ('consulta', 'Consulta')], string="Job Type")
    active = fields.Boolean(
            string="Active",
            default=True, )
    n_atencion = fields.Char(
            string="Número atención", )
    date_time = fields.Datetime(
            string='Auto Envío al SII', )
    send_email = fields.Boolean(
            string="Auto Enviar Email",
            default=False, )

    @api.multi
    def name_get(self):
        result = []
        for r in self:
            try:
                name = 'Envio: %s, para enviar el: %s. VER COLA' % (r.tipo_trabajo, fields.Datetime.to_string(
                    fields.Datetime.context_timestamp(self, fields.Datetime.from_string(r.date_time))))
            except AssertionError:
                name = 'Envio: %s, para enviar (datetime). VER COLA' % r.tipo_trabajo
                _logger.info('el registro está desactualizado (antiguo o no implementado en la cola)')
            result.append((r.id, name))
        return result

    def send_template_email(self, doc):
        atts = [doc._create_attachment().id]
        # este reemplazar por la version local...(no manda el pdf) se soluciona directamente
        # con el modulo l10n_cl_docsonline_print
        # atts.append(doc.get_pdf_docsonline(doc.sii_xml_exchange).id)
        template = self.env.ref('l10n_cl_dte.email_template_edi_invoice', False)
        if template.attachment_ids:
            for a in template.attachment_ids:
                atts.append(a.id)
        mail_id = template.send_mail(
            doc.id,
            force_send=True,
            email_values={'attachment_ids': atts})
        _logger.info('mass email from send queue.... mail_id: %s' % mail_id)

    def _send_condition(self):
        return (self.active and self.tipo_trabajo == 'pasivo' and
                self.date_time and datetime.now() >= datetime.strptime(self.date_time, DTF)) or \
                self.tipo_trabajo == 'envio'

    def _process_job_type(self):
        _logger.info('Entrando en proceso de ejecución de cola de envío')
        if self.model_selection == 'account.invoice':
            docs = self.invoice_ids
        else:
            docs = self.picking_ids
        # docs = self.env[self.model_selection].browse(ast.literal_eval(self.doc_ids))
        if self.tipo_trabajo in {'pasivo', 'envio'}:
            if self._send_condition() and docs[0].sii_result not in {
                'Aceptado', 'Enviado', 'Proceso', 'Reparo', 'Rechazado'}:
                try:
                    envio_id = docs.do_dte_send()
                    if envio_id:
                        self.tipo_trabajo = 'consulta'
                except Exception as error:
                    _logger.warning('Error en Envío %s' % error)
                docs.get_sii_result()
            return
        else:  # consulta
            if True:
                for doc in docs:
                    doc.ask_for_dte_status()
                    if self.send_email and doc.sii_result in {'Aceptado', 'Proceso'}:
                        if self.send_template_email(doc):
                            _logger.info('pasa por acá después')
                            doc.sii_result = 'Aceptado'
                            self.active = False
            else:  # except Exception as e:
                _logger.warning("Error en Consulta")
                _logger.warning(str(e))

    @api.model
    def _cron_process_queue(self):
        ids = self.search([('active', '=', True)])
        if ids:
            for c in ids:
                c._process_job_type()

    @api.multi
    def cron_process_queue(self):
        for record in self:
            if record.active:
                record._cron_process_queue()
