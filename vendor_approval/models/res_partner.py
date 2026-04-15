from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vendor_approval_state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve_accounts', 'Waiting Accounts Approval'),
        ('to_approve_management', 'Waiting Management Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected / Blacklisted'),
    ], string='Vendor Approval Status',
       default='draft',
       tracking=True,
       copy=False,
    )

    rejection_reason = fields.Text(string='Rejection Reason', copy=False)

    # ------------------------------------------------------------------ #
    #  Computed helper so views / domain rules can check approval easily  #
    # ------------------------------------------------------------------ #
    is_vendor_approved = fields.Boolean(
        string='Vendor Approved',
        compute='_compute_is_vendor_approved',
        store=True,
    )

    @api.depends('vendor_approval_state')
    def _compute_is_vendor_approved(self):
        for rec in self:
            rec.is_vendor_approved = rec.vendor_approval_state == 'approved'

    # ------------------------------------------------------------------ #
    #  Action buttons                                                      #
    # ------------------------------------------------------------------ #

    def action_send_for_accounts(self):
        """Submit vendor for Accounts team review."""
        for rec in self:
            if rec.vendor_approval_state != 'draft':
                raise UserError(_('Only draft vendors can be submitted for approval.'))
            rec.vendor_approval_state = 'to_approve_accounts'

    def action_accounts_approve(self):
        """Accounts team approves → escalate to Management."""
        self._check_group('product_vendor_rfq.group_accounts_approval_m')
        for rec in self:
            if rec.vendor_approval_state != 'to_approve_accounts':
                raise UserError(_('Vendor is not pending Accounts approval.'))
            rec.vendor_approval_state = 'to_approve_management'

    def action_accounts_reject(self):
        """Accounts team rejects → blacklist vendor."""
        self._check_group('product_vendor_rfq.group_accounts_approval_m')
        return self._open_reject_wizard('accounts')

    # def action_accounts_approve(self):
    #     """Accounts team approves → escalate to Management."""
    #     self._check_group(
    #         'product_vendor_rfq.group_accounts_approval',
    #         'product_vendor_rfq.group_accounts_approval_m',
    #     )
    #     for rec in self:
    #         if rec.vendor_approval_state != 'to_approve_accounts':
    #             raise UserError(_('Vendor is not pending Accounts approval.'))
    #         rec.vendor_approval_state = 'to_approve_management'
    
    
    # def action_accounts_reject(self):
    #     """Accounts team rejects → blacklist vendor."""
    #     self._check_group(
    #         'product_vendor_rfq.group_accounts_approval',
    #         'product_vendor_rfq.group_accounts_approval_m',
    #     )
    #     return self._open_reject_wizard('accounts')



    def action_management_approve(self):
        """Management approves → vendor is fully approved."""
        self._check_group('product_vendor_rfq.group_management_approval')
        for rec in self:
            if rec.vendor_approval_state != 'to_approve_management':
                raise UserError(_('Vendor is not pending Management approval.'))
            rec.vendor_approval_state = 'approved'
            # Remove from mail blacklist if previously rejected and re-submitted
            if rec.email:
                blacklist_entry = self.env['mail.blacklist'].sudo().search(
                    [('email', '=', rec.email.lower())], limit=1
                )
                if blacklist_entry:
                    blacklist_entry.sudo()._unblacklist_domain(rec.email)

    def action_management_reject(self):
        """Management rejects → blacklist vendor."""
        self._check_group('product_vendor_rfq.group_management_approval')
        return self._open_reject_wizard('management')

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #



    def _check_group(self, group_xml_id):
        user = self.env.user
        if not any(user.has_group(g) for g in group_xml_id):
                raise UserError(_(
                    "You do not have permission to perform this action.\n"
                    "Required group(s): %s"
                ) % ', '.join(group_xml_id))





    # def _check_group(self, group_xml_ids):
    #     user = self.env.user
    #     if not any(user.has_group(g) for g in group_xml_ids):
    #             raise UserError(_(
    #                 "You do not have permission to perform this action.\n"
    #                 "Required group(s): %s"
    #             ) % ', '.join(group_xml_ids))

    def _open_reject_wizard(self, stage):
        """Return wizard action so approver can enter a rejection reason."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Vendor'),
            'res_model': 'vendor.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_ids': self.ids,
                'default_stage': stage,
            },
        }

    def _do_reject(self, reason):
        """
        Final rejection: set state, store reason, blacklist the vendor.
        Called by the wizard.
        """
        for rec in self:
            rec.vendor_approval_state = 'rejected'
            rec.rejection_reason = reason
            # Blacklist using Odoo's built-in mail.blacklist if partner has email,
            # and also flag supplier rank to 0 so it won't appear in vendor lists.
            rec.supplier_rank = 0
            if rec.email:
                self.env['mail.blacklist'].sudo()._add(rec.email)
            # Log a note on the chatter
            rec.message_post(
                body=_('<b>Vendor Rejected & Blacklisted</b><br/>Reason: %s') % (reason or '—'),
                subtype_xmlid='mail.mt_note',
            )

    # ------------------------------------------------------------------ #
    #  Override: block rejected vendors from being used on POs            #
    # ------------------------------------------------------------------ #

    @api.constrains('vendor_approval_state')
    def _check_not_rejected_on_po(self):
        # Validation is done at PO level (see purchase_order.py override).
        pass
