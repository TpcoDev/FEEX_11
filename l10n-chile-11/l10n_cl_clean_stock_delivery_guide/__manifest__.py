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
    'name': u'Clean not accepted or cancelled Delivery Guide',
    'version': '11.0.1.0.0',
    'category': 'Stock',
    'sequence': 14,
    'summary': u'Invoicing, Number, Cancelled',
    'author':  u'Blanco Martín & Asociados',
    'website': 'http://blancomartin.cl',
    'depends': [
        'account_cancel', 'l10n_cl_account', 'l10n_cl_stock_delivery_guide'
    ],
    'data': [
        'views/stock_picking_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
