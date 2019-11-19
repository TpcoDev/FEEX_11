from odoo import api, fields, models


class LocalizationFields(models.Model):
    _name = 'localization.fields'

    chart_account = fields.Char(required=True)
    model = fields.Char(required=True)
    field = fields.Char(required=True)

    def get_localization_fields(self, model_name):
        model_fields = self.search([('model', '=', model_name)])
        fields_name = [f.field for f in model_fields]
        return fields_name
