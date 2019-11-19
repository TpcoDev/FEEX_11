from odoo import api, fields, models

"""
    def action_confirm(self):
        localization = self.company_id.localization
        if hasattr(rec, '%s_action_confirm' % localization):
            getattr(self, '%s_action_confirm' % localization)()
        return super(AccountInvoice, self).action_confirm()


    # ej loc chilena
    def chile_action_confirm(self):
        pass
        # codigo especifico ar

    # metodo dummy en account_document
    def action_confirm(self):
        localization = self.company_id.localization

        if hasattr(rec, 'pre_%s_action_confirm' % localization):
            getattr(self, 'pre_%s_action_confirm' % localization)()
        res = super(AccountInvoice, self).action_confirm()

        if hasattr(rec, 'post_%s_action_confirm' % localization):
            getattr(self, 'post_%s_action_confirm' % localization)()
        return res


    # ej loc ar
    def pre_chile_action_confirm(self):
        # codigo especifico ar pre confirmación factura
        pass

    # ej loc ar
    def post_chile_action_confirm(self):
        # codigo especifico ar post confirmación factura
        pass
"""
