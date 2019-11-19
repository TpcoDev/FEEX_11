# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015  ADHOC SA  (http://www.adhoc.com.ar)
#    All Rights Reserved.
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
    'author': 'Blanco Martín & Asociados',
    'category': 'Delivery Guide / Chilean Localization',
    'demo_xml': [],
    'depends': ['l10n_cl_stock_delivery_guide'],
    'installable': True,
    'name': 'Delivery Guide Change Currency',
    'test': [],
    'data': [
        'security/security.xml',
        'wizard/delivery_guide_change_currency_view.xml',
        'views/picking_view.xml',
    ],
    'version': '11.0.1.0.0',
    'website': 'https://www.bmya.cl',
    'license': 'AGPL-3'
}
