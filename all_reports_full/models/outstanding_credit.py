# -*- coding: utf-8 -*-
from odoo import api, fields, models


class OutstandingCreditNotesWizard(models.TransientModel):
    _name = "outstanding.credit.notes.wizard"
    _description = "Outstanding Credit Notes Report Wizard"

    date_from = fields.Date(string="From (optional)")
    date_to = fields.Date(string="As of (required)", required=True)
    partner_ids = fields.Many2many(
        "res.partner",
        string="Partners (optional)",
        help="Select partners to restrict the report. Leave empty for all."
    )
    partner_type = fields.Selection(
        [
            ("both", "Both"),
            ("customer", "Customer"),
            ("supplier", "Supplier"),
        ],
        string="Type",
        default="both",
        help="Choose which credit notes to include"
    )

    def action_print_outstanding_credit_notes(self):
        self.ensure_one()

        url = '/report/pdf/all_reports_full.outstanding_credit_notes_template/%s?date_from=%s&date_to=%s&partner_ids=%s&partner_type=%s' % (
            self.id,
            self.date_from or '',
            self.date_to or '',
            ','.join(map(str, self.partner_ids.ids)) if self.partner_ids else '',
            self.partner_type or ''
        )

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


from odoo import api, models
from odoo.http import request

class ReportOutstandingCreditNotes(models.AbstractModel):
    _name = "report.all_reports_full.outstanding_credit_notes_template"
    _description = "Outstanding Credit Notes QWeb Report"

    @api.model
    def _get_report_values(self, docids, data=None):

        # ============================================
        # ✅ 1. GET DATA FROM URL (act_url)
        # ============================================
        params = request.httprequest.args

        if params:
            date_from = params.get("date_from")
            date_to = params.get("date_to")
            partner_ids = params.get("partner_ids")
            partner_type = params.get("partner_type") or "both"

            partner_ids = [int(x) for x in partner_ids.split(',')] if partner_ids else []

        # ============================================
        # ✅ 2. FALLBACK (report_action)
        # ============================================
        elif data:
            date_from = data.get("date_from")
            date_to = data.get("date_to")
            partner_ids = data.get("partner_ids") or []
            partner_type = data.get("partner_type") or "both"

        else:
            wizard = self.env["outstanding.credit.notes.wizard"].browse(docids)
            date_from = wizard.date_from
            date_to = wizard.date_to
            partner_ids = wizard.partner_ids.ids
            partner_type = wizard.partner_type

        # ============================================
        # ✅ 3. DOMAIN
        # ============================================
        move_types = []
        if partner_type in ("both", "customer"):
            move_types.append("out_refund")
        if partner_type in ("both", "supplier"):
            move_types.append("in_refund")

        domain = [
            ("move_type", "in", move_types),
            ("state", "=", "posted"),
            ("amount_residual", ">", 0.0),
        ]

        if date_to:
            domain.append(("invoice_date", "<=", date_to))

        if date_from:
            domain.append(("invoice_date", ">=", date_from))

        if partner_ids:
            domain.append(("partner_id", "in", partner_ids))

        # ============================================
        # ✅ 4. FETCH DATA
        # ============================================
        moves = self.env["account.move"].search(
            domain, order="partner_id, invoice_date, id"
        )

        # ============================================
        # ✅ 5. GROUPING
        # ============================================
        partners = {}
        grand_total = 0.0

        for m in moves:
            pid = m.partner_id.id or 0

            partners.setdefault(pid, {
                "partner": m.partner_id,
                "lines": [],
                "total_residual": 0.0
            })

            line = {
                "move_id": m.id,
                "move_name": m.name or m.display_name,
                "date": m.invoice_date,
                "journal": m.journal_id.name,
                "origin": m.invoice_origin or m.ref or "",
                "amount_total": m.amount_total,
                "amount_residual": m.amount_residual,
                "currency": m.currency_id,
            }

            partners[pid]["lines"].append(line)
            partners[pid]["total_residual"] += m.amount_residual
            grand_total += m.amount_residual

        grouped = sorted(
            partners.values(),
            key=lambda x: (x["partner"].name or "")
        )

        # ============================================
        # ✅ 6. RETURN
        # ============================================
        return {
            "doc_ids": docids,
            "doc_model": "outstanding.credit.notes.wizard",
            "docs": self.env["outstanding.credit.notes.wizard"].browse(docids),

            "date_from": date_from,
            "date_to": date_to,
            "partner_type": partner_type,

            "grouped": grouped,
            "grand_total": grand_total,
        }



# class ReportOutstandingCreditNotes(models.AbstractModel):
#     _name = "report.all_reports_full.outstanding_credit_notes_template"
#     _description = "Outstanding Credit Notes QWeb Report"

#     @api.model
#     def _get_report_values(self, docids, data=None):
#         # read data
#         date_from = data.get("date_from")
#         date_to = data.get("date_to")
#         partner_ids = data.get("partner_ids") or []
#         partner_type = data.get("partner_type") or "both"

#         # move types to include
#         move_types = []
#         if partner_type in ("both", "customer"):
#             # customer credit notes
#             move_types.append("out_refund")
#         if partner_type in ("both", "supplier"):
#             # supplier credit notes
#             move_types.append("in_refund")

#         domain = [
#             ("move_type", "in", move_types),
#             ("state", "=", "posted"),
#             ("amount_residual", ">", 0.0),
#             ("invoice_date", "<=", date_to) if date_to else ("invoice_date", "!=", False),
#         ]

#         # If date_from provided, consider only credit notes dated on/after date_from
#         if date_from:
#             domain.append(("invoice_date", ">=", date_from))

#         if partner_ids:
#             domain.append(("partner_id", "in", partner_ids))

#         # search moves
#         moves = self.env["account.move"].search(domain, order="partner_id, invoice_date, id")

#         # prepare report data structure: grouped by partner
#         partners = {}
#         grand_total = 0.0
#         for m in moves:
#             pid = m.partner_id.id or 0
#             partners.setdefault(pid, {"partner": m.partner_id, "lines": [], "total_residual": 0.0})
#             line = {
#                 "move_id": m.id,
#                 "move_name": m.name or m.display_name,
#                 "date": m.invoice_date,
#                 "journal": m.journal_id.name,
#                 "origin": m.invoice_origin or m.ref or "",
#                 "amount_total": m.amount_total,
#                 "amount_residual": m.amount_residual,
#                 "currency": m.currency_id,
#             }
#             partners[pid]["lines"].append(line)
#             partners[pid]["total_residual"] += m.amount_residual
#             grand_total += m.amount_residual

#         grouped = [partners[k] for k in sorted(partners.keys(), key=lambda x: (partners[x]["partner"].name or ""))]

#         return {
#             "doc_ids": docids,
#             "doc_model": "outstanding.credit.notes.wizard",
#             "data": data,
#             "date_from": date_from,
#             "date_to": date_to,
#             "partner_type": partner_type,
#             "grouped": grouped,
#             "grand_total": grand_total,
#         }
