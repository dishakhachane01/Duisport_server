from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class DwQualityCheck(models.Model):
    _name = 'dw.quality.check'
    _description = 'Quality Check'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # name = fields.Char(string='QC Reference', required=True, copy=False, default='New')
    name = fields.Char( string='QC Reference', required=True, copy=False, readonly=True, default='New', index=True, tracking=True,)
    picking_id = fields.Many2one('stock.picking', string='Picking', ondelete='cascade', index=True)
    mrp_id = fields.Many2one('mrp.production', string="Manufacturing Order")
    product_id = fields.Many2one('product.product', string='Product')
    lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial')
    quantity = fields.Float(string='Quantity')
    passed = fields.Boolean(string='Passed')
    remarks = fields.Text(string='Remarks')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    inspected_by = fields.Many2one('res.users', string='Inspected By')
    approved_by = fields.Many2one('res.users', string='Approved By')

    source_reference = fields.Char(string='Source Reference', compute='_compute_source_reference', store=True, readonly=True)
    status = fields.Selection([('pending', 'Pending'), ('passed', 'Passed'), ('failed', 'Failed')], string='QC Result', default='pending', tracking=True)
    qc_status = fields.Selection([('received', 'Received for QC'), ('returned', 'Returned'), ('done', 'QC Done')], string="QC Process Status", default='received', tracking=True)

    # New fields for reports
    inspection_type = fields.Selection([
        ('wood_pallet', 'Wood Pallet'),
        ('corrugation', 'Corrugation'),
        ('pallet', 'Pallet'),
        ('screw', 'Screw/Nail'),
        ('metal', 'Metal'),
        ('angle_board', 'Angle Board'),
        ('polybag', 'Polybag'),
        ('pinewood', 'Pinewood'),
    ], string='Inspection Type', required=True)
    supplier_code = fields.Char(string='Supplier Code')
    material_name = fields.Char(string='Material Type/Name')
    customer_code = fields.Char(string='Customer Code/Model')
    invoice_no = fields.Char(string='Invoice No.')
    invoice_date = fields.Date(string='Invoice Date')
    invoice_qty = fields.Float(string='Invoice Qty')
    sample_qty = fields.Float(string='Sample Qty')
    qty_accepted = fields.Float(string='Qty Accepted')
    qty_hold = fields.Float(string='Qty Hold/Reworked')
    qty_rejected = fields.Float(string='Qty Rejected')
    qty_deviated = fields.Float(string='Qty Deviated')
    deviation_approved_by = fields.Char(string='Deviation Approved By (Name/Sign)')
    reason_non_conformity = fields.Text(string='Reason of Non-Conformity')
    corrective_action = fields.Text(string='Corrective/Preventive Action')
    verification_action = fields.Text(string='Verification of Corrective/Preventive Action')
    verified_by = fields.Many2one('res.users', string='Verified By (Name/Sign)')
    verified_date = fields.Date(string='Verified Date')

    inspection_lines = fields.One2many('dw.inspection.line', 'check_id', string='Inspection Lines')
    lab_lines = fields.One2many('dw.inspection.lab.line', 'check_id', string='Lab Lines')

    # Add this dummy field to trigger recompute on form load
    # _force_lines = fields.Boolean(compute='_compute_inspection_lines_force', store=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        inspection_type = self.env.context.get('default_inspection_type')

        if not inspection_type:
            return res

        params = self._get_predefined_parameters()
        type_params = params.get(inspection_type)

        if not type_params:
            return res

        inspection_lines = []
        lab_lines = []

        # Inspection Lines
        for i, p in enumerate(type_params.get('inspection', []), 1):
            inspection_lines.append((0, 0, {
                'sequence': i,
                'parameter': p['parameter'],
                'specification': p['specification'],
                'measurement_method': p.get('method'),
            }))

        # Lab Lines
        for i, p in enumerate(type_params.get('lab', []), 1):
            lab_lines.append((0, 0, {
                'sequence': i,
                'parameter': p['parameter'],
                'specification': p['specification'],
            }))

        res['inspection_lines'] = inspection_lines
        res['lab_lines'] = lab_lines

        return res


    @api.onchange('inspection_type')
    def _onchange_inspection_type(self):

        if not self.inspection_type:
            return

        # Clear existing
        self.inspection_lines = [(5, 0, 0)]
        self.lab_lines = [(5, 0, 0)]

        params = self._get_predefined_parameters()
        type_params = params.get(self.inspection_type)

        if not type_params:
            return

        inspection_vals = []
        lab_vals = []

        # Inspection
        for i, p in enumerate(type_params.get('inspection', []), 1):
            inspection_vals.append((0, 0, {
                'sequence': i,
                'parameter': p['parameter'],
                'specification': p['specification'],
                'measurement_method': p.get('method'),
            }))

        # Lab
        for i, p in enumerate(type_params.get('lab', []), 1):
            lab_vals.append((0, 0, {
                'sequence': i,
                'parameter': p['parameter'],
                'specification': p['specification'],
            }))

        self.inspection_lines = inspection_vals
        self.lab_lines = lab_vals

    


    def _pull_from_source(self):
        """Pull data from PO/MO"""
        for rec in self:
            if rec.picking_id:
                rec.supplier_code = rec.picking_id.partner_id.ref or rec.picking_id.partner_id.name
                purchase = rec.picking_id.purchase_id
                if purchase:
                    rec.invoice_no = purchase.partner_ref
                    rec.invoice_date = purchase.date_order.date()
                    rec.invoice_qty = sum(purchase.order_line.mapped('product_qty'))
            if rec.product_id:
                rec.material_name = rec.product_id.name
                # Auto-set type based on product category if defined (customize as needed)
                # e.g., if rec.product_id.categ_id.name == 'Wood': rec.inspection_type = 'wood_pallet'

    # def _populate_inspection_lines(self):
    #     """Auto-create lines based on type from templates"""
    #     self.inspection_lines.unlink()
    #     self.lab_lines.unlink()
    #     params = self._get_predefined_parameters()
    #     for idx, param in enumerate(params.get(self.inspection_type, {}).get('inspection', []), 1):
    #         self.inspection_lines.create({
    #             'check_id': self.id,
    #             'sequence': idx,
    #             'parameter': param['parameter'],
    #             'specification': param['specification'],
    #             'measurement_method': param.get('method', False),
    #         })
    #     for idx, param in enumerate(params.get(self.inspection_type, {}).get('lab', []), 1):
    #         self.lab_lines.create({
    #             'check_id': self.id,
    #             'sequence': idx,
    #             'parameter': param['parameter'],
    #             'specification': param['specification'],
    #         })

    def _get_predefined_parameters(self):
        """Dict of parameters from your attachments"""
        return {
            'wood_pallet': {
                'inspection': [
                    {'parameter': 'Type of wood', 'specification': 'Plywood / HardWood / Pine Wood'},
                    {'parameter': 'Type of face (For Plywood)', 'specification': 'Single Face/Double Face'},
                    {'parameter': 'Colour of Top Surface (For Plywood)', 'specification': 'Red /Plain Milky/Makai'},
                    {'parameter': 'Length', 'specification': '± 5 mm'},
                    {'parameter': 'Width', 'specification': '± 5 mm'},
                    {'parameter': 'Thickness', 'specification': '± mm'},
                    {'parameter': 'Dia of Holes (If Any)', 'specification': '± mm'},
                    {'parameter': 'Position of Holes (If any)', 'specification': 'As per Drawing'},
                    {'parameter': 'Weight of 01 Piece (For Plywood Only)', 'specification': '± 5% in Kg'},
                    {'parameter': 'Heat Treatment (Not Applicable for Plywood)', 'specification': 'Yes / No'},
                    {'parameter': 'Visual (Crack,Knot,Delamination,Over Nails,Burr etc.)', 'specification': 'Should be ok'},
                    {'parameter': 'Moisture Content', 'specification': 'Hardwood/Pinewood :08-20% Plywood : 3-10%'},
                ],
                'lab': [],  # No lab for this
            },
            'corrugation': {
                'inspection': [
                    {'parameter': 'No. of ply', 'specification': '3Ply/5Ply/7Ply'},
                    {'parameter': 'Flute Profile', 'specification': 'A/B/C/E/AA/AC/BC/AAA Other...'},
                    {'parameter': 'Paper Specification (Test Individual paper specs in case of low GSM of board only)', 'specification': ''},
                    {'parameter': 'Length', 'specification': '+1 mm'},
                    {'parameter': 'Width', 'specification': '+1 mm'},
                    {'parameter': 'Height', 'specification': '+1 mm'},
                    {'parameter': 'Thickness of Sheet', 'specification': '±1.0-0.5 mm'},
                    {'parameter': 'Printing Matter', 'specification': 'As per artwork / drawing'},
                    {'parameter': 'Visual (Bending,Crack,Tear,Delamination oil mark etc)', 'specification': 'Should be ok'},
                    {'parameter': 'Others', 'specification': 'Should be ok'},
                ],
                'lab': [
                    {'parameter': 'GSM', 'specification': 'Min (...... ) G/m²'},
                    {'parameter': 'Bursting Strength', 'specification': 'Min (...... ) Kg/cm²'},
                    {'parameter': 'ECT', 'specification': 'Min (...... ) Kn/m'},
                    {'parameter': 'Moisture (At Incoming stage)', 'specification': '8-12%'},
                ],
            },
            'pallet': {
                'inspection': [
                    {'parameter': 'Type of wood', 'specification': 'Plywood / HardWood / Pine Wood'},
                    {'parameter': 'Type of Pallet Top', 'specification': 'Plank / Full Deck/Full Cover With Plank'},
                    {'parameter': 'Gap / No. of Plank on Top', 'specification': 'As per Drawing'},
                    {'parameter': 'Pallet Orientation', 'specification': 'As per Drawing'},
                    {'parameter': 'Type of Pallet', 'specification': '2 Way / 4 Way'},
                    {'parameter': 'Pallet Length', 'specification': '± 5 mm'},
                    {'parameter': 'Pallet Width', 'specification': '± 5 mm'},
                    {'parameter': 'Pallet Height', 'specification': '± mm'},
                    {'parameter': 'Holes', 'specification': '± mm'},
                    {'parameter': 'Position of Holes', 'specification': 'As per Drawing'},
                    {'parameter': 'Plank /Material Thickness Top / Mid / Bottom', 'specification': '/ / ±2 mm'},
                    {'parameter': 'Runner/Block Size (LXWXH)', 'specification': 'X X mm'},
                    {'parameter': 'Heat Treatment', 'specification': 'Yes / No'},
                    {'parameter': 'Visual (Crack,Knot,Delamination,Over Nails,Burr etc.)', 'specification': 'Should be ok'},
                    {'parameter': 'Moisture Content', 'specification': 'Hardwood/Pinewood :12-20% Plywood : 5-15%'},
                ],
                'lab': [],
            },
            'screw': {
                'inspection': [
                    {'parameter': 'Diameter', 'specification': '± 0.1 mm', 'method': 'Vernier Caliper'},
                    {'parameter': 'Length', 'specification': '± 0.2 mm', 'method': 'Vernier Caliper'},
                    {'parameter': 'Thread Pitch', 'specification': '', 'method': 'Thread Gauge'},
                    {'parameter': 'Head Type & Size', 'specification': '', 'method': 'Visual & Caliper'},
                    {'parameter': 'Material Grade', 'specification': '', 'method': 'Certificate / Test'},
                    {'parameter': 'Defects (Rust, Burrs)', 'specification': 'No visual defects allowed', 'method': 'Visual'},
                    {'parameter': 'Thread Quality', 'specification': 'Clean, no damage', 'method': 'Visual'},
                ],
                'lab': [],
            },
            'metal': {
                'inspection': [
                    {'parameter': 'Material Type', 'specification': 'As per drawing/spec'},
                    {'parameter': 'Dimensions (L×W×H)', 'specification': ''},
                    {'parameter': 'Thickness', 'specification': '± 0.2 mm'},
                    {'parameter': 'Weld Quality', 'specification': 'No cracks/Porosity'},
                    {'parameter': 'Surface Finish', 'specification': 'Smooth, No Rust/Burr'},
                    {'parameter': 'Coating/Painting', 'specification': 'As per spec (if any)'},
                    {'parameter': 'Hole Diameter/Slot Position', 'specification': 'As per drawing'},
                    {'parameter': 'Overall Fitment', 'specification': 'As per assembly fit'},
                    {'parameter': 'Visual Inspection', 'specification': 'No dents, deformation'},
                    {'parameter': 'Quantity Checked', 'specification': 'Yes / No'},
                ],
                'lab': [],
            },
            'angle_board': {
                'inspection': [
                    {'parameter': 'Corner Width 01', 'specification': '± 5 mm'},
                    {'parameter': 'Corner Width 02', 'specification': '± 5 mm'},
                    {'parameter': 'Thickness', 'specification': '± 1 mm'},
                    {'parameter': 'Length', 'specification': '± 5 mm'},
                    {'parameter': 'Visual (Delamination,Crack,Tear, Bending,Oil mark etc)', 'specification': 'Should be ok'},
                    {'parameter': 'Others', 'specification': 'Should be ok'},
                ],
                'lab': [
                    {'parameter': 'ECT', 'specification': 'MIN (± 1) Kn/m'},
                    {'parameter': 'Moisture', 'specification': '8-12 %'},
                ],
            },
            'polybag': {
                'inspection': [
                    {'parameter': 'Type of Polybag', 'specification': 'Bubble / Plain / VCI'},
                    {'parameter': 'Length', 'specification': '(+/-) mm'},
                    {'parameter': 'Width', 'specification': '(+/-) mm'},
                    {'parameter': 'Height', 'specification': '(+/-) mm'},
                    {'parameter': 'Colour', 'specification': ''},
                    {'parameter': 'Thickness', 'specification': '(+/- 10%) mic'},
                    {'parameter': 'Weight of one piece', 'specification': '(+/- 10%) gm'},
                    {'parameter': 'Visual (Dust,Oil mark,Tear,Pasting etc)', 'specification': 'Should be ok'},
                    {'parameter': 'Other', 'specification': 'Should be ok'},
                ],
                'lab': [],
            },
            'pinewood': {
                'inspection': [
                    {'parameter': 'Type of wood', 'specification': 'HardWood / Pine Wood'},
                    {'parameter': 'Type of face (For Plywood)', 'specification': 'Single Face/Double Face'},
                    {'parameter': 'Colour of Top Surface (For Plywood)', 'specification': 'Plain Milky/Makai'},
                    {'parameter': 'Length', 'specification': '± 5 ft'},
                    {'parameter': 'Width', 'specification': '± 5 inch'},
                    {'parameter': 'Thickness', 'specification': '± inch'},
                    {'parameter': 'Dia of Holes (If Any)', 'specification': '± mm'},
                    {'parameter': 'Position of Holes (If any)', 'specification': 'As per Drawing'},
                    {'parameter': 'Weight of 01 Piece (For Plywood Only)', 'specification': '± 5% in Kg'},
                    {'parameter': 'Heat Treatment (Not Applicable for Plywood)', 'specification': 'Yes / No'},
                    {'parameter': 'Visual (Crack,Knot,Delamination,Over Nails,Burr etc.)', 'specification': 'Should be ok'},
                    {'parameter': 'Moisture Content', 'specification': 'Hardwood/Pinewood :08-20%'},
                ],
                'lab': [],
            },
        }


    @api.depends('mrp_id', 'picking_id')
    def _compute_source_reference(self):
        """Show source reference from MO or PO."""
        for rec in self:
            if rec.mrp_id:
                rec.source_reference = rec.mrp_id.origin or rec.mrp_id.name
            elif rec.picking_id:
                rec.source_reference = rec.picking_id.origin or rec.picking_id.name
            else:
                rec.source_reference = False


    # Updated action_qc_done (cleaned up, reusable time tracking)
    def action_qc_done(self):

        for rec in self:

            rec.write({
                'passed': True,     
                'status': 'passed',
                'qc_status': 'done',
                'inspected_by': self.env.user,   
            })

            rec.message_post(
                body=f"✅ QC Done by {self.env.user.name} → PASSED"
            )

            rec._update_time_tracking()
            rec._update_picking_qc_state()

        return True
        # return self.env.ref(
        #     'dw_quality_check.action_report_inspection'
        # ).report_action(self)




    def _update_time_tracking(self):

        for rec in self:

            target_model = False
            lead_id = False

            # ====================================
            # CASE 1: QC from MRP
            # ====================================
            if rec.mrp_id:

                mo = rec.mrp_id

                target_model = f"mrp.production,{mo.id}"

                sale_order = self.env['sale.order'].search([
                    ('name', '=', mo.origin)
                ], limit=1)

                if sale_order and sale_order.opportunity_id:
                    lead_id = sale_order.opportunity_id.id

            # ====================================
            # CASE 2: QC from Purchase
            # ====================================
            elif rec.picking_id:

                picking = rec.picking_id

                purchase_orders = picking.move_ids_without_package.mapped(
                    "purchase_line_id.order_id"
                )

                purchase_order = purchase_orders[:1]

                if purchase_order:

                    target_model = f"purchase.order,{purchase_order.id}"

                    sale_order = self.env['sale.order'].search([
                        ('name', '=', purchase_order.origin)
                    ], limit=1)

                    if sale_order and sale_order.opportunity_id:
                        lead_id = sale_order.opportunity_id.id

            # ====================================
            # SAFETY CHECK
            # ====================================
            if not target_model:
                return

            # ====================================
            # CLOSE IN-PROGRESS RECORD
            # ====================================
            last_track = self.env['department.time.tracking'].search([
                ('target_model', '=', target_model),
                ('status', '=', 'in_progress')
            ], limit=1, order='start_time desc')

            if last_track:
                last_track.write({
                    'end_time': fields.Datetime.now(),
                    'status': 'done'
                })

            # ====================================
            # CREATE QC DONE ENTRY
            # ====================================
            self.env['department.time.tracking'].create({
                'target_model': target_model,
                'stage_name': 'QC Done',
                'user_id': self.env.user.id,
                'employee_id': (
                    self.env.user.employee_id.id
                    if self.env.user.employee_id else False
                ),
                'start_time': fields.Datetime.now(),
                'end_time': fields.Datetime.now(),
                'status': 'done',
                'lead_id': lead_id,
            })

    
    def _update_picking_qc_state(self):

        for rec in self:

            if not rec.picking_id:
                continue

            picking = rec.picking_id

            # Example: mark picking as QC done
            picking.write({
                'qc_done': True
            })

            # Optional log
            rec.message_post(
                body=f"📦 Picking {picking.name} marked as QC Done"
            )

        
    
    
    
    
    
    
    





    # @api.model
    # def create(self, vals):
    #     rec = super().create(vals)

    #     # Refill lines after save (optional safety)
    #     if rec.inspection_type:
    #         rec._populate_inspection_lines()

    #     return rec

    def _create_default_lines(self):

        for rec in self:

            # Do NOT recreate
            if rec.inspection_lines or rec.lab_lines:
                continue

            if not rec.inspection_type:
                continue

            params = rec._get_predefined_parameters()
            type_params = params.get(rec.inspection_type)

            if not type_params:
                continue

            inspection_vals = []
            lab_vals = []

            # Inspection
            for i, p in enumerate(type_params.get('inspection', []), 1):
                inspection_vals.append({
                    'check_id': rec.id,
                    'sequence': i,
                    'parameter': p['parameter'],
                    'specification': p['specification'],
                    'measurement_method': p.get('method'),
                })

            # Lab
            for i, p in enumerate(type_params.get('lab', []), 1):
                lab_vals.append({
                    'check_id': rec.id,
                    'sequence': i,
                    'parameter': p['parameter'],
                    'specification': p['specification'],
                })

            self.env['dw.inspection.line'].create(inspection_vals)
            self.env['dw.inspection.lab.line'].create(lab_vals)


    @api.model
    def create(self, vals):
        # Generate sequence BEFORE super().create()
        if vals.get('name', 'New') == 'New':
            if vals.get('picking_id'):
                sequence_code = 'dw.quality.check.inward'
            elif vals.get('mrp_id'):
                sequence_code = 'dw.quality.check.outward'
            else:
                # fallback - manual creation or unknown context
                sequence_code = 'dw.quality.check.inward'

            vals['name'] = self.env['ir.sequence'].next_by_code(sequence_code) or 'New/ERR'

        # Now create the record
        record = super(DwQualityCheck, self).create(vals)

        # Your existing logic for lines
        if record.inspection_type:
            record._create_default_lines()

        return record

    

    @api.model
    def create(self, vals):

        rec = super().create(vals)

        if rec.inspection_type and not rec.inspection_lines:
            rec._create_default_lines()

        return rec

    # Other methods (action_return_file, action_set_passed, etc.) remain similar
    # ...

class DwInspectionLine(models.Model):
    _name = 'dw.inspection.line'
    _description = 'Inspection Line'

    check_id = fields.Many2one('dw.quality.check', required=True)
    sequence = fields.Integer(string='S.No')
    parameter = fields.Char(string='Inspection Parameters')
    specification = fields.Char(string='Std. Specification')
    measurement_method = fields.Char(string='Measurement Method')
    observation = fields.Char(string='Observations')

class DwInspectionLabLine(models.Model):
    _name = 'dw.inspection.lab.line'
    _description = 'Lab Inspection Line'

    check_id = fields.Many2one('dw.quality.check', required=True)
    sequence = fields.Integer(string='S.No')
    parameter = fields.Char(string='Parameter')
    specification = fields.Char(string='Std. Specification')
    observation = fields.Char(string='Observations')