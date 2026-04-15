from odoo import models, fields, api

# ==================================================
# MAIN MODEL
# ==================================================
class CostBreakup(models.Model):
    _name = 'cost.breakup'
    _description = 'Cost Break Up'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, tracking=True)
    case_type = fields.Char(string='Type', default='Rubber Wood Case')
    product_weight = fields.Float(string='Product Weight (KG)')
    box_type = fields.Char(string='Box Type', default='Case 1')
    line_ids = fields.One2many(
        'cost.breakup.line',
        'breakup_id',
        string='Cost Details'
    )
    # =======================
    # INCH (USER INPUT)
    # =======================
    size_l = fields.Float(string='L (Inch)')
    size_w = fields.Float(string='W (Inch)')
    size_h = fields.Float(string='H (Inch)')
    thickness = fields.Float(string='T (Inch)')

    # =======================
    # OD (AUTO)
    # =======================
    size_l_od = fields.Float(string='L (OD)', compute='_compute_od', store=True)
    size_w_od = fields.Float(string='W (OD)', compute='_compute_od', store=True)
    size_h_od = fields.Float(string='H (OD)', compute='_compute_od', store=True)
    size_t_od = fields.Float(string='T (OD)', compute='_compute_od', store=True)

    # =======================
    # MM (AUTO)
    # =======================
    size_l_mm = fields.Float(string='L (MM)', compute='_compute_mm', store=True)
    size_w_mm = fields.Float(string='W (MM)', compute='_compute_mm', store=True)
    size_h_mm = fields.Float(string='H (MM)', compute='_compute_mm', store=True)
    size_t_mm = fields.Float(string='T (MM)', compute='_compute_mm', store=True)




    # =======================
    # AREA & VOLUME
    # =======================
    total_sq_inch = fields.Float(
        string='Total Sq Inch',
        compute='_compute_total_sq_inch',
        store=True
    )

    wastage_percent = fields.Float(
        string='Wastage %',
        default=4.0
    )

    total_sq_inch_with_wastage = fields.Float(
        string='Sq Inch (With Wastage)',
        compute='_compute_wastage',
        store=True
    )

    cft = fields.Float(
        string='CFT',
        compute='_compute_cft',
        store=True
    )

    total_cost = fields.Float(
        string='Total Cost',
        compute='_compute_total_cost',
        store=True
    )


    rate=fields.Float(string='Rate')
    cost = fields.Float(string="Cost(Rs.)" ,compute="_compute_total_cost_rs", store=True)

 
    # OD = Inch + (2 × T)
 
    @api.depends('size_l', 'size_w', 'size_h', 'thickness')
    def _compute_od(self):
        for rec in self:
            t = rec.thickness or 0.0
            rec.size_l_od = (rec.size_l or 0.0) + (2 * t)
            rec.size_w_od = (rec.size_w or 0.0) + (2 * t)
            rec.size_h_od = (rec.size_h or 0.0) + (2 * t)
            rec.size_t_od = (rec.thickness or 0.0) + (2 * t)


 
    # MM = OD × 25.4
 
    @api.depends('size_l_od', 'size_w_od', 'size_h_od')
    def _compute_mm(self):
        for rec in self:
            rec.size_l_mm = rec.size_l_od * 25.4
            rec.size_w_mm = rec.size_w_od * 25.4
            rec.size_h_mm = rec.size_h_od * 25.4
            rec.size_t_mm = rec.size_t_od * 25.4


 
    # Total Sq Inch from lines
 
    @api.depends('line_ids.sq_inch')
    def _compute_total_sq_inch(self):
        for rec in self:
            rec.total_sq_inch = sum(rec.line_ids.mapped('sq_inch'))


 
    # Add wastage %
 
    @api.depends('total_sq_inch', 'wastage_percent')
    def _compute_wastage(self):
        for rec in self:
            rec.total_sq_inch_with_wastage = (
                rec.total_sq_inch * (1 + (rec.wastage_percent / 100))
            )


 
    # Convert to CFT
    # 1 CFT = 1728 sq.inch
 
    @api.depends('total_sq_inch_with_wastage')
    def _compute_cft(self):
        for rec in self:
            rec.cft = rec.total_sq_inch_with_wastage / 1728 if rec.total_sq_inch_with_wastage else 0.0


 
    # Total Cost
 
    @api.depends('line_ids.cost')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = sum(rec.line_ids.mapped('cost'))

    @api.depends('cft','rate')
    def _compute_total_cost_rs(self):
        for rec in self:
            rec.cost = rec.cft * rec.rate




# ==================================================
# LINE MODEL
# ==================================================
class CostBreakupLine(models.Model):
    _name = 'cost.breakup.line'
    _description = 'Cost Break Up Line'

    breakup_id = fields.Many2one('cost.breakup', ondelete='cascade')

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

    sq_inch = fields.Float(
        string='Sq Inch',
        compute='_compute_sq_inch',
        store=True
    )

    calculation_type = fields.Selection([
    ('cft', 'CFT Based'),
    ('qty', 'Quantity Based'),
    ('sqft', 'Sq.Ft Based'),
    ('flat', 'Flat Rate')
], string='Calculation Type', required=True)

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


 
    # Cost calculation
    @api.depends('calculation_type','rate','qty','sq_ft','breakup_id.cft')
    def _compute_cost(self):
        for rec in self:
            if rec.calculation_type == 'cft':
                rec.cost = rec.breakup_id.cft * rec.rate

            elif rec.calculation_type == 'qty':
                rec.cost = rec.qty * rec.rate

            elif rec.calculation_type == 'sqft':
                rec.cost = rec.sq_ft * rec.rate

            elif rec.calculation_type == 'flat':
                rec.cost = rec.rate

            else:
                rec.cost = 0.0

