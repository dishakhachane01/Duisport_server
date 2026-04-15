from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    # is_from_quote = fields.Boolean("From Quote", tracking=True)
    state = fields.Selection([  
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('from_quote', 'From Confirmed Quote'),
        ('to_approve_accounts', 'Waiting Accounts Approval'),
        ('to_approve_management', 'Waiting Management Approval'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, copy=False, index=True, default='draft', tracking=True)

    # 🔔 Utility: send notification to group
    # def _notify_group(self, group_xml_id, message):
    #     group = self.env.ref(group_xml_id, raise_if_not_found=False)
    #     if not group:
    #         return

    #     partners = group.users.mapped('partner_id')
    #     for rec in self:
    #         rec.message_post(
    #             body=message,
    #             partner_ids=partners.ids,
    #             message_type='notification',
    #             subtype_xmlid="mail.mt_comment"
    #         )

    # Step 1: Send to Accounts
    def action_send_for_accounts(self):
        for rec in self:
            if rec.state not in ['draft', 'sent', 'from_quote']:
                raise UserError("Only RFQ can be sent for approval.")

            rec.state = 'to_approve_accounts'

            # 🔔 Notify Accounts
            # rec._notify_group(
            #     'product_vendor_rfq.group_accounts_approval',
            #     _("Purchase Order %s requires Accounts Approval.") % rec.name
            # )

    # Step 2: Accounts Approval
    def action_accounts_approve(self):
        for rec in self:
            if rec.state != 'to_approve_accounts':
                raise UserError("Not in Accounts Approval stage.")

            rec.state = 'to_approve_management'

            # 🔔 Notify Management
            # rec._notify_group(
            #     'product_vendor_rfq.group_management_approval',
            #     _("Purchase Order %s approved by Accounts and needs Management Approval.") % rec.name
            # )

    def action_management_approve(self):
        for rec in self:
            if rec.state != 'to_approve_management':
                raise UserError("Not in Management Approval stage.")
            rec.write({'state': 'draft'})

        self.button_confirm()
            # 🔔 Notify Store Team
            # rec._notify_group(
            #     'product_vendor_rfq.group_store_team',
            #     _("Purchase Order %s is Confirmed and ready for processing.") % rec.name
            # )


        return {'type': 'ir.actions.client', 'tag': 'reload'}


    def button_confirm(self):
        for rec in self:
            if rec.state == 'to_approve_management':
                rec.write({'state': 'draft'})
        return super().button_confirm()


    # def action_management_approve(self):
    #     for rec in self:
    #         if rec.state != 'to_approve_management':
    #             raise UserError("Not in Management Approval stage.")

    #         # Directly confirm without Odoo approval interference
    #         rec.write({'state': 'purchase'})

    #         # Call confirm logic (stock moves etc.)
    #         rec.button_confirm()

    #         # 🔔 Notify Store Team
    #         rec._notify_group(
    #             'product_vendor_rfq.group_store_team',
    #             _("Purchase Order %s is Confirmed and ready for processing.") % rec.name
    #         )