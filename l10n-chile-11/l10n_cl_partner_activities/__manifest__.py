# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'active': False,
    'author': u'Blanco Martín & Asociados',
    'category': 'Localization/Chile',
    'demo_xml': [],
    'depends': ['l10n_cl_base', 'l10n_cl_account'],
    'installable': True,
    'license': 'AGPL-3',
    'name': u'Chile - Actividades Económicas',
    'data': [
        # 'security/l10n_cl_partner_activities.xml',
        'data/partner.activities.csv',
        'views/partner_activities.xml',
        'views/account_invoice.xml',
        'views/res_company.xml',
        'views/res_partner.xml',
        'views/sii_activity_description.xml',
        'security/ir.model.access.csv',
    ],
    'version': '11.0.2.0.0',
    'website': 'http://blancomartin.cl'
}
