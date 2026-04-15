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

class StockRegisterReport(models.TransientModel):
    _name = 'stock.register.report'
    _description = 'Stock Register Report'


    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True
    )
    start_date = fields.Date(string='From Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='To Date', required=True, default=fields.Date.context_today)
    product_ids = fields.Many2many('product.product', string='Products')
    category_ids = fields.Many2many('product.category', string='Product Categories')
    line_ids = fields.One2many('stock.register.line', 'report_id', string='Lines')
    report_generated = fields.Boolean(string='Report Generated', default=False)

    def _get_domain(self):
        """Build search domain based on filters"""
        domain = [
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            ('state', '=', 'done')
        ]
        
        # Product filter
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        
        # Category filter
        if self.category_ids:
            domain.append(('product_id.categ_id', 'child_of', self.category_ids.ids))
        
        return domain

    def action_generate_report(self):
        """Generate and display report data"""
        self.line_ids.unlink()
        
        domain = self._get_domain()
        moves = self.env['stock.move'].search(domain, order='date, product_id')
        
        if not moves:
            raise UserError(_('No stock moves found for the selected filters.'))
        
        lines_to_create = []
        
        for m in moves:
            lines_to_create.append({
                'report_id': self.id,
                'date': m.date,
                'reference': m.reference or m.picking_id.name or '',
                'product_name': m.product_id.name or '',
                'sku': m.product_id.default_code or '',
                'category': m.product_id.categ_id.name or '',
                'quantity': m.product_uom_qty or 0.0,
                'uom': m.product_uom.name or '',
                'source_location': m.location_id.complete_name or '',
                'dest_location': m.location_dest_id.complete_name or '',
                'status': m.state or '',
            })
        
        self.env['stock.register.line'].create(lines_to_create)
        self.report_generated = True
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.register.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'form_view_initial_mode': 'edit'}
        }

    def action_download_xlsx(self):
        """Download Excel report (Stock Register)"""
        if not self.report_generated:
            raise UserError(_('Please generate the report first by clicking "Generate Report" button.'))

        if xlsxwriter is None:
            raise UserError(_('Python library xlsxwriter is required for Excel export.'))

        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('Stock Register')

        # Formats
        header_format = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
        cell_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({'border': 1, 'align': 'right', 'num_format': '#,##0.00'})
        total_format = workbook.add_format({'bold': True, 'border': 1})

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
        title_format = workbook.add_format({'bold': True, 'align': 'center', 'font_size': 16})
        sheet.merge_range(row, 0, row, 9, 'Stock Register Report', title_format)
        row += 2

        # ---------------------------------------------------
        # Period + Generated time
        # ---------------------------------------------------
        sheet.write(row, 0, 'Period:')
        sheet.write(row, 1, f"{self.start_date} to {self.end_date}")

        sheet.write(row, 6, 'Generated:')
        sheet.write(row, 7, fields.Datetime.now().strftime('%Y-%m-%d %H:%M'))
        row += 2

        # ---------------------------------------------------
        # Filters
        # ---------------------------------------------------
        if self.product_ids or self.category_ids:
            sheet.write(row, 0, 'Filters Applied:')
            row += 1

            if self.product_ids:
                products = ", ".join(self.product_ids.mapped('name'))
                sheet.write(row, 0, 'Products:')
                sheet.write(row, 1, products)
                row += 1

            if self.category_ids:
                cats = ", ".join(self.category_ids.mapped('name'))
                sheet.write(row, 0, 'Categories:')
                sheet.write(row, 1, cats)
                row += 1

            row += 1

        # ---------------------------------------------------
        # Table Headers
        # ---------------------------------------------------
        headers = [
            'Date', 'Reference', 'Product', 'SKU', 'Category',
            'Quantity', 'UOM', 'Source Location', 'Destination Location', 'Status'
        ]

        for col, h in enumerate(headers):
            sheet.write(row, col, h, header_format)

        row += 1

        total_qty = 0

        # ---------------------------------------------------
        # Data Rows
        # ---------------------------------------------------
        domain = self._get_domain()
        moves = self.env['stock.move'].search(domain, order='date, product_id')

        for m in moves:
            sheet.write(row, 0, str(m.date), cell_format)
            sheet.write(row, 1, m.reference or m.picking_id.name or '', cell_format)
            sheet.write(row, 2, m.product_id.name or '', cell_format)
            sheet.write(row, 3, m.product_id.default_code or '', cell_format)
            sheet.write(row, 4, m.product_id.categ_id.name or '', cell_format)
            sheet.write(row, 5, float(m.product_uom_qty or 0.0), number_format)
            sheet.write(row, 6, m.product_uom.name or '', cell_format)
            sheet.write(row, 7, m.location_id.complete_name or '', cell_format)
            sheet.write(row, 8, m.location_dest_id.complete_name or '', cell_format)
            sheet.write(row, 9, m.state or '', cell_format)

            total_qty += m.product_uom_qty or 0.0
            row += 1

        # ---------------------------------------------------
        # Total Row
        # ---------------------------------------------------
        sheet.write(row, 4, 'Total:', total_format)
        sheet.write(row, 5, total_qty, total_format)

        # Column Widths
        sheet.set_column(0, 0, 12)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 30)
        sheet.set_column(3, 3, 15)
        sheet.set_column(4, 4, 20)
        sheet.set_column(5, 5, 12)
        sheet.set_column(6, 6, 10)
        sheet.set_column(7, 8, 25)
        sheet.set_column(9, 9, 12)

        workbook.close()

        filename = f'stock_register_{self.start_date}_{self.end_date}.xlsx'

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(workbook_stream.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
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
            'url': '/report/pdf/all_reports_full.stock_register_pdf_template/%d' % self.id,
            'target': 'new',
        }

        # """Download PDF report"""
        # if not self.report_generated:
        #     raise UserError(_('Please generate the report first by clicking "Generate Report" button.'))
            
        # return self.env.ref('all_reports_full.report_stock_register_pdf').report_action(self)

    def get_report_data(self):
        """Get data for PDF report"""
        domain = self._get_domain()
        return self.env['stock.move'].search(domain, order='date, product_id')


class StockRegisterLine(models.TransientModel):
    _name = 'stock.register.line'
    _description = 'Stock Register Line'

    report_id = fields.Many2one('stock.register.report', string='Report', ondelete='cascade')
    date = fields.Date(string='Date')
    reference = fields.Char(string='Reference')
    product_name = fields.Char(string='Product')
    sku = fields.Char(string='SKU')
    category = fields.Char(string='Category')
    quantity = fields.Float(string='Quantity')
    uom = fields.Char(string='UOM')
    source_location = fields.Char(string='Source Location')
    dest_location = fields.Char(string='Destination Location')
    status = fields.Char(string='Status')