# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PackingCost(models.Model):
    _name = 'pallet.cost.sheet'
    _description = 'Packing Cost Calculator'
    _order = 'create_date desc'



    active = fields.Boolean(default=True)
    part_name = fields.Char(string='Part name')
    
    # Part Information
    # part_name = fields.Char(string='Part Name')
    box_id_l = fields.Float(string='Length')
    box_id_w = fields.Float(string='Width')
    box_id_h = fields.Float(string='Height')

    box_od_l = fields.Float(string='Length', compute="_compute_box_od_l")
    box_od_w = fields.Float(string='Width', compute="_compute_box_od_w")
    box_od_h = fields.Float(string='Height', compute="_compute_box_od_h")

    part_weight = fields.Float(string='Part Weight (KGS)', default=3000)
    moq = fields.Float(string='MOQ', default=0.0)
    empty_pallet_weight = fields.Float(string='Empty Pallet Weight in KG',compute="_compute_empty_pallet_weight", default=0.0)
   

    uom_id = fields.Many2one(
        'uom.uom',
        string="Unit of Measure",
        required=True
    )


    line_ids = fields.One2many(
        'cost.breakup.line',
        'breakup_id',
        string='Cost Details'
    )


    total_sq_inch = fields.Float(
        string='Total Sq Inch',
      
        store=True
    )

    wastage_percent = fields.Float(
        string='Wastage %',
        default=4.0
    )

    total_sq_inch_with_wastage = fields.Float(
        string='Sq Inch (With Wastage)',
        
        store=True
    )

    cft = fields.Float(
        string='CFT',
       
        store=True
    )

    total_cost = fields.Float(
        string='Total Cost',
       
        store=True
    )




    # # Base Section
    # base_plywood_length = fields.Float(string='Length')
    # base_plywood_width = fields.Float(string='Width')
    # base_plywood_thickness = fields.Float(string='Thickness')
    # base_plywood_qty = fields.Float(string='Qty')
    # base_plywood_sqft = fields.Float(string='SQFT/CFT')
    # base_plywood_rm_rate = fields.Float(string='RM Rate')
    # base_plywood_amount = fields.Float(string='Amount', compute='_compute_base_plywood_amount', store=True)
    
    # length_runner_length = fields.Float(string='Length')
    # length_runner_width = fields.Float(string='Width')
    # length_runner_thickness = fields.Float(string='Thickness')
    # length_runner_qty = fields.Float(string='Qty')
    # length_runner_sqft = fields.Float(string='SQFT/CFT')
    # length_runner_rm_rate = fields.Float(string='RM Rate')
    # length_runner_amount = fields.Float(string='Amount', compute='_compute_length_runner_amount', store=True)
    
    # width_runner_length = fields.Float(string='Length')
    # width_runner_width = fields.Float(string='Width')
    # width_runner_thickness = fields.Float(string='Thickness')
    # width_runner_qty = fields.Float(string='Qty')
    # width_runner_sqft = fields.Float(string='SQFT/CFT')
    # width_runner_rm_rate = fields.Float(string='RM Rate')
    # width_runner_amount = fields.Float(string='Amount', compute='_compute_width_runner_amount', store=True)
    
    # # Loose Pine Support
    # pine_supp_length = fields.Float(string='Length')
    # pine_supp_width = fields.Float(string='Width')
    # pine_supp_thickness = fields.Float(string='Thickness')
    # pine_supp_qty = fields.Float(string='Qty')
    # pine_supp_sqft = fields.Float(string='SQFT/CFT')
    # pine_supp_rm_rate = fields.Float(string='RM Rate')
    # pine_supp_amount = fields.Float(string='Amount', compute='_compute_pine_supp_amount', store=True)
    
    # # Consumables
    # lag_screw_rm_rate = fields.Float(string='RM Rate')
    # lag_screw_amount = fields.Float(string='Amount', default=0.0)
    
    # nut_bolt_rm_rate = fields.Float(string='RM Rate')
    # nut_bolt_amount = fields.Float(string='Amount', default=0.0)
    
    # d_clamp_rm_rate = fields.Float(string='RM Rate')
    # d_clamp_amount = fields.Float(string='Amount', default=0.0)
    
    # hdpe_rm_rate = fields.Float(string='RM Rate')
    # hdpe_amount = fields.Float(string='Amount', default=0.0)
    
    # vci_rm_rate = fields.Float(string='RM Rate')
    # vci_amount = fields.Float(string='Amount', default=0.0)
    
    # aluminium_foil_rm_rate = fields.Float(string='RM Rate')
    # aluminium_foil_amount = fields.Float(string='Amount', default=0.0)
    
    # silpaulin_bag_rm_rate = fields.Float(string='RM Rate')
    # silpaulin_bag_amount = fields.Float(string='Amount', default=0.0)
    
    # hdpe_bag_rm_rate = fields.Float(string='RM Rate')
    # hdpe_bag_amount = fields.Float(string='Amount', default=0.0)
    
    # desicant_rm_rate = fields.Float(string='RM Rate')
    # desicant_amount = fields.Float(string='Amount', default=0.0)
    
    # foam_6mm_rm_rate = fields.Float(string='RM Rate')
    # foam_6mm_amount = fields.Float(string='Amount', default=0.0)
    
    # bubble_roll_rm_rate = fields.Float(string='RM Rate')
    # bubble_roll_amount = fields.Float(string='Amount', default=0.0)
    
    # lashing_belt_rm_rate = fields.Float(string='RM Rate')
    # lashing_belt_amount = fields.Float(string='Amount', default=0.0)
    
    # buckles_rm_rate = fields.Float(string='RM Rate')
    # buckles_amount = fields.Float(string='Amount', default=0.0)
    
    # stretch_wrap_rm_rate = fields.Float(string='RM Rate')
    # stretch_wrap_amount = fields.Float(string='Amount', default=0.0)
    
    # Totals
    total_cft = fields.Float(string='Total CFT', default=0.0)
    total_sqft = fields.Float(string='Total SQFT', default=0.0)
    # total_material = fields.Float(string='Total', compute='_compute_total_material', store=True)
    
    mfg_percentage = fields.Float(string='Mfg %', default=5.0)
    mfg_amount = fields.Float(string='Mfg Amount', compute='_compute_mfg_amount', store=True)
    
    overhead_percentage = fields.Float(string='Overhead %', default=5.0)
    overhead_amount = fields.Float(string='Overhead Amount', compute='_compute_overhead_amount', store=True)
    
    profit_percentage = fields.Float(string='Profit %', default=30.0)
    profit_amount = fields.Float(string='Profit Amount', compute='_compute_profit_amount', store=True)
    
    packing_charges = fields.Float(string='Packing Charges', default=0.0)
    freight = fields.Float(string='Freight', default=0.0)
    
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('pallet.cost.sheet') or 'New'
        return super(PackingCost, self).create(vals)
    

    @api.depends('box_id_l')
    def _compute_box_od_l(self):
        for record in self:
            record.box_od_l = record.box_id_l

    @api.depends('box_id_w')
    def _compute_box_od_w(self):
        for record in self:
            record.box_od_w = record.box_id_w

    @api.depends('box_id_h')
    def _compute_box_od_h(self):
        for record in self:
            record.box_od_h = record.box_id_h 

    @api.depends('total_cft','total_sqft')
    def _compute_empty_pallet_weight(self):
        for record in self:
            record.empty_pallet_weight = (((record.total_cft*17)+(record.total_sqft*0.6))+20)


    # @api.depends('base_plywood_qty', 'base_plywood_sqft', 'base_plywood_rm_rate')
    # def _compute_base_plywood_amount(self):
    #     for record in self:
    #         record.base_plywood_amount = record.base_plywood_qty * record.base_plywood_sqft * record.base_plywood_rm_rate

    # @api.depends('length_runner_qty', 'length_runner_sqft', 'length_runner_rm_rate')
    # def _compute_length_runner_amount(self):
    #     for record in self:
    #         record.length_runner_amount = record.length_runner_qty * record.length_runner_sqft * record.length_runner_rm_rate

    # @api.depends('width_runner_qty', 'width_runner_sqft', 'width_runner_rm_rate')
    # def _compute_width_runner_amount(self):
    #     for record in self:
    #         record.width_runner_amount = record.width_runner_qty * record.width_runner_sqft * record.width_runner_rm_rate

    # @api.depends('pine_supp_qty', 'pine_supp_sqft', 'pine_supp_rm_rate')
    # def _compute_pine_supp_amount(self):
    #     for record in self:
    #         record.pine_supp_amount = record.pine_supp_qty * record.pine_supp_sqft * record.pine_supp_rm_rate

    # @api.depends('base_plywood_amount', 'length_runner_amount', 'width_runner_amount', 'pine_supp_amount',
    #              'lag_screw_amount', 'nut_bolt_amount', 'd_clamp_amount', 'hdpe_amount', 'vci_amount',
    #              'aluminium_foil_amount', 'silpaulin_bag_amount', 'hdpe_bag_amount', 'desicant_amount',
    #              'foam_6mm_amount', 'bubble_roll_amount', 'lashing_belt_amount', 'buckles_amount', 'stretch_wrap_amount')
    # def _compute_total_material(self):
    #     for record in self:
    #         record.total_material = (
    #             record.base_plywood_amount + 
    #             record.length_runner_amount + 
    #             record.width_runner_amount + 
    #             record.pine_supp_amount +
    #             record.lag_screw_amount + 
    #             record.nut_bolt_amount + 
    #             record.d_clamp_amount + 
    #             record.hdpe_amount + 
    #             record.vci_amount +
    #             record.aluminium_foil_amount + 
    #             record.silpaulin_bag_amount + 
    #             record.hdpe_bag_amount + 
    #             record.desicant_amount +
    #             record.foam_6mm_amount + 
    #             record.bubble_roll_amount + 
    #             record.lashing_belt_amount + 
    #             record.buckles_amount + 
    #             record.stretch_wrap_amount
    #         )

    @api.depends('mfg_percentage')
    def _compute_mfg_amount(self):
        for record in self:
            record.mfg_amount = record.total_material * (record.mfg_percentage / 100.0)

    @api.depends('mfg_amount', 'overhead_percentage')
    def _compute_overhead_amount(self):
        for record in self:
            base = record.total_material + record.mfg_amount
            record.overhead_amount = base * (record.overhead_percentage / 100.0)

    @api.depends('mfg_amount', 'overhead_amount', 'profit_percentage')
    def _compute_profit_amount(self):
        for record in self:
            base = record.total_material + record.mfg_amount + record.overhead_amount
            record.profit_amount = base * (record.profit_percentage / 100.0)

    @api.depends('mfg_amount', 'overhead_amount', 'profit_amount', 'packing_charges', 'freight')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = (
                record.total_material + 
                record.mfg_amount + 
                record.overhead_amount + 
                record.profit_amount + 
                record.packing_charges + 
                record.freight
            )





