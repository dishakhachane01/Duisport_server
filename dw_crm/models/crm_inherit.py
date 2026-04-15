from odoo import models, fields, api, _
from odoo.exceptions import UserError



class CrmLead(models.Model):
    _inherit = 'crm.lead'
    # _inherit = ['mail.thread', 'mail.activity.mixin']


    

    department_times_ids = fields.One2many(
        'department.time.tracking',
        string='Department Time Tracking',
        compute='_compute_department_times'
    )

    engineering_team_id = fields.Many2one(
        'res.users', 
        string="Engineering Team",
        help="Assign the lead to an Engineering team member."
    )

    product_line_ids = fields.One2many(
        'crm.lead.product.line',
        'lead_id',

        string='Products'
    )
    
    engineer_id = fields.Many2one(
        'res.users', string="Sales person",
        default=lambda self: self.env.user
    )
    engineering_id = fields.Many2one(
        'engineering.team',
        ondelete='cascade',
       
    )

    design_ref = fields.Binary("Design Reference")
    design_ref_filename = fields.Char()
    estimation_time = fields.Float("Estimation Time (Days)")
    engineering_notes = fields.Text()
    quantity = fields.Float(default=1.0)
    product_id = fields.Many2one('product.product')
    cost_price = fields.Float(string="Unit Price")
    total_price = fields.Float(
        store=True
    )
    vailability_status = fields.Char(
        string="Overall Availability",
        store=False
    )
    main_product_display = fields.Char(
        string='Engineering Product',
        store=True,
        readonly=True
    )

    bom_id = fields.Many2one(
        'mrp.bom',
        string='BoM',
        readonly=True
    )

    component_id = fields.Many2one(
        'product.product',
        string='Component',
        readonly=True,
    )

    engineering_qty = fields.Float(
        string='Engineering Qty',
        readonly=True
    )

    total_required_qty = fields.Float(
        string='Total Required Qty',
        store=True,
        readonly=True
    )

    component_unit_price = fields.Float(
        string='Unit Price',
        store=True,
        readonly=True
    )

    component_total_price = fields.Float(
        string='Total Price',
        store=True,
        readonly=True
    )
    design_document = fields.Binary("Design Document")
    design_document_filename = fields.Char()
    
    packing_cost_sheet_ids = fields.One2many(
        'packing.cost.sheet',
        'lead_id',
        string="Packing Cost Sheets",
        readonly=True
    )

    engineering_response_ids = fields.One2many(
        'engineering.response',
        'lead_id',
        string="Engineering Responses"
    )


    def action_sale_quotations_new(self):
        """Create a draft quotation from CRM lead products and open it."""
        self.ensure_one()
        print("\n\n>>> METHOD CALLED: action_sale_quotations_new <<<\n\n")

        # 1️⃣ Create new sale order (draft)
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'opportunity_id': self.id,
            'origin': self.name or self.display_name,
            'user_id': self.user_id.id,
            'team_id': self.team_id.id,
        })
        print(f"\n>>> SALE ORDER CREATED: {sale_order.name} (ID: {sale_order.id}) <<<\n")

        # 2️⃣ Add products from lead
        for line in self.product_line_ids:
            print(f" - Product Added: {line.product_id.display_name}, Qty: {line.quantity}, Price: {line.unit_price}")
            self.env['sale.order.line'].create({
                'order_id': sale_order.id,
                'product_id': line.product_id.id,
                'name': line.product_id.display_name,
                'product_uom_qty': line.quantity or 1.0,
                'price_unit': line.product_id.list_price,
            })

        # 3️⃣ Log result
        print("\n>>> QUOTATION CREATED SUCCESSFULLY <<<\n")

        # 4️⃣ Return action to open the new quotation in form view
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotation',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
            'target': 'current',
        }


    def action_send_to_engineering(self):
        """Send lead to Engineering and move to 'Send for Analysis' stage."""
        self.ensure_one()

        # Get the 'Send for Analysis' stage
        send_stage = self.env.ref('dw_crm.stage_send_for_analysis', raise_if_not_found=False)
        if not send_stage:
            raise UserError(_("Stage 'Send for Analysis' not found. Please install CRM stages data."))

        # Update the stage
        self.stage_id = send_stage.id

        # Check if Engineering record already exists
        existing_eng = self.env['engineering.team'].search([('lead_id', '=', self.id)], limit=1)
        if not existing_eng:
            eng = self.env['engineering.team'].create_from_crm(self)

        # Post chatter message
        self.message_post(
            body=_("Lead sent to Engineering for analysis by <b>%s</b>.") % self.env.user.name)
        
        return True

    def _compute_department_times(self):
        for lead in self:
            lead.department_times_ids = self.env['department.time.tracking'].search([
                '|',
                ('target_model', '=', f'crm.lead,{lead.id}'),
                ('lead_id', '=', lead.id)
            ])


    def write(self, vals):
        if 'stage_id' in vals and not self.env.context.get('skip_stage_tracking'):
            for lead in self:
                new_stage = self.env['crm.stage'].browse(vals['stage_id'])

                last_tracking = self.env['department.time.tracking'].search([
                    ('target_model', '=', f'crm.lead,{lead.id}'),
                    ('status', '=', 'in_progress')
                ], limit=1, order='start_time desc')

                if last_tracking:
                    last_tracking.write({
                        'end_time': fields.Datetime.now(),
                        'status': 'done',
                    })

                tracking_vals = {
                    'target_model': f'crm.lead,{lead.id}',
                    'stage_name': new_stage.name,
                    'user_id': self.env.user.id,
                    'start_time': fields.Datetime.now(),
                    'status': 'in_progress'
                }

                if new_stage.is_won:
                    now = fields.Datetime.now()
                    tracking_vals.update({
                        'start_time': now,
                        'end_time': now,
                        'status': 'done',
                    })

                self.env['department.time.tracking'].create(tracking_vals)

        return super().write(vals)
       

    def action_analysis_done(self):
        """Transition from 'Send for Analysis' to 'Analysis Done' stage."""
        done_stage = self.env.ref('dw_crm.stage_analysis_done', raise_if_not_found=False)
        if not done_stage:
            raise UserError("Stage 'Analysis Done' not found. Please install CRM stages data.")
        self.write({'stage_id': done_stage.id})
        self.message_post(body="Analysis completed by %s." % self.env.user.name)
        return True  # Triggers form refresh
    




    def action_open_engineering_wizard(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Engineering Response',
            'res_model': 'engineering.note.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
            }
        }

