from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Link to original order (Professional way instead of REV in sequence)
    source_sale_id = fields.Many2one(
        'sale.order',
        string="Source Sales Order",
        readonly=True
    )

    customer_po_ids = fields.One2many(
        'sale.order.customer.po',
        'sale_order_id',
        string="Customer PO History"
    )

    def action_create_new_so_with_po(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create New Sales Order',
            'res_model': 'sale.order.create.po.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'active_id': self.id,
            }
        }


class SaleOrderCustomerPO(models.Model):
    _name = 'sale.order.customer.po'
    _description = 'Customer PO History'
    _order = 'create_date desc'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        ondelete='cascade'
    )

    customer_po = fields.Binary(
        string="Customer PO",
        attachment=True,
        required=True
    )

    customer_po_filename = fields.Char(string="Filename")

    uploaded_on = fields.Datetime(
        string="Uploaded On",
        default=fields.Datetime.now
    )

    uploaded_by = fields.Many2one(
        'res.users',
        string="Uploaded By",
        default=lambda self: self.env.user
    )