class CostBreakupLine(models.Model):
    _name = 'cost.breakup.line'
    _description = 'Cost Break Up Line'





    active = fields.Boolean(default=True)
    breakup_id = fields.Many2one(
    'pallet.cost.sheet',
    string='Cost Sheet',
    required=True,
    ondelete='cascade'
)
    section = fields.Selection([
        ('base', 'Base'),
        ('top', 'Top'),
        ('long', 'Long Side'),
        ('short', 'Short Side')
    ], string='Section', required=True)

    description = fields.Char(string='Details')

    length = fields.Float(string='L')
    width = fields.Float(string='W')
    height = fields.Float(string='H')
    thickness = fields.Float(string='T')

    qty = fields.Integer(string='Qty')
    uom_id = fields.Many2one(
        'uom.uom',
        string="Unit of Measure",
        required=True
    )

    sq_inch = fields.Float(
        string='Sq Inch',
        compute='_compute_sq_inch',
        store=True
    )

    rate = fields.Float(string='Rate')

    sq_ft = fields.Float(
        string='Sq Ft',
        compute='_compute_sq_ft',
        store=True
    )

    cost = fields.Float(
        string='Cost',
        compute='_compute_cost',
        store=True
    )


    @api.depends('length', 'width', 'qty')
    def _compute_sq_inch(self):
        for rec in self:
            rec.sq_inch = (rec.length or 0.0) * (rec.width or 0.0) * (rec.qty or 0)

 
    # Sq.ft conversion
    @api.depends('sq_inch')
    def _compute_sq_ft(self):
        for rec in self:
            rec.sq_ft = rec.sq_inch / 144 if rec.sq_inch else 0.0
