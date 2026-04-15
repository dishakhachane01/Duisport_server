
from odoo import models, fields, api

class CustomerPO(models.Model):
    _name = 'customer.po'
    _description = 'Customer PO Flow'

    customer_id = fields.Many2one('res.partner', string='Customer')
    customer_po = fields.Binary(string="Customer PO", attachment=True)
    customer_po_filename = fields.Char(string="Filename")
    customer_po_date = fields.Datetime(string="PO Date")
    customer_po_number = fields.Char(string="PO Number")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Accounts'),
        ('done', 'Completed')
    ], default='draft')

    def action_submit(self):
        self.state = 'pending'

    def action_create_sale_order(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_partner_id': self.customer_id.id,
                'default_customer_po': self.customer_po,
                'default_customer_po_filename': self.customer_po_filename,
                'default_customer_po_date': self.customer_po_date,
                'default_customer_po_number': self.customer_po_number,
            }
        }
    
    def action_mark_done(self):
        self.state = 'done'