from odoo import fields, models


class ProductTemplate(models.Model):
    """Inherited the model for adding new fields and functions"""
    _inherit = 'product.template'

    dimension = fields.Char(string='Dimensions')
    description= fields.Char(string="Description")
    length = fields.Char(string="Length")
    width = fields.Char(string="Width")
    thickness = fields.Char(string="Thickness")
    cal = fields.Char(string="Cal")
    opening_qty = fields.Char(string="opening quantity")
    opening_qty_in_cft = fields.Char(string="Opening Quantity in CFT/SQFT")
    recieved_qty = fields.Char(string="Recieved quantity")
    recieved_qty_in_cft = fields.Char(string="Recieved Quantity in CFT/SQFT")
    consumed_qty = fields.Char(string="Consumed quantity")
    closing_qty = fields.Char(string="Closing quantity")
    used_cft = fields.Char(string= "Total Used CFT/SFT/Nos" )
    closing_cft = fields.Char(string="Closing CFT")

    asset_category_id = fields.Many2one(
        'account.asset.category', string='Asset Type',
        company_dependent=True, ondelete="restrict")
    deferred_revenue_category_id = fields.Many2one(
        'account.asset.category', string='Deferred Revenue Type',
        company_dependent=True, ondelete="restrict")

    def _get_asset_accounts(self):
        res = super(ProductTemplate, self)._get_asset_accounts()
        if self.asset_category_id:
            res['stock_input'] = self.property_account_expense_id
        if self.deferred_revenue_category_id:
            res['stock_output'] = self.property_account_income_id
        return res
