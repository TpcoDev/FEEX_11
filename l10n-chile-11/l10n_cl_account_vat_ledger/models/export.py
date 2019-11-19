# -*- coding: utf-8 -*-
from pysiidte import normalize_tags as tags

import xmltodict
from odoo import api, models

import logging
_logger = logging.getLogger(__name__)

numeric_keys = [
        'TotDoc', 'TotMntExe', 'TotMntNeto', 'TotOpIVARec', 'TotMntIVA', 'TotMntTotal',
        'NroDoc', 'MntExe', 'MntNeto', 'TasaImp', 'MntIVA', 'IVAUsoComun', 'MntSinCred', 'MntTotal']


def sheet_write(sheet, line_detail, col, detail, key, cell_format):
    try:
        if key in numeric_keys:
            sheet.write_number(line_detail, col, float(detail[key]), cell_format)
        else:
            sheet.write(line_detail, col, detail[key], cell_format)
    except KeyError:
        sheet.write(line_detail, col, '', cell_format)


class LibroXlsx(models.AbstractModel):
    _name ="report.libroxlsx"
    _inherit = 'report.report_xlsx.abstract'

    @staticmethod
    def generate_xlsx_report(workbook, data, libro):
        for obj in libro:
            report_name = obj.name

            sheet = workbook.add_worksheet(report_name[:31])
            bold = workbook.add_format({
                'bold': True,
                'align': 'center',
                'bg_color': 'silver',
                'border': 1,
                })
            center = workbook.add_format({
                'align': 'center',
                })
            cell_format = workbook.add_format({
                'border': 1,
                })

            sheet.set_column(0, 15, 18)

            operation_type = "FEES" if obj.is_fee else obj.operation_type.upper()

            sheet.merge_range('A1:L1', "LIBRO MENSUAL - %s - %s" % (
                report_name.upper(), operation_type), bold)

            sheet.merge_range('A3:B3', "Nombre o Razón Social", bold)
            sheet.merge_range('A4:B4', "Rol Único Tributario", bold)
            sheet.merge_range('A5:B5', "Fecha", bold)
            sheet.merge_range('A6:B6', "Periodo Tributario", bold)

            sheet.merge_range('C3:D3', obj.company_id.name, center)
            sheet.merge_range('C4:D4', obj.company_id.main_id_number, center)
            sheet.merge_range('C5:D5', obj.date, center)
            sheet.merge_range('C6:D6', obj.fiscal_period, center)

            if not obj.sii_xml_request:
                sheet.merge_range(6, 4, 6, 6, "NO HAY FACTURAS PARA ESTE PERIODO")
            else:
                xml_dict = xmltodict.parse(obj.sii_xml_request)

                line = 2
                sheet.merge_range(line, 4, line, 11, "RESUMEN", bold)
                summary = xml_dict['LibroCompraVenta']['EnvioLibro']['ResumenPeriodo']['TotalesPeriodo']

                if isinstance(summary, dict):
                    summary = [summary]

                keys_sum_ordered = [
                    'TpoDoc', 'TpoImp', 'TotDoc', 'TotMntExe', 'TotMntNeto', 'TotOpIVARec', 'TotMntIVA', 'TotMntTotal']

                line += 1
                line_detail = line
                
                for key, col in zip(keys_sum_ordered, range(0, len(keys_sum_ordered))):
                    sheet.write(line, col + 4, key, bold)
                    line_detail = line
                    for detail in summary:
                        line_detail += 1
                        sheet_write(sheet, line_detail, col + 4, detail, key, cell_format)

                line = line_detail + 4

                sheet.merge_range(line, 0, line, 11, "DETALLE", bold)
                details = xml_dict['LibroCompraVenta']['EnvioLibro']['Detalle']

                if isinstance(details, dict):
                    details = [details]

                all_keys_ordered = [
                    'TpoDoc', 'NroDoc', 'FchDoc', 'RUTDoc', 'RznSoc',
                    'MntExe', 'MntNeto', 'TasaImp', 'MntIVA', 'IVAUsoComun', 'MntSinCred', 'MntTotal']

                line += 1

                for key, col in zip(all_keys_ordered, range(0, len(all_keys_ordered))):
                    sheet.write(line, col, key, bold)
                    line_detail = line
                    for detail in details:
                        line_detail += 1
                        sheet_write(sheet, line_detail, col, detail, key, cell_format)
