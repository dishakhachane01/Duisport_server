from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import re


_logger = logging.getLogger(__name__)

class PackingCostSheet(models.Model):
    _name = 'packing.cost.sheet'
    _description = 'Packing Cost Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'sequence_no'

    reference_bom_id = fields.Many2one(
        'packing.cost.sheet',
        string="Reference BOM",
        help="Select BOM to copy lines from"
    )

    revision_history_ids = fields.One2many(
        'packing.cost.revision.history',
        'sheet_id',
        string="Revision History",
        readonly=True
    )

    sequence_no = fields.Char(
        string="Packing Cost Sheet No",
        readonly=True,
        copy=False,
        index=True,
        default='New'
    )

    revision_no = fields.Integer(
        string="Revision No",
        default=0,
        tracking=True,
        copy=True
    )

    name = fields.Char(
        string="Revision",
        compute="_compute_revision_name",
        store=True,
        tracking=True
    )

    parent_id = fields.Many2one(
        'packing.cost.sheet',
        string="Parent BOM",
        readonly=True,
        copy=False,
        help="Original BOM if this is a revision"
    )

    child_ids = fields.One2many(
        'packing.cost.sheet',
        'parent_id',
        string="Revisions",
        copy=False
    )

    highest_revision = fields.Integer(
        string="Latest Revision",
        compute="_compute_highest_revision",
        store=False
    )
    display_sequence = fields.Char(
        string="Sequence number",
        compute="_compute_display_sequence",
        store=False
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    @api.depends('sequence_no', 'revision_no')
    def _compute_display_sequence(self):
        for rec in self:
            if rec.revision_no:
                rec.display_sequence = f"{rec.sequence_no} / Rev-{rec.revision_no}"
            else:
                rec.display_sequence = rec.sequence_no or ""

    lead_id = fields.Many2one(
        'crm.lead',
        string="CRM Lead",
        ondelete='cascade',
        index=True
    )

    engineering_id = fields.Many2one(
        'engineering.team',
        string="Engineering Reference",
        ondelete='cascade',
        readonly=True
    )

    # HEADER DETAILS
    ref = fields.Char(string="Reference")
    part_name = fields.Char(string="Part Name")
    box_id_l = fields.Float(string='Length')
    box_id_w = fields.Float(string='Width')
    box_id_h = fields.Float(string='Height')

    box_od_l = fields.Float(string='Length', compute="_compute_box_od_l", store=True, readonly=False)
    box_od_w = fields.Float(string='Width', compute="_compute_box_od_w", store=True, readonly=False)
    box_od_h = fields.Float(
        string='Height',
        compute="_compute_box_od_h",
        store=True,
        readonly=False
    )

    engineering_product_line_id = fields.Many2one(
    'engineering.team.product',
    string="Engineering Product Line",
    ondelete='cascade'
)


    # state = fields.Selection([
    #     ('draft',          'Draft'),
    #     ('quality_check',  'Sent for Quality Check'),
    #     ('revision',       'Revision Requested'),
    #     ('approved',       'Approved'),
    # ], string="Status",
    # default='draft',
    # tracking=True,
    # copy=False,
    # readonly=True,
    # )

    qc_remark = fields.Text(
    string="QC Remarks",
    tracking=True,
    copy=False,
)
    
    qc_attachment = fields.Binary(string="QC attachment", copy=False)

    sent_to_qc_by = fields.Many2one('res.users', string="Sent to QC By", readonly=True, copy=False)
    sent_to_qc_date = fields.Datetime(string="Sent to QC On", readonly=True, copy=False)
    approved_by = fields.Many2one('res.users', string="Approved By", readonly=True, copy=False)
    approved_date = fields.Datetime(string="Approved On", readonly=True, copy=False)



    @api.depends('line_ids.thickness', 'line_ids.description', 'bom_type', 'box_id_h')
    def _compute_box_od_l(self):
        for record in self:
            if record.bom_type == '4way_runner':
               
                ts_ply_length = 0
                
                for line in record.line_ids:
                    if not line.description:
                        continue
                        
                    name = line.description.name
                    
                    if name == 'TS Ply':
                        ts_ply_length = line.length
                    
                
                record.box_od_l = ts_ply_length

            if record.bom_type == '2way_runner':
               
                ts_ply_length = 0
                
                for line in record.line_ids:
                    if not line.description:
                        continue
                        
                    name = line.description.name
                    
                    if name == 'TS Ply':
                        ts_ply_length = line.length
                    
                
                record.box_od_l = ts_ply_length


    @api.depends('line_ids.thickness', 'line_ids.description', 'bom_type', 'box_id_h')
    def _compute_box_od_w(self):
        for record in self:
            if record.bom_type == '4way_runner':
               
                ts_ply_width = 0
                
                for line in record.line_ids:
                    if not line.description:
                        continue
                        
                    name = line.description.name
                    
                    if name == 'TS Ply':
                        ts_ply_width = line.width
                    
                
                record.box_od_w = ts_ply_width
        
            elif record.bom_type == '2way_runner':
               
                ts_ply_width = 0
                
                for line in record.line_ids:
                    if not line.description:
                        continue
                        
                    name = line.description.name
                    
                    if name == 'TS Ply':
                        ts_ply_width = line.width
                    
                
                record.box_od_w = ts_ply_width    
    

    @api.depends('line_ids.thickness', 'line_ids.description', 'bom_type', 'box_id_h')
    def _compute_box_od_h(self):
        for record in self:
            if record.bom_type == '4way_runner':
                # Excel Row 4: =F3+F6+F7+F8+F19
                # F3 = box_id_h
                # F6 = Base Plywood thickness
                # F7 = Length Runner thickness
                # F8 = Width Runner thickness
                # F19 = TS Ply thickness
                
                base_ply_thick = 0
                lr_thick = 0
                wr_thick = 0
                ts_ply_thick = 0
                l_wise = 0
                
                for line in record.line_ids:
                    if not line.description:
                        continue
                        
                    name = line.description.name
                    
                    if 'Base Plywood' in name:
                        base_ply_thick = line.thickness
                    elif 'Length Runner' in name:
                        lr_thick = line.thickness
                    elif 'Width Runner' in name:
                        wr_thick = line.thickness
                    elif name == 'TS Ply':
                        ts_ply_thick = line.thickness
                    elif name == 'TS L wise Batten':
                        l_wise = line.thickness
                
                record.box_od_h = (record.box_id_h or 0) + base_ply_thick + lr_thick + wr_thick + ts_ply_thick + l_wise
                
            elif record.bom_type in ['pinewood_pallet', 'pinewood_plywood']:
                # Sum all thicknesses
                record.box_od_h = sum(record.line_ids.mapped('thickness'))
           
           
            elif record.bom_type == 'block_type':

                base_ply_thick = 0
                above_block_plank_thick = 0
                block_thick = 0
                below_block_plank_thick = 0
                ts_ply_thick = 0
                l_wise_batten_thick = 0

                for line in record.line_ids:
                    if not line.description:
                        continue

                    name = line.description.name.strip()

                    if 'Base Plywood' in name:
                        base_ply_thick = line.thickness

                    elif 'Above Block Plank' in name:
                        above_block_plank_thick = line.thickness

                    elif 'Below Block Plank' in name:
                        below_block_plank_thick = line.thickness

                    elif 'Block' in name:
                        block_thick = line.thickness

                    elif name == 'TS Ply':
                        ts_ply_thick = line.thickness

                    elif name == 'TS L wise Batten':
                        l_wise_batten_thick = line.thickness


                _logger.info(
                    f"Computed thicknesses for block type: "
                    f"base_ply={base_ply_thick}, "
                    f"above_block_plank={above_block_plank_thick}, "
                    f"block={block_thick}, "
                    f"below_block_plank={below_block_plank_thick}, "
                    f"ts_ply={ts_ply_thick}, "
                    f"l_wise_batten={l_wise_batten_thick}"
                )

                record.box_od_h = (
                    (record.box_id_h or 0)
                    + base_ply_thick
                    + above_block_plank_thick
                    + below_block_plank_thick
                    + block_thick
                    + ts_ply_thick
                    + l_wise_batten_thick
                )


            elif record.bom_type == '2way_runner':

                
                base_ply_thick = 0
                lr_thick = 0
                ts_ply_thick = 0
                l_wise = 0
                
                for line in record.line_ids:
                    if not line.description:
                        continue
                        
                    name = line.description.name
                    
                    if 'Base Plywood' in name:
                        base_ply_thick = line.thickness
                    elif 'Length Runner' in name:
                        lr_thick = line.thickness
                    elif name == 'TS Ply':
                        ts_ply_thick = line.thickness
                    elif name == 'TS L wise Batten':
                        l_wise = line.thickness
                
                record.box_od_h = (record.box_id_h or 0) + base_ply_thick + lr_thick + ts_ply_thick + l_wise
          

            else:
                record.box_od_h = 0
    
    
    # COST LINES
    line_ids = fields.One2many(
        'packing.cost.line',
        'sheet_id',
        string="Cost Details"
    )
    empty_box_weight = fields.Float("Empty Box Weight (KGS)", compute="_compute_empty_box_weight")
    moq = fields.Integer("MOQ")

    # TOTALS
    total_sqft = fields.Float(compute="_compute_totals", store=True)
    total_cft = fields.Float(compute="_compute_totals", store=True)
    material_total = fields.Monetary(compute="_compute_totals", store=True, currency_field='currency_id')
    part_weight = fields.Float("Part Weight (KGS)")
    mfg_percent = fields.Float(default=0.05)
    overhead_percent = fields.Float(default=0.05)
    profit_percent = fields.Float(default= 0.30)


    mfg_amount = fields.Monetary(compute="_compute_totals", store=True,  currency_field='currency_id')
    overhead_amount = fields.Monetary(compute="_compute_totals", store=True,  currency_field='currency_id')
    profit_amount = fields.Monetary(compute="_compute_totals", store=True,  currency_field='currency_id')


    freight = fields.Monetary(default=0.0,  currency_field='currency_id')
    packing_charges = fields.Monetary(default=0.0,  currency_field='currency_id')

    grand_total = fields.Monetary(compute="_compute_totals", store=True,  currency_field='currency_id')

    bom_type = fields.Selection([
        ('2way_runner', '2 Way Runner Type Pine + Ply Boxes'),
        ('4way_runner', '4 Way Runner Type Pine + Ply Boxes'),
        ('block_type', 'Block Type Pine + Plywood Wooden Boxes'),
        ('thyssen_heavy', 'Thyssen Heavy Pallets + Bags'),
        ('pinewood_pallet', 'Pinewood Pallet'),
        ('pinewood_plywood', 'Pinewood + Plywood Pallets'),
         ('ch_box', 'CH Boxes Cost Sheet Format'),
        ('full_pinewood_box', 'Full Pinewood Box'),
    ], string="BOM Type")

    lead_id = fields.Many2one('crm.lead', ondelete='cascade')
    lead_product_line_id = fields.Many2one(
        'crm.lead.product.line',
        string="Lead Product"
    )

    discount_percent = fields.Float(
    string="Discount (%)",
    default=0.0
)

    discount_amount = fields.Monetary(
        string="Discount Amount",
        compute="_compute_totals",
        store=True,
        currency_field='currency_id'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        if not self.env.context.get('default_parent_id'):
            line_commands = []
            Description = self.env['description.master']

            bom_type = self.env.context.get('default_bom_type')

            if bom_type:
                line_commands = []
                Description = self.env['description.master']

            for line in self._get_default_bom_lines(bom_type):
                desc = Description.search([
                    ('name', '=', line['description']),
                    ('section', '=', line['section'])
                ], limit=1)

                if not desc:
                    continue

                line_commands.append((0, 0, {
                    'section': line['section'],
                    'description': desc.id,
                    'is_template': True,
                }))

            res['line_ids'] = line_commands

        return res

    @api.depends('sequence_no', 'revision_no')
    def _compute_revision_name(self):
        for rec in self:
            if rec.revision_no == 0:
                rec.name = f"{rec.sequence_no}"
            else:
                rec.name = f"{rec.sequence_no} / Rev-{rec.revision_no}"

    @api.depends('revision_no', 'parent_id', 'parent_id.child_ids', 'child_ids.revision_no')
    def _compute_highest_revision(self):
        for rec in self:
            parent_bom = rec.parent_id if rec.parent_id else rec
            all_boms = parent_bom | parent_bom.child_ids
            
            if all_boms:
                rec.highest_revision = max(all_boms.mapped('revision_no'))
            else:
                rec.highest_revision = rec.revision_no

        # def action_create_revision(self):
        #     self.ensure_one()
            
        #     parent_bom = self.parent_id if self.parent_id else self
        #     all_existing_revisions = parent_bom | parent_bom.child_ids
        #     new_rev_no = max(all_existing_revisions.mapped('revision_no')) + 1
            
        #     new_bom = self.copy({
        #         'sequence_no': parent_bom.sequence_no,
        #         'revision_no': new_rev_no,
        #         'parent_id': parent_bom.id,
        #         'part_name': self.part_name,
        #         'ref': self.ref,
        #     })
            
        #     for line in self.line_ids:
        #         line.copy({'sheet_id': new_bom.id})
            
        #     return {
        #         'type': 'ir.actions.act_window',
        #         'name': f'Revision {new_rev_no}',
        #         'res_model': 'packing.cost.sheet',
        #         'res_id': new_bom.id,
        #         'view_mode': 'form',
        #         'target': 'current',
        #     }

    def _get_default_bom_lines(self, bom_type):

        if bom_type == '2way_runner':
            return [
                {'section': 'base', 'description': 'Base Plywood', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'base', 'description': 'Length Runner', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'long_side', 'description': 'LS Ply', 'material_id': 'Plywood', 'rm_rate': '33'},
                {'section': 'long_side', 'description': 'LS Horizontal Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'long_side', 'description': 'LS Vertical Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'short_side', 'description': 'SS Ply', 'material_id': 'Plywood', 'rm_rate': '33'},
                {'section': 'short_side', 'description': 'SS Horizontal Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'short_side', 'description': 'SS Vertical Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'short_side', 'description': 'SS Bharti', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'top_side', 'description': 'TS Ply', 'material_id': 'Plywood', 'rm_rate': '33'},
                {'section': 'top_side', 'description': 'TS L wise Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'top_side', 'description': 'TS W wise Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'loose_pine_support', 'description': 'Pine Supp', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'consumables', 'description': 'HDPE'},
                {'section': 'consumables', 'description': 'VCI'},
                {'section': 'consumables', 'description': 'Desicant'},
            ]

        elif bom_type == '4way_runner':
            return [
                {'section': 'base', 'description': 'Base Plywood', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'base', 'description': 'Length Runner', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'base', 'description': 'Width Runner', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'long_side', 'description': 'LS Ply', 'material_id': 'Plywood', 'rm_rate': '33'},
                {'section': 'long_side', 'description': 'LS Horizontal Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'long_side', 'description': 'LS Vertical Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'short_side', 'description': 'SS Ply', 'material_id': 'Plywood', 'rm_rate': '33'},
                {'section': 'short_side', 'description': 'SS Horizontal Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'short_side', 'description': 'SS Vertical Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'short_side', 'description': 'SS Bharti', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'top_side', 'description': 'TS Ply', 'material_id': 'Plywood', 'rm_rate': '33'},
                {'section': 'top_side', 'description': 'TS L wise Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'top_side', 'description': 'TS W wise Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'loose_pine_support', 'description': 'Pine Supp', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'consumables', 'description': 'HDPE'},
                {'section': 'consumables', 'description': 'VCI'},
                {'section': 'consumables', 'description': 'Desicant'},
            ]

        
        elif bom_type == 'block_type':
            return [
                {'section': 'base', 'description': 'Base Plywood', 'material_id': 'Plywood', 'rm_rate': '33'},
                {'section': 'base', 'description': 'Above Block Plank', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'base', 'description': 'Block', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'base', 'description': 'Below Block Plank', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'long_side', 'description': 'LS Ply', 'material_id': 'Plywood', 'rm_rate': '33'},
                {'section': 'long_side', 'description': 'LS Horizontal Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'long_side', 'description': 'LS Vertical Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'short_side', 'description': 'SS Ply', 'material_id': 'Plywood', 'rm_rate': '33'},
                {'section': 'short_side', 'description': 'SS Horizontal Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'short_side', 'description': 'SS Vertical Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'top_side', 'description': 'TS Ply', 'material_id': 'Plywood', 'rm_rate': '33'},
                {'section': 'top_side', 'description': 'TS L wise Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'top_side', 'description': 'TS W wise Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'loose_ply_sheet', 'description': 'Ply sheet', 'material_id': 'Plywood', 'rm_rate': '33'},
                {'section': 'loose_pine_support', 'description': 'Pine Supp', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'consumables', 'description': 'HDPE'},
                {'section': 'consumables', 'description': 'VCI'},
                {'section': 'consumables', 'description': 'Desicant'},
            ]

        elif bom_type == 'thyssen_heavy':
            return [
                {'section': 'base', 'description': 'Base Plywood', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'base', 'description': 'Length Runner', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'base', 'description': 'Width Runner', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'loose_pine_support', 'description': 'Pine Supp', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'consumables', 'description': 'Lag Screw 10x150 mm'},
                {'section': 'consumables', 'description': 'M16x300 mm Nut Bolt'},
                {'section': 'consumables', 'description': 'D Clamp & Lag Screw'},
                {'section': 'consumables', 'description': 'HDPE'},
                {'section': 'consumables', 'description': 'VCI'},
                {'section': 'consumables', 'description': 'Aluminium Foil Bag'},
                {'section': 'consumables', 'description': 'Silpaulin Bag'},
                {'section': 'consumables', 'description': 'HDPE Bag'},
                {'section': 'consumables', 'description': 'Desicant'},
                {'section': 'consumables', 'description': '5 mm Foam'},
                {'section': 'consumables', 'description': 'Bubble Roll'},
                {'section': 'consumables', 'description': 'Lashing Belt'},
                {'section': 'consumables', 'description': 'Buckles'},
                {'section': 'consumables', 'description': 'Stretch wrap'},
            ]

        elif bom_type == 'pinewood_pallet':
            return [
                {'section': 'base', 'description': 'Top Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'base', 'description': 'Above Block Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'base', 'description': 'Block', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'base', 'description': 'Below Block Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
            ]
        elif bom_type == 'pinewood_plywood':
            return [
                {'section': 'base', 'description': 'Top Batten', 'material_id': 'Plywood', 'rm_rate': '33'},
                {'section': 'base', 'description': 'Above Block Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'base', 'description': 'Block', 'material_id': 'Pinewood', 'rm_rate': '700'},
                {'section': 'base', 'description': 'Below Block Batten', 'material_id': 'Pinewood', 'rm_rate': '700'},
            ]


        elif bom_type == 'ch_box':
            return [
                {
                    'sheet_id': self.id,
                    'sr_no': 1,
                    'box_type': 'Universal Box',
                    'length': 0,
                    'width': 0,
                    'height': 0,
                    'no_of_ply': 0,
                    'board_gsm': 0,
                    'deckle': 0.0,
                    'cl': 0.0,
                    'weight_kg': 0.0,
                    'sqm': 0.0,
                },
                {
                    'sheet_id': self.id,
                    'sr_no': 2,
                    'box_type': 'Half Universal',
                    'length': 0,
                    'width': 0,
                    'height': 0,
                    'no_of_ply': 0,
                    'board_gsm': 0,
                    'deckle': 0.0,
                    'cl': 0.0,
                    'weight_kg': 0.0,
                    'sqm': 0.0,
                },
                {
                    'sheet_id': self.id,
                    'sr_no': 3,
                    'box_type': 'Sleeve',
                    'length': 0,
                    'width': 0,
                    'height': 0,
                    'no_of_ply': 0,
                    'board_gsm': 0,
                    'deckle': 0.0,
                    'cl': 0.0,
                    'weight_kg': 0.0,
                    'sqm': 0.0,
                },
                {
                    'sheet_id': self.id,
                    'sr_no': 4,
                    'box_type': 'Cap',
                    'length': 0,
                    'width': 0,
                    'height': 0,
                    'no_of_ply': 0,
                    'board_gsm': 0,
                    'deckle': 0.0,
                    'cl': 0.0,
                    'weight_kg': 0.0,
                    'sqm': 0.0,
                },
            ]

        elif bom_type == 'full_pinewood_box':
            return [
                # DECK
                {'section': 'base', 'description': 'Deck'},
                {'section': 'base', 'description': 'Length Runner'},
                {'section': 'base', 'description': 'Width Runner'},
                {'section': 'base', 'description': 'HDPE'},


                # LONG SIDE
                {'section': 'long_side', 'description': 'Long side'},
                {'section': 'long_side', 'description': 'H Batten'},
                {'section': 'long_side', 'description': 'V Batten'},
                {'section': 'long_side', 'description': 'HDPE'},


                # SHORT SIDE
                {'section': 'short_side', 'description': 'Short Side'},
                {'section': 'short_side', 'description': 'H Batten'},
                {'section': 'short_side', 'description': 'V Batten'},
                {'section': 'short_side', 'description': 'HDPE'},


                # TOP
                {'section': 'top_side', 'description': 'Top side'},
                {'section': 'top_side', 'description': 'L Batten'},
                {'section': 'top_side', 'description': 'W Batten'},
                {'section': 'top_side', 'description': 'HDPE'},


                # SUPPORT
                {'section': 'loose_pine_support', 'description': 'Loose Support'},

                # PACKING MATERIAL
                {'section': 'consumables', 'description': 'VCI Bag in SQM'},
                {'section': 'consumables', 'description': 'Aluminium Bag in SQM'},
                {'section': 'consumables', 'description': 'Bubble Sheet in SQM'},
                {'section': 'consumables', 'description': 'Stretch Wrap in KG'},
                {'section': 'consumables', 'description': 'Lashing 32mm in Meter'},
                {'section': 'consumables', 'description': 'Buckle 32mm in Meter'},
                {'section': 'consumables', 'description': 'Desiccant in KG'},
            ]



        return []
    

    def _create_default_lines(self):
        Description = self.env['description.master']
        Material = self.env['material.master']

        lines = self._get_default_bom_lines(self.bom_type)

        for line in lines:
            print("Processing line:", line)

            desc = Description.search([
                ('name', '=', line['description']),
                ('section', '=', line['section']),
            ], limit=1)

            material = Material.search([
                ('name', '=', line['material_id'])
            ], limit=1)

            print("Found description:", desc)
            print("Found material:", material)

            self.env['packing.cost.line'].create({
                'sheet_id': self.id,
                'section': line['section'],
                'description': desc.id if desc else False,
                'material_id': material.id if material else False,
                'is_template': True,
            })

  

    # QUALITY CHECK OF BOM
    # def action_send_to_quality_check(self):
    #     self.ensure_one()
    #     if self.state != 'draft':
    #         raise UserError(_("Only a Draft BOM can be sent for Quality Check."))
    #     self.write({
    #         'state': 'quality_check',
    #         'sent_to_qc_by': self.env.uid,
    #         'sent_to_qc_date': fields.Datetime.now(),
    #         'qc_remark': False,
    #         'qc_attachment': False,
    #     })
    #     self.message_post(
    #         body=_("BOM <b>%s</b> sent for Quality Check by <b>%s</b>.") % (
    #             self.display_sequence, self.env.user.name),
    #         message_type='notification',
    #         subtype_xmlid='mail.mt_note',
    #     )

    # def action_request_revision(self):
    #     self.ensure_one()
    #     if self.state != 'quality_check':
    #         raise UserError(_("Only a BOM under Quality Check can be sent back."))
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': _('Request Revision'),
    #         'res_model': 'packing.cost.revision.wizard',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {'default_sheet_id': self.id},
    #     }

    # def action_approve(self):
    #     self.ensure_one()
    #     if self.state != 'quality_check':
    #         raise UserError(_("Only a BOM under Quality Check can be approved."))

    #     # Mark all pending revision history as resolved
    #     self.revision_history_ids.filtered(
    #         lambda r: r.status == 'pending'
    #     ).write({'status': 'resolved'})

    #     self.write({
    #         'state': 'approved',
    #         'approved_by': self.env.uid,
    #         'approved_date': fields.Datetime.now(),
    #     })
    #     self.message_post(
    #         body=_("BOM <b>%s</b> <b>Approved</b> by <b>%s</b>.") % (
    #             self.display_sequence, self.env.user.name),
    #         message_type='notification',
    #         subtype_xmlid='mail.mt_note',
    #     )

    # def action_reset_to_draft(self):
    #     self.ensure_one()
    #     if self.state != 'revision':
    #         raise UserError(_("Only a BOM with 'Revision Requested' status can be reset."))
    #     self.write({'state': 'draft'})
    #     self.message_post(
    #         body=_("BOM <b>%s</b> reset to Draft by <b>%s</b> to address QC remarks.") % (
    #             self.display_sequence, self.env.user.name),
    #         message_type='notification',
    #         subtype_xmlid='mail.mt_note',
    #     )






    @api.onchange('bom_type')
    def _onchange_bom_type(self):
        if self.reference_bom_id:
            return

        if not self.bom_type:
            return

        lines = self._get_default_bom_lines(self.bom_type)
        new_lines = []

        for line in lines:

            desc = self.env['description.master'].search([
                ('name', '=', line.get('description')),
                ('section', '=', line.get('section')),
            ], limit=1)

            material_name = line.get('material_id')

            material = False
            if material_name:
                material = self.env['material.master'].search([
                    ('name', 'ilike', material_name)
                ], limit=1)

            new_lines.append((0, 0, {
                'section': line.get('section'),
                'description': desc.id if desc else False,
                'material_id': material.id if material else False,
                'is_template': True,
            }))

        self.line_ids = [(5, 0, 0)] + new_lines



    @api.onchange('reference_bom_id')
    def _onchange_reference_bom(self):
        if not self.reference_bom_id:
            return
    
        ref_bom = self.reference_bom_id

        # ✅ Copy Header Fields
        self.bom_type = ref_bom.bom_type
        self.part_name = ref_bom.part_name
        self.box_id_l = ref_bom.box_id_l
        self.box_id_w = ref_bom.box_id_w
        self.box_id_h = ref_bom.box_id_h
        self.moq = ref_bom.moq
        self.part_weight = ref_bom.part_weight

        self.mfg_percent = ref_bom.mfg_percent
        self.overhead_percent = ref_bom.overhead_percent
        self.profit_percent = ref_bom.profit_percent

        self.freight = ref_bom.freight
        self.packing_charges = ref_bom.packing_charges

        new_lines = []

        for line in self.reference_bom_id.line_ids:
            new_lines.append((0, 0, {
                'section': line.section,
                'description': line.description.id,
                'material_id': line.material_id.id,
                'length': line.length,
                'width': line.width,
                'thickness': line.thickness,
                'qty': line.qty,
                'rm_rate': line.rm_rate,
                'is_template': False,
            }))

        # 🔥 Clear existing lines and copy new ones
        self.line_ids = [(5, 0, 0)] + new_lines


    @api.model
    def create(self, vals):
        if vals.get('sequence_no', 'New') == 'New':
            vals['sequence_no'] = self.env['ir.sequence'].next_by_code(
                'packing.cost.sheet'
            ) or 'New'

        record = super().create(vals)

        if record.box_id_l and record.box_id_w and record.box_id_h:
            record._calculate_line_dimensions()
     
        return record

    def action_view_revisions(self):
        self.ensure_one()
        parent_bom = self.parent_id if self.parent_id else self
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'All Revisions',
            'res_model': 'packing.cost.sheet',
            'view_mode': 'tree,form',
            'domain': ['|', ('id', '=', parent_bom.id), ('parent_id', '=', parent_bom.id)],
        }

    @api.depends(
        'line_ids.amount',
        'line_ids.sqft',
        'line_ids.material_id',
        'line_ids.material_id.name',
        'mfg_percent',
        'overhead_percent',
        'profit_percent',
        'freight',
        'packing_charges',
        'discount_percent'
    )
    def _compute_totals(self):
        for rec in self:
            total_sqft = 0.0
            total_cft = 0.0

            for line in rec.line_ids:
                if not line.material_id:
                    continue

                mat_name = (line.material_id.name or '').lower()

                if 'plywood' in mat_name:
                    total_sqft += line.sqft or 0.0
                elif any(k in mat_name for k in ['pinewood', 'rubberwood', 'junglewood']):
                    total_cft += line.sqft or 0.0

            rec.total_sqft = total_sqft
            rec.total_cft = total_cft

            rec.material_total = sum(rec.line_ids.mapped('amount'))

            rec.mfg_amount = rec.material_total * rec.mfg_percent
            rec.overhead_amount = rec.material_total * rec.overhead_percent
            rec.profit_amount = rec.material_total * rec.profit_percent

            subtotal = (
                rec.material_total
                + rec.mfg_amount
                + rec.overhead_amount
                + rec.profit_amount
                + rec.freight
                + rec.packing_charges
            )

            # Discount calculation
            rec.discount_amount = subtotal * (rec.discount_percent / 100.0)

            # Final total after discount
            rec.grand_total = subtotal - rec.discount_amount

  
  
    @api.depends('total_cft', 'total_sqft')
    def _compute_empty_box_weight(self):
        for record in self:
            if record.bom_type == 'block_type':
               record.empty_box_weight = ((record.total_cft * 17) + (record.total_sqft * 0.6))
            if record.bom_type == '4way_runner':
               record.empty_box_weight = ((record.total_cft * 17) + (record.total_sqft * 0.6))
            if record.bom_type == '2way_runner':
               record.empty_box_weight = ((record.total_cft * 17) + (record.total_sqft * 0.6))
            else:
                record.empty_box_weight = (((record.total_cft * 17) + (record.total_sqft * 0.6)) + 20)



    def write(self, vals):
        res = super().write(vals)

        if any(key in vals for key in ['box_id_l', 'box_id_w', 'box_id_h', 'bom_type']):
            for record in self:
                if record.box_id_l and record.box_id_w and record.box_id_h:
                    record._calculate_line_dimensions()
        return res

    def action_recalculate_dimensions(self):
        """Manual button to recalculate all dimensions"""
        self.ensure_one()
        self._calculate_line_dimensions()
        
        # Force complete form reload
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'packing.cost.sheet',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'context': self.env.context,
        }


    def _calculate_line_dimensions(self):
        """Calculate and update line dimensions - BASED ON EXCEL FORMULAS"""
        self.ensure_one()
        
        _logger.info(f"Calculating dimensions for BOM {self.display_sequence}")
        
        # For PALLET types, use box_od_l and box_od_w (not box_id)
        if self.bom_type in ['pinewood_pallet', 'pinewood_plywood']:
            L = self.box_od_l or 0
            W = self.box_od_w or 0
            H = 0
            _logger.info(f"Pallet type: using box_od_l={L}, box_od_w={W}")
        else:
            # For other types, use box_id dimensions
            L = self.box_id_l or 0  # D3
            W = self.box_id_w or 0  # E3
            H = self.box_id_h or 0  # F3
            _logger.info(f"BOM type {self.bom_type}: using box_id_l={L}, box_id_w={W}, box_id_h={H}")

        if not L or not W:
            _logger.warning("Missing L or W dimensions - aborting calculation")
            return
        
        if self.bom_type not in ['pinewood_pallet', 'pinewood_plywood'] and not H:
            _logger.warning("Missing box_id_h - aborting calculation")
            return

        def get_line_id(name):
            for line in self.line_ids:
                if line.description and name in line.description.name:
                    return line.id
            return None

        def get_line_value(name, field):
            for line in self.line_ids:
                if line.description and name in line.description.name:
                    return getattr(line, field, 0)
            return 0

        _logger.info(f"BOM type: {self.bom_type}")

        # =====================================================
        # 4 WAY RUNNER - EXCEL FORMULA BASED
        # =====================================================
        if self.bom_type == '4way_runner':
            
            # Get all line IDs
            base_id = get_line_id('Base Plywood')
            lr_id = get_line_id('Length Runner')
            wr_id = get_line_id('Width Runner')
            ls_ply_id = get_line_id('LS Ply')
            ls_h_id = get_line_id('LS Horizontal Batten')
            ls_v_id = get_line_id('LS Vertical Batten')
            ss_ply_id = get_line_id('SS Ply')
            ss_h_id = get_line_id('SS Horizontal Batten')
            ss_v_id = get_line_id('SS Vertical Batten')
            ss_bharti_id = get_line_id('SS Bharti')
            ts_ply_id = get_line_id('TS Ply')
            ts_l_id = get_line_id('TS L wise Batten')
            ts_w_id = get_line_id('TS W wise Batten')
            pine_id = get_line_id('Pine Supp')
            hdpe_id = get_line_id('HDPE')
            vci_id = get_line_id('VCI')

            # Get thickness and qty values (F and G columns)
            ss_ply_thickness = get_line_value('SS Ply', 'thickness')  # F14
            ss_ply_qty = get_line_value('SS Ply', 'qty')  # G14
            vr_width = get_line_value('SS Vertical Batten', 'width')
            vr_qty = get_line_value('SS Vertical Batten', 'qty')  # G14
            ss_h_thickness = get_line_value('SS Horizontal Batten', 'thickness')  # F15
            ss_h_qty = get_line_value('SS Horizontal Batten', 'qty')  # G15
            ss_h_width = get_line_value('SS Horizontal Batten', 'width')  # E15
            base_thickness = get_line_value('Base Plywood', 'thickness')  # F6
            lr_thickness = get_line_value('Length Runner', 'thickness')  # F7
            pine_thickness = get_line_value('Pine Supp', 'thickness')  # F23
            ls_h_width = get_line_value('LS Horizontal Batten', 'width')  # E11
            ls_h_qty = get_line_value('LS Horizontal Batten', 'qty')  # G11
            ts_l_width = get_line_value('TS L wise Batten', 'width')
            ts_W_width = get_line_value('TS W wise Batten', 'width')  # E20  # E20
            ts_l_qty = get_line_value('TS L wise Batten', 'qty')  # G20
            ss_v_width = get_line_value('SS Vertical Batten', 'width')  # E16
            ss_v_qty = get_line_value('SS Vertical Batten', 'qty')  # G16

            # BASE PLYWOOD - Row 6
            # Length: =D3+(F14*G14)
            # Width: =E3
            if base_id:
                base_length = L + (ss_ply_thickness * ss_ply_qty)
                base_width = W
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (base_length, base_width, base_id))
            else:
                base_length = L
                base_width = W

            # LENGTH RUNNER - Row 7
            # Length: =D3+(F14*G14)+(F15*G15/2)
            # Width: =F3+F6+F7+F23
            if lr_id:
                lr_length = base_length
                self.env.cr.execute("""
                        UPDATE packing_cost_line 
                        SET length = %s
                        WHERE id = %s
                    """, (lr_length, lr_id))

            # WIDTH RUNNER - Row 8
            # Length: =E3
            # Width: =F3+F6+F7+F23 (same as Length Runner width)
            if wr_id:
                wr_length = W
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (wr_length, wr_id))

            # LS PLY - Row 10
            # Length: =D3+(F14*G14)+(F15*G15/2)
            # Width: =F3+(F6+F23+F7)
            if ls_ply_id:
                ls_ply_length = L + (ss_ply_thickness * ss_ply_qty) + (ss_h_thickness * ss_h_qty / 2)
                ls_ply_width = H + base_thickness + pine_thickness + lr_thickness
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (ls_ply_length, ls_ply_width, ls_ply_id))

            # LS HORIZONTAL BATTEN - Row 11
            # Length: =D13 (Base Plywood length)
            if ls_h_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (base_length, ls_h_id))

            # LS VERTICAL BATTEN - Row 12
            # Length: =F3-(E11*G11/2)
            if ls_v_id:
                ls_v_length = H - (ls_h_width * ls_h_qty / 2)
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ls_v_length, ls_v_id))

            # SS PLY - Row 14
            # Length: =E3
            # Width: =F3+(F6+F23)
            if ss_ply_id:
                ss_ply_length = W
                ss_ply_width = H + base_thickness + pine_thickness
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (ss_ply_length, ss_ply_width, ss_ply_id))

            # SS HORIZONTAL BATTEN - Row 15
            # Length: =D14 (SS Ply length = E3)
            if ss_h_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (W, ss_h_id))

            # SS VERTICAL BATTEN - Row 16
            # Length: =(F3+F6+F7)-E15
            if ss_v_id:
                ss_v_length = (H + base_thickness + lr_thickness) - ss_h_width
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ss_v_length, ss_v_id))

            # SS BHARTI - Row 17
            # Length: =(D14-E16*G16)
            if ss_bharti_id:
                ss_bharti_length = ss_ply_length - (vr_width * vr_qty/2)
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ss_bharti_length, ss_bharti_id))

            # TS PLY - Row 19
            # Length: =D3+(F14*G14)+(F15*G15)
            # Width: =E3+(F14*G14)+(F15*G15)
            if ts_ply_id:
                ts_ply_length = L + (ss_ply_thickness * ss_ply_qty) + (ss_h_thickness * ss_h_qty)
                ts_ply_width = W + (ss_ply_thickness * ss_ply_qty) + (ss_h_thickness * ss_h_qty)
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (ts_ply_length, ts_ply_width, ts_ply_id))
            else:
                ts_ply_length = L
                ts_ply_width = W

            # TS L WISE BATTEN - Row 20
            # Length: =D19 (TS Ply length)
            if ts_l_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ts_ply_length, ts_l_id))

            # TS W WISE BATTEN - Row 21
            # Length: =E19-(E20*G20)
            if ts_w_id:
                ts_w_length = ts_ply_width - (ts_l_width * ts_l_qty)
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ts_w_length, ts_w_id))

            # PINE SUPP - Row 23
            # Length: =E3
            if pine_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (W, pine_id))

            # HDPE - Row 24
            # Length: =D3/1000
            # Width: =E3/1000
            # Thickness: =F3/1000
            if hdpe_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, (L / 1000, W / 1000, H / 1000, hdpe_id))

            # VCI - Row 25
            # Length: =(D4+50)/1000
            # Width: =(E3+50)/1000
            # Thickness: =(F3+50)/1000
            if vci_id:
                # length_vcl = 
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, ((base_length + 50) / 1000, (W + 50) / 1000, (H + 50) / 1000, vci_id))

      
      
        # =====================================================
        # PALLET TYPES - CORRECTED
        if self.bom_type in ['pinewood_pallet', 'pinewood_plywood']:
            
            top_id = get_line_id('Top Batten')
            above_id = get_line_id('Above Block Batten')
            below_id = get_line_id('Below Block Batten')

            # Top Batten: length = box_od_l
            if top_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (L, top_id))

            # Above Block Batten: length = box_od_w
            if above_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (W, above_id))


            # Below Block Batten: length = box_od_l
            if below_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (L, below_id))

        # =====================================================
        # BLOCK TYPE - CORRECTED
        # =====================================================
        elif self.bom_type == 'block_type':
            
            base_id = get_line_id('Base Plywood')
            above_block_id = get_line_id('Above Block Plank')
            below_block_id = get_line_id('Below Block Plank')
            ls_ply_id = get_line_id('LS Ply')
            ls_h_id = get_line_id('LS Horizontal Batten')
            ls_v_id = get_line_id('LS Vertical Batten')
            ss_ply_id = get_line_id('SS Ply')
            ss_h_id = get_line_id('SS Horizontal Batten')
            ss_v_id = get_line_id('SS Vertical Batten')
            ts_ply_id = get_line_id('TS Ply')
            ts_l_id = get_line_id('TS L wise Batten')
            ts_w_id = get_line_id('TS W wise Batten')
            # ply_sheet_id = get_line_id('Ply sheet')
            pine_id = get_line_id('Pine Supp')
            ply_sheet_id = get_line_id('Ply sheet')
            hdpe_id = get_line_id('HDPE')
            vci_id = get_line_id('VCI')

            # Get values
            ls_ply_thickness = get_line_value('LS Ply', 'thickness')
            ls_ply_qty = get_line_value('LS Ply', 'qty')
            ls_h_thickness = get_line_value('LS Horizontal Batten', 'thickness')
            ls_h_qty = get_line_value('LS Horizontal Batten', 'qty')
            ls_h_width = get_line_value('LS Horizontal Batten', 'width')
            ss_ply_thickness = get_line_value('SS Ply', 'thickness')
            ss_ply_qty = get_line_value('SS Ply', 'qty')
            ss_h_thickness = get_line_value('SS Horizontal Batten', 'thickness')
            ss_h_qty = get_line_value('SS Horizontal Batten', 'qty')
            ss_h_width = get_line_value('SS Horizontal Batten', 'width')
            ts_l_width = get_line_value('TS L wise Batten', 'width')
            ts_l_qty = get_line_value('TS L wise Batten', 'qty')

            # Base Plywood
            # Length = box_id_l + (ls_ply_thickness * ls_ply_qty) + (ls_h_thickness * ls_h_qty)
            # Width = box_id_w + (ss_ply_thickness * ss_ply_qty) + (ss_h_thickness * ss_h_qty)
            if base_id:
                base_length = (
                    L
                    + (ls_ply_thickness * ls_ply_qty if ls_ply_thickness and ls_ply_qty else 0)
                    + (ls_h_thickness * ls_h_qty if ls_h_thickness and ls_h_qty else 0)
                )
                base_width = (
                    W
                    + (ss_ply_thickness * ss_ply_qty if ss_ply_thickness and ss_ply_qty else 0)
                    + (ss_h_thickness * ss_h_qty if ss_h_thickness and ss_h_qty else 0)
                )
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (base_length, base_width, base_id))
                base_length_final = base_length
                base_width_final = base_width
            else:
                base_length_final = L
                base_width_final = W

            # Above Block Plank: length = Base Plywood length
            if above_block_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (base_length_final, above_block_id))

            # Below Block Plank: length = Base Plywood width
            if below_block_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (base_width_final, below_block_id))

            # LS Ply: length = Base Plywood length, width = box_id_h
            if ls_ply_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (base_length_final, H, ls_ply_id))

            # LS Horizontal Batten: length = LS Ply length
            if ls_h_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (base_length_final, ls_h_id))

            # LS Vertical Batten: length = box_id_h - (ls_h_width * ls_h_qty / 2)
            if ls_v_id and ls_h_width and ls_h_qty:
                ls_v_length = H - ((ls_h_width * ls_h_qty) / 2)
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ls_v_length, ls_v_id))

            # SS Ply - CORRECTED: length = box_id_w (NOT box_id_h), width = box_id_h
            if ss_ply_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (W, H, ss_ply_id))

            # SS Horizontal Batten: length = SS Ply length
            if ss_h_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (W, ss_h_id))

            # SS Vertical Batten: length = box_id_h - (ss_h_width * ss_h_qty / 2)
            if ss_v_id and ss_h_width and ss_h_qty:
                ss_v_length = H - ((ss_h_width * ss_h_qty) / 2)
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ss_v_length, ss_v_id))

            # TS Ply: length = base_length, width = base_width
            if ts_ply_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (base_length_final, base_width_final, ts_ply_id))

            # TS L wise Batten: length = TS Ply length
            if ts_l_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (base_length_final, ts_l_id))

            # TS W wise Batten: length = TS Ply width - (ts_l_width * ts_l_qty)
            if ts_w_id and ts_l_width and ts_l_qty:
                ts_w_length = base_width_final - (ts_l_width * ts_l_qty)
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ts_w_length, ts_w_id))

            # Ply Sheet: length = box_id_l, width = box_id_w
            if ply_sheet_id:
                ply_length=L
                ply_width=W
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (ply_length, ply_width, ply_sheet_id))

            # Pine Supp: length = box_id_l
            if pine_id:
                pine_Length = L

                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (pine_Length, pine_id))

            # HDPE
            if hdpe_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, (L / 1000, W / 1000, H / 1000, hdpe_id))

            # Update box OD
            self.env.cr.execute("""
                UPDATE packing_cost_sheet 
                SET box_od_l = %s, box_od_w = %s
                WHERE id = %s
            """, (base_length_final, base_width_final, self.id))

            # Calculate box_od_h
            self.env.cr.execute("""
                SELECT COALESCE(SUM(thickness), 0)
                FROM packing_cost_line
                WHERE sheet_id = %s
            """, (self.id,))
            box_od_h_calc = self.env.cr.fetchone()[0]

            # VCI - CORRECTED
            if vci_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, ((base_length_final + 50) / 1000, (base_width_final + 50) / 1000, (box_od_h_calc + 50) / 1000, vci_id))

        # =====================================================
        # 2-WAY RUNNER - EXCEL FORMULA BASED
        # =====================================================
        elif self.bom_type == '2way_runner':
            
            # Get all line IDs
            base_id = get_line_id('Base Plywood')
            lr_id = get_line_id('Length Runner')
            ls_ply_id = get_line_id('LS Ply')
            ls_h_id = get_line_id('LS Horizontal Batten')
            ls_v_id = get_line_id('LS Vertical Batten')
            ss_ply_id = get_line_id('SS Ply')
            ss_h_id = get_line_id('SS Horizontal Batten')
            ss_v_id = get_line_id('SS Vertical Batten')
            ss_bharti_id = get_line_id('SS Bharti')
            ts_ply_id = get_line_id('TS Ply')
            ts_l_id = get_line_id('TS L wise Batten')
            ts_w_id = get_line_id('TS W wise Batten')
            pine_id = get_line_id('Pine Supp')
            hdpe_id = get_line_id('HDPE')
            vci_id = get_line_id('VCI')

            # Get thickness, width, and qty values from lines
            # LS (Long Side) values
            ls_ply_thickness = get_line_value('LS Ply', 'thickness')  # F9
            ls_ply_qty = get_line_value('LS Ply', 'qty')  # G9
            ls_h_thickness = get_line_value('LS Horizontal Batten', 'thickness')  # F10
            ls_h_qty = get_line_value('LS Horizontal Batten', 'qty')  # G10
            ls_h_width = get_line_value('LS Horizontal Batten', 'width')  # E10
            
            # SS (Short Side) values
            ss_ply_thickness = get_line_value('SS Ply', 'thickness')  # F13
            ss_ply_qty = get_line_value('SS Ply', 'qty')  # G13
            ss_h_thickness = get_line_value('SS Horizontal Batten', 'thickness')  # F14
            ss_h_width = get_line_value('SS Horizontal Batten', 'width')  # E14
            ss_v_width = get_line_value('SS Vertical Batten', 'width')  # E15
            ss_v_qty = get_line_value('SS Vertical Batten', 'qty')  # G15
            
            # TS (Top Side) values
            ts_l_width = get_line_value('TS L wise Batten', 'width')  # E19
            ts_l_qty = get_line_value('TS L wise Batten', 'qty')  # G19
            
            # Base values
            base_thickness = get_line_value('Base Plywood', 'thickness')  # F6
            lr_thickness = get_line_value('Length Runner', 'thickness')  # F7
            pine_thickness = get_line_value('Pine Supp', 'thickness')  # F22

            # =====================================================
            # BASE PLYWOOD - Row 6
            # Excel: Length = =D3+(F13*G13)
            #        Width = =E3
            # =====================================================
            if base_id:
                base_length = L + (ls_ply_thickness * ls_ply_qty)
                base_width = W
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (base_length, base_width, base_id))
                _logger.info(f"Base Plywood: length={base_length}, width={base_width}")
            else:
                base_length = L
                base_width = W

            # =====================================================
            # LENGTH RUNNER - Row 7
            # Excel: Length = =D6 (Base Plywood length)
            # =====================================================
            if lr_id:
                lr_length = base_length
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (lr_length, lr_id))
                _logger.info(f"Length Runner: length={lr_length}")

            # =====================================================
            # LS PLY - Row 9
            # Excel: Length = =D3+(F13*G13)+(F14*G14)
            #        Width = =F3+F6+F22+F7
            # =====================================================
            if ls_ply_id:
                # These values are already retrieved at the top
                ss_ply_thickness = get_line_value('SS Ply', 'thickness')  # F13
                ss_ply_qty = get_line_value('SS Ply', 'qty')  # G13
                ss_h_thickness = get_line_value('SS Horizontal Batten', 'thickness')  # F14
                ss_h_qty = get_line_value('SS Horizontal Batten', 'qty')  # G14

                # So in LS PLY calculation, just use them directly:
                ls_ply_length = L + (ss_ply_thickness * ss_ply_qty) + (ss_h_thickness * ss_h_qty / 2)
                # ls_ply_length = L + (ss_ply_thickness * ss_ply_qty) + (ss_h_thickness * ss_h_qty / 2)
                ls_ply_width = H + base_thickness + pine_thickness + lr_thickness
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (ls_ply_length, ls_ply_width, ls_ply_id))
                _logger.info(f"LS Ply: length={ls_ply_length}, width={ls_ply_width}")

            # =====================================================
            # LS HORIZONTAL BATTEN - Row 10
            # Excel: Length = =D9 (LS Ply length)
            # =====================================================
            if ls_h_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ls_ply_length, ls_h_id))
                _logger.info(f"LS Horizontal Batten: length={ls_ply_length}")

            # =====================================================
            # LS VERTICAL BATTEN - Row 11
            # Excel: Length = =F3-(E10*G10/2)
            # =====================================================
            if ls_v_id:
                ls_v_length = H - (ls_h_width * ls_h_qty / 2)
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ls_v_length, ls_v_id))
                _logger.info(f"LS Vertical Batten: length={ls_v_length}")

            # =====================================================
            # SS PLY - Row 13
            # Excel: Length = =E3
            #        Width = =F3+F6+F22
            # =====================================================
            if ss_ply_id:
                ss_ply_length = W
                ss_ply_width = H + base_thickness + pine_thickness
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (ss_ply_length, ss_ply_width, ss_ply_id))
                _logger.info(f"SS Ply: length={ss_ply_length}, width={ss_ply_width}")

            # =====================================================
            # SS HORIZONTAL BATTEN - Row 14
            # Excel: Length = =D13 (SS Ply length = E3)
            # =====================================================
            if ss_h_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (W, ss_h_id))
                _logger.info(f"SS Horizontal Batten: length={W}")

            # =====================================================
            # SS VERTICAL BATTEN - Row 15
            # Excel: Length = =(F3+F6+F7)-E14
            # =====================================================
            if ss_v_id:
                ss_v_length = (H + base_thickness + lr_thickness) - ss_h_width
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ss_v_length, ss_v_id))
                _logger.info(f"SS Vertical Batten: length={ss_v_length}")

            # =====================================================
            # SS BHARTI - Row 16
            # Excel: Length = =D13-(E15*G15/2)
            # Note: D13 is SS Ply length (which equals W = E3)
            # =====================================================
            if ss_bharti_id:
                ss_bharti_length = W - (ss_v_width * ss_v_qty / 2)
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ss_bharti_length, ss_bharti_id))
                _logger.info(f"SS Bharti: length={ss_bharti_length}")

            # =====================================================
            # TS PLY - Row 18
            # Excel: Length = =D3+(F13*G13)+(F13*G13)+(F14*2)
            #        Width = =E3+(F13*G13)+(F14*2)
            # =====================================================
            if ts_ply_id:
                ss_ply_thickness = get_line_value('SS Ply', 'thickness')  # F13
                ss_ply_qty = get_line_value('SS Ply', 'qty')  # G13
                ss_h_thickness = get_line_value('SS Horizontal Batten', 'thickness')  # F14
                ss_h_qty = get_line_value('SS Horizontal Batten', 'qty')  # G14

                # So in LS PLY calculation, just use them directly:
                ts_ply_length = L + (ss_ply_thickness * ss_ply_qty) + (ss_h_thickness * ss_h_qty)
                ts_ply_width = W + (ls_ply_thickness * ls_ply_qty) + (ls_h_thickness * 2)
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (ts_ply_length, ts_ply_width, ts_ply_id))
                _logger.info(f"TS Ply: length={ts_ply_length}, width={ts_ply_width}")
            else:
                # Fallback values if TS Ply doesn't exist
                ts_ply_length = L
                ts_ply_width = W

            # =====================================================
            # TS L WISE BATTEN - Row 19
            # Excel: Length = =D18 (TS Ply length)
            # =====================================================
            if ts_l_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ts_ply_length, ts_l_id))
                _logger.info(f"TS L wise Batten: length={ts_ply_length}")

            # =====================================================
            # TS W WISE BATTEN - Row 20
            # Excel: Length = =E18-(E19*G19)
            # =====================================================
            if ts_w_id:
                ts_w_length = ts_ply_width - (ts_l_width * ts_l_qty)
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ts_w_length, ts_w_id))
                _logger.info(f"TS W wise Batten: length={ts_w_length}")

            # =====================================================
            # PINE SUPP - Row 22
            # Excel: Length = =E3
            # =====================================================
            if pine_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (W, pine_id))
                _logger.info(f"Pine Supp: length={W}")

            # =====================================================
            # HDPE - Row 23
            # Excel: Length = =D3/1000
            #        Width = =E3/1000
            #        Thickness = =F3/1000
            # =====================================================
            if hdpe_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, (L / 1000, W / 1000, H / 1000, hdpe_id))
                _logger.info(f"HDPE: length={L/1000}, width={W/1000}, thickness={H/1000}")

            # =====================================================
            # VCI - Row 24
            # Excel: Length = =(D4+50)/1000  (where D4 is Box OD = D18)
            #        Width = =(E3+50)/1000
            #        Thickness = =(F3+50)/1000
            # Note: Using base_length as the Box OD length
            # =====================================================
            if vci_id:
                ts_ply_l = get_line_value('TS Ply', 'length')
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, ((ts_ply_l + 50) / 1000, (W + 50) / 1000, (H + 50) / 1000, vci_id))
                _logger.info(f"VCI: length={(ts_ply_l+50)/1000}, width={(W+50)/1000}, thickness={(H+50)/1000}")

        # =====================================================
        # THYSSEN HEAVY PALLETS + BAGS
        # =====================================================
        elif self.bom_type == 'thyssen_heavy':
            
            # Get all line IDs
            base_id = get_line_id('Base Plywood')
            lr_id = get_line_id('Length Runner')
            wr_id = get_line_id('Width Runner')
            pine_id = get_line_id('Pine Supp')
            
            # Consumables
            lag_screw_id = get_line_id('Lag Screw 10x150 mm')
            nut_bolt_id = get_line_id('M16x300 mm Nut Bolt')
            d_clamp_id = get_line_id('D Clamp & Lag Screw')
            hdpe_id = get_line_id('HDPE')
            vci_id = get_line_id('VCI')
            foil_bag_id = get_line_id('Aluminium Foil Bag')
            silpaulin_id = get_line_id('Silpaulin Bag')
            hdpe_bag_id = get_line_id('HDPE Bag')
            desicant_id = get_line_id('Desicant')
            foam_id = get_line_id('6mm Foam')
            bubble_id = get_line_id('Bubble Roll')
            lashing_id = get_line_id('Lashing Belt')
            buckles_id = get_line_id('Buckles')
            stretch_id = get_line_id('Stretch wrap')

            # Get thickness and qty values
            base_thickness = get_line_value('Base Plywood', 'thickness')  # F6 = 25
            lr_thickness = get_line_value('Length Runner', 'thickness')  # F7 = 100
            lr_qty = get_line_value('Length Runner', 'qty')  # G7
            wr_qty = get_line_value('Width Runner', 'qty')  # G8
            lashing_qty = get_line_value('Lashing Belt', 'qty')  # G23

            # =====================================================
            # BASE PLYWOOD - Row 6
            # Excel: Length = =D4 (which is =D3, Box ID Length)
            #        Width = =E3 (Box ID Width)
            #        Thickness = 25 (Fixed)
            # =====================================================
            if base_id:
                base_length = L
                base_width = W
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (base_length, base_width, base_id))
                _logger.info(f"Base Plywood: length={base_length}, width={base_width}")
            else:
                base_length = L
                base_width = W

            # =====================================================
            # LENGTH RUNNER - Row 7
            # Excel: Length = =D6 (Base Plywood length)
            #        Width = 100 (Fixed)
            #        Thickness = 100 (Fixed)
            # =====================================================
            if lr_id:
                lr_length = base_length
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (lr_length, lr_id))
                _logger.info(f"Length Runner: length={lr_length}")

            # =====================================================
            # WIDTH RUNNER - Row 8
            # Excel: Length = =E3 (Box ID Width)
            #        Width = 100 (Fixed)
            #        Thickness = 8 (Fixed)
            # =====================================================
            if wr_id:
                wr_length = W
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (wr_length, wr_id))
                _logger.info(f"Width Runner: length={wr_length}")

            # =====================================================
            # PINE SUPP - Row 10
            # Excel: Length = =E3 (Box ID Width)
            #        Width = 75 (Fixed)
            #        Thickness = 75 (Fixed)
            # =====================================================
            if pine_id:
                pine_length = W
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (pine_length, pine_id))
                _logger.info(f"Pine Supp: length={pine_length}")

            # =====================================================
            # LAG SCREW 10x150 mm - Row 12
            # Excel: Thickness = =G7*G8 (Length Runner Qty * Width Runner Qty)
            # This is a quantity calculation stored in thickness field
            # =====================================================
            if lag_screw_id and lr_qty and wr_qty:
                lag_screw_calc = lr_qty * wr_qty
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET thickness = %s
                    WHERE id = %s
                """, (lag_screw_calc, lag_screw_id))
                _logger.info(f"Lag Screw 10x150 mm: thickness={lag_screw_calc}")

            # =====================================================
            # M16x300 mm NUT BOLT - Row 13
            # Excel: Thickness = 12 (Fixed)
            # No calculation needed - fixed value
            # =====================================================

            # =====================================================
            # D CLAMP & LAG SCREW - Row 14
            # Excel: Thickness = 20 (Fixed)
            # No calculation needed - fixed value
            # =====================================================

            # =====================================================
            # HDPE - Row 15
            # Excel: Length = =D3/1000
            #        Width = =E3/1000
            #        Thickness = =F3/1000
            # =====================================================
            if hdpe_id:
                hdpe_length = L / 1000
                hdpe_width = W / 1000
                hdpe_thickness = H / 1000
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, (hdpe_length, hdpe_width, hdpe_thickness, hdpe_id))
                _logger.info(f"HDPE: length={hdpe_length}, width={hdpe_width}, thickness={hdpe_thickness}")

            # =====================================================
            # VCI - Row 16
            # Excel: Length = =(D4+50)/1000 (Box OD + 50) / 1000
            #        Width = =(E3+50)/1000
            #        Thickness = =(F3+50)/1000
            # Note: D4 = D3 (Box ID Length)
            # =====================================================
            if vci_id:
                vci_length = (L + 50) / 1000
                vci_width = (W + 50) / 1000
                vci_thickness = (H + 50) / 1000
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, (vci_length, vci_width, vci_thickness, vci_id))
                _logger.info(f"VCI: length={vci_length}, width={vci_width}, thickness={vci_thickness}")
            else:
                vci_length = (L + 50) / 1000
                vci_width = (W + 50) / 1000
                vci_thickness = (H + 50) / 1000

            # =====================================================
            # ALUMINIUM FOIL BAG - Row 17
            # Excel: Length = =D16 (VCI length)
            #        Width = =E16 (VCI width)
            #        Thickness = =F16 (VCI thickness)
            # =====================================================
            if foil_bag_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, (vci_length, vci_width, vci_thickness, foil_bag_id))
                _logger.info(f"Aluminium Foil Bag: length={vci_length}, width={vci_width}, thickness={vci_thickness}")

            # =====================================================  
            # SILPAULIN BAG - Row 18
            # Excel: Length = =D16 (VCI length)
            #        Width = =E16 (VCI width)
            #        Thickness = =F16 (VCI thickness)
            # =====================================================
            if silpaulin_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, (vci_length, vci_width, vci_thickness, silpaulin_id))
                _logger.info(f"Silpaulin Bag: length={vci_length}, width={vci_width}, thickness={vci_thickness}")

            # =====================================================
            # HDPE BAG - Row 19
            # Excel: Length = =D18 (Silpaulin Bag length)
            #        Width = =E18 (Silpaulin Bag width)
            #        Thickness = =F18 (Silpaulin Bag thickness)
            # Note: Since Silpaulin uses VCI dimensions, HDPE Bag also uses VCI
            # =====================================================
            if hdpe_bag_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, (vci_length, vci_width, vci_thickness, hdpe_bag_id))
                _logger.info(f"HDPE Bag: length={vci_length}, width={vci_width}, thickness={vci_thickness}")

            # =====================================================
            # DESICANT - Row 20
            # Excel: Qty = 2 (Fixed)
            # No calculation needed - fixed value
            # =====================================================

            # =====================================================
            # 6MM FOAM - Row 21
            # Excel: Length = =D3/1000
            #        Width = =E3/1000
            #        Thickness = =F3/1000
            # =====================================================
            if foam_id:
                foam_length = L / 1000
                foam_width = W / 1000
                foam_thickness = H / 1000
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, (foam_length, foam_width, foam_thickness, foam_id))
                _logger.info(f"6mm Foam: length={foam_length}, width={foam_width}, thickness={foam_thickness}")
            else:
                foam_length = L / 1000
                foam_width = W / 1000
                foam_thickness = H / 1000

            # =====================================================
            # BUBBLE ROLL - Row 22
            # Excel: Length = =D21 (6mm Foam length)
            #        Width = =E21 (6mm Foam width)
            #        Thickness = =F21 (6mm Foam thickness)
            # =====================================================
            if bubble_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, (foam_length, foam_width, foam_thickness, bubble_id))
                _logger.info(f"Bubble Roll: length={foam_length}, width={foam_width}, thickness={foam_thickness}")

            # =====================================================
            # LASHING BELT - Row 23
            # Excel: Length = =D3/1000
            #        Width = =E3/1000
            #        Thickness = =F3/1000
            # =====================================================
            if lashing_id:
                lashing_length = L / 1000
                lashing_width = W / 1000
                lashing_thickness = H / 1000
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, (lashing_length, lashing_width, lashing_thickness, lashing_id))
                _logger.info(f"Lashing Belt: length={lashing_length}, width={lashing_width}, thickness={lashing_thickness}")

            # =====================================================
            # BUCKLES - Row 24
            # Excel: Qty = =(E23*F2+2+F23*2+E2)/2)*G23
            # Note: This formula appears to have errors/unclear references
            # Typically buckles qty = lashing belt qty (1 buckle per belt)
            # =====================================================
            if buckles_id and lashing_qty:
                # Using simplified logic: 1 buckle per lashing belt
                buckles_qty_calc = lashing_qty
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET qty = %s
                    WHERE id = %s
                """, (buckles_qty_calc, buckles_id))
                _logger.info(f"Buckles: qty={buckles_qty_calc}")

            # =====================================================
            # STRETCH WRAP - Row 25
            # Excel: Qty = 5 (Fixed)
            # No calculation needed - fixed value
            # =====================================================

            # =====================================================
            # UPDATE BOX OD
            # Excel: Box OD Length = =D3 (Box ID Length)
            #        Box OD Width = =E3 (Box ID Width)
            #        Box OD Height = =F3+F6+F7 (Box ID Height + Base + Length Runner)
            # =====================================================
            box_od_l_calc = L
            box_od_w_calc = W
            box_od_h_calc = H + base_thickness + lr_thickness
            
            self.env.cr.execute("""
                UPDATE packing_cost_sheet 
                SET box_od_l = %s, box_od_w = %s, box_od_h = %s
                WHERE id = %s
            """, (box_od_l_calc, box_od_w_calc, box_od_h_calc, self.id))
            _logger.info(f"Box OD: length={box_od_l_calc}, width={box_od_w_calc}, height={box_od_h_calc}")

    
        # =====================================================
        # FULL PINEWOOD BOX - NO DEFAULT VALUES
        # =====================================================
        elif self.bom_type == 'full_pinewood_box':
            
            # Get all line IDs
            # DECK Section
            deck_id = get_line_id('Deck')
            lr_id = get_line_id('Length Runner')
            wr_id = get_line_id('Width Runner')
            deck_hdpe_id = None
            for line in self.line_ids:
                if line.description and 'HDPE' in line.description.name and line.section == 'base':
                    deck_hdpe_id = line.id
                    break
            
            # LONG SIDE Section
            ls_id = get_line_id('Long Side')
            ls_h_id = None
            ls_v_id = None
            ls_hdpe_id = None
            for line in self.line_ids:
                if not line.description or line.section != 'long_side':
                    continue
                if 'H Batten' in line.description.name:
                    ls_h_id = line.id
                elif 'V Batten' in line.description.name:
                    ls_v_id = line.id
                elif 'HDPE' in line.description.name:
                    ls_hdpe_id = line.id
            
            # SHORT SIDE Section
            ss_id = get_line_id('Short Side')
            ss_h_id = None
            ss_v_id = None
            ss_hdpe_id = None
            for line in self.line_ids:
                if not line.description or line.section != 'short_side':
                    continue
                if 'H Batten' in line.description.name:
                    ss_h_id = line.id
                elif 'V Batten' in line.description.name:
                    ss_v_id = line.id
                elif 'HDPE' in line.description.name:
                    ss_hdpe_id = line.id
            
            # TOP Section
            top_id = get_line_id('Top')
            ts_l_id = get_line_id('L Batten')
            ts_w_id = get_line_id('W Batten')
            
            # LOOSE SUPPORT
            support_id = get_line_id('Loose Support')
            
            # CONSUMABLES
            vci_id = get_line_id('VCI Bag in SQM')
            al_bag_id = get_line_id('Aluminium Bag in SQM')
            bubble_id = get_line_id('Bubble Sheet in SQM')
            stretch_id = get_line_id('Stretch Wrap in KG')
            lashing_id = get_line_id('Lashing 32mm in Meter')
            buckle_id = get_line_id('Buckle 32mm in Meter')
            desiccant_id = get_line_id('Desiccant in KG')

            # Get thickness values from line records (no defaults)
            deck_thickness = get_line_value('Deck', 'thickness')
            lr_width = get_line_value('Length Runner', 'width')
            lr_thickness = get_line_value('Length Runner', 'thickness')
            wr_width = get_line_value('Width Runner', 'width')
            wr_thickness = get_line_value('Width Runner', 'thickness')
            
            ls_thickness = get_line_value('Long Side', 'thickness')
            ls_h_width = get_line_value('LS H Batten', 'width') or get_line_value('H Batten', 'width')
            ls_h_thickness = get_line_value('LS H Batten', 'thickness') or get_line_value('H Batten', 'thickness')
            ls_v_width = get_line_value('LS V Batten', 'width') or get_line_value('V Batten', 'width')
            ls_v_thickness = get_line_value('LS V Batten', 'thickness') or get_line_value('V Batten', 'thickness')
            
            ss_thickness = get_line_value('Short Side', 'thickness')
            ss_h_width = get_line_value('SS H Batten', 'width')
            ss_h_thickness = get_line_value('SS H Batten', 'thickness')
            ss_v_width = get_line_value('SS V Batten', 'width')
            ss_v_thickness = get_line_value('SS V Batten', 'thickness')
            
            top_thickness = get_line_value('Top', 'thickness')
            ts_l_width = get_line_value('L Batten', 'width')
            ts_l_thickness = get_line_value('L Batten', 'thickness')
            ts_w_width = get_line_value('W Batten', 'width')
            ts_w_thickness = get_line_value('W Batten', 'thickness')
            
            support_width = get_line_value('Loose Support', 'width')
            support_thickness = get_line_value('Loose Support', 'thickness')

            # =====================================================
            # DECK - Row 6
            # Excel: Length = =C4+40
            #        Width = =D4+40
            #        Height/Thk = from line record
            # =====================================================
            if deck_id:
                deck_length = L + 40
                deck_width = W + 40
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (deck_length, deck_width, deck_id))
                _logger.info(f"Deck: length={deck_length}, width={deck_width}, thickness={deck_thickness}")
            else:
                deck_length = L + 40
                deck_width = W + 40

            # =====================================================
            # LENGTH RUNNER - Row 7
            # Excel: Length = =C6 (Deck length)
            #        Width = from line record
            #        Height/Thk = from line record
            # =====================================================
            if lr_id:
                lr_length = deck_length
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (lr_length, lr_id))
                _logger.info(f"Length Runner: length={lr_length}, width={lr_width}, thickness={lr_thickness}")

            # =====================================================
            # WIDTH RUNNER - Row 8
            # Excel: Length = =D6 (Deck width)
            #        Width = from line record
            #        Height/Thk = from line record
            # =====================================================
            if wr_id:
                wr_length = deck_width
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (wr_length, wr_id))
                _logger.info(f"Width Runner: length={wr_length}, width={wr_width}, thickness={wr_thickness}")

            # =====================================================
            # DECK HDPE - Row 9
            # Excel: Length = =C6
            #        Width = =D6
            # =====================================================
            if deck_hdpe_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (deck_length, deck_width, deck_hdpe_id))
                _logger.info(f"Deck HDPE: length={deck_length}, width={deck_width}")

            # =====================================================
            # LONG SIDE - Row 11
            # Excel: Length = =C7 (Length Runner length)
            #        Width = =E4 (Box ID Height)
            #        Height/Thk = from line record
            # =====================================================
            if ls_id:
                ls_length = lr_length
                ls_width_dim = H  # Box ID Height
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (ls_length, ls_width_dim, ls_id))
                _logger.info(f"Long Side: length={ls_length}, width={ls_width_dim}, thickness={ls_thickness}")

            # =====================================================
            # LONG SIDE H BATTEN - Row 12
            # Excel: Length = =C11 (Long Side length)
            #        Width = from line record
            #        Height/Thk = from line record
            # =====================================================
            if ls_h_id:
                ls_h_length = ls_length
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ls_h_length, ls_h_id))
                _logger.info(f"LS H Batten: length={ls_h_length}, width={ls_h_width}, thickness={ls_h_thickness}")

            # =====================================================
            # LONG SIDE V BATTEN - Row 13
            # Excel: Length = =(D11+185)-75
            #        Width = from line record
            #        Height/Thk = from line record
            # Note: D11 = Box ID Height (E4)
            # The +185 and -75 are structural adjustments
            # =====================================================
            if ls_v_id:
                ls_v_length = (H + 185) - 75
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ls_v_length, ls_v_id))
                _logger.info(f"LS V Batten: length={ls_v_length}, width={ls_v_width}, thickness={ls_v_thickness}")

            # =====================================================
            # LONG SIDE HDPE - Row 14
            # Excel: Length = =C11
            #        Width = =D11 (Box ID Height)
            # =====================================================
            if ls_hdpe_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (ls_length, H, ls_hdpe_id))
                _logger.info(f"LS HDPE: length={ls_length}, width={H}")

            # =====================================================
            # SHORT SIDE - Row 16
            # Excel: Length = =D6 (Deck width)
            #        Width = =E4 (Box ID Height)
            #        Height/Thk = from line record
            # =====================================================
            if ss_id:
                ss_length = deck_width
                ss_width_dim = H
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (ss_length, ss_width_dim, ss_id))
                _logger.info(f"Short Side: length={ss_length}, width={ss_width_dim}, thickness={ss_thickness}")

            # =====================================================
            # SHORT SIDE H BATTEN - Row 17
            # Excel: Length = =C16 (Short Side length)
            #        Width = from line record
            #        Height/Thk = from line record
            # =====================================================
            if ss_h_id:
                ss_h_length = ss_length
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ss_h_length, ss_h_id))
                _logger.info(f"SS H Batten: length={ss_h_length}, width={ss_h_width}, thickness={ss_h_thickness}")

            # =====================================================
            # SHORT SIDE V BATTEN - Row 18
            # Excel: Length = =(D16+94)-75
            #        Width = from line record
            #        Height/Thk = from line record
            # Note: D16 = Box ID Height (E4)
            # The +94 and -75 are structural adjustments
            # =====================================================
            if ss_v_id:
                ss_v_length = (H + 94) - 75
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ss_v_length, ss_v_id))
                _logger.info(f"SS V Batten: length={ss_v_length}, width={ss_v_width}, thickness={ss_v_thickness}")

            # =====================================================
            # SHORT SIDE HDPE - Row 19
            # Excel: Length = =C16
            #        Width = =D16 (Box ID Height)
            # =====================================================
            if ss_hdpe_id:
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (ss_length, H, ss_hdpe_id))
                _logger.info(f"SS HDPE: length={ss_length}, width={H}")

            # =====================================================
            # TOP - Row 21
            # Excel: Length = =C7 (Length Runner length)
            #        Width = =C8 (Width Runner length)
            #        Height/Thk = from line record
            # =====================================================
            if top_id:
                top_length = lr_length
                top_width = wr_length
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s
                    WHERE id = %s
                """, (top_length, top_width, top_id))
                _logger.info(f"Top: length={top_length}, width={top_width}, thickness={top_thickness}")

            # =====================================================
            # TOP L BATTEN - Row 22
            # Excel: Length = =C21 (Top length)
            #        Width = from line record
            #        Height/Thk = from line record
            # =====================================================
            if ts_l_id:
                ts_l_length = top_length
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ts_l_length, ts_l_id))
                _logger.info(f"TS L Batten: length={ts_l_length}, width={ts_l_width}, thickness={ts_l_thickness}")

            # =====================================================
            # TOP W BATTEN - Row 23
            # Excel: Length = =D21-150 (Top width - 150)
            #        Width = from line record
            #        Height/Thk = from line record
            # =====================================================
            if ts_w_id:
                ts_w_length = top_width - 150
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (ts_w_length, ts_w_id))
                _logger.info(f"TS W Batten: length={ts_w_length}, width={ts_w_width}, thickness={ts_w_thickness}")

            # =====================================================
            # LOOSE SUPPORT - Row 26
            # Excel: Length = =D4 (Box ID Width)
            #        Width = from line record
            #        Height/Thk = from line record
            # =====================================================
            if support_id:
                support_length = W
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s
                    WHERE id = %s
                """, (support_length, support_id))
                _logger.info(f"Loose Support: length={support_length}, width={support_width}, thickness={support_thickness}")

            # =====================================================
            # VCI BAG IN SQM - Row 28
            # Excel: Length = =C4/1000
            #        Width = =D4/1000
            #        Thickness = =E4/1000
            # =====================================================
            if vci_id:
                vci_length = L / 1000
                vci_width = W / 1000
                vci_thickness = H / 1000
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, (vci_length, vci_width, vci_thickness, vci_id))
                _logger.info(f"VCI Bag: length={vci_length}, width={vci_width}, thickness={vci_thickness}")

            # =====================================================
            # ALUMINIUM BAG IN SQM - Row 29
            # Excel: Length = =C4/1000
            #        Width = =D4/1000
            #        Thickness = =E4/1000
            # =====================================================
            if al_bag_id:
                al_length = L / 1000
                al_width = W / 1000
                al_thickness = H / 1000
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, width = %s, thickness = %s
                    WHERE id = %s
                """, (al_length, al_width, al_thickness, al_bag_id))
                _logger.info(f"Aluminium Bag: length={al_length}, width={al_width}, thickness={al_thickness}")

            # =====================================================
            # BUBBLE SHEET IN SQM - Row 30
            # Excel: Length = =(C7*2+C8*2)*3/1000
            # Perimeter × 3 / 1000
            # =====================================================
            if bubble_id:
                bubble_length = (lr_length * 2 + wr_length * 2) * 3 / 1000
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, qty = %s
                    WHERE id = %s
                """, (bubble_length, bubble_length, bubble_id))
                _logger.info(f"Bubble Sheet: length={bubble_length}, qty={bubble_length}")

            # =====================================================
            # STRETCH WRAP IN KG - Row 31
            # Excel: Qty = =C31*7.5
            # Get the base value from the line's existing length or qty field
            # If not set, skip (no default value)
            # =====================================================
            if stretch_id:
                stretch_base = get_line_value('Stretch Wrap in KG', 'length')
                if stretch_base:
                    stretch_qty = stretch_base * 7.5
                    self.env.cr.execute("""
                        UPDATE packing_cost_line 
                        SET qty = %s
                        WHERE id = %s
                    """, (stretch_qty, stretch_id))
                    _logger.info(f"Stretch Wrap: qty={stretch_qty} (base={stretch_base})")
                else:
                    _logger.warning("Stretch Wrap: No base value found in length field, skipping calculation")

            # =====================================================
            # LASHING 32MM IN METER - Row 32
            # Excel: Length = =(C8*2+D11*2)*4/10
            # (Width Runner × 2 + Box Height × 2) × 4 / 10
            # =====================================================
            if lashing_id:
                lashing_length = (wr_length * 2 + H * 2) * 4 / 10
                self.env.cr.execute("""
                    UPDATE packing_cost_line 
                    SET length = %s, qty = %s
                    WHERE id = %s
                """, (lashing_length, lashing_length, lashing_id))
                _logger.info(f"Lashing: length={lashing_length}, qty={lashing_length}")

            # =====================================================
            # BUCKLE 32MM - Row 33
            # Excel: Qty = from line record (no default)
            # =====================================================
            if buckle_id:
                # Qty is already set in the line record, no calculation needed
                buckle_qty = get_line_value('Buckle 32mm in Meter', 'qty')
                _logger.info(f"Buckle: qty={buckle_qty} (from line record)")

            # =====================================================
            # DESICCANT IN KG - Row 34
            # Excel: Qty = from line record (no default)
            # =====================================================
            if desiccant_id:
                # Qty is already set in the line record, no calculation needed
                desiccant_qty = get_line_value('Desiccant in KG', 'qty')
                _logger.info(f"Desiccant: qty={desiccant_qty} (from line record)")
    
    
    

        # Manually trigger recomputation of sqft and amount
        for line in self.line_ids:
            line._compute_area()
            line._compute_amount()

        self._compute_box_od_l()
        self._compute_box_od_w()
        self._compute_empty_box_weight()
        self._compute_box_od_h()


        
        _logger.info("Calculation complete")
        
        _logger.info("Calculation complete")


    is_locked = fields.Boolean(
        string="Locked",
        default=False,
        copy=False,
        tracking=True,
    )

    def action_create_revision(self):
        self.ensure_one()
        
        parent_bom = self.parent_id if self.parent_id else self
        if parent_bom.is_locked:
            raise UserError(_(
                "BOM %s is locked. No further revisions can be created."
            ) % parent_bom.display_sequence)
        
        all_existing_revisions = parent_bom | parent_bom.child_ids
        if all_existing_revisions.filtered('is_locked'):
            raise UserError(_(
                "A revision of BOM %s is locked. No further revisions can be created."
            ) % parent_bom.display_sequence)

        new_rev_no = max(all_existing_revisions.mapped('revision_no')) + 1
        new_bom = self.copy({
            'sequence_no': parent_bom.sequence_no,
            'revision_no': new_rev_no,
            'parent_id': parent_bom.id,
            'part_name': self.part_name,
            'ref': self.ref,
            'is_locked': False,
        })
        for line in self.line_ids:
            line.copy({'sheet_id': new_bom.id})
        return {
            'type': 'ir.actions.act_window',
            'name': f'Revision {new_rev_no}',
            'res_model': 'packing.cost.sheet',
            'res_id': new_bom.id,
            'view_mode': 'form',
            'target': 'current',
        }



    def action_lock_bom(self):
        self.ensure_one()
        if self.is_locked:
            raise UserError(_("BOM %s is already locked.") % self.display_sequence)
        self.write({'is_locked': True})
        self.message_post(
            body=_("BOM <b>%s</b> has been <b>locked</b> by <b>%s</b>. No further revisions can be created.") % (
                self.display_sequence, self.env.user.name),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

    def action_unlock_bom(self):
        self.ensure_one()
        if not self.is_locked:
            raise UserError(_("BOM %s is not locked.") % self.display_sequence)
        self.write({'is_locked': False})
        self.message_post(
            body=_("BOM <b>%s</b> has been <b>unlocked</b> by <b>%s</b>.") % (
                self.display_sequence, self.env.user.name),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )










class PackingCostLine(models.Model):
    _name = 'packing.cost.line'
    _description = 'Packing Cost Line'

    sheet_id = fields.Many2one(
        'packing.cost.sheet',
        ondelete='cascade'
    )

    is_template = fields.Boolean(
        string="Template Line",
        default=False
    )

    section = fields.Selection([
        ('base', 'Base'),
        ('long_side', 'Long Side'),
        ('short_side', 'Short Side'),
        ('top_side', 'Top Side'),
        ('loose_ply_sheet', 'Loose Ply Sheet'),
        ('loose_pine_support', 'Loose Pine Support'),
        ('consumables', 'Consumables')
    ], string="Section")

    description = fields.Many2one('description.master', string="Description")

    length = fields.Float("Length")
    width = fields.Float("Width")
    thickness = fields.Float("Thickness")
    qty = fields.Float("Qty")

    sqft = fields.Float("SQFT/CFT", compute="_compute_area",readonly=False, store=True,  digits=(16, 6))

    material_id = fields.Many2one('material.master', string="Material")
    rm_rate = fields.Float("RM Rate",  related="material_id.rm_rate",  store=True, readonly=False,  digits=(16, 6))
    amount = fields.Float("Amount", compute="_compute_amount", readonly=False, store=True,  digits=(16, 6))

    # CH BOX FIELDS
    sr_no = fields.Integer("Sr.No")
    box_type = fields.Char("Box Type")

    height = fields.Float("Height")
    no_of_ply = fields.Integer("No.Of Ply")
    board_gsm = fields.Float("Board GSM")

    deckle = fields.Float("Deckle")
    cl = fields.Float("CL")

    weight_kg = fields.Float("Weight/KG")
    sqm = fields.Float("SQM")

    box_rate = fields.Float("Box Rate", compute="_compute_box_rate", store=True,  digits=(16, 6))

    def _normalize_material_name(self, name):
        if not name:
            return ''
        return re.sub(r'[^a-z0-9]', '', name.lower())

    @api.depends('length', 'width', 'thickness', 'qty', 'material_id')
    def _compute_area(self):
        for line in self:
            line.sqft = 0.0
            material = line.material_id

            if not line.material_id:
                continue
            if not line.length or not line.width:
                continue
            if not line.qty or line.qty <= 0:
                continue

            mat_name = self._normalize_material_name(line.material_id.name)

            if 'pinewood' in mat_name:
                if not line.thickness:
                    continue
                line.sqft = (
                    (line.length * line.width * line.thickness)
                    / (305 * 305 * 305) * (line.qty / 0.95))

            elif 'plywood' in mat_name:
                line.sqft = (
                    (line.length / 1000) * (line.width / 1000) * line.qty / 0.95 * 10.764)

            elif any(k in mat_name for k in ['hdpe', 'vci', 'micron', 'meter']):
                if not line.thickness:
                    continue
                line.sqft = (
                    (
                        (2 * line.length * line.width)
                        + (2 * line.length * line.thickness)
                        + (2 * line.width * line.thickness)
                    )
                    * line.qty
                )

    @api.depends('sqft', 'rm_rate')
    def _compute_amount(self):
        for line in self:
            line.amount = line.sqft * line.rm_rate

    def is_empty_line(self):
        self.ensure_one()
        return (
            not self.length and
            not self.width and
            not self.thickness and
            not self.qty and
            not self.rm_rate and
            not self.sqft and
            not self.amount
        )

    @api.depends('sqm', 'rm_rate')
    def _compute_box_rate(self):
        for rec in self:
            rec.box_rate = rec.sqm * rec.rm_rate




class MaterialMaster(models.Model):
    _name = 'material.master'
    _description = 'Material Master'
    _rec_name = 'name'

    name = fields.Char(
        string="Material Name",
        required=True
    )

    rm_rate = fields.Float(string="RM rate")

class DescriptionlMaster(models.Model):
    _name = 'description.master'
    _description = 'Description Master'
    _rec_name = 'name'

    name = fields.Char(
        string="Description Name",
        required=True
    )
    section = fields.Selection([
        ('base', 'Base'),
        ('long_side', 'Long Side'),
        ('short_side', 'Short Side'),
        ('top_side', 'Top Side'),
        ('loose_ply_sheet', 'Loose Ply Sheet'),
        ('loose_pine_support', 'Loose Pine Support'),
        ('consumables', 'Consumables')
    ], string="Section")

    material_id = fields.Many2one(
        'material.master',
        string="Material"
    )


class PackingCostRevisionWizard(models.TransientModel):
    _name = 'packing.cost.revision.wizard'
    _description = 'Request BOM Revision'

    sheet_id = fields.Many2one('packing.cost.sheet', string="BOM", required=True, readonly=True)
    remark = fields.Text(string="Revision Remarks", required=True)
    attachment = fields.Binary(string="Attachment")

    def action_confirm_revision(self):
        self.ensure_one()
        sheet = self.sheet_id

        # Mark previous pending history as resolved before adding new one
        sheet.revision_history_ids.filtered(
            lambda r: r.status == 'pending'
        ).write({'status': 'resolved'})

        # Create new history record
        self.env['packing.cost.revision.history'].create({
            'sheet_id': sheet.id,
            'requested_by': self.env.uid,
            'remark': self.remark,
            'attachment': self.attachment,
            'revision_no': sheet.revision_no,
            'status': 'pending',
        })

        sheet.write({
            'state': 'revision',
            'qc_remark': self.remark,
            'qc_attachment': self.attachment,

        })
        sheet.message_post(
            body=_("Revision Requested by <b>%s</b>.<br/><b>Remarks:</b> %s") % (
                self.env.user.name, self.remark),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        return {'type': 'ir.actions.act_window_close'}


class PackingCostRevisionHistory(models.Model):
    _name = 'packing.cost.revision.history'
    _description = 'BOM Revision History'
    _order = 'date desc'

    sheet_id = fields.Many2one(
        'packing.cost.sheet',
        string="BOM",
        required=True,
        ondelete='cascade'
    )
    date = fields.Datetime(
        string="Requested On",
        default=fields.Datetime.now,
        readonly=True
    )
    requested_by = fields.Many2one(
        'res.users',
        string="Requested By",
        readonly=True
    )
    remark = fields.Text(
        string="QC Remarks",
        readonly=True
    )
    attachment = fields.Binary(string="QC attachment", readonly=True)
    revision_no = fields.Integer(
        string="At Revision No",
        readonly=True
    )
    status = fields.Selection([
        ('pending',   'Pending'),
        ('resolved',  'Resolved'),
    ], string="Status", default='pending', readonly=True)