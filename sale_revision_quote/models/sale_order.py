
from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    revision_number = fields.Integer(string="Revision No", default=0, copy=False)
    original_name = fields.Char(string="Original Quotation", copy=False)

    def action_create_revision(self):
        for order in self:
            base_name = order.original_name or order.name
            new_revision = order.revision_number + 1

            new_name = f"{base_name}-{str(new_revision).zfill(3)}"

            new_order = order.copy({
                'name': new_name,
                'revision_number': new_revision,
                'original_name': base_name,
            })

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'view_mode': 'form',
                'res_id': new_order.id,
            }
