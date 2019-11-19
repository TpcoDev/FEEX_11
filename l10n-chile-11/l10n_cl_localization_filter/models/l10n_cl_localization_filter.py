import json

from lxml import etree

from odoo import api, fields, models
from odoo.osv import expression, orm


class L10nClLocalizationFilter(models.AbstractModel):
    _name = 'l10n.cl.localization.filter'

    def _get_localization_from_company(self):
        for record in self:
            record.localization_view = self.env.user.company_id.localization

    def _get_cl_localization_template(self):
        template = self.env['ir.model.data'].xmlid_to_object(
            'l10n_cl_chart.cl_chart_template_bmya', False)
        return template and template.id

    def _get_user_localization(self):
        user_localization = self.env.user.company_id.chart_template_id
        return user_localization and user_localization.id

    def _is_user_localization(self):
        return (self._get_cl_localization_template() ==
                self._get_user_localization())

    @staticmethod
    def _add_localization_field(doc):
        elem = etree.Element(
            'field', {
                'name': 'l10n_cl_localization',
                'invisible': 'True',
            }
        )
        nodes = doc.xpath("//form//field")
        if len(nodes):
            orm.setup_modifiers(elem)
            nodes[0].addnext(elem)

    def _get_localization_fields(self):
        return self.env['localization.fields']\
            .get_localization_fields(self._name)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        ret_val = super(L10nClLocalizationFilter, self).fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)

        if view_type not in ('form', 'tree'):
            return ret_val

        doc = etree.XML(ret_val['arch'])
        self._add_localization_field(doc)
        model_fields = self._get_localization_fields()
        for field in ret_val['fields']:
            if field not in model_fields:
                continue
            self._add_localization_filter_to_domain(doc, field, view_type)

        ret_val['arch'] = etree.tostring(doc, encoding='unicode')
        return ret_val

    def _add_localization_filter_to_domain(self, doc, field, view_type):
        xpaths = ["//field[@name='%s']", "//label[@for='%s']"]
        for xpath in xpaths:
            for node in doc.xpath(xpath % field):
                mod_field = (view_type == 'tree' and 'column_invisible'
                             or 'invisible')
                modifiers = json.loads(node.get("modifiers", '{}'))
                if view_type == 'tree':
                    modifiers[mod_field] = not self._is_user_localization()
                if view_type == 'form':
                    domain = modifiers.get(mod_field, [])
                    if isinstance(domain, bool) and domain:
                        continue
                    if domain:
                        domain = expression.normalize_domain(domain)
                    domain = expression.OR([
                        [('l10n_cl_localization', '=', False)], domain])
                    modifiers[mod_field] = domain
                node.set("modifiers", json.dumps(modifiers))

    def _default_l10n_cl_localization(self):
        if not hasattr(self.env.user.company_id, 'chart_template_id'):
            return True

        return self._is_user_localization()

    @api.multi
    @api.depends()
    def _compute_is_cl_localization(self):
        user_template = self._get_user_localization()
        for record in self:
            if hasattr(record, 'company_id'):
                user_template = (record.company_id.chart_template_id
                                 and record.company_id.chart_template_id.id
                                 or user_template)
            cl_template = self._get_cl_localization_template()
            record.l10n_cl_localization = cl_template == user_template

    l10n_cl_localization = fields.Boolean(
        compute=_compute_is_cl_localization,
        default=lambda self: self._default_l10n_cl_localization(),
        string='Is CL localization?')

    localization = fields.Char(
        compute='_get_company_localization',
        default=lambda self: self._get_company_localization(),
        string='Localization')

    def _get_company_localization(self):
        for record in self:
            record.localization = self.env.user.company_id.localization
