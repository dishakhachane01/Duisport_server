from odoo import api, fields, models


class AdvanceVendorReportWizard(models.TransientModel):
    _name = "advance.vendor.report.wizard"
    _description = "Advance to Vendors Report Wizard"


    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    # -----------------------------
    # PDF Action
    # -----------------------------
    def action_print_pdf(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/all_reports_full.advance_vendor_report_pdf/%d' % self.id,
            'target': 'new',
        }
        # return self.env.ref(
        #     "all_reports_full.action_advance_vendor_report_pdf"
        # ).report_action(self)

    # -----------------------------
    # XLSX Action (if needed later)
    # -----------------------------
    # def action_print_xlsx(self):
    #     return self.env.ref(
    #         "all_reports_full.action_advance_vendor_report_xlsx"
    #     ).report_action(self)

    # -----------------------------
    # DATA EXTRACTOR
    # -----------------------------
    # def get_report_data(self):
    #     AccountMoveLine = self.env['account.move.line']

    #     moves = AccountMoveLine.search([
    #         ('account_id.account_type', '=', 'payable'),
    #         ('date', '>=', self.date_from),
    #         ('date', '<=', self.date_to),
    #         ('company_id', '=', self.company_id.id),
    #         ('credit', '>', 0),
    #     ])

    #     vendors = {}

    #     for line in moves:
    #         vendor = line.partner_id

    #         if vendor.id not in vendors:
    #             vendors[vendor.id] = {
    #                 'vendor_name': vendor.name,
    #                 'entries': [],
    #                 'total_advance': 0,
    #             }

    #         vendors[vendor.id]['entries'].append({
    #             'date': line.date,
    #             'journal': line.journal_id.name,
    #             'ref': line.move_id.name,
    #             'amount': abs(line.balance),
    #         })

    #         vendors[vendor.id]['total_advance'] += abs(line.balance)

    #     return list(vendors.values())



    def get_report_data(self):
        AccountMoveLine = self.env['account.move.line']

        moves = AccountMoveLine.search([
            ('account_id.account_type', '=', 'payable'),
        ])

        print("STEP 1 - PAYABLE:", len(moves))

        moves = AccountMoveLine.search([
            ('account_id.account_type', '=', 'payable'),
            ('credit', '>', 0),
        ])

        print("STEP 2 - CREDIT:", len(moves))

        moves = AccountMoveLine.search([
            ('account_id.account_type', '=', 'payable'),
            ('credit', '>', 0),
            ('company_id', '=', self.company_id.id),
        ])

        print("STEP 3 - COMPANY:", len(moves))

        moves = AccountMoveLine.search([
            ('account_id.account_type', '=', 'payable'),
            ('credit', '>', 0),
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ])

        print("STEP 4 - DATE:", len(moves))

        return []



