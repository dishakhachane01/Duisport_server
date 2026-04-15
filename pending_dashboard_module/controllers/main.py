# controllers/main.py
from odoo import http
from odoo.http import request


class PendingDashboardController(http.Controller):

    # @http.route('/pending_dashboard/data', type='json', auth='user')
    # def get_dashboard_data(self):

    #     user = request.env.user
    #     env = request.env
    #     company = request.env.company

    #     if not user.has_group('product_vendor_rfq.group_management_approval'):
    #         return {
    #             'po_count': 0,
    #             'po_list': [],
    #             'rfq_count': 0,
    #             'rfq_list': [],
    #             'vendor_count': 0,
    #             'vendor_list': [],
    #         }

    #     po_domain = [('state', '=', 'to_approve_management'),  ('company_id', '=', company.id)]
    #     rfq_domain = [('state', '=', 'waiting'),  ('company_id', '=', company.id)]   # ✅ FIXED

    #     pos = env['purchase.order'].search(po_domain, limit=10)
    #     rfqs = env['rfq.request'].search(rfq_domain, limit=10)

    #     vendor_domain = [('vendor_approval_state', '=', 'to_approve_management')]
    #     vendors = env['res.partner'].search(vendor_domain, limit=10)


    #     return {
    #         'po_count': env['purchase.order'].search_count(po_domain),

    #         'po_list': [{
    #             'id': p.id,
    #             'name': p.name,
    #             'partner': p.partner_id.name,
    #             'amount': p.amount_total,
    #         } for p in pos],

    #         'rfq_count': env['rfq.request'].search_count(rfq_domain),

    #         'rfq_list': [{
    #             'id': r.id,
    #             'name': r.name,
    #             'date': str(r.date) if r.date else '',
    #             'state': r.state,
    #         } for r in rfqs],

    #         'vendor_count': env['res.partner'].search_count(vendor_domain),

    #         'vendor_list': [{
    #             'id': v.id,
    #             'name': v.name,
    #             'email': v.email or '',
    #             'state': v.vendor_approval_state,
    #         } for v in vendors],
    #     }

    @http.route('/pending_dashboard/data', type='json', auth='user')
    def get_dashboard_data(self):

        user = request.env.user
        env = request.env
        company = request.env.company

        # ================= DETERMINE ROLE =================
        is_management = user.has_group('product_vendor_rfq.group_management_approval')
        is_accounts = user.has_group('product_vendor_rfq.group_accounts_approval')

        if not (is_management or is_accounts):
            return {
                'po_count': 0,
                'po_list': [],
                'vendor_count': 0,
                'vendor_list': [],
                'rfq_count': 0,
                'rfq_list': [],
            }

        # ================= DOMAIN BASED ON ROLE =================
        if is_management:
            po_domain = [('state', '=', 'to_approve_management'), ('company_id', '=', company.id)]
            vendor_domain = [('vendor_approval_state', '=', 'to_approve_management')]
            
            # RFQ only for management
            rfq_domain = [('state', '=', 'received'), ('company_id', '=', company.id)]
            rfq_enabled = True

        else:  # ACCOUNTS
            po_domain = [('state', '=', 'to_approve_accounts'), ('company_id', '=', company.id)]
            vendor_domain = [('vendor_approval_state', '=', 'to_approve_accounts')]
            
            rfq_domain = []
            rfq_enabled = False

        # ================= FETCH DATA =================
        pos = env['purchase.order'].search(po_domain, limit=10)
        vendors = env['res.partner'].search(vendor_domain, limit=10)

        rfqs = env['rfq.request'].search(rfq_domain, limit=10) if rfq_enabled else env['rfq.request']

        # ================= RESPONSE =================
        return {
            # ---------- PO ----------
            'po_count': env['purchase.order'].search_count(po_domain),
            'po_list': [{
                'id': p.id,
                'name': p.name,
                'partner': p.partner_id.name,
                'amount': p.amount_total,
            } for p in pos],

            # ---------- VENDOR ----------
            'vendor_count': env['res.partner'].search_count(vendor_domain),
            'vendor_list': [{
                'id': v.id,
                'name': v.name,
                'email': v.email or '',
                'state': v.vendor_approval_state,
            } for v in vendors],

            # ---------- RFQ (ONLY MANAGEMENT) ----------
            'rfq_enabled': rfq_enabled,

            'rfq_count': env['rfq.request'].search_count(rfq_domain) if rfq_enabled else 0,

            'rfq_list': [{
                'id': r.id,
                'name': r.name,
                'date': str(r.date) if r.date else '',
                'state': r.state,
            } for r in rfqs] if rfq_enabled else [],
        }

class DashboardController(http.Controller):

    @http.route('/dashboard/stats', type='json', auth='user')
    def get_dashboard_stats(self):

        user = request.env.user
        env = request.env
        company = request.env.company

        # ✅ Restrict to Management
        if not user.has_group('product_vendor_rfq.group_management_approval'):
            return {
                'sales': {},
                'inventory': {},
                'manufacturing': {},
            }

        sale_data = {
            'draft': env['sale.order'].search_count([('state', '=', 'draft'), ('company_id', '=', company.id)]),
            'sent': env['sale.order'].search_count([('state', '=', 'sent'), ('company_id', '=', company.id)]),
            'sale': env['sale.order'].search_count([('state', '=', 'sale'), ('company_id', '=', company.id)]),
        }

        stock_data = {
            'waiting': env['stock.picking'].search_count([('state', '=', 'waiting'), ('company_id', '=', company.id)]),
            'assigned': env['stock.picking'].search_count([('state', '=', 'assigned'),  ('company_id', '=', company.id)]),
            'done': env['stock.picking'].search_count([('state', '=', 'done'),  ('company_id', '=', company.id)]),
        }

        mrp_data = {
            'draft': env['mrp.production'].search_count([('state', '=', 'draft'),  ('company_id', '=', company.id)]),
            'confirmed': env['mrp.production'].search_count([('state', '=', 'confirmed'),  ('company_id', '=', company.id)]),
            'done': env['mrp.production'].search_count([('state', '=', 'done'),  ('company_id', '=', company.id)]),
        }

        return {
            'sales': sale_data,
            'inventory': stock_data,
            'manufacturing': mrp_data,
        }