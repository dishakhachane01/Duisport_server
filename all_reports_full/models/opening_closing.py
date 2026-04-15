# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date
import io, base64
from odoo.modules.module import get_module_resource 


try:
    import xlsxwriter
except Exception:
    xlsxwriter = None


class OpeningClosingWizard(models.TransientModel):
    _name = "opening.closing.report.wizard"
    _description = "Opening & Closing Balance Report Wizard"



    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True
    )
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    report_format = fields.Selection([
        ('xlsx', 'Excel'),
        ('pdf', 'PDF')
    ], default='xlsx', required=True)

    # -----------------------------
    #  EXPORT ACTION
    # -----------------------------
    def action_export(self):
    # def action_download_pdf(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/all_reports_full.opening_closing_template/%d' % self.id,
            'target': 'new',
        }
    # -----------------------------
    #  CALCULATE BALANCES
    # -----------------------------
    def _get_balance_data(self):
        start = self.start_date
        end = self.end_date

        accounts = self.env['account.account'].search([], order='code')
        result = []

        for acc in accounts:
            # Opening
            ob_domain = [
                ('account_id', '=', acc.id),
                ('date', '<', start),
                ('parent_state', '=', 'posted')
            ]
            opening = sum(self.env['account.move.line'].search(ob_domain).mapped(lambda l: l.debit - l.credit))

            # Period Movement
            pr_domain = [
                ('account_id', '=', acc.id),
                ('date', '>=', start),
                ('date', '<=', end),
                ('parent_state', '=', 'posted')
            ]
            lines = self.env['account.move.line'].search(pr_domain)
            debit = sum(lines.mapped('debit'))
            credit = sum(lines.mapped('credit'))

            closing = opening + debit - credit

            result.append({
                'account': acc,
                'opening': opening,
                'debit': debit,
                'credit': credit,
                'closing': closing
            })

        return result

    # -----------------------------
    #  EXCEL EXPORT
    # -----------------------------
    def export_xlsx(self):
        if xlsxwriter is None:
            raise UserError("xlsxwriter missing!")

        stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(stream, {'in_memory': True})
        sheet = workbook.add_worksheet('Opening-Closing')

        # Formats
        title_format = workbook.add_format({'bold': True, 'align': 'center', 'font_size': 16})
        header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
        cell_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0.00'})

        row = 0

        # ---------------------------------------------------
        # Header Image
        # ---------------------------------------------------
        module_path = get_module_resource('all_reports_full', 'static/src/img', 'header2.png')
        if module_path:
            sheet.insert_image(row, 0, module_path, {'x_scale': 0.8, 'y_scale': 0.8})
            row += 6

        # ---------------------------------------------------
        # Title
        # ---------------------------------------------------
        sheet.merge_range(row, 0, row, 5, 'Opening and Closing Balance Report', title_format)
        row += 2

        # ---------------------------------------------------
        # Period + Generated Time
        # ---------------------------------------------------
        sheet.write(row, 0, 'Period:')
        sheet.write(row, 1, f"{self.start_date} to {self.end_date}")

        sheet.write(row, 4, 'Generated:')
        sheet.write(row, 5, fields.Datetime.now().strftime('%Y-%m-%d %H:%M'))

        row += 2

        # ---------------------------------------------------
        # Headers
        # ---------------------------------------------------
        headers = ["Account Code", "Account Name", "Opening", "Debit", "Credit", "Closing"]

        for col, h in enumerate(headers):
            sheet.write(row, col, h, header_format)

        sheet.freeze_panes(row + 1, 0)

        row += 1

        # ---------------------------------------------------
        # Data
        # ---------------------------------------------------
        data = self._get_balance_data()

        for item in data:
            sheet.write(row, 0, item['account'].code or '', cell_format)
            sheet.write(row, 1, item['account'].name or '', cell_format)
            sheet.write(row, 2, float(item['opening']), number_format)
            sheet.write(row, 3, float(item['debit']), number_format)
            sheet.write(row, 4, float(item['credit']), number_format)
            sheet.write(row, 5, float(item['closing']), number_format)
            row += 1

        # ---------------------------------------------------
        # Column Widths
        # ---------------------------------------------------
        sheet.set_column(0, 0, 15)
        sheet.set_column(1, 1, 35)
        sheet.set_column(2, 5, 18)

        workbook.close()

        attachment = self.env['ir.attachment'].create({
            'name': f"opening_closing_{self.start_date}_{self.end_date}.xlsx",
            'type': 'binary',
            'datas': base64.b64encode(stream.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': f"/web/content/{attachment.id}?download=true"
        }
    




