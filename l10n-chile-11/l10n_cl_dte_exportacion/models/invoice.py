# -*- coding: utf-8 -*-
import collections
import logging
import pysiidte


from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import xmltodict
except ImportError:
    _logger.warning('Cannot import xmltodict library')

try:
    import dicttoxml
except ImportError:
    _logger.warning('Cannot import dicttoxml library')

try:
    import base64
except ImportError:
    _logger.warning('Cannot import base64 library')

dicttoxml.LOG.setLevel(logging.ERROR)


class Exportacion(models.Model):
    _inherit = "account.invoice"

    exportacion = fields.One2many(
        string="Exportación",
        comodel_name="account.invoice.exportacion",
        inverse_name="invoice_id",
        context={"form_view_ref": "l10n_cl_exportacion.exportacion_view_form"},
        help="Explain your field.",
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    def format_vat(self, value, with_zero=False):
        # al ya venir el rut ingresado en res.partner (en main_id_number de extranjeros) esta función carece de sentido
        if self._check_doc_type('E') and self.commercial_partner_id.vat == value:
            value = "CL555555555"
        return super(Exportacion, self).format_vat(value, with_zero)

    def _es_nc_exportacion(self):
        return self.document_type_id.code in [ 112 ]

    # def _es_exportacion(self):
    #     if self.document_type_id.code in [ 110, 111, 112 ]:
    #         return True
    #     return False

    def _totals_normal(self, MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal=0):
        if not self._check_doc_type('E'):
            return super(Exportacion, self)._totals_normal(MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal)
        if IVA:
            raise UserError("En facturas de Exportación no debe haber productos con IVA")
        total_amounts = collections.OrderedDict()
        if self.currency_id != self.env.ref('base.cl'):
            total_amounts['TpoMoneda'] = self.currency_id.short_name
        else:
            raise UserError('El tipo de moneda no se ha definido')
        if MntExe:
            total_amounts['MntExe'] = MntExe
        total_amounts['MntTotal'] = MntTotal
        #     # Totales['MontoNF']
        #     # Totales['TotalPeriodo']
        #     # Totales['SaldoAnterior']
        #     # Totales['VlrPagar']
        #     return Totales#
        return total_amounts

   # def _totals_normal(self, currency_id, MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal=0):
   #     if not self._check_doc_type('E'):
   #         return super(Exportacion, self)._totals_normal(MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal)
   #     if IVA:
   #         raise UserError("No debe haber Productos con IVA")
   #     Totales = collections.OrderedDict()
   #     if currency_id:
   #         Totales['TpoMoneda'] = currency_id.short_name
   #     else:
   #         raise UserError('El tipo de moneda no se ha definido')
   #     Totales['MntExe'] = MntExe
   #     Totales['MntTotal'] = MntTotal
   #     # Totales['MontoNF']
   #     # Totales['TotalPeriodo']
   #     # Totales['SaldoAnterior']
   #     # Totales['VlrPagar']
   #     return Totales#
    """
    <Totales>
		<TpoMoneda>DOLAR USA</TpoMoneda>
		<MntExe>3680.0</MntExe>
		<MntTotal>3681</MntTotal>
    </Totales>
	<OtraMoneda>
		<TpoMoneda>PESO CL</TpoMoneda>
		<TpoCambio>0.0015</TpoCambio>
		<MntExeOtrMnda>2494230</MntExeOtrMnda>
		<MntTotOtrMnda>2494908</MntTotOtrMnda>
	</OtraMoneda>
    """

    def _totals_otra_moneda(self, currency_id, MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal=0):
        if not self._check_doc_type('E'):
            return super(Exportacion, self)._totals_otra_moneda(currency_id, MntExe, MntNeto, IVA, TasaIVA, ImptoReten, MntTotal)
        total_amounts = collections.OrderedDict()
        total_amounts['TpoMoneda'] = pysiidte.str_shorten(self.company_id.currency_id.short_name, 15)  # PESO CL
        total_amounts['TpoCambio'] = round(self.currency_id.rate, 4)  # currency_id.rate del euro 0,00127323656735
        if MntExe:
            if self.currency_id:
                MntExe = self.currency_id.compute(MntExe, self.company_currency_id)
            total_amounts['MntExeOtrMnda'] = MntExe
        if self.currency_id:
            MntTotal = self.currency_id.compute(MntTotal, self.company_currency_id)
        total_amounts['MntTotOtrMnda'] = MntTotal
        return total_amounts

    def _aplicar_gdr(self, MntExe):
        gdr = self.discount_charges_percent()
        MntExe *= gdr
        return self.currency_id.round(MntExe)

    def _totals(self, MntExe=0, no_product=False, tax_include=False):
        MntExe, MntNeto, MntIVA, TasaIVA, ImptoReten, MntTotal = super(Exportacion, self)._totals(
            MntExe, no_product, tax_include)
        if self._check_doc_type('E'):
            MntExe = self._aplicar_gdr(MntExe)
        return MntExe, MntNeto, MntIVA, TasaIVA, ImptoReten, MntTotal

    def _bultos(self, bultos):
        Bultos = []
        for b in bultos:
            Bulto = dict()
            Bulto['TipoBultos'] = collections.OrderedDict()
            Bulto['TipoBultos']['CodTpoBultos'] = bultos.tipo_bulto.code
            Bulto['TipoBultos']['CantBultos'] = bultos.cantidad_bultos
            Bultos.append(Bulto)
        return Bultos

    def _aduana(self):
        expo = self.exportacion
        Aduana = collections.OrderedDict()
        # if not in 3, 4, 5
        if self.payment_term_id:
            Aduana['CodModVenta'] = self.payment_term_id.forma_pago_aduanas.code
            mnt_clau = self.payment_term_id.with_context(currency_id=self.currency_id.id).compute(
                self.amount_total, date_ref=self.date_invoice)[0]
            Aduana['TotClauVenta'] = round(mnt_clau[0][1], 2)
        elif not self._es_nc_exportacion():
            raise UserError("Debe Ingresar un Término de Pago")
        if self.incoterms_id:
            Aduana['CodClauVenta'] = self.incoterms_id.aduanas_code
        if expo.via:
            Aduana['CodViaTransp'] = expo.via.code
        if expo.ship_name:
            # Aduana['NombreTransp'] = expo.ship_name.name
            Aduana['NombreTransp'] = expo.ship_name
        try:
            Aduana['RUTCiaTransp'] = self.format_vat(expo.carrier_id.partner_id.vat)
            Aduana['NomCiaTransp'] = expo.carrier_id.name
        except AttributeError:
            _logger.info('Cia Transporte no definida')
        #Aduana['IdAdicTransp'] = self.indicador_adicional
        if expo.puerto_embarque:
            Aduana['CodPtoEmbarque'] = expo.puerto_embarque.code
        #Aduana['IdAdicPtoEmb'] = expo.ind_puerto_embarque
        if expo.puerto_desembarque:
            Aduana['CodPtoDesemb'] = expo.puerto_desembarque.code
        #Aduana['IdAdicPtoDesemb'] = expo.ind_puerto_desembarque
        if expo.tara:
            Aduana['Tara'] = expo.tara
            Aduana['CodUnidMedTara'] = expo.uom_tara.code
        if expo.peso_bruto:
            Aduana['PesoBruto'] = round(expo.peso_bruto, 2)
            Aduana['CodUnidPesoBruto'] = expo.uom_peso_bruto.code
        if expo.peso_neto:
            Aduana['PesoNeto'] = round(expo.peso_neto, 2)
            Aduana['CodUnidPesoNeto'] = expo.uom_peso_neto.code
        if expo.total_items:
            Aduana['TotItems'] = expo.total_items
        if expo.total_bultos:
            Aduana['TotBultos'] = expo.total_bultos
            Aduana['item'] = self._bultos(expo.bultos)
        # Aduana['Marcas'] =
        # Solo si es contenedor
        # Aduana['IdContainer'] =
        # Aduana['Sello'] =
        # Aduana['EmisorSello'] =
        if expo.monto_flete:
            Aduana['MntFlete'] = expo.monto_flete
        if expo.monto_seguro:
            Aduana['MntSeguro'] = expo.monto_seguro
        if expo.pais_recepcion:
            Aduana['CodPaisRecep'] = expo.pais_recepcion.code
        if expo.pais_destino:
            Aduana['CodPaisDestin'] = expo.pais_destino.code
        return Aduana

    def _transporte(self):
        Transporte = collections.OrderedDict()
        expo = self.exportacion
        if expo.carrier_id:
            """
            es un dato opcional y por ahora no lo incluimos
            if self.patente:
                Transporte['Patente'] = self.patente[:8]
            elif self.vehicle:
                Transporte['Patente'] = self.vehicle.matricula or ''
            """

            """
            tambien son opcionales (no obligatorios)
            if self.transport_type in ['2', '3'] and self.chofer:
                if not self.chofer.vat:
                    raise UserError("Debe llenar los datos del chofer")
                if self.transport_type == '2':
                    Transporte['RUTTrans'] = self.format_vat(self.company_id.vat)
                else:
                    if not self.carrier_id.partner_id.vat:
                        raise UserError("Debe especificar el RUT del transportista, en su ficha de partner")
                    Transporte['RUTTrans'] = self.format_vat(self.carrier_id.partner_id.vat)
                if self.chofer:
                    Transporte['Chofer'] = collections.OrderedDict()
                    Transporte['Chofer']['RUTChofer'] = self.format_vat(self.chofer.vat)
                    Transporte['Chofer']['NombreChofer'] = self.chofer.name[:30]
            """
        partner_id = self.partner_id or self.company_id.partner_id
        Transporte['DirDest'] = (partner_id.street or '') + ' ' + (partner_id.street2 or '')
        Transporte['CmnaDest'] = partner_id.state_id.name or ''
        Transporte['CiudadDest'] = partner_id.city or ''
        Transporte['Aduana'] = self._aduana()
        return Transporte

    def _xml_header(self, MntExe=0, no_product=False, tax_include=False):
        res = super(Exportacion, self)._xml_header(MntExe, no_product, tax_include)
        if not self._check_doc_type('E'):
            _logger.info('\n\n\nNo lo toma como exportación\n\n\n')
            return res
        result = collections.OrderedDict()
        for key, value in res.items():
            result[key] = value
            if key == 'Receptor':
                result['Transporte'] = self._transporte()
        _logger.info('\n\n\n ##### exportación ######## %s \n\n\n' % result)
        return result

    def _tpo_dte(self):
        if self._check_doc_type('E'):
            return 'Exportaciones'
        return super(Exportacion, self)._tpo_dte()
