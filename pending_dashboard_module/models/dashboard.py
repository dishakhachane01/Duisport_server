from odoo import models, fields, api


class PendingDashboard(models.TransientModel):
    _name = 'pending.dashboard'
    _description = 'Pending Work Dashboard'

    crm_count = fields.Integer()
    sale_count = fields.Integer()
    purchase_count = fields.Integer()
    rfq_count = fields.Integer()
    inventory_in_count = fields.Integer()
    inventory_out_count = fields.Integer()
    mfg_count = fields.Integer()
    invoice_count = fields.Integer()

    @api.model
    def get_dashboard_data(self):
        company_id = self.env.company.id

        def count(model, domain):
            # Append company filter based on which field the model uses
            model_obj = self.env[model]
            if 'company_id' in model_obj._fields:
                domain = domain + [('company_id', '=', company_id)]
            elif 'company_ids' in model_obj._fields:
                domain = domain + [('company_ids', 'in', [company_id])]
            return model_obj.search_count(domain)

        data = {
            'crm_count': count('crm.lead', [
                ('probability', '<', 100),
            ]),
            'sale_count': count('sale.order', [
                ('state', 'in', ['draft', 'sent']),
            ]),
            'purchase_count': count('purchase.order', [
                ('state', '=', 'to approve'),
            ]),
            'rfq_count': count('rfq.vendor.quote', [
                ('state', '=', 'received'),
            ]),
            'inventory_in_count': count('stock.picking', [
                ('picking_type_code', '=', 'incoming'),
                ('state', 'not in', ['done', 'cancel']),
            ]),
            'inventory_out_count': count('stock.picking', [
                ('picking_type_code', '=', 'outgoing'),
                ('state', 'not in', ['done', 'cancel']),
            ]),
            'mfg_count': count('mrp.production', [
                ('state', 'not in', ['done', 'cancel']),
            ]),
            'invoice_count': count('account.move', [
                ('move_type', 'in', ['out_invoice', 'in_invoice']),
                ('payment_state', '!=', 'paid'),
                ('state', '=', 'posted'),
            ]),
            'company_name': self.env.company.name,
        }

        return data