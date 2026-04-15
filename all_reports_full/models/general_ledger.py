# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io, base64
from datetime import date
from odoo.modules.module import get_module_resource


try:
    import xlsxwriter
except Exception:
    xlsxwriter = None

class GeneralLedgerReport(models.TransientModel):
    _name = 'general.ledger.report'
    _description = 'General Ledger Report'



    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True
    )
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    line_ids = fields.One2many('general.ledger.line', 'report_id', string='Lines')

    def action_view_report(self):
        """Fetch and display report data"""
        self.line_ids.unlink()
        
        domain = [
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            ('parent_state', '=', 'posted')
        ]
        amls = self.env['account.move.line'].search(domain, order='date,account_id,partner_id')
        
        balance_map = {}
        lines_to_create = []
        
        for line in amls:
            acc = line.account_id
            key = acc.id
            bal = balance_map.get(key, 0.0) + (line.debit - line.credit)
            balance_map[key] = bal
            
            lines_to_create.append({
                'report_id': self.id,
                'date': line.date,
                'journal': line.move_id.journal_id.name or '',
                'account_code': acc.code or '',
                'account_name': acc.name,
                'partner': line.partner_id.name or '',
                'label': line.name or '',
                'debit': line.debit,
                'credit': line.credit,
                'balance': bal,
            })
        
        self.env['general.ledger.line'].create(lines_to_create)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'general.ledger.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_download_xlsx(self):
        """Download Excel report"""
        if xlsxwriter is None:
            raise UserError(_('Python library xlsxwriter is required for Excel export.'))

        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('General Ledger')

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
        sheet.merge_range(row, 0, row, 8, 'General Ledger Report', title_format)
        row += 2

        # ---------------------------------------------------
        # Period + Generated Time
        # ---------------------------------------------------
        sheet.write(row, 0, 'Period:')
        sheet.write(row, 1, f"{self.start_date} to {self.end_date}")

        sheet.write(row, 6, 'Generated:')
        sheet.write(row, 7, fields.Datetime.now().strftime('%Y-%m-%d %H:%M'))
        row += 2

        # ---------------------------------------------------
        # Table Headers
        # ---------------------------------------------------
        headers = [
            'Date', 'Journal', 'Account Code', 'Account Name',
            'Partner', 'Label', 'Debit', 'Credit', 'Balance'
        ]

        for col, h in enumerate(headers):
            sheet.write(row, col, h, header_format)

        sheet.freeze_panes(row + 1, 0)

        row += 1

        # ---------------------------------------------------
        # Data
        # ---------------------------------------------------
        domain = [
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            ('parent_state', '=', 'posted')
        ]

        amls = self.env['account.move.line'].search(domain, order='account_id,date,partner_id')

        balance_map = {}

        for line in amls:
            acc = line.account_id
            key = acc.id

            bal = balance_map.get(key, 0.0) + (line.debit - line.credit)
            balance_map[key] = bal

            sheet.write(row, 0, str(line.date), cell_format)
            sheet.write(row, 1, line.move_id.journal_id.name or '', cell_format)
            sheet.write(row, 2, acc.code or '', cell_format)
            sheet.write(row, 3, acc.name or '', cell_format)
            sheet.write(row, 4, line.partner_id.name or '', cell_format)
            sheet.write(row, 5, line.name or '', cell_format)
            sheet.write(row, 6, float(line.debit), number_format)
            sheet.write(row, 7, float(line.credit), number_format)
            sheet.write(row, 8, float(bal), number_format)

            row += 1

        # ---------------------------------------------------
        # Column Widths
        # ---------------------------------------------------
        sheet.set_column(0, 0, 12)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 14)
        sheet.set_column(3, 3, 28)
        sheet.set_column(4, 4, 22)
        sheet.set_column(5, 5, 30)
        sheet.set_column(6, 8, 14)

        workbook.close()

        attachment = self.env['ir.attachment'].create({
            'name': f'general_ledger_{self.start_date}_{self.end_date}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(workbook_stream.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
        
    # def action_download_pdf(self):
    # # def action_preview_quotation(self):
    #     self.ensure_one()
    #     return {
    #         'type': 'ir.actions.act_url',
    #         'url': '/report/html/all_reports_full.general_ledger_pdf_template/%d' % self.id,
    #         'target': 'new',
    #     }
    
    def action_download_pdf(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/all_reports_full.general_ledger_pdf_template/%d' % self.id,
            'target': 'new',
        }

    def get_report_data(self):
        """Get data for PDF report"""   
        domain = [
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            ('parent_state', '=', 'posted')
        ]
        return self.env['account.move.line'].search(domain, order='date,account_id')


class GeneralLedgerLine(models.TransientModel):
    _name = 'general.ledger.line'
    _description = 'General Ledger Line'

    report_id = fields.Many2one('general.ledger.report', string='Report', ondelete='cascade')
    date = fields.Date(string='Date')
    journal = fields.Char(string='Journal')
    account_code = fields.Char(string='Account Code')
    account_name = fields.Char(string='Account Name')
    partner = fields.Char(string='Partner')
    label = fields.Char(string='Label')
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Credit')
    balance = fields.Float(string='Balance')