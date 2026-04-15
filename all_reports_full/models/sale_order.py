from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    quotation_terms = fields.Html(
        string="Terms & Conditions",
        help="Quotation Terms & Conditions",
        default="""
        <p><strong>Price:</strong> The quoted price is exclusive of GST.<br/>
        <strong>Transportation:</strong>
        Freight will be charged Extra at the Actual if the truck freight cost is not matched due to less qty.<br/>
<strong>MOQ:</strong>
        Rates are valid only if order received as per the MOQ.<br/>
<strong>Inventory:</strong>
        Stock will be maintained based on the schedule given – 15 to 20% extra – if there is any change in plan or
        specification or short closure of the order, you need to bear the full cost of material kept in Inventory –
        In the case of SFG / FG parts.<br/>

       For the plain boards, it can be mutually discussed and resolved depending on the usability of the boards.<br/>

       <strong>GST:</strong> Extra as applicable depending on the product.<br/>
        <strong>HSN Code:</strong><br/>
        Corrugated box/board only – 48191010<br/>
        Corrugated box with pallet – 48191010<br/>
        Wood / Plywood box/pallet – 44151000
        <br/>

       <strong>Lead Time:</strong>
        First set 10 to 15 days – 3 months tentative schedule to be shared by you,
        2nd set onwards based on the schedule shared by you.<br/>

        <strong>Additional Process / Treatment cost:</strong>
        Extra as applicable – will be processed and chargeable as mutually agreed upon.<br/>

        <strong>Quotation Validity:</strong> 7 days.<br/>

        <strong>Payment Terms:</strong>
        Advance or 30 days credit period from date of Invoice.<br/>

        <strong>General Note:</strong><br/>
        1. As per ISPM-15 standard, Duisport does not guarantee for mold and fungus formation due to Increase   
        in moisture levels in wood/Plywood (Naturally due to atmospheric conditions / due to water splash or 
        getting wet in water through any kind of source).<br/>
        2. Plywood and corrugated boards are exempted from fumigation / heat treatment.<br/>
        3. If market rates fluctuate, then we have to revise the rates accordingly on mutual concern.<br/>
        4. If there is any additional process or design change made prices will be revised accordingly.>br/>
        5.The outsourced items supplied or referred by us are as per the Standards shared by the Suppliers terms 
        and conditions.  Any discrepancy arising from this will have to be referred and taken up with the 
        concerned suppliers as per their terms and conditions.<br/>
        6.In-house Inspection reports will be shared for every batch, if the material test certificate required 
        from the 3rd party Lab, the cost for the same will be charged @ actual + the material cost + freight + taxes.
        <br/>
        <strong>For Duisport Packing Logistics India Pvt. Ltd.</strong><br/>
       
        """
    )

 # <strong>Khushbu Baiswar</strong><br/>
        # Customer Support<br/>
        # Mobile No.: +91 7408247865</p>

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    moq = fields.Float(
        string="MOQ",
        default=1.0,
        help="Minimum Order Quantity"
    )

    hsn_code = fields.Char(
        string="HSN Code",
        related='product_id.l10n_in_hsn_code',
        readonly=True
    )





# class SaleOrder(models.Model):
#     _inherit = 'sale.order'

#     approval_state = fields.Selection([
#         ('draft', 'Draft'),
#         ('sent', 'Quotation Sent'),
#         ('submitted', 'Submitted for Approval'),
#         ('approved', 'Approved')
#     ], string="Approval Status", default='draft')


#     def action_submit_for_approval(self):
#         self.approval_state = 'submitted'

#     def action_confirm(self):
#         # Only allow Accounts group to confirm, and only in 'submitted' state
#         if self.approval_state != 'submitted':
#             raise UserError("Quotation must be submitted for approval first.")
#         if not self.env.user.has_group('account.group_account_user'):
#             raise UserError("Only Accounts team can confirm this quotation.")
#         return super(SaleOrder, self).action_confirm()
    


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    approval_state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Quotation Sent'),
        ('submitted', 'Submitted for Approval'),
        ('approved', 'Approved'),
    ], string="Approval Status", default='draft', tracking=True)

    def action_submit_for_approval(self):
        for order in self:
            if order.state != 'sent':
                raise UserError("You can only submit a quotation after sending it to the customer.")
            order.approval_state = 'submitted'

    def action_confirm(self):
        for order in self:
            # if order.approval_state != 'submitted':
            #     raise UserError("Quotation must be submitted for approval before confirming.")
            if not self.env.user.has_group('account.group_account_user'):
                raise UserError("Only the Accounts team can confirm this quotation.")
        result = super().action_confirm()
        # Set approval_state to approved after successful confirm
        for order in self:
            order.approval_state = 'approved'
        return result


    def action_quotation_send(self):
        result = super().action_quotation_send()
        for order in self:
            order.approval_state = 'sent'
        return result
    



class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_preview_quotation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/html/all_reports_full.quotation_report_document/%d' % self.id,
            'target': 'new',
        }

    def action_download_quotation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/all_reports_full.quotation_report_document/%d' % self.id,
            'target': 'new',
        }
    




class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_preview_purchase_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/html/all_reports_full.report_purchase_order_custom/%d' % self.id,
            'target': 'new',
        }

    def action_download_purchase_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/all_reports_full.report_purchase_order_custom/%d' % self.id,
            'target': 'new',
        }
    


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    hsn_code = fields.Char(string="HSN Code")


    @api.onchange('product_id')
    def _onchange_product_id_hsn(self):
        for line in self:
            if line.product_id:
                line.hsn_code = line.product_id.l10n_in_hsn_code