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

class JournalRegisterReport(models.TransientModel):
    _name = 'journal.register.report'
    _description = 'Journal Register Report'


    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True
    )
    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True)
    target_move = fields.Selection([
        ('posted', 'Posted Entries'),
        ('all', 'All Entries')
    ], string='Target Moves', required=True, default='posted')
    line_ids = fields.One2many('journal.register.line', 'report_id', string='Lines')

    def action_view_report(self):
        """Fetch and display journal register data"""
        self.line_ids.unlink()
        
        # Build domain
        domain = [
            ('journal_id', 'in', self.journal_ids.ids),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        
        if self.target_move == 'posted':
            domain.append(('state', '=', 'posted'))
        
        # Get journal entries
        journal_entries = self.env['account.move'].search(domain, order='date, name')
        
        lines_to_create = []
        
        for move in journal_entries:
            # Create journal entry header
            lines_to_create.append({
                'report_id': self.id,
                'is_header': True,
                'move_id': move.id,
                'move_name': move.name or '',
                'move_date': move.date,
                'journal_id': move.journal_id.id,
                'journal_name': move.journal_id.name,
                'partner_id': move.partner_id.id if move.partner_id else False,
                'partner_name': move.partner_id.name if move.partner_id else '',
                'reference': move.ref or '',
                'state': dict(move._fields['state'].selection).get(move.state, move.state),
            })
            
            # Create lines for each move line
            for line in move.line_ids:
                lines_to_create.append({
                    'report_id': self.id,
                    'is_header': False,
                    'move_id': move.id,
                    'account_code': line.account_id.code or '',
                    'account_name': line.account_id.name or '',
                    'line_name': line.name or '',
                    'line_partner': line.partner_id.name if line.partner_id else '',
                    'debit': line.debit,
                    'credit': line.credit,
                    'balance': line.debit - line.credit,
                })
        
        self.env['journal.register.line'].create(lines_to_create)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'journal.register.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_download_xlsx(self):
        """Download Excel report"""

        self.ensure_one()

        if xlsxwriter is None:
            raise UserError(_('Python library xlsxwriter is required for Excel export.'))

        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('Journal Register')

        # ---------------------------------------------------
        # Formats
        # ---------------------------------------------------

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center'
        })

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'center'
        })

        entry_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E8E8E8',
            'border': 1
        })

        number_format = workbook.add_format({'num_format': '#,##0.00'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})

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

        sheet.merge_range(row, 0, row, 9, 'Journal Register Report', title_format)
        row += 2

        # ---------------------------------------------------
        # REPORT INFO
        # ---------------------------------------------------

        sheet.write(row, 0, f'Period: {self.date_from} to {self.date_to}')
        row += 1

        journal_names = ', '.join(self.journal_ids.mapped('name'))
        sheet.write(row, 0, f'Journals: {journal_names}')
        row += 1

        sheet.write(row, 0, f'Target Moves: {dict(self._fields["target_move"].selection).get(self.target_move)}')
        row += 2

        # ---------------------------------------------------
        # TABLE HEADERS
        # ---------------------------------------------------

        headers = [
            'Account',
            'Label',
            'Partner',
            'Debit',
            'Credit',
            'Balance'
        ]

        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)

        row += 1

        # ---------------------------------------------------
        # BUILD DOMAIN
        # ---------------------------------------------------

        domain = [
            ('journal_id', 'in', self.journal_ids.ids),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]

        if self.target_move == 'posted':
            domain.append(('state', '=', 'posted'))

        journal_entries = self.env['account.move'].search(domain, order='date, name')

        grand_total_debit = 0
        grand_total_credit = 0

        # ---------------------------------------------------
        # WRITE DATA
        # ---------------------------------------------------

        for move in journal_entries:

            # Journal Entry Header
            header_text = f"{move.date} - {move.name} - {move.journal_id.name}"

            if move.partner_id:
                header_text += f" - Partner: {move.partner_id.name}"

            if move.ref:
                header_text += f" - Ref: {move.ref}"

            header_text += f" - Status: {dict(move._fields['state'].selection).get(move.state)}"

            sheet.merge_range(row, 0, row, 5, header_text, entry_header_format)
            row += 1

            move_debit = 0
            move_credit = 0

            for line in move.line_ids:

                sheet.write(row, 0, f"{line.account_id.code or ''} - {line.account_id.name or ''}")
                sheet.write(row, 1, line.name or '')
                sheet.write(row, 2, line.partner_id.name if line.partner_id else '')
                sheet.write(row, 3, line.debit, number_format)
                sheet.write(row, 4, line.credit, number_format)
                sheet.write(row, 5, line.debit - line.credit, number_format)

                move_debit += line.debit
                move_credit += line.credit

                row += 1

            # Entry total
            sheet.write(row, 2, 'Entry Total:', entry_header_format)
            sheet.write(row, 3, move_debit, number_format)
            sheet.write(row, 4, move_credit, number_format)
            sheet.write(row, 5, move_debit - move_credit, number_format)

            row += 2

            grand_total_debit += move_debit
            grand_total_credit += move_credit

        # ---------------------------------------------------
        # GRAND TOTAL
        # ---------------------------------------------------

        sheet.write(row, 2, 'GRAND TOTAL:', entry_header_format)
        sheet.write(row, 3, grand_total_debit, number_format)
        sheet.write(row, 4, grand_total_credit, number_format)
        sheet.write(row, 5, grand_total_debit - grand_total_credit, number_format)

        # ---------------------------------------------------
        # COLUMN WIDTH
        # ---------------------------------------------------

        sheet.set_column(0, 0, 35)
        sheet.set_column(1, 1, 35)
        sheet.set_column(2, 2, 25)
        sheet.set_column(3, 5, 15)

        workbook.close()

        attachment = self.env['ir.attachment'].create({
            'name': f'journal_register_{self.date_from}_{self.date_to}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(workbook_stream.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }




    def action_download_pdf(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/all_reports_full.journal_register_pdf_template/%d' % self.id,
            'target': 'new',
        }
        # """Download PDF report"""
        # return self.env.ref('all_reports_full.report_journal_register_pdf').report_action(self)


class JournalRegisterLine(models.TransientModel):
    _name = 'journal.register.line'
    _description = 'Journal Register Line'

    report_id = fields.Many2one('journal.register.report', string='Report', ondelete='cascade')
    
    # Header fields (for journal entry header)
    is_header = fields.Boolean(string='Is Header', default=False)
    move_id = fields.Many2one('account.move', string='Journal Entry')
    move_name = fields.Char(string='Entry Number')
    move_date = fields.Date(string='Date')
    journal_id = fields.Many2one('account.journal', string='Journal')
    journal_name = fields.Char(string='Journal Name')
    partner_id = fields.Many2one('res.partner', string='Partner')
    partner_name = fields.Char(string='Partner Name')
    reference = fields.Char(string='Reference')
    state = fields.Char(string='Status')
    
    # Line fields (for journal entry lines)
    account_code = fields.Char(string='Account Code')
    account_name = fields.Char(string='Account Name')
    line_name = fields.Char(string='Label')
    line_partner = fields.Char(string='Partner')
    debit = fields.Float(string='Debit', digits=(16, 2))
    credit = fields.Float(string='Credit', digits=(16, 2))
    balance = fields.Float(string='Balance', digits=(16, 2))