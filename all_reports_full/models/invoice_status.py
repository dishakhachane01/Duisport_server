from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class InvoiceStatusWizard(models.TransientModel):
    _name = 'invoice.status.wizard'
    _description = 'Invoice Status Report Wizard'



    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True
    )
    date_from = fields.Date(string='Date From', required=False, 
                            default=lambda self: fields.Date.today())
    date_to = fields.Date(string='Date To', required=False, 
                          default=lambda self: fields.Date.today())
    partner_ids = fields.Many2many('res.partner', string='Customers')
    invoice_type = fields.Selection([
        ('out_invoice', 'Customer Invoices'),
        ('in_invoice', 'Vendor Bills'),
        ('out_refund', 'Customer Credit Notes'),
        ('in_refund', 'Vendor Credit Notes'),
        ('all', 'All Types')
    ], string='Invoice Type', default='out_invoice', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All States')
    ], string='Status', default='all', required=True)
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
        ('all', 'All Payment States')
    ], string='Payment Status', default='all')



    def print_report(self):
        self.ensure_one()

        url = '/report/pdf/all_reports_full.invoice_status_template/%s?date_from=%s&date_to=%s&partner_ids=%s&invoice_type=%s&state=%s&payment_state=%s' % (
            self.id,
            self.date_from or '',
            self.date_to or '',
            ','.join(map(str, self.partner_ids.ids)) if self.partner_ids else '',
            self.invoice_type or '',
            self.state or '',
            self.payment_state or ''
        )

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


    # def print_report(self):
    #     self.ensure_one()
    #     data = {
    #         'ids': self.ids,
    #         'model': self._name,
    #         'form': {
    #             'date_from': self.date_from.strftime('%Y-%m-%d') if self.date_from else False,
    #             'date_to': self.date_to.strftime('%Y-%m-%d') if self.date_to else False,
    #             'partner_ids': self.partner_ids.ids,
    #             'invoice_type': self.invoice_type,
    #             'state': self.state,
    #             'payment_state': self.payment_state,
    #         }
    #     }


    #     # return self.env.ref('all_reports_full.action_invoice_status_report').report_action(self, data=data)


from odoo import api, models, fields
from odoo.http import request

