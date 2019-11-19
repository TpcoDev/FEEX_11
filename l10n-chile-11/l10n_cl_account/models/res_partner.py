##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
# import base64
# try:
#     from pyafipws.padron import PadronAFIP
# except ImportError:
#     PadronAFIP = None
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'l10n.cl.localization.filter']

    start_date = fields.Date(
        'Start-up Date'
    )
    taxpayer_type_id = fields.Many2one(
        'account.taxpayer.type',
        'Tax Payer Type',
        auto_join=True,
    )
    # campos desde
    # http://www.sistemasagiles.com.ar/trac/wiki/PadronContribuyentesAFIP
    # profits_tax_type = fields.Selection([
    estado_padron = fields.Char(
        'Estado SII',
    )
    imp_ganancias_padron = fields.Selection([
        ('NI', 'No Inscripto'),
        ('AC', 'Activo'),
        ('EX', 'Exento'),
        # ('NA', 'No alcanzado'),
        # ('XN', 'Exento no alcanzado'),
        # ('AN', 'Activo no alcanzado'),
        ('NC', 'No corresponde'),
    ],
        'Ganancias',
    )
    # vat_tax_type_padron = fields.Selection([
    imp_iva_padron = fields.Selection([
        ('NI', 'No Inscripto'),
        ('AC', 'Activo'),
        ('EX', 'Exento'),
        ('NA', 'No alcanzado'),
        ('XN', 'Exento no alcanzado'),
        ('AN', 'Activo no alcanzado'),
        # ('NC', 'No corresponde'),
    ],
        'IVA',
    )
    integrante_soc_padron = fields.Selection(
        [('N', 'No'), ('S', 'Si')],
        'Integrante Sociedad',
    )
    monotributo_padron = fields.Selection(
        [('N', 'No'), ('S', 'Si')],
        'Monotributo',
    )
    actividad_monotributo_padron = fields.Char(
    )
    empleador_padron = fields.Boolean(
    )
    last_update_padron = fields.Date(
        'Last Update Padron',
    )

    @api.onchange('taxpayer_type_id')
    def _onchange_taxpayer_type(self):
        if not self.main_id_number:
            if self.taxpayer_type_id.code in ['CF', 'EXT']:
                self.main_id_category_id = self.env.ref('l10n_cl_partner.dt_RUT')
                if self.taxpayer_type_id.code == 'CF':
                    self.main_id_number = '66666666-6'
                else:
                    self.main_id_number = '55555555-5'
        else:
            if self.taxpayer_type_id.code in ['EXT']:
                self.main_id_category_id = self.env.ref('l10n_cl_partner.dt_RUT')
                self.main_id_number = '55555555-5'
