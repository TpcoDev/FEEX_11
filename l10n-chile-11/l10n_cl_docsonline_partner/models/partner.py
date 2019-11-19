# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
import json
import logging
from itertools import compress

import requests
from odoo import _, api, fields, models
from odoo.exceptions import Warning as UserError

_logger = logging.getLogger(__name__)
tax_resp_category = {u'1': u'res_IVARI',  u'2': u'res_BH', u'ND': u'res_IVARI'}
controlled_fields = ['name', 'street', 'email', 'activity_description']


class PartnerDataSII(models.Model):
    _inherit = 'res.partner'

    backup_name = fields.Char('Backup Name')

    def press_to_update(self):
        msg = u'Debe existir el RUT para utilizar la actualización desde www.documentosonline.cl'
        _logger.info('main id number: %s, name: %s' % (self.main_id_number, self.name))
        try:
            rut_input = self.main_id_number.replace('.', '')
            _logger.info('rut input (try) %s' % rut_input)
            if rut_input == 0:
                raise UserError(msg)
        except AttributeError:
            rut_input = self.name.replace('.', '')
            if 'name' in controlled_fields:
                try:
                    controlled_fields.remove('name')
                except ValueError:
                    pass
            _logger.info('rut input (except) %s' % rut_input)
            if rut_input == 0:
                raise UserError(msg)
        self._get_data_from_docsonline(rut_input)

    def _process_dol_data(self, partner_values, rut):
        list_partner_data = []
        address_type = {
            'DOMICILIO': 'contact',
            'SUCURSAL': 'other',
        }
        if self.parent_id:
            type_address = 'SUCURSAL'
        else:
            type_address = 'DOMICILIO'
        partner_odoo_data = {}
        activities_list = []
        new_activities = []
        for data in partner_values:
            if 'razon_social' in data:
                partner_odoo_data['name'] = self._capital_preferences(data['razon_social'])
            if 'dv' in data:
                partner_odoo_data['main_id_number'] = '%s-%s' % (rut, data['dv'])
            if 'tipo' in data:
                # es dirección
                if data['tipo'] == type_address and 'type' not in partner_odoo_data:
                    partner_odoo_data['type'] = address_type[data['tipo']]
                    partner_odoo_data['street'] = self._capital_preferences(data['calle'] + ' ' + data['numero'])
                    if data['depto'] != '':
                        partner_odoo_data['street2'] = 'Of. ' + self._capital_preferences(data['depto'])
                        partner_odoo_data['street2'] = 'Of. ' + self._capital_preferences(data['depto'])
                        if data['bloque'] != '':
                            partner_odoo_data['street2'] += ' Bloque ' + self._capital_preferences(data['bloque'])
                    else:
                        if data['bloque'] != '':
                            partner_odoo_data['street2'] = 'Bloque ' + self._capital_preferences(data['bloque'])
                    if 'comuna' in data:
                        if True:  # try
                            location_id = self._get_partner_location_id(data['comuna'])
                            _logger.info('location id: {}'.format(location_id))
                            if location_id:
                                partner_odoo_data['state_id'] = location_id.state_id.id
                                partner_odoo_data['country_id'] = location_id.country_id.id
                                partner_odoo_data['city_id'] = location_id.id
                                partner_odoo_data['city'] = location_id.name
                        else:  # except KeyError:
                            _logger.warning('###### ---- could not get location id info from DocsOnline')
            if 'acteco_val' in data:
                new_activity = False if 'acteco_new' not in data else True
                if 'activity_description' not in partner_odoo_data:  # todavia no se determinó la glosa del giro
                    partner_odoo_data['activity_description'] = self._create_or_search_activity_description(
                        self._capital_preferences(data['acteco_val'])).id
                try:
                    acteco = self._get_partner_turn_id(data['acteco_key'], new_activity)
                    _logger.info('Actividad economica: %s' % acteco[0].id)
                    activities_list.append(acteco[0].id)
                    new_activities.append(new_activity)
                    _logger.info('############ ---- activities: %s' % activities_list)
                    _logger.info('############ ---- tax categ: %s' % acteco[0].tax_category)
                    try:
                        partner_odoo_data['taxpayer_type_id'] = self.env.ref(
                            'l10n_cl_account.%s' % tax_resp_category[acteco[0].tax_category]).id
                    except:
                        _logger.warning(
                            'tax category could not be properly selected')
                        self.taxpayer_type_id = self.env.ref(
                            'l10n_cl_account.%s' % tax_resp_category[acteco[0].tax_category]).id
                except:
                    _logger.warning('could not get activity from DocsOnline')
            if 'mail_intercambio' in data:
                partner_odoo_data['dte_email'] = data['mail_intercambio']
                # todo: agregar fecha resolucion y autorizacion si es que interesa el dato
        activities_list1 = list(compress(activities_list, new_activities))
        if len(activities_list1) > 0:
            activities_list = activities_list1
        partner_odoo_data['partner_activities_ids'] = [(6, 0, activities_list)]
        _logger.info('partner_odoo_data %s' % partner_odoo_data)
        list_partner_data.append(partner_odoo_data)
        return list_partner_data

    def _get_docsonline_data(self):
        conf = self.env['ir.config_parameter'].sudo()
        docsonline_data = {
            'url': conf.get_param('docsonline.url'),
            'token': conf.get_param('docsonline.token'), }
        for f in controlled_fields:
            docsonline_data['replace_%s' % f] = conf.get_param(
                'docsonline.replace_%s' % f) in [
                'True', 'true', '1', 'Verdadero', 'verdadero']
        return docsonline_data

    def _get_partner_turn_id(self, acteco_key, new_activity=False):
        _logger.info('partner_activities_ids: %s' % acteco_key)
        act_obj = self.env['partner.activities']
        act_record = act_obj.search([('code', '=', acteco_key), ('new_activity', '=', new_activity)])
        return act_record

    def _create_or_search_activity_description(self, activity_description):
        _logger.info('activity_description: %s' % activity_description)
        act_desc_obj = self.env['sii.activity.description']
        act_record = act_desc_obj.search([('name', '=', activity_description)])
        if not act_record:
            act_record = act_desc_obj.create({
                'name': activity_description,
                'vat_affected': 'SI',  # asume por defecto
                'active': True, })
        return act_record

    def _capital_preferences(self, value):
        return value.title()

    def _get_partner_location_id(self, comuna_id):
        try:
            return self.env.ref(
                'l10n_cl_counties.CL%s' % comuna_id)
        except:
            _logger.info('county code failed. looking by name: %s' % comuna_id.title())
            try:
                return self.env['res.city'].search([('name', '=', comuna_id.title())])[0]
            except:
                return False

    @api.multi
    def call_wizard(self, partner_values):
        self.ensure_one()

        docsonline_data = self._get_docsonline_data()
        host = docsonline_data['url']
        headers = {
            'Authorization': 'Basic %s' % docsonline_data['token'],
            'Accept-Encoding': 'gzip, deflate, identity',
            'Accept': '*/*',
            'User-Agent': 'python-requests/2.6.0 CPython/2.7.6 #Linux/3.13.0-88-generic',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'charset': 'utf-8', }
        _logger.info('estoy consultando con este header %s' % headers)
        data = {
            'params': {
                'vat': self.name, }, }
        _logger.info('estoy consultando con este data %s' % json.dumps(data))
        r = requests.post(
            '%s/partner/jget' % host,
            headers=headers,
            data=json.dumps(data))
        if r.status_code != 200:
            _logger.info('Error al obtener datos del contribuyente: ')
            raise UserError('DocsOnline: %s' % r)
        _logger.info('Data: %s' % r.text)
        try:
            partner_values = json.loads(r.text)['result']
        except KeyError:
            raise UserError('Docsonline: Se produjo un error en la consulta')
        if 'error' in partner_values:
            _logger.warning('DocsOnline error: %s' % partner_values['error'])
            raise UserError('No pudo obtener datos de www.documentosonline.cl: %s' % partner_values['error'])

        wizard_obj = self.env['res.partner.docs.online']
        wizard_obj_data = self.env['res.partner.docs.online.data']
        wizard_obj.truncate()
        wizard_obj_data.truncate()
        wizard_id = wizard_obj.create({'partner_id': self.id})

        for rut_iter, lines in partner_values.items():
            list_partner_data = self._process_dol_data(lines, rut_iter)
            for partner_odoo_data in list_partner_data:
                wizard_obj_data.create(partner_odoo_data)

        """
        partner_list = [
            {
                'name': 'nombre 1',
                'main_id_number': '76201224-3'
            },
            {
                'name': 'nombre 2',
                'main_id_number': '76201517-K'
            },
        ]
        for lines in partner_list:
            wizard_obj_data.create(lines)
        """
        response = {
            'type': 'ir.actions.act_window',
            'name': _('Select a partner from a list'),
            'res_model': 'res.partner.docs.online',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': self.env.ref('l10n_cl_docsonline_partner.tree_docsonline_partners_view').id,
            'target': 'new',
            'active_id': wizard_id.id,
            'res_id': wizard_id.id,
        }
        _logger.info(response)
        return response

    @api.multi
    # @api.onchange('main_id_number')
    def _get_data_from_docsonline(self, rut_input=False):
        self.ensure_one()
        _logger.info('rut input (_get_data_from...) %s' % rut_input)
        self.ensure_one()
        if self.main_id_category_id != self.env.ref('l10n_cl_partner.dt_RUT') or not self.main_id_category_id:
            if not self.main_id_category_id:
                self.main_id_category_id = self.env.ref('l10n_cl_partner.dt_RUT')
            try:
                if not rut_input and not self.main_id_number:
                    _logger.info('there is no name / main id number to evaluate')
                    return
            except:
                return
        self.taxpayer_type_id = self.env.ref('l10n_cl_account.res_IVARI').id
        self.main_id_category_id = self.env.ref('l10n_cl_partner.dt_RUT')

        _logger.info('self_main_id_number: %s' % self.main_id_number)
        try:
            rut = str(int(self.main_id_number.replace('.', '').replace('-', '')[:-1]))
        except:
            rut = rut_input
        docsonline_data = self._get_docsonline_data()
        host = docsonline_data['url']
        headers = {
            'Authorization': 'Basic %s' % docsonline_data['token'],
            'Accept-Encoding': 'gzip, deflate, identity',
            'Accept': '*/*',
            'User-Agent': 'python-requests/2.6.0 CPython/2.7.6 #Linux/3.13.0-88-generic',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'charset': 'utf-8', }
        _logger.info('estoy consultando con este header %s' % headers)
        data = {
            'params': {
                'vat': rut, }, }
        _logger.info('estoy consultando con este data %s' % json.dumps(data))
        r = requests.post(
            host + '/partner/jget',
            headers=headers,
            data=json.dumps(data))
        if r.status_code != 200:
            _logger.info('Error al obtener datos del contribuyente: ')
            raise UserError('DocsOnline: %s' % r)
        else:
            _logger.info('Data: %s' % r.text)
            try:
                partner_values = json.loads(r.text)['result']
            except KeyError:
                raise UserError('Docsonline: Se produjo un error en la consulta')
            if 'error' in partner_values:
                _logger.warning('DocsOnline error: %s' % partner_values['error'])
                raise UserError('No pudo obtener datos de www.documentosonline.cl: %s' % partner_values['error'])
            _logger.info('rut input: %s, pv: %s, rut %s' % (rut_input, partner_values, rut))
            if rut not in partner_values:
                raise UserError('Datos no encontrados. Intente con búsqueda en www.documentosonline.cl')
            else:
                partner_odoo_data = self._process_dol_data(partner_values[rut], rut)[0]
            _logger.info('partner_odoo_data %s' % partner_odoo_data)
            for k in controlled_fields:
                if getattr(self, k):
                    try:
                        del partner_odoo_data[k]
                    except KeyError:
                        _logger.info('########### del %s' % k)
            _logger.info('partner_odoo_data removed protected data %s' % partner_odoo_data)
            self.update(partner_odoo_data)

    @api.model
    def multiple_update(self):
        # records = self.search([('dte_email', '=', False), ('main_id_number', '!=', False), ])
        for r in self:
            try:
                r.press_to_update()
                _logger.info('updated %s' % r.id)
            except:
                _logger.info('could not update %s' % r.id)
                continue
