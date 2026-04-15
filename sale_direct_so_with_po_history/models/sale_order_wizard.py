from odoo import models, fields

class SaleOrderCreatePOWizard(models.TransientModel):
    _name = 'sale.order.create.po.wizard'
    _description = 'Create Sales Order with PO'

    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    customer_po = fields.Binary(string="Customer PO", required=True)
    customer_po_filename = fields.Char(string="Filename")

    def action_create_order(self):
        active_order = self.env['sale.order'].browse(self.env.context.get('active_id'))

        # Create NEW sale order (fresh sequence auto-generated)
        new_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'source_sale_id': active_order.id,
            'customer_po': self.customer_po,
            'customer_po_filename': self.customer_po_filename,
        })

        # Copy order lines
        for line in active_order.order_line:
            line.copy({'order_id': new_order.id})

        # Add PO history
        self.env['sale.order.customer.po'].create({
            'sale_order_id': new_order.id,
            'customer_po': self.customer_po,
            'customer_po_filename': self.customer_po_filename,
        })

        # Confirm order (only here, not in create())
        new_order.action_confirm()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': new_order.id,
            'view_mode': 'form',
        }