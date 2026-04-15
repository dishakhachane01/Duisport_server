from odoo import models, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # ------------------------------------------------------------------ #
    #  Prevent selecting a non-approved / rejected vendor on a PO         #
    # ------------------------------------------------------------------ #

    @api.onchange('partner_id')
    def _onchange_partner_id_check_vendor_approval(self):
        if self.partner_id and self.partner_id.supplier_rank:
            state = self.partner_id.vendor_approval_state
            if state == 'rejected':
                return {
                    'warning': {
                        'title': _('Blacklisted Vendor'),
                        'message': _(
                            'The selected vendor "%s" has been rejected and blacklisted. '
                            'You cannot create a purchase order for this vendor.'
                        ) % self.partner_id.name,
                    }
                }
            elif state != 'approved':
                return {
                    'warning': {
                        'title': _('Vendor Not Approved'),
                        'message': _(
                            'The selected vendor "%s" has not been approved yet '
                            '(current status: %s). Please complete the vendor approval '
                            'process before raising a purchase order.'
                        ) % (self.partner_id.name, state),
                    }
                }

    def button_confirm(self):
        """Hard block at confirmation: reject if vendor is not approved."""
        for order in self:
            partner = order.partner_id
            if partner.vendor_approval_state == 'rejected':
                raise UserError(_(
                    'Vendor "%s" is blacklisted/rejected. '
                    'This purchase order cannot be confirmed.'
                ) % partner.name)
            if partner.vendor_approval_state != 'approved':
                raise UserError(_(
                    'Vendor "%s" is not yet approved (status: %s). '
                    'Please complete the vendor approval flow first.'
                ) % (partner.name, partner.vendor_approval_state))
        return super().button_confirm()
