from odoo import models, fields


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    offcut_ids = fields.One2many(
        'mrp.offcut',
        'production_id',
        string='Offcut Entries',
    )
    offcut_count = fields.Integer(
        compute='_compute_offcut_count',
        string='Offcuts',
    )

    def _compute_offcut_count(self):
        for rec in self:
            rec.offcut_count = len(rec.offcut_ids)

    def action_view_offcuts(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('mrp_offcut.action_mrp_offcut')
        action['domain'] = [('production_id', '=', self.id)]
        action['context'] = {'default_production_id': self.id}
        if self.offcut_count == 1:
            action['res_id'] = self.offcut_ids[0].id
            action['view_mode'] = 'form'
        return action
