# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from openerp.addons.l10n_cl_partner import hooks
from openerp.modules.registry import RegistryManager
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(cr, version):
    # si l10n_cl_partner estaba instalado lo renombramos por este
    # entonces el hook no se corre, forzamos con upgrade
    pool = RegistryManager.get(cr.dbname)
    hooks.post_init_hook(cr, pool)
