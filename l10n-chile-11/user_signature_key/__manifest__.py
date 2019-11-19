# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015  BMyA SA  (http://blancomartin.cl)
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
    "name": """User Signature Key""",
    'version': '11.0.1.0.0',
    'category': 'Utilities',
    'sequence': 12,
    'author': u'BMyA SA - Blanco Martín & Asociados',
    'website': 'http://blancomartin.cl',
    'license': 'AGPL-3',
    'summary': '',
    'external_dependencies': {
        'python': [
            'base64',
            'datetime',
            'logging',
            'M2Crypto',
            'OpenSSL',
        ]
    },
    'depends': [
        'base',
    ],
    'data': [
        'views/user_signature_tab.xml',
        # 'security/ir.model.access.csv'
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
