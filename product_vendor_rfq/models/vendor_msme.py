from odoo import models, fields
import base64
import io
import xlsxwriter

class ResPartnerMsme(models.Model):
    _inherit = 'res.partner'

    is_msme = fields.Boolean("MSME Vendor")
    udyam_number = fields.Char("Udyam Registration Number")

    def action_download_msme_list(self):
        """Generate and download MSME vendor list as Excel"""

        vendors = self.env['res.partner'].search([
            ('is_msme', '=', True)
        ])

        # Create Excel in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("MSME Vendors")

        headers = ["Vendor Name", "Udyam Number", "GSTIN", "PAN", "Phone", "Email"]
        for col, head in enumerate(headers):
            sheet.write(0, col, head)

        row = 1
        for v in vendors:
            sheet.write(row, 0, v.name or '')
            sheet.write(row, 1, v.udyam_number or '')
            sheet.write(row, 2, v.vat or '')
            sheet.write(row, 3, v.l10n_in_pan or '')
            sheet.write(row, 4, v.phone or '')
            sheet.write(row, 5, v.email or '')
            row += 1

        workbook.close()
        output.seek(0)
        file_data = output.read()
        output.close()

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'MSME_Vendors.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }