# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PartnerActivities(models.Model):
    _description = 'SII Economical Activities'
    _name = 'partner.activities'

    code = fields.Char('Activity Code', required=True, translate=True)
    parent_id = fields.Many2one(
        'partner.activities', 'Parent Activity', ondelete='cascade')
    grand_parent_id = fields.Many2one(
        'partner.activities', related='parent_id.parent_id', string='Grand Parent Activity',
        ondelete='cascade', store=True)
    name = fields.Char('Complete Name', required=True, translate=True)
    vat_affected = fields.Selection(
        [('SI', 'Si'), ('NO', 'No'), ('ND', 'ND')], 'VAT Affected', translate=True, default='SI')
    tax_category = fields.Selection(
        [('1', '1'), ('2', '2'), ('ND', 'ND')], 'TAX Category', translate=True, default='1')
    internet_available = fields.Boolean('Available at Internet', default=True)
    active = fields.Boolean(
        'Active', help="Allows you to hide the activity without removing it.",
        default=True)
    partner_ids = fields.Many2many(
        'res.partner', id1='activities_id', id2='partner_id', string='Partners')
    new_activity = fields.Boolean(
        'New Activity Code',
        help='Your activity codes must be replaced with the new ones. Effective November 1, 2018')

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.code:
                name = '(%s) %s' % (record.code, name)
            result.append((record.id, name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if self._context.get('search_by_code', False):
            if name:
                args = args if args else []
                args.extend(['|', ['name', 'ilike', name], ['code', 'ilike', name]])
                name = ''
        return super(PartnerActivities, self).name_search(name=name, args=args, operator=operator, limit=limit)


class PartnerTurns(models.Model):
    _description = 'Partner registered turns'
    _inherit = 'res.partner'

    partner_activities_ids = fields.Many2many(
        'partner.activities', id1='partner_id', id2='activities_id',
        string='Activities Names', translate=True,
        help=u'Please select the economic activities from SII\'s nomenclator')
    activity_description_invisible = fields.Boolean(
        related='company_id.company_activity_description_invisible', readonly=True)
    activities_opt = fields.Selection([
        ('encoded_activity', 'Business Turn Based on Economic Activities \
(B2B or SMEs)'),
        ('activity_description', 'Business Turn Based on Activity Description \
(B2C or MSEs)'), ],
        help="""If your company is a small or medium business, probably you'd \
prefer to describe your activity or your partner's activities based on the \
SII's economic activities nomenclator.
But if your company is a micro or small enterprise, or if you mostly serves \
your customers at a counter, you will probably prefer to describe your \
partners' activities based on a simple description through a phrase. 
In either case, establishing at least one of the economic activities for \
your own company is mandatory.""", related='company_id.activities_opt', readonly=True)


class CompanyTurns(models.Model):

    _description = 'Company registered turns'
    _inherit = 'res.company'

    def activities_company_default_get(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        if not get_param('activities_description_required', default=False) \
                and not get_param('activities_invisible', default=False):
            return 'encoded_activity'
        else:
            return 'activity_description'

    def _get_invisible_param(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        return get_param(
            'activity_description_invisible_company', default=False)

    company_activities_ids = fields.Many2many(
        string='Activities Names',
        related='partner_id.partner_activities_ids',
        relation='partner.activities',
        help=u'Seleccione las actividades económicas registradas en el SII')

    company_activity_description_invisible = fields.Boolean(
        default=lambda self: self._get_invisible_param())

    activities_opt = fields.Selection([
        ('activity_description', 'Business Turn Based on Activity Description \
(B2C or MSEs)'),
        ('encoded_activity', 'Business Turn Based on Economic Activities \
(B2B or SMEs)'), ],
        default=lambda self: self.activities_company_default_get(),
        help="""If your company is a small or medium business, probably you'd \
prefer to describe your activity or your partner's activities based on the \
SII's economic activities nomenclator.
But if your company is a micro or small enterprise, or if you mostly serves \
your customers at a counter, you will probably prefer to describe your \
partners' activities based on a simple description through a phrase.
In either case, establishing at least one of the economic activities for your \
own company is mandatory. """)
