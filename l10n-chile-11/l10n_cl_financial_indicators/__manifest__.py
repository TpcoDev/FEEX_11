# -*- coding: utf-8 -*-
##############################################################################
#
# Odoo, Open Source Management Solution
# Copyright (C) 2004-2015 OdooL (<http://odoo.com>).
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# This module authored by Daniel Blanco, Blanco Martín & Asociados
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Chilean Financial Indicators',
    'version': '11.0.1.0.0',
    'category': 'Tools',
    'license': 'AGPL-3',
    'author': u'Blanco Martin & Asociados',
    'website': 'http://blancomartin.cl',
    'depends': [
        'base'
    ],
    'data': [
        'data/decimal.precision.xml',
        # 'data/res.currency.xml',
        'data/ir_cron.xml',
        'data/ir.config_parameter.xml',
        'views/update_button.xml',
        'data/res.currency.csv',
    ],
    'init_xml': [
        'query0.sql',
        'query1.sql',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
