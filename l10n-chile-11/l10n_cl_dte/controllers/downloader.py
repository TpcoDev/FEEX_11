import logging

from odoo import api, http, models
from odoo.addons.web.controllers.main import (content_disposition,
                                              serialize_exception)
from odoo.http import request

_logger = logging.getLogger(__name__)


class Binary1(http.Controller):

    @http.route('/web/binary/download_document', type='http', auth="public")
    @serialize_exception
    def download_document(
            self, model, field, id, filename=None, filetype='xml', **kw):
        """
        :param str filename: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        """
        Model = request.registry[model]
        _logger.info('Model =========================111: %s' % Model)
        cr, uid, context = request.cr, request.uid, request.context
        fields = [field]
        res = Model.read(cr, uid, [int(id)], fields, context)[0]
        filecontent = res.get(field)
        print(filecontent)
        _logger.info('Model: %s' % Model)
        if not filecontent:
            return request.not_found()
        else:
            if not filename:
                filename = '%s_%s' % (model.replace('.', '_'), id)
            headers = [
                ('Content-Type', 'application/%s' % filetype),
                ('Content-Disposition', content_disposition(filename)),
                ('charset', 'utf-8'), ]
            return request.make_response(
                    filecontent, headers=headers, cookies=None)


class Binary2(http.Controller):

    def document(self, filename, filecontent):
        if not filecontent:
            return request.not_found()
        headers = [
            ('Content-Type', 'application/xml'),
            ('Content-Disposition', content_disposition(filename)),
            ('charset', 'utf-8'),
        ]
        return request.make_response(
                filecontent, headers=headers, cookies=None)

    @http.route(["/download/xml/<kind>/<model('account.invoice'):document_id>"], type='http', auth='user')
    @serialize_exception
    def download_document(self, kind, document_id, **post):
        _logger.info('download doc: %s' % kind)
        filename = ('%s.xml' % document_id.display_name).replace(' ', '_')
        if kind == 'dte':
            file_content = document_id.sii_xml_dte
            filename = 'DTE_' + filename
        elif kind in ['xml_exchange', 'invoice']:
            file_content = document_id.sii_xml_request.xml_envio
        else:
            return 'This kind of document not implemented: %s' % kind
        return self.document(filename, file_content)

    @http.route(["/download/xml/cf/<model('account.move.consumo_folios'):rec_id>"], type='http', auth='user')
    @serialize_exception
    def download_cf(self, rec_id, **post):
        filename = ('CF_%s.xml' % rec_id.name).replace(' ', '_')
        filecontent = rec_id.sii_xml_request.xml_envio
        return self.document(filename, filecontent)

    @http.route(["/download/xml/libro/<model('account.move.book'):rec_id>"], type='http', auth='user')
    @serialize_exception
    def download_book(self, rec_id, **post):
        filename = ('Libro_%s.xml' % rec_id.name).replace(' ', '_')
        filecontent = rec_id.sii_xml_request.xml_envio
        return self.document(filename, filecontent)
