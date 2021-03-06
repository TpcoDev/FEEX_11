# -*- coding: utf-8 -*-
import logging

import requests
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

indicators = {
    'USD': ['dolar', 'Dolares'],
    'EUR': ['euro', 'Euros'],
    'UF': ['uf', 'UFs'],
    'UTM': ['utm', 'UTMs'], }


class ResCurrency(models.Model):
    _name = "res.currency"
    _inherit = "res.currency"

    @api.model
    def update_currency(self, indic, currency_id=False):
        conf = self.env['ir.config_parameter'].sudo()
        if not currency_id:
            currency_id = self
        apikey = conf.get_param('sbif.financial.indicators.apikey')
        baseurl = conf.get_param('sbif.financial.indicators.baseurl')
        host = '%s/%s?apikey=%s&formato=json' % (baseurl, indic[1][0], apikey)
        _logger.info(host)
        r = requests.get(host)
        if r.status_code == 200:
            data_json = r.json()
            _logger.info(data_json)
            rate = float(
                data_json[indic[1][1]][0]['Valor'].replace('.', '').replace(',', '.'))
            try:
                _logger.info('moneda: base.' + indic[0])
                _logger.info('Updating %s' % (indic[1][1]))
                _logger.info(' currency: %s result: %s' % (
                    currency_id, data_json))
                currency_rate_obj = self.env['res.currency.rate']
                company_obj = self.env['res.company']
                company_ids = company_obj.search([('currency_id.name', '=', 'CLP')])
                for company_id in company_ids:
                    values = {
                        'rate': 1 / rate,
                        'company_id': company_id.id,
                        'currency_id': currency_id.id, }
                    _logger.info(values)
                    try:
                        _logger.info('Trying to create currency rate...')
                        currency_rate_obj.create(values)
                    except:
                        _logger.info('Unique name per day %s' % (indic[1][1]))
            except:
                _logger.info('could not open currency %s' % (indic[0]))

        else:
            _logger.info(
                "Currency %s not available: %s" % (indic[0], r.status_code))

    def action_update_currency(self):
        indic = [
            self.name, [indicators[self.name][0], indicators[self.name][1]]]
        self.update_currency(indic)
        _logger.info(
            'Individual function to get quotation: %s' % indic)

    @api.model
    def currency_schedule_update(self):
        for indic in indicators.items():
            try:
                currency_id = self.search([('name', '=', indic[0])])[0]
                _logger.info('indic: %s, currency: %s' % (indic[0], currency_id))
                self.update_currency(indic, currency_id)
            except:
                _logger.info('indic: %s, NOT FOUND' % indic[0])
