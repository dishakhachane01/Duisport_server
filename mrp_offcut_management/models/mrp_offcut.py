from odoo import models, fields, api, exceptions


class MrpOffcut(models.Model):
    _name = 'mrp.offcut'
    _description = 'Manufacturing Offcut Entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Reference',
        default='New',
        copy=False,
        readonly=True,
        tracking=True,
    )
    production_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order',
        required=True,
        tracking=True,
        states={'approved': [('readonly', True)], 'submitted': [('readonly', True)]},
    )
    store_location_id = fields.Many2one(
        'stock.location',
        string='Store Location',
        required=True,
        domain="[('usage', '=', 'internal')]",
        tracking=True,
        states={'approved': [('readonly', True)], 'submitted': [('readonly', True)]},
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted to Store'),
        ('approved', 'Approved'),
    ], default='draft', string='Status', tracking=True, readonly=True)

    offcut_line_ids = fields.One2many(
        'mrp.offcut.line',
        'offcut_id',
        string='Offcut Lines',
        states={'approved': [('readonly', True)]},
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    notes = fields.Text(string='Notes')

    # ── Computed summary fields ─────────────────────────────────────────────
    total_offcut_lines = fields.Integer(
        compute='_compute_summary', string='Total Lines'
    )

    @api.depends('offcut_line_ids')
    def _compute_summary(self):
        for rec in self:
            rec.total_offcut_lines = len(rec.offcut_line_ids)

    # ── Sequence ────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('mrp.offcut') or 'New'
        return super().create(vals_list)

    # ── Actions ─────────────────────────────────────────────────────────────
    def action_submit(self):
        for rec in self:
            if not rec.offcut_line_ids:
                raise exceptions.UserError('Please add at least one offcut line before submitting.')
            if any(line.offcut_qty <= 0 for line in rec.offcut_line_ids):
                raise exceptions.UserError(
                    'Some lines have no offcut (actual length >= planned length). '
                    'Please review or remove those lines.'
                )
            rec.state = 'submitted'
            rec.message_post(body='Offcut entry submitted to store for approval.')

    def action_approve(self):
        for rec in self:
            if rec.state != 'submitted':
                raise exceptions.UserError('Only submitted entries can be approved.')
            for line in rec.offcut_line_ids:
                if line.total_offcut > 0:
                    move = self.env['stock.move'].create({
                        'name': f'Offcut: {rec.name} / {line.product_id.display_name}',
                        'origin': rec.name,
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.total_offcut,
                        'product_uom': line.product_id.uom_id.id,
                        'location_id': rec.production_id.location_src_id.id,
                        'location_dest_id': rec.store_location_id.id,
                        'company_id': rec.company_id.id,
                    })
                    move._action_confirm()
                    move._action_assign()
                    move._action_done()
            rec.state = 'approved'
            rec.message_post(body='Offcut entry approved. Stock has been transferred to the store location.')

    def action_reset_draft(self):
        for rec in self:
            if rec.state == 'approved':
                raise exceptions.UserError('Approved entries cannot be reset.')
            rec.state = 'draft'

    def action_view_stock_moves(self):
        self.ensure_one()
        moves = self.env['stock.move'].search([('origin', '=', self.name)])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Moves',
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', moves.ids)],
        }


class MrpOffcutLine(models.Model):
    _name = 'mrp.offcut.line'
    _description = 'Offcut Line'

    offcut_id = fields.Many2one(
        'mrp.offcut',
        string='Offcut Reference',
        required=True,
        ondelete='cascade',
    )
    production_id = fields.Many2one(
        'mrp.production',
        related='offcut_id.production_id',
        store=True,
        string='Manufacturing Order',
    )

    # Available products pulled from the MO's raw materials
    available_product_ids = fields.Many2many(
        'product.product',
        'mrp_offcut_line_avail_rel',
        'line_id',
        'product_id',
        compute='_compute_available_products',
        string='Available Raw Materials',
    )

    product_id = fields.Many2one(
        'product.product',
        string='Raw Material',
        required=True,
        domain="[('id', 'in', available_product_ids)]",
    )

    uom_id = fields.Many2one(
        'uom.uom',
        related='product_id.uom_id',
        string='Unit',
    )

    planned_qty = fields.Float(
        string='Planned Length/Qty',
        required=True,
        digits='Product Unit of Measure',
        help='The planned quantity of raw material allocated to this operation.',
    )
    actual_qty = fields.Float(
        string='Actual Consumed',
        required=True,
        digits='Product Unit of Measure',
        help='The actual quantity consumed during manufacturing.',
    )
    offcut_qty = fields.Float(
        string='Offcut Qty',
        compute='_compute_offcut',
        store=True,
        digits='Product Unit of Measure',
        help='Leftover = Planned - Actual (minimum 0)',
    )
    quantity = fields.Float(
        string='No. of Pieces',
        default=1.0,
        required=True,
        help='Number of pieces/rods/boards processed.',
    )
    total_offcut = fields.Float(
        string='Total Offcut',
        compute='_compute_total',
        store=True,
        digits='Product Unit of Measure',
        help='Total offcut = Offcut per piece × Number of pieces',
    )

    # ── Computes ────────────────────────────────────────────────────────────
    @api.depends('offcut_id.production_id', 'offcut_id.production_id.move_raw_ids.product_id')
    def _compute_available_products(self):
        for rec in self:
            if rec.offcut_id.production_id:
                rec.available_product_ids = rec.offcut_id.production_id.move_raw_ids.mapped('product_id')
            else:
                rec.available_product_ids = self.env['product.product']

    @api.depends('planned_qty', 'actual_qty')
    def _compute_offcut(self):
        for rec in self:
            diff = rec.planned_qty - rec.actual_qty
            rec.offcut_qty = max(diff, 0.0)

    @api.depends('offcut_qty', 'quantity')
    def _compute_total(self):
        for rec in self:
            rec.total_offcut = rec.offcut_qty * rec.quantity

    # ── Auto-fill planned qty from MO ───────────────────────────────────────
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and self.offcut_id.production_id:
            move = self.offcut_id.production_id.move_raw_ids.filtered(
                lambda m: m.product_id == self.product_id
            )
            if move:
                # Use product_uom_qty (planned qty from the MO)
                self.planned_qty = sum(move.mapped('product_uom_qty'))
