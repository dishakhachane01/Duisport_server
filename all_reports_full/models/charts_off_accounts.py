# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io, base64
from datetime import datetime
from odoo.modules.module import get_module_resource 


try:
    import xlsxwriter
except Exception:
    xlsxwriter = None

class ChartOfAccountsReport(models.TransientModel):
    _name = 'chart.of.accounts.report'
    _description = 'Chart of Accounts Report'



    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True
    )
    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    line_ids = fields.One2many('chart.of.accounts.line', 'report_id', string='Lines')
    show_entries = fields.Boolean(string='Show Journal Entries', default=True)


    def action_view_report(self):
        """Fetch and display report data with entries"""
        self.line_ids.unlink()
        
        accounts = self.env['account.account'].search([], order='code')
        lines_to_create = []
        
        for acc in accounts:
            acc_type = ''
            if hasattr(acc, 'account_type'):
                acc_type = dict(acc._fields['account_type'].selection).get(acc.account_type, acc.account_type or '')
            
            # Get move lines for this account within date range
            domain = [
                ('account_id', '=', acc.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('parent_state', '=', 'posted')  # Only posted entries
            ]
            move_lines = self.env['account.move.line'].search(domain, order='date, id')
            
            # Create main account line
            lines_to_create.append({
                'report_id': self.id,
                'account_code': acc.code or '',
                'account_name': acc.name,
                'account_type': acc_type,
                'reconcile': 'Yes' if acc.reconcile else 'No',
                'is_account': True,
                'entry_count': len(move_lines),
            })
            
            # Create entry lines if show_entries is enabled
            if self.show_entries:
                for line in move_lines:
                    lines_to_create.append({
                        'report_id': self.id,
                        'is_account': False,
                        'entry_date': line.date,
                        'entry_reference': line.move_id.name or '',
                        'entry_label': line.name or '',
                        'entry_partner': line.partner_id.name or '',
                        'entry_debit': line.debit,
                        'entry_credit': line.credit,
                        'entry_balance': line.debit - line.credit,
                    })
        
        self.env['chart.of.accounts.line'].create(lines_to_create)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'chart.of.accounts.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_download_xlsx(self):

        self.ensure_one()

        if xlsxwriter is None:
            raise UserError(_('Python library xlsxwriter is required for Excel export.'))

        if not self.line_ids:
            raise UserError(_("Please click 'View Report' first to generate the data."))

        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('Chart of Accounts')

        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1
        })

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center'
        })

        account_format = workbook.add_format({
            'bold': True,
            'bg_color': '#EFEFEF'
        })

        number_format = workbook.add_format({
            'num_format': '#,##0.00'
        })

        row = 0

        # ---------------------------------------------------
        # HEADER IMAGE
        # ---------------------------------------------------

        module_path = get_module_resource(
            'all_reports_full',
            'static/src/img',
            'header2.png'
        )

        if module_path:
            sheet.insert_image(row, 0, module_path, {'x_scale': 0.8, 'y_scale': 0.8})
            row += 6

        # ---------------------------------------------------
        # TITLE
        # ---------------------------------------------------

        sheet.merge_range(row, 0, row, 10, 'Chart of Accounts Report', title_format)
        row += 2

        # ---------------------------------------------------
        # PERIOD
        # ---------------------------------------------------

        sheet.write(row, 0, f'Period: {self.date_from} to {self.date_to}')
        row += 2

        # ---------------------------------------------------
        # TABLE HEADERS
        # ---------------------------------------------------

        headers = [
            'Account Code', 'Account Name', 'Type', 'Reconcile',
            'Date', 'Reference', 'Label', 'Partner', 'Debit', 'Credit', 'Balance'
        ]

        for col, h in enumerate(headers):
            sheet.write(row, col, h, header_format)

        row += 1

        # ---------------------------------------------------
        # WRITE DATA
        # ---------------------------------------------------

        for line in self.line_ids:

            if line.is_account:
                sheet.write(row, 0, line.account_code or '', account_format)
                sheet.write(row, 1, line.account_name or '', account_format)
                sheet.write(row, 2, line.account_type or '', account_format)
                sheet.write(row, 3, line.reconcile or '', account_format)

            else:
                sheet.write(row, 4, line.entry_date.strftime('%Y-%m-%d') if line.entry_date else '')
                sheet.write(row, 5, line.entry_reference or '')
                sheet.write(row, 6, line.entry_label or '')
                sheet.write(row, 7, line.entry_partner or '')
                sheet.write(row, 8, line.entry_debit or 0.0, number_format)
                sheet.write(row, 9, line.entry_credit or 0.0, number_format)
                sheet.write(row, 10, line.entry_balance or 0.0, number_format)

            row += 1

        # ---------------------------------------------------
        # COLUMN WIDTH
        # ---------------------------------------------------

        sheet.set_column(0, 0, 15)
        sheet.set_column(1, 1, 30)
        sheet.set_column(2, 2, 20)
        sheet.set_column(3, 3, 10)
        sheet.set_column(4, 4, 12)
        sheet.set_column(5, 5, 18)
        sheet.set_column(6, 6, 30)
        sheet.set_column(7, 7, 25)
        sheet.set_column(8, 10, 15)

        workbook.close()

        # ---------------------------------------------------
        # CREATE ATTACHMENT
        # ---------------------------------------------------

        attachment = self.env['ir.attachment'].create({
            'name': f'chart_of_accounts_{self.date_from}_{self.date_to}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(workbook_stream.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # ---------------------------------------------------
        # DOWNLOAD ACTION
        # ---------------------------------------------------

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
 
    def action_download_pdf(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/all_reports_full.chart_of_accounts_pdf_template/%d' % self.id,
            'target': 'new',
        }
        # """Download PDF report"""
        # return self.env.ref('all_reports_full.report_chart_of_accounts_pdf').report_action(self)


class ChartOfAccountsLine(models.TransientModel):
    _name = 'chart.of.accounts.line'
    _description = 'Chart of Accounts Line'

    report_id = fields.Many2one('chart.of.accounts.report', string='Report', ondelete='cascade')
    
    # Account fields
    is_account = fields.Boolean(string='Is Account', default=False)
    account_code = fields.Char(string='Account Code')
    account_name = fields.Char(string='Account Name')
    account_type = fields.Char(string='Type')
    reconcile = fields.Char(string='Reconcile')
    entry_count = fields.Integer(string='Entry Count')
    
    # Entry fields
    entry_date = fields.Date(string='Date')
    entry_reference = fields.Char(string='Reference')
    entry_label = fields.Char(string='Label')
    entry_partner = fields.Char(string='Partner')
    entry_debit = fields.Float(string='Debit')
    entry_credit = fields.Float(string='Credit')
    entry_balance = fields.Float(string='Balance')