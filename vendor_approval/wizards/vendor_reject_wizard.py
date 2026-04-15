from odoo import models, fields, _


class VendorRejectWizard(models.TransientModel):
    _name = 'vendor.reject.wizard'
    _description = 'Vendor Rejection Wizard'

    partner_ids = fields.Many2many(
        'res.partner',
        string='Vendors',
    )
    stage = fields.Char()          # 'accounts' or 'management' – informational
    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=True,
    )

    def action_confirm_reject(self):
        self.partner_ids._do_reject(self.rejection_reason)
        return {'type': 'ir.actions.act_window_close'}