class CrmStage(models.Model):
    _inherit = 'crm.stage'

    allowed_group_ids = fields.Many2many(
                            'res.groups',
                            string="Allowed Groups",
                            help="Only users in these groups can move a lead into this stage."
                        )

    @api.model
    def create_default_stages(self):  

        stage_data = [
            {'name': 'New', 'sequence': 1, 'fold': False},
            {'name': 'Send for Analysis', 'sequence': 2, 'fold': False},
            {'name': 'Analysis Done', 'sequence': 3, 'fold': False},
            {'name': 'Quotation Sent', 'sequence': 4, 'fold': False},
            {'name': 'Won', 'sequence': 5, 'fold': True, 'is_won': True},
        ]




class EngineeringNoteWizard(models.TransientModel):
    _name = 'engineering.note.wizard'
    _description = 'Engineering Note Wizard'

    lead_id = fields.Many2one('crm.lead', required=True)
    note = fields.Text(string="Note")
    attachment = fields.Binary(string="Attachment")
    attachment_filename = fields.Char()

    def action_submit(self):
        self.ensure_one()

        engineering = self.env['engineering.team'].search([
            ('lead_id', '=', self.lead_id.id)
        ], limit=1)

        self.env['engineering.response'].create({
            'lead_id': self.lead_id.id,
            'engineering_id': engineering.id if engineering else False,
            'note': self.note,
            'attachment': self.attachment,
            'attachment_filename': self.attachment_filename,
            'user_id': self.env.user.id,
        })

        # Optional chatter log
        self.lead_id.message_post(
            body="New Engineering response added by %s" % self.env.user.name
        )

        return {'type': 'ir.actions.act_window_close'}



