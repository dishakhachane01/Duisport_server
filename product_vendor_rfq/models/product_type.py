from odoo import models, fields, api

CUSTOM_TYPES = ['packing_material', 'trading_goods', 'raw_material']


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    stored_custom_type = fields.Char(
        string='Custom Product Type Value',
        store=True
    )

    custom_product_type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product'),
        ('packing_material', 'Purchase of Packing Material'),
        ('trading_goods', 'Purchase of Trading Goods'),
        ('raw_material', 'Purchase of Raw Material'),
    ],
        string='Product Type',
        compute='_compute_custom_type',
        inverse='_inverse_custom_type',
        store=True
    )

    # ================= CREATE =================
    @api.model
    def create(self, vals):
        if 'custom_product_type' in vals:
            vals['stored_custom_type'] = vals['custom_product_type']

        # ✅ Always force detailed_type to storable
        vals['detailed_type'] = 'product'

        return super().create(vals)

    # ================= WRITE =================
    def write(self, vals):
        if 'custom_product_type' in vals:
            vals['stored_custom_type'] = vals['custom_product_type']

        # ✅ Always force detailed_type to storable
        vals['detailed_type'] = 'product'

        return super().write(vals)

    # ================= COMPUTE =================
    @api.depends('stored_custom_type', 'detailed_type')
    def _compute_custom_type(self):
        for record in self:
            record.custom_product_type = (
                record.stored_custom_type or record.detailed_type
            )

    # ================= INVERSE =================
    def _inverse_custom_type(self):
        for record in self:
            record.stored_custom_type = record.custom_product_type
            # ✅ Always force detailed_type to storable
            record.detailed_type = 'product'

    # ================= ONCHANGE =================
    @api.onchange('custom_product_type')
    def _onchange_custom_product_type(self):
        self.stored_custom_type = self.custom_product_type
        # ✅ Always force detailed_type to storable
        self.detailed_type = 'product'