class InvoiceStatusReport(models.AbstractModel):
    _name = 'report.all_reports_full.invoice_status_template'
    _description = 'Invoice Status Report'

    def _safe_sum(self, recordset, field_name):
        try:
            if not recordset:
                return 0.0
            result = sum(recordset.mapped(field_name))
            return result if result is not None else 0.0
        except:
            return 0.0

    @api.model
    def _get_report_values(self, docids, data=None):

        # ============================================
        # ✅ 1. GET DATA (URL → act_url support)
        # ============================================
        params = request.httprequest.args

        if params:
            date_from = params.get('date_from')
            date_to = params.get('date_to')
            partner_ids = params.get('partner_ids')
            invoice_type = params.get('invoice_type')
            state = params.get('state')
            payment_state = params.get('payment_state')

            partner_ids = [int(x) for x in partner_ids.split(',')] if partner_ids else []

        # ============================================
        # ✅ 2. FALLBACK (report_action support)
        # ============================================
        elif data and data.get('form'):
            form_data = data['form']
            date_from = form_data.get('date_from')
            date_to = form_data.get('date_to')
            partner_ids = form_data.get('partner_ids', [])
            invoice_type = form_data.get('invoice_type', 'out_invoice')
            state = form_data.get('state', 'all')
            payment_state = form_data.get('payment_state', 'all')

        # ============================================
        # ✅ 3. LAST FALLBACK (wizard record)
        # ============================================
        else:
            wizard = self.env['invoice.status.wizard'].browse(docids)
            date_from = wizard.date_from
            date_to = wizard.date_to
            partner_ids = wizard.partner_ids.ids
            invoice_type = wizard.invoice_type
            state = wizard.state
            payment_state = wizard.payment_state

        # ============================================
        # ✅ 4. BUILD DOMAIN
        # ============================================
        domain = []

        # Invoice type
        if invoice_type and invoice_type != 'all':
            domain.append(('move_type', '=', invoice_type))
        else:
            domain.append(('move_type', 'in', [
                'out_invoice', 'in_invoice', 'out_refund', 'in_refund'
            ]))

        # State
        if state and state != 'all':
            domain.append(('state', '=', state))

        # Payment state
        if payment_state and payment_state != 'all':
            domain.append(('payment_state', '=', payment_state))

        # Partner
        if partner_ids:
            domain.append(('partner_id', 'in', partner_ids))

        # Date filters
        if date_from:
            domain.append(('invoice_date', '>=', date_from))

        if date_to:
            domain.append(('invoice_date', '<=', date_to))

        # ============================================
        # ✅ 5. FETCH DATA
        # ============================================
        invoices = self.env['account.move'].search(domain, order='invoice_date desc')

        # ============================================
        # ✅ 6. GROUPING
        # ============================================
        draft_invoices = invoices.filtered(lambda i: i.state == 'draft')
        posted_invoices = invoices.filtered(lambda i: i.state == 'posted')
        cancelled_invoices = invoices.filtered(lambda i: i.state == 'cancel')

        not_paid = invoices.filtered(lambda i: i.payment_state == 'not_paid')
        partial_paid = invoices.filtered(lambda i: i.payment_state == 'partial')
        paid = invoices.filtered(lambda i: i.payment_state == 'paid')

        # ============================================
        # ✅ 7. TOTALS
        # ============================================
        total_draft = self._safe_sum(draft_invoices, 'amount_total')
        total_posted = self._safe_sum(posted_invoices, 'amount_total')
        total_cancelled = self._safe_sum(cancelled_invoices, 'amount_total')

        total_not_paid = self._safe_sum(not_paid, 'amount_residual')
        total_paid = self._safe_sum(paid, 'amount_total')
        total_partial = self._safe_sum(partial_paid, 'amount_residual')

        grand_total = self._safe_sum(invoices, 'amount_total')
        total_due = self._safe_sum(invoices, 'amount_residual')

        # ============================================
        # ✅ 8. CUSTOMER SUMMARY
        # ============================================
        customer_summary = []
        customer_dict = {}

        for inv in invoices:
            partner = inv.partner_id
            if not partner:
                continue

            if partner.id not in customer_dict:
                customer_dict[partner.id] = {
                    'partner_name': partner.name,
                    'invoice_count': 0,
                    'total_amount': 0.0,
                    'total_due': 0.0,
                }

            customer_dict[partner.id]['invoice_count'] += 1
            customer_dict[partner.id]['total_amount'] += inv.amount_total or 0.0
            customer_dict[partner.id]['total_due'] += inv.amount_residual or 0.0

        customer_summary = sorted(
            customer_dict.values(),
            key=lambda x: x['total_amount'],
            reverse=True
        )

        # ============================================
        # ✅ 9. LABELS
        # ============================================
        invoice_type_labels = {
            'out_invoice': 'Customer Invoices',
            'in_invoice': 'Vendor Bills',
            'out_refund': 'Customer Credit Notes',
            'in_refund': 'Vendor Credit Notes',
            'all': 'All Types'
        }

        # ============================================
        # ✅ 10. RETURN
        # ============================================
        return {
            'doc_ids': docids,
            'doc_model': 'invoice.status.wizard',
            'docs': self.env['invoice.status.wizard'].browse(docids),

            'date_from': date_from or '',
            'date_to': date_to or '',

            'invoice_type_label': invoice_type_labels.get(invoice_type, 'All Types'),

            'invoices': invoices,
            'invoice_count': len(invoices),

            'draft_count': len(draft_invoices),
            'posted_count': len(posted_invoices),
            'cancelled_count': len(cancelled_invoices),

            'not_paid_count': len(not_paid),
            'partial_count': len(partial_paid),
            'paid_count': len(paid),

            'total_draft': total_draft,
            'total_posted': total_posted,
            'total_cancelled': total_cancelled,

            'total_not_paid': total_not_paid,
            'total_paid': total_paid,
            'total_partial': total_partial,

            'grand_total': grand_total,
            'total_due': total_due,

            'customer_summary': customer_summary,

            'company_name': self.env.company.name,
        }
        _logger.info("#"*80)
        _logger.info("INVOICE STATUS REPORT - _get_report_values CALLED")
        _logger.info(f"docids: {docids}")
        _logger.info(f"data: {data}")
        
        # Get wizard data
        if data and data.get('form'):
            form_data = data['form']
            date_from = form_data.get('date_from')
            date_to = form_data.get('date_to')
            partner_ids = form_data.get('partner_ids', [])
            invoice_type = form_data.get('invoice_type', 'out_invoice')
            state = form_data.get('state', 'all')
            payment_state = form_data.get('payment_state', 'all')
            _logger.info("Data source: FORM DATA")
        else:
            wizard = self.env['invoice.status.wizard'].browse(docids)
            if wizard:
                date_from = wizard.date_from.strftime('%Y-%m-%d') if wizard.date_from else False
                date_to = wizard.date_to.strftime('%Y-%m-%d') if wizard.date_to else False
                partner_ids = wizard.partner_ids.ids
                invoice_type = wizard.invoice_type
                state = wizard.state
                payment_state = wizard.payment_state
                _logger.info("Data source: WIZARD BROWSE")
            else:
                date_from = fields.Date.today().strftime('%Y-%m-%d')
                date_to = fields.Date.today().strftime('%Y-%m-%d')
                partner_ids = []
                invoice_type = 'all'
                state = 'all'
                payment_state = 'all'
                _logger.info("Data source: DEFAULT")
        
        _logger.info(f"Parsed Date From: {date_from}")
        _logger.info(f"Parsed Date To: {date_to}")
        _logger.info(f"Parsed Invoice Type: {invoice_type}")
        _logger.info(f"Parsed State: {state}")
        _logger.info(f"Parsed Payment State: {payment_state}")
        
        # Build simple domain
        domain = []
        
        # Invoice type filter
        if invoice_type == 'out_invoice':
            domain.append(('move_type', '=', 'out_invoice'))
        elif invoice_type == 'in_invoice':
            domain.append(('move_type', '=', 'in_invoice'))
        elif invoice_type == 'out_refund':
            domain.append(('move_type', '=', 'out_refund'))
        elif invoice_type == 'in_refund':
            domain.append(('move_type', '=', 'in_refund'))
        else:
            domain.append(('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']))
        
        _logger.info(f"Domain after invoice_type: {domain}")
        
        # State filter
        if state and state != 'all':
            domain.append(('state', '=', state))
            _logger.info(f"Added state filter: {state}")
        
        # Payment state filter
        if payment_state and payment_state != 'all':
            domain.append(('payment_state', '=', payment_state))
            _logger.info(f"Added payment_state filter: {payment_state}")
        
        # Partner filter
        if partner_ids:
            domain.append(('partner_id', 'in', partner_ids))
            _logger.info(f"Added partner filter: {partner_ids}")
        
        # Date filter - try both fields
        if date_from:
            domain.append('|')
            domain.append(('invoice_date', '>=', date_from))
            domain.append('&')
            domain.append(('invoice_date', '=', False))
            domain.append(('date', '>=', date_from))
            _logger.info(f"Added date_from filter: {date_from}")
        
        if date_to:
            domain.append('|')
            domain.append(('invoice_date', '<=', date_to))
            domain.append('&')
            domain.append(('invoice_date', '=', False))
            domain.append(('date', '<=', date_to))
            _logger.info(f"Added date_to filter: {date_to}")
        
        _logger.info(f"FINAL DOMAIN: {domain}")
        
        # Get invoices
        invoices = self.env['account.move'].search(domain, order='date desc, name')
        _logger.info(f"FOUND {len(invoices)} INVOICES")
        
        if invoices:
            _logger.info("SAMPLE INVOICES:")
            for inv in invoices[:5]:  # Show first 5
                _logger.info(f"  - {inv.name}: Date={inv.invoice_date}, Type={inv.move_type}, State={inv.state}, Payment={inv.payment_state}")
        else:
            _logger.info("NO INVOICES FOUND - Let's check total invoices in system:")
            all_invoices = self.env['account.move'].search([('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund'])], limit=10)
            _logger.info(f"Total invoices in system (sample of 10): {len(all_invoices)}")
            for inv in all_invoices:
                _logger.info(f"  - {inv.name}: Date={inv.invoice_date}, Type={inv.move_type}, State={inv.state}")
        
        _logger.info("#"*80)
        
        # Group invoices by status
        draft_invoices = invoices.filtered(lambda inv: inv.state == 'draft')
        posted_invoices = invoices.filtered(lambda inv: inv.state == 'posted')
        cancelled_invoices = invoices.filtered(lambda inv: inv.state == 'cancel')
        
        # Group by payment state
        not_paid = invoices.filtered(lambda inv: inv.payment_state == 'not_paid')
        partial_paid = invoices.filtered(lambda inv: inv.payment_state == 'partial')
        paid = invoices.filtered(lambda inv: inv.payment_state == 'paid')
        
        # Calculate totals using safe sum
        total_draft = self._safe_sum(draft_invoices, 'amount_total')
        total_posted = self._safe_sum(posted_invoices, 'amount_total')
        total_cancelled = self._safe_sum(cancelled_invoices, 'amount_total')
        total_not_paid = self._safe_sum(not_paid, 'amount_residual')
        total_paid = self._safe_sum(paid, 'amount_total')
        total_partial = self._safe_sum(partial_paid, 'amount_residual')
        
        # Overall totals
        grand_total = self._safe_sum(invoices, 'amount_total')
        total_due = self._safe_sum(invoices, 'amount_residual')
        
        # Group by customer
        customer_summary = []
        if invoices:
            customer_dict = {}
            for invoice in invoices:
                partner = invoice.partner_id
                if partner:
                    if partner.id not in customer_dict:
                        customer_dict[partner.id] = {
                            'partner_name': partner.name or 'Unknown',
                            'invoice_count': 0,
                            'total_amount': 0.0,
                            'total_due': 0.0,
                        }
                    customer_dict[partner.id]['invoice_count'] += 1
                    customer_dict[partner.id]['total_amount'] += (invoice.amount_total or 0.0)
                    customer_dict[partner.id]['total_due'] += (invoice.amount_residual or 0.0)
            
            # Convert to list and sort
            customer_summary = sorted(customer_dict.values(), 
                                    key=lambda x: x['total_amount'], reverse=True)
        
        # Get invoice type label
        invoice_type_labels = {
            'out_invoice': 'Customer Invoices',
            'in_invoice': 'Vendor Bills',
            'out_refund': 'Customer Credit Notes',
            'in_refund': 'Vendor Credit Notes',
            'all': 'All Types'
        }
        
        # State labels
        state_label = state.replace('_', ' ').title() if state else 'All'
        payment_state_label = payment_state.replace('_', ' ').title() if payment_state else 'All'
        
        return {
            'doc_ids': docids,
            'doc_model': 'invoice.status.wizard',
            'date_from': str(date_from) if date_from else '',
            'date_to': str(date_to) if date_to else '',
            'invoice_type': invoice_type or 'all',
            'invoice_type_label': invoice_type_labels.get(invoice_type, 'All Types'),
            'state_filter': state or 'all',
            'payment_state_filter': payment_state or 'all',
            'state_label': state_label,
            'payment_state_label': payment_state_label,
            'invoices': invoices,
            'invoice_count': len(invoices),
            'draft_invoices': draft_invoices,
            'draft_count': len(draft_invoices),
            'posted_invoices': posted_invoices,
            'posted_count': len(posted_invoices),
            'cancelled_invoices': cancelled_invoices,
            'cancelled_count': len(cancelled_invoices),
            'not_paid': not_paid,
            'not_paid_count': len(not_paid),
            'partial_paid': partial_paid,
            'partial_count': len(partial_paid),
            'paid': paid,
            'paid_count': len(paid),
            'total_draft': float(total_draft),
            'total_posted': float(total_posted),
            'total_cancelled': float(total_cancelled),
            'total_not_paid': float(total_not_paid),
            'total_paid': float(total_paid),
            'total_partial': float(total_partial),
            'grand_total': float(grand_total),
            'total_due': float(total_due),
            'customer_summary': customer_summary,
            'company_name': self.env.company.name or 'Company',
        }