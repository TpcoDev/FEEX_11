# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# http://www.bmya.cl
import logging

from odoo import SUPERUSER_ID, api, registry

_logger = logging.getLogger(__name__)


def no_update_module(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    chart_template_id = env.ref('l10n_cl_chart.cl_chart_template_bmya')
    chart_template_id.try_loading_for_current_company()
    wizard = env['wizard.multi.charts.accounts'].create({
        'company_id': chart_template_id.env.user.company_id.id,
        'chart_template_id': chart_template_id.id,
        'code_digits': chart_template_id.code_digits,
        'transfer_account_id': chart_template_id.transfer_account_id.id,
        'currency_id': chart_template_id.currency_id.id,
        'bank_account_code_prefix': chart_template_id.bank_account_code_prefix,
        'cash_account_code_prefix': chart_template_id.cash_account_code_prefix,
    })
    wizard.onchange_chart_template_id()
    wizard.execute()
    _logger.info('l10n_cl_chart no update module hook')
