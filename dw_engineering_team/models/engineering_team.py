# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


# --------------------------------------------------
# CRM Lead Product Line
# --------------------------------------------------
class CrmLeadProductLine(models.Model):
    _name = 'crm.lead.product.line'
    _description = 'CRM Lead Product Line'

    lead_id = fields.Many2one('crm.lead', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', required=True)
    product_tmpl_id = fields.Many2one(
        'product.template',
        related='product_id.product_tmpl_id',
        store=True
    )
    quantity = fields.Float(default=1.0)
    unit_price = fields.Float(string="Target Rate")
    product_weight = fields.Float(string="Part weight  (in kgs)     ")



    # def action_create_packing_cost_sheet(self):
    #     self.ensure_one()

    #     existing = self.env['packing.cost.sheet'].search([
    #         ('lead_product_line_id', '=', self.id)
    #     ], limit=1)

    #     if existing:
    #         sheet = existing
    #     else:
    #         sheet = self.env['packing.cost.sheet'].create({
    #             'lead_id': self.lead_id.id,
    #             'lead_product_line_id': self.id,
    #             'part_name': self.product_id.display_name,
    #         })

    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Packing Cost Sheet',
    #         'res_model': 'packing.cost.sheet',
    #         'view_mode': 'form',
    #         'res_id': sheet.id,
    #         'target': 'current',
    #     }

    def action_create_packing_cost_sheet(self):
        self.ensure_one()
        existing_sheet = self.env['packing.cost.sheet'].search([
            ('engineering_product_line_id', '=', self.id)
        ], limit=1)
        if existing_sheet:
            existing_sheet.write({
            'part_weight': self.product_weight,
            'part_name': self.product_id.display_name,
        })
            sheet = existing_sheet
        else:
            sheet = self.env['packing.cost.sheet'].create({
                'engineering_product_line_id': self.id,
                'engineering_id': self.engineering_id.id,  
                'lead_id': self.engineering_id.lead_id.id if self.engineering_id.lead_id else False,  
                'part_name': self.product_id.display_name,
                'bom_type': self.product_id.bom_type if hasattr(self.product_id, 'bom_type') else False,
                'part_weight':self.product_weight,
            })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Packing Cost Sheet',
            'res_model': 'packing.cost.sheet',
            'view_mode': 'form',
            'res_id': sheet.id,
            'target': 'current',
        }





