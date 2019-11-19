# -*- coding: utf-8 -*-
from odoo import api, models, fields
from odoo.tools.translate import _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class Procurement(models.Model):
    _inherit = 'procurement.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, values, group_id):
        result = super(Procurement, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, values, group_id)
        result.update({
                'delivery_price_unit': values.get('delivery_price_unit', 0),
                'discount': values.get('discount', 0),
                'move_line_tax_ids': [(6, 0,values.get('move_line_tax_ids', False))],
                'currency_id': values.get('currency_id', self.env.user.company_id.currency_id.id),
            })
        return result
