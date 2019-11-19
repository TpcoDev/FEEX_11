# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import api, fields, models


class PartnerDocumentsOnline(models.TransientModel):
    """Wizard to show www.documentosonline.cl data"""
    _name = 'res.partner.docs.online'

    partner_id = fields.Many2one('res.partner')
    name = fields.Char(string='Name', related='partner_id.name', readonly=True)
    docs_online_data_ids = fields.Many2many(
        'res.partner.docs.online.data', string='-')

    @api.model
    def truncate(self):
        cursor = self.env.cr
        cursor.execute('truncate res_partner_docs_online cascade')

    def pick_partner(self):
        # implemented just for one record by now
        nr = self.docs_online_data_ids[0]
        self.partner_id.update({
            'name': nr.name,
            'street': nr.street,
            'street2': nr.street2,
            'city': nr.city,
            'city_id': nr.city_id,
            'state_id': nr.state_id,
            'dte_email': nr.dte_email,
            'main_id_number': nr.main_id_number,
            'partner_activities_ids':  nr.partner_activities_ids,
            'activity_description':  nr.activity_description,
            'country_id':  nr.country_id,
            'taxpayer_type_id':  nr.taxpayer_type_id,
            'type':  nr.type,
            'main_id_category_id': self.env.ref('l10n_cl_partner.dt_RUT').id
        })

    def pick_partner_protect(self):
        # implemented just for one record by now
        nr = self.docs_online_data_ids[0]
        self.partner_id.update({
            # 'name': nr.name,
            # 'street': nr.street,
            # 'street2': nr.street2,
            'city': nr.city,
            'city_id': nr.city_id,
            'state_id': nr.state_id,
            'dte_email': nr.dte_email,
            'main_id_number': nr.main_id_number,
            'partner_activities_ids':  nr.partner_activities_ids,
            'activity_description':  nr.activity_description,
            'country_id':  nr.country_id,
            'taxpayer_type_id':  nr.taxpayer_type_id,
            'type':  nr.type,
            'main_id_category_id': self.env.ref('l10n_cl_partner.dt_RUT').id
        })


class PartnerDocumentsOnLineData(models.TransientModel):
    _name = 'res.partner.docs.online.data'

    partner_docs_ids = fields.Many2many('res.partner.docs.online', string='Lines')
    name = fields.Char('Name')
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    city = fields.Char('City')
    city_id = fields.Many2one('res.city', 'County')
    state_id = fields.Many2one('res.country.state', string='Province')
    dte_email = fields.Char('DTE Email')
    main_id_number = fields.Char('RUT')
    partner_activities_ids = fields.Many2many('partner.activities', string='Econ. Activities')
    activity_description = fields.Many2one('sii.activity.description', string='Activity Description')
    country_id = fields.Many2one('res.country', string='Country')
    taxpayer_type_id = fields.Many2one('account.taxpayer.type')
    type = fields.Selection(
        [
            ('contact', 'Contact'),
            ('invoice', 'Invoice Address'),
            ('delivery', 'Shipping Address'),
            ('other', 'Other Address'),
            ('private', 'Private Address'),
        ], string='Type of Address'
    )

    @api.model
    def truncate(self):
        cursor = self.env.cr
        cursor.execute('truncate res_partner_docs_online_data cascade')

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.main_id_number:
                name = '%s %s' % (name, record.main_id_number)
            if record.street:
                name = '%s %s' % (name, record.street)
            if record.street2:
                name = '%s %s' % (name, record.street2)
            if record.city:
                name = '%s, %s' % (name, record.city)
            if record.type:
                if record.type == 'other':
                    name = '%s (%s)' % (name, 'Sucursal')
            if record.activity_description:
                name = '%s - %s' % (name, record.activity_description.name)
            result.append((record.id, name))
        return result