# --------------------------------------------------
# Engineering Product Line
# --------------------------------------------------
class EngineeringProductLine(models.Model):
    _name = 'engineering.team.product'
    _description = 'Engineering Team Product Line'

    engineering_id = fields.Many2one(
        'engineering.team',
        ondelete='cascade',
        required=True
    )
    product_id = fields.Many2one('product.product', required=True)
    product_tmpl_id = fields.Many2one(
        'product.template',
        related='product_id.product_tmpl_id',
        store=True
    )
    product_weight= fields.Float(string ="Part Weight")
    quantity = fields.Float(default=1.0)
    cost_price = fields.Float(string="Target Price")
    cost_price_m = fields.Float(string="Unit Price Mgnt")

    total_price = fields.Float(
        compute='_compute_total_price',
        store=True
    )

    @api.onchange('product_id')
    def _onchange_product_id_set_price(self):
        for rec in self:
            if rec.product_id and not rec.cost_price:
                rec.cost_price = rec.product_id.lst_price or 0.0

    @api.depends('quantity', 'cost_price')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = rec.quantity * rec.cost_price

    def write(self, vals):
        res = super().write(vals)
        for line in self:
            if line.engineering_id:
                line.engineering_id._recompute_bom_exploded_lines()
        return res

    def name_get(self):
        result = []
        for rec in self:
            name = rec.product_id.display_name if rec.product_id else ''
            result.append((rec.id, name))
        return result
    


    def action_create_packing_cost_sheet(self):
        self.ensure_one()

        existing_sheet = self.env['packing.cost.sheet'].search([
            ('engineering_product_line_id', '=', self.id)
        ], limit=1)

        if existing_sheet:
            existing_sheet.write({
            'part_weight': self.product_weight,
            'part_name': self.product_id.display_name,
        })
            sheet = existing_sheet
        else:
            sheet = self.env['packing.cost.sheet'].create({
                'engineering_product_line_id': self.id,
                'engineering_id': self.engineering_id.id,
            'lead_id': self.engineering_id.lead_id.id,
                'part_name': self.product_id.display_name,
                'part_weight': self.product_weight,
                'bom_type': self.product_id.bom_type if hasattr(self.product_id, 'bom_type') else False,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Packing Cost Sheet',
            'res_model': 'packing.cost.sheet',
            'view_mode': 'form',
            'res_id': sheet.id,
            'target': 'current',
        }
# --------------------------------------------------
# Engineering Team
# --------------------------------------------------
class EngineeringTeam(models.Model):
    _name = 'engineering.team'
    _description = 'Engineering Team Analysis'
    _rec_name = 'lead_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # --------------------------------------------------
    # BASIC
    # --------------------------------------------------
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        readonly=True
    )

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    partner_id = fields.Many2one(
        'res.partner',
        related='lead_id.partner_id',
        store=True,
        readonly=True
    )

    # --------------------------------------------------
    # ENGINEERING DETAILS
    # --------------------------------------------------
    design_ref = fields.Binary("Design Reference")
    design_ref_filename = fields.Char()
    estimation_time = fields.Float("Estimation Time (Days)")
    engineering_notes = fields.Text()

    design_document = fields.Binary("Design Document", readonly=True)
    design_document_filename = fields.Char()
    # --------------------------------------------------
    # PRODUCTS
    # --------------------------------------------------
    product_line_ids = fields.One2many(
        'engineering.team.product',
        'engineering_id'
    )

    packing_cost_sheet_ids = fields.One2many(
        'packing.cost.sheet',
        'engineering_id',
        string="Packing Cost Sheets"
    )
    engineering_response_ids = fields.One2many(
        'engineering.response',
        'engineering_id',
        string="CRM Responses"
    )

    analysis_note = fields.Text("Analysis Note")
    analysis_attachment = fields.Binary("Attachment")
    analysis_attachment_filename = fields.Char()



    @api.model
    def create_from_crm(self, crm_lead):
        """Create Engineering Team record from CRM Lead"""

        existing = self.search([('lead_id', '=', crm_lead.id)], limit=1)
        if existing:
            raise UserError(_("Engineering analysis already exists for this lead!"))

        # 1️⃣ Create Engineering Team
        eng_record = self.create({
            'lead_id': crm_lead.id,
            'state': 'draft',
            'engineer_id': self.env.user.id,
            'design_document': crm_lead.design_document,
            'design_document_filename': crm_lead.design_document_filename,
        })

        # 2️⃣ LINK packing.cost.sheet → CRM + Engineering
        if crm_lead.packing_cost_sheet_ids:
            crm_lead.packing_cost_sheet_ids.write({
                'engineering_id': eng_record.id,
                'lead_id': crm_lead.id,  
            })

        # 3️⃣ Copy product lines
        for line in crm_lead.product_line_ids:
            self.env['engineering.team.product'].create({
                'engineering_id': eng_record.id,
                'product_id': line.product_id.id,
                'quantity': line.quantity,
                'cost_price': line.unit_price or line.product_id.lst_price or 0.0,
                'product_weight':line.product_weight or 0.0,
            })

        # # 4️⃣ Update CRM lead
        # crm_lead.write({
        #     'engineering_team_id': self.env.user.id,
        # })

        return eng_record



    state = fields.Selection(
        [('draft', 'New'), ('done', 'Analysis Done')],
        default='draft'
    )
    engineer_id = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user
    )
    date_done = fields.Datetime(readonly=True)


    # def action_analysis_done(self):
    #     for rec in self:
    #         if rec.state == 'done':
    #             raise UserError(_("Analysis already done"))

    #         # Update Engineering record
    #         rec.state = 'done'
    #         rec.date_done = fields.Datetime.now()

    #         if rec.lead_id:
    #             lead = rec.lead_id

    #             # Move CRM lead to "Analysis Done" stage
    #             stage = self.env['crm.stage'].search(
    #                 [('name', '=', 'Analysis Done')],
    #                 limit=1
    #             )
    #             if not stage:
    #                 stage = self.env['crm.stage'].create({
    #                     'name': 'Analysis Done'
    #                 })

    #             # FIX IS HERE
    #             lead.write({
    #                 'stage_id': stage.id,
    #                 # 'engineering_team_id': rec.engineer_id.id,
    #                 # 'engineering_id': rec.id,
    #                 'design_ref': rec.design_ref,
    #                 'design_ref_filename': rec.design_ref_filename,
    #                 'estimation_time': rec.estimation_time,
    #                 'engineering_notes': rec.engineering_notes,
                    
    #             })

    #               # 🔥 THIS is what links Packing Cost Sheet to CRM
    #             rec.packing_cost_sheet_ids.write({
    #                 'lead_id': lead.id
    #             })

    #             # Chatter
    #             lead.message_post(
    #                 body=_("Engineering analysis completed by <b>%s</b>.") %
    #                     rec.engineer_id.name
    #             )


    def action_analysis_done(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_("Analysis already done"))
            rec.state = 'done'
            rec.date_done = fields.Datetime.now()

            if rec.lead_id:
                lead = rec.lead_id
                stage = self.env['crm.stage'].search([('name', '=', 'Analysis Done')], limit=1)
                if not stage:
                    stage = self.env['crm.stage'].create({'name': 'Analysis Done'})

                lead.write({
                    'stage_id': stage.id,
                    'design_ref': rec.design_ref,
                    'design_ref_filename': rec.design_ref_filename,
                    'estimation_time': rec.estimation_time,
                    'engineering_notes': rec.engineering_notes,
                })

                # Find ALL sheets linked to this engineering record
                # (directly via engineering_id OR via product lines)
                product_line_ids = rec.product_line_ids.ids
                all_sheets = self.env['packing.cost.sheet'].search([
                    '|',
                    ('engineering_id', '=', rec.id),
                    ('engineering_product_line_id', 'in', product_line_ids)
                ])
                all_sheets.write({
                    'lead_id': lead.id,
                    'engineering_id': rec.id,  # ensure all are linked
                })

                lead.message_post(
                    body=_("Engineering analysis completed by <b>%s</b>.") % rec.engineer_id.name
                )



    def action_open_packing_cost_sheet(self):
        self.ensure_one()

        # If already created → open existing
        if self.packing_cost_sheet_ids:
            sheet = self.packing_cost_sheet_ids[0]
        else:
            # Create new Packing Cost Sheet
            sheet = self.env['packing.cost.sheet'].create({
                'name': self.lead_id.name or 'Packing Cost Sheet',
                'engineering_id': self.id,
                'lead_id': self.lead_id.id,   # ← THIS MUST EXIST
                'moq': 1,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Packing Cost Sheet',
            'res_model': 'packing.cost.sheet',
            'view_mode': 'form',
            'res_id': sheet.id,
            'target': 'current',
        }



class EngineeringResponse(models.Model):
    _name = 'engineering.response'
    _description = 'Engineering Response History'
    _order = 'create_date desc'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    engineering_id = fields.Many2one('engineering.team')
    note = fields.Text("Note")
    attachment = fields.Binary("Attachment")
    attachment_filename = fields.Char()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    date = fields.Datetime(default=fields.Datetime.now)