from odoo import _, api, models
from odoo.exceptions import UserError

# from odoo.addons.l10n_cl_account.models import account_journal
# try:
#     from pyafipws.padron import PadronAFIP
# except ImportError:
#     PadronAFIP = None


class AccountConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.multi
    def refresh_taxes_from_padron(self):
        self.refresh_from_padron("impuestos")

    @api.multi
    def refresh_concepts_from_padron(self):
        self.refresh_from_padron("conceptos")

    @api.multi
    def refresh_activities_from_padron(self):
        self.refresh_from_padron("actividades")

    # @api.multi
    # def refresh_from_padron(self, resource_type):
    #     """
    #     resource_type puede ser "impuestos", "conceptos", "actividades",
    #     "caracterizaciones", "categoriasMonotributo", "categoriasAutonomo".
    #     """
    #     self.ensure_one()
    #     if resource_type == 'impuestos':
    #         model = 'afip.tax'
    #     elif resource_type == 'actividades':
    #         model = 'afip.activity'
    #     elif resource_type == 'conceptos':
    #         model = 'afip.concept'
    #     else:
    #         raise UserError(_('Resource Type %s not implemented!') % (
    #             resource_type))
    #     padron = PadronAFIP()
    #     separator = ';'
    #     data = padron.ObtenerTablaParametros(resource_type, separator)
    #     codes = []
    #     for line in data:
    #         # None, code, name, None = line.split(separator)
    #         split = line.split(separator)
    #         code = split[1]
    #         name = split[2]
    #         vals = {
    #             'code': code,
    #             'name': name,
    #             'active': True,
    #         }
    #         record = self.env[model].search([('code', '=', code)], limit=1)
    #         codes.append(code)
    #         if record:
    #             record.write(vals)
    #         else:
    #             record.create(vals)
    #     # deactivate the ones that are not in afip
    #     self.env[model].search([('code', 'not in', codes)]).write(
    #         {'active': False})
