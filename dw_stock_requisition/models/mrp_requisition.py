from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

# Add logger
_logger = logging.getLogger(__name__)

class MrpRequisition(models.Model):
    _name = 'dw.mrp.requisition'
    _description = 'Manufacturing Requisition Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    is_requested_other_location = fields.Boolean(
        string='Requested Other Location',
        default=False,
        tracking=True
    )

    is_submitted_to_purchase = fields.Boolean(
        string='Submitted to Purchase',
        default=False,
        tracking=True
    )

    name = fields.Char(
        string='Requisition Number',
        required=True,
        readonly=True,
        default=lambda self: _('New')
    )
    date = fields.Date(
        string='Requisition Date',
        default=fields.Date.today
    )
    department = fields.Selection([
        ('manufacturing', 'Manufacturing'),
        ('production', 'Production'),
        ('assembly', 'Assembly'),
        ('finishing', 'Finishing'),
        ('store', 'Store')
    ], string='Department', required=True, default='store')
    
    requested_by = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user
    )
    required_date = fields.Date(
        string='Required Date',
        required=True
    )
    
    manufacturing_order_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order',
        domain="[('state', 'in', ['confirmed', 'progress'])]"
    )
    
    requisition_line_ids = fields.One2many(
        'dw.mrp.requisition.line',
        'requisition_id',
        string='Items'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted to Store'),
        ('ready_for_transfer', 'Ready for Internal Transfer'),
        ('requested_other_location', 'Requested to Another Location'),
        ('submitted_to_purchase', 'Submitted to Purchase'),
    ], string='Status', default='draft')

    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    notes = fields.Text(string='Internal Notes')
    
    source_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        domain="[('usage', '=', 'internal')]",
        required=True,
        default=lambda self: self._get_default_source_location()
    )
    destination_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location', 
        domain="[('usage', '=', 'internal')]",
        required=True,
        default=lambda self: self._get_default_destination_location()
    )
    
    internal_transfer_id = fields.Many2one(
        'stock.picking',
        string='Internal Transfer',
        readonly=True
    )
    requested_location_id = fields.Many2one(
        'stock.location',
        string='Requested Location',
        domain="[('usage', '=', 'internal')]"
    )
    
    total_items = fields.Integer(
        string='Total Items',
        compute='_compute_total_items'
    )
    total_quantity = fields.Float(
        string='Total Quantity',
        compute='_compute_total_quantity'
    )
    
    @api.depends('requisition_line_ids')
    def _compute_total_items(self):
        for requisition in self:
            requisition.total_items = len(requisition.requisition_line_ids)
    
    @api.depends('requisition_line_ids.quantity')
    def _compute_total_quantity(self):
        for requisition in self:
            requisition.total_quantity = sum(line.quantity for line in requisition.requisition_line_ids)
    
    def _get_default_source_location(self):
        """Get default source location from stock settings"""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        return picking_type.default_location_src_id if picking_type else False
    
    def _get_default_destination_location(self):
        """Get default destination location from stock settings"""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        return picking_type.default_location_dest_id if picking_type else False
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('dw.mrp.requisition') or _('New')
        return super().create(vals)
    
    def _check_manufacturing_user_permission(self):
        """Check if current user is a manufacturing user and owns the requisition"""
        is_manufacturing_user = self.env.user.has_group('dw_stock_requisition.group_manufacturing_team')
        is_admin = self.env.user.has_group('base.group_erp_manager')  # Built-in admin group
        is_requester = self.requested_by == self.env.user
        return (is_manufacturing_user and is_requester) or is_admin
    
    def _check_inventory_user_permission(self):
        """Check if current user is an inventory user or admin"""
        is_inventory_user = self.env.user.has_group('dw_stock_requisition.group_inventory_team')
        is_admin = self.env.user.has_group('base.group_erp_manager')  # Built-in admin group
        return is_inventory_user or is_admin
    
    def action_submit_to_store(self):
        """Submit requisition to store - Only manufacturing users can submit their own drafts"""
        for requisition in self:
            # Debug
            _logger.info(f"Submitting requisition {requisition.name} from state: {requisition.state}")
            
            if requisition.state != 'draft':
                raise UserError(_("Only draft requisitions can be submitted. Current state: %s") % requisition.state)
            
            if not requisition._check_manufacturing_user_permission():
                raise UserError(_("You can only submit your own draft requisitions."))
            
            if not requisition.requisition_line_ids:
                raise UserError(_("Cannot submit requisition without any items."))
            
            if not requisition.source_location_id or not requisition.destination_location_id:
                raise UserError(_("Please set both source and destination locations."))
            
            
            requisition.state = 'submitted'
            _logger.info(f"Requisition {requisition.name} state changed to: {requisition.state}")
            
            
            requisition.message_post(
                body=_("Requisition submitted to store."),
                subject=_("Submitted to Store")
            )
        
        return True
        
    def action_ready_for_internal_transfer(self):
        """Create Internal Transfer - Only for submitted requisitions (not from requested location)"""
        for requisition in self:
            if requisition.state != 'submitted':
                raise UserError(_("Only submitted requisitions can be processed for transfer."))
            
            if not requisition._check_inventory_user_permission():
                raise UserError(_("Only inventory users can process requisitions."))
            
            if not requisition.requisition_line_ids:
                raise UserError(_("Cannot create transfer without any items."))
            
           
            source_location = requisition.source_location_id
            
            if not source_location:
                raise UserError(_("Please set source location."))
            
            if not requisition.destination_location_id:
                raise UserError(_("Please set destination location."))
            
            
            for line in requisition.requisition_line_ids:
                available_qty = line.product_id.with_context(
                    location=source_location.id
                ).qty_available
                
                if available_qty < line.quantity:
                    raise UserError(_(
                        "Product %s is not available in sufficient quantity at %s. Available: %s, Required: %s"
                    ) % (line.product_id.name, source_location.name, available_qty, line.quantity))
            
            
            picking_type = self._find_or_create_internal_picking_type(requisition.company_id)
            if not picking_type:
                raise UserError(_(
                    "No internal transfer operation type found. Please contact your administrator to set up Inventory operations."
                ))
            
            picking_vals = {
                'picking_type_id': picking_type.id,
                'location_id': source_location.id,
                'location_dest_id': requisition.destination_location_id.id,
                'origin': f"Requisition: {requisition.name}",
                'scheduled_date': requisition.required_date,
                'company_id': requisition.company_id.id,
                'move_type': 'direct',
                'priority': '1',
            }
            
            picking = self.env['stock.picking'].create(picking_vals)
            
            for line in requisition.requisition_line_ids:
                move_vals = {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom': line.uom_id.id,
                    'product_uom_qty': line.quantity,
                    'picking_id': picking.id,
                    'location_id': source_location.id,
                    'location_dest_id': requisition.destination_location_id.id,
                    'company_id': requisition.company_id.id,
                }
                self.env['stock.move'].create(move_vals)
            
            requisition.internal_transfer_id = picking.id
            requisition.state = 'ready_for_transfer'
            
            picking.action_confirm()
            picking.action_assign()
            
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Transfer Created'),
                    'message': _('Internal transfer has been created successfully. State updated to Ready for Transfer.'),
                    'sticky': False,
                }
            }
    


    def _find_or_create_internal_picking_type(self, company):
        """Find or create an internal picking type with multiple fallbacks"""
        
        search_domains = [
            [('code', '=', 'internal'), ('company_id', '=', company.id)],
            [('code', '=', 'internal'), ('company_id', '=', False)],
            [('code', '=', 'internal')],
            [('name', 'ilike', 'internal'), ('company_id', '=', company.id)],
            [('name', 'ilike', 'internal')],
        ]
        
        for domain in search_domains:
            picking_type = self.env['stock.picking.type'].search(domain, limit=1)
            if picking_type:
                return picking_type
        
       
        return self._create_default_internal_picking_type(company)

    def _create_default_internal_picking_type(self, company):
        """Create a default internal picking type"""
        try:
            
            stock_location = self.env.ref('stock.stock_location_stock')
            if not stock_location:
                
                stock_location = self.env['stock.location'].search([
                    ('usage', '=', 'internal')
                ], limit=1)
            
            if not stock_location:
                raise UserError(_("No internal stock locations found. Please set up inventory locations first."))
            
           
            picking_type_vals = {
                'name': 'Internal Transfers',
                'code': 'internal',
                'sequence_code': 'INT',
                'default_location_src_id': stock_location.id,
                'default_location_dest_id': stock_location.id,
                'company_id': company.id,
            }
            
            return self.env['stock.picking.type'].create(picking_type_vals)
            
        except Exception as e:
           
            _logger.warning("Failed to create internal picking type: %s", str(e))
            return False
            


    # def action_request_to_another_location(self):
    #     """Request products from another location - Only inventory users"""
    #     self.ensure_one()
        
       
    #     if self.state != 'submitted':
    #         raise UserError(_(
    #             "Only submitted requisitions can be requested from other locations. Current state: %s"
    #         ) % self.state)
        
    #     if not self._check_inventory_user_permission():
    #         raise UserError(_("Only inventory users can request from other locations."))
        
    #     if not self.requested_location_id:
    #         raise UserError(_("Please select a location to request from."))
        
        
    #     all_available = True
    #     unavailable_products = []
        
    #     for line in self.requisition_line_ids:
    #         available_qty = line.product_id.with_context(
    #             location=self.requested_location_id.id
    #         ).qty_available
            
    #         if available_qty < line.quantity:
    #             all_available = False
    #             unavailable_products.append({
    #                 'product': line.product_id.name,
    #                 'available': available_qty,
    #                 'required': line.quantity
    #             })
        
    #     if all_available:
           
    #         self.write({
    #             'is_requested_other_location': True,
    #             'source_location_id': self.requested_location_id.id,
    #         })
            
            
    #         picking_type = self._find_or_create_internal_picking_type(self.company_id)
    #         if not picking_type:
    #             raise UserError(_(
    #                 "No internal transfer operation type found. Please contact your administrator."
    #             ))
            
           
    #         picking_vals = {
    #             'picking_type_id': picking_type.id,
    #             'location_id': self.requested_location_id.id,
    #             'location_dest_id': self.destination_location_id.id,
    #             'origin': f"Requisition: {self.name} (From Requested Location)",
    #             'scheduled_date': self.required_date,
    #             'company_id': self.company_id.id,
    #             'move_type': 'direct',
    #             'priority': '1',
    #         }
            
    #         picking = self.env['stock.picking'].create(picking_vals)
            
           
    #         for line in self.requisition_line_ids:
    #             move_vals = {
    #                 'name': line.product_id.name,
    #                 'product_id': line.product_id.id,
    #                 'product_uom': line.uom_id.id,
    #                 'product_uom_qty': line.quantity,
    #                 'picking_id': picking.id,
    #                 'location_id': self.requested_location_id.id,
    #                 'location_dest_id': self.destination_location_id.id,
    #                 'company_id': self.company_id.id,
    #             }
    #             self.env['stock.move'].create(move_vals)
            
    #         self.internal_transfer_id = picking.id
    #         self.state = 'ready_for_transfer'
            
            
    #         picking.action_confirm()
    #         picking.action_assign()
            
            
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'title': _('✅ Transfer Created'),
    #                 'message': _('Internal transfer has been created successfully. State updated to Ready for Transfer.'),
    #                 'type': 'success',
    #                 'sticky': True,
    #                 'next': {
    #                     'type': 'ir.actions.act_window',
    #                     'res_model': 'dw.mrp.requisition',
    #                     'res_id': self.id,
    #                     'view_mode': 'form',
    #                     'target': 'current',
    #                     'views': [(False, 'form')],
    #                 }
    #             }
    #         }
    #     else:
            
    #         self.write({
    #             'is_requested_other_location': True,
    #             'state': 'requested_other_location',
    #         })
            
            
    #         warning_lines = []
    #         for item in unavailable_products:
    #             warning_lines.append(_("• %s: Available: %s, Required: %s") % (
    #                 item['product'], item['available'], item['required']
    #             ))
            
    #         warning_msg = _("⚠️ <strong>Products Not Available</strong><br><br>") + \
    #                     _("The following products are not available in sufficient quantity:<br><br>") + \
    #                     "<br>".join(warning_lines) + \
    #                     _("<br><br><strong>Next Step:</strong> You can now submit this requisition to purchase.")
            
            
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'title': _('⚠️ Products Not Available'),
    #                 'message': warning_msg,
    #                 'type': 'warning',
    #                 'sticky': True,
    #                 'next': {
    #                     'type': 'ir.actions.act_window',
    #                     'res_model': 'dw.mrp.requisition',
    #                     'res_id': self.id,
    #                     'view_mode': 'form',
    #                     'target': 'current',
    #                     'views': [(False, 'form')],
    #                 }
    #             }
    #         }


    def _create_transfer_from_requested_location(self):
        """Create internal transfer from requested location to destination"""
        
        picking_type = self._find_or_create_internal_picking_type(self.company_id)
        if not picking_type:
            raise UserError(_(
                "No internal transfer operation type found. Please contact your administrator."
            ))
        
        
        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': self.requested_location_id.id,
            'location_dest_id': self.destination_location_id.id,
            'origin': f"Requisition: {self.name} (From Requested Location)",
            'scheduled_date': self.required_date,
            'company_id': self.company_id.id,
            'move_type': 'direct',
            'priority': '1',
        }
        
        picking = self.env['stock.picking'].create(picking_vals)
        
        
        for line in self.requisition_line_ids:
            move_vals = {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom': line.uom_id.id,
                'product_uom_qty': line.quantity,
                'picking_id': picking.id,
                'location_id': self.requested_location_id.id,
                'location_dest_id': self.destination_location_id.id,
                'company_id': self.company_id.id,
            }
            self.env['stock.move'].create(move_vals)
        
        self.internal_transfer_id = picking.id
        self.state = 'ready_for_transfer'
        
        
        picking.action_confirm()
        picking.action_assign()
        
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Transfer Created'),
                'message': _('Internal transfer has been created from the requested location. State updated to Ready for Transfer.'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'dw.mrp.requisition',
                    'res_id': self.id,
                    'view_mode': 'form',
                    'view_id': self.env.ref('dw_stock_requisition.view_dw_mrp_requisition_form').id,
                    'target': 'current',
                }
            }
        }

    def action_set_draft(self):
        """Reset to draft - Only original requester, inventory users, or admin can reset"""
        for requisition in self:
            is_admin = self.env.user.has_group('base.group_erp_manager')
            can_reset = (
                is_admin or
                (requisition.state == 'draft' and requisition.requested_by == self.env.user) or
                (requisition.state == 'submitted' and self.env.user.has_group('dw_stock_requisition.group_inventory_team'))
            )
            
            if not can_reset:
                raise UserError(_("You don't have permission to reset this requisition."))
            
            # Reset the flags when going back to draft
            # requisition.is_requested_other_location = False
            requisition.is_submitted_to_purchase = False
            requisition.state = 'draft'
            requisition.message_post(
                body=_("Requisition reset to draft."),
                subject=_("Reset to Draft")
            )
    def action_create_purchase_order(self):
        """Create and open Purchase Order from requisition - Only purchase users"""
        for requisition in self:
            
            if not requisition._check_purchase_user_permission():
                raise UserError(_("Only purchase users can create RFQ."))
            
            if not requisition.requisition_line_ids:
                raise UserError(_("Cannot create purchase order without any items."))
            
            # Set the flag that this requisition is submitted to purchase
            requisition.write({
                'is_submitted_to_purchase': True,
                'state': 'submitted_to_purchase',
            })
            
            # ... rest of your purchase order creation code ...
            # Find a common vendor for all products
            common_partner = False
            vendor_candidates = {}
            
            # Collect all possible vendors from product suppliers
            for line in requisition.requisition_line_ids:
                if line.product_id.seller_ids:
                    for seller in line.product_id.seller_ids:
                        # Use seller.partner_id instead of seller.name
                        vendor_candidates[seller.partner_id.id] = vendor_candidates.get(seller.partner_id.id, 0) + 1
            
            # Find the vendor that supplies the most products
            if vendor_candidates:
                common_partner_id = max(vendor_candidates, key=vendor_candidates.get)
                common_partner = self.env['res.partner'].browse(common_partner_id)
            else:
                # If no vendor found, try to get any vendor from the company
                common_partner = self.env['res.partner'].search([
                    ('supplier_rank', '>', 0),
                    ('company_id', 'in', [False, requisition.company_id.id])
                ], limit=1)
                
                if not common_partner:
                    # If still no vendor, create a temporary one or raise error
                    raise UserError(_("No vendor found. Please set up at least one supplier in the system."))
            
            # Create purchase order with the found vendor
            purchase_vals = {
                'partner_id': common_partner.id,
                'origin': f"Requisition: {requisition.name}",
                'date_order': fields.Datetime.now(),
                'company_id': requisition.company_id.id,
                'currency_id': common_partner.property_purchase_currency_id.id or requisition.company_id.currency_id.id,
            }
            
            purchase_order = self.env['purchase.order'].create(purchase_vals)
            
            # Create purchase order lines
            for line in requisition.requisition_line_ids:
                # Get the supplier info for the product with the selected vendor
                seller = line.product_id._select_seller(
                    partner_id=common_partner,  # Pass the partner recordset, not ID
                    quantity=line.quantity,
                    date=fields.Date.today(),
                    uom_id=line.uom_id
                )
                
                line_vals = {
                    'order_id': purchase_order.id,
                    'product_id': line.product_id.id,
                    'name': line.description or line.product_id.name,
                    'product_qty': line.quantity,
                    'product_uom': line.uom_id.id,
                    'price_unit': seller.price if seller else line.product_id.standard_price,
                    'date_planned': requisition.required_date or fields.Date.today(),
                }
                self.env['purchase.order.line'].create(line_vals)
            
            # Return action to open the created purchase order
            return {
                'type': 'ir.actions.act_window',
                'name': _('Purchase Order'),
                'res_model': 'purchase.order',
                'res_id': purchase_order.id,
                'view_mode': 'form',
                'view_id': self.env.ref('purchase.purchase_order_form').id,
                'target': 'current',
                'context': {
                    'form_view_initial_mode': 'edit',
                    'create': False,
                }
            }

    def _check_purchase_user_permission(self):
        """Check if current user is purchase user or admin"""
        is_purchase_user = self.env.user.has_group('purchase.group_purchase_user')
        is_admin = self.env.user.has_group('base.group_erp_manager')
        return is_purchase_user or is_admin


    show_submit_to_store = fields.Boolean(
        string='Show Submit to Store',
        compute='_compute_button_visibility',
        help="Show Submit to Store button",
        store=False
    )

    show_ready_transfer = fields.Boolean(
        string='Show Ready Transfer',
        compute='_compute_button_visibility',
        help="Show Ready for Internal Transfer button",
        store=False
    )

    show_request_location = fields.Boolean(
        string='Show Request Location',
        compute='_compute_button_visibility',
        help="Show Request to Another Location button",
        store=False
    )

    show_submit_purchase = fields.Boolean(
        string='Show Submit Purchase',
        compute='_compute_button_visibility',
        help="Show Submit to Purchase button",
        store=False
    )

    show_reset_draft_inventory = fields.Boolean(
        string='Show Reset Draft (Inventory)',
        compute='_compute_button_visibility',
        help="Show Reset to Draft button for inventory users",
        store=False
    )

    show_reset_draft_manufacturing = fields.Boolean(
        string='Show Reset Draft (Manufacturing)',
        compute='_compute_button_visibility',
        help="Show Reset to Draft button for manufacturing users",
        store=False
    )

    @api.depends('state', 'is_requested_other_location', 'requested_location_id')
    def _compute_button_visibility(self):
        for requisition in self:
            requisition.show_submit_to_store = (requisition.state == 'draft')
            requisition.show_ready_transfer = (
                requisition.state == 'submitted'
                # requisition.state == 'submitted' and 
                # not requisition.is_requested_other_location
            )
            
            requisition.show_request_location = (
                requisition.state == 'submitted'
                #   and 
                # not requisition.is_requested_other_location
            )
            
            requisition.show_submit_purchase = (
                requisition.state == 'submitted' 
                # and 
                # not requisition.is_submitted_to_purchase
            )
            
            requisition.show_reset_draft_inventory = (
                requisition.state in ['submitted']
            )
            requisition.show_reset_draft_manufacturing = (requisition.state == 'draft')


    def _get_store_mail_user(self):
        return self.env['res.users'].search([
            ('name', '=', 'Store Mail'),
            ('company_id.name', '=', 'Dreamwarez_IN')
        ], limit=1)




    # def action_send_to_store_person(self):
    #     self.ensure_one()

    #     if self.state != 'submitted':
    #         raise UserError(_("Only submitted requisitions can be requested to another location."))

    #     if not self.store_user_id:
    #         raise UserError(_("Please select a Store Person."))

    #     store_partner = self.store_user_id.partner_id
    #     if not store_partner or not store_partner.email:
    #         raise UserError(_("Selected Store Person does not have an email configured."))

    #     # ✅ Change state FIRST
    #     self.write({
    #         'state': 'requested_other_location',
    #         'is_requested_other_location': True,
    #     })

    #     # ✅ Log in chatter
    #     self.message_post(
    #         body=_("Requisition requested to another location."),
    #         subject=_("Requested to Another Location")
    #     )

    #     # Sender = current inventory user
    #     sender_email = self.env.user.email
    #     if not sender_email:
    #         raise UserError(_("Your user does not have an email configured."))

    #     # ✅ Open mail wizard
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': _('Request to Another Location'),
    #         'res_model': 'mail.compose.message',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {
    #             'default_model': 'dw.mrp.requisition',
    #             'default_res_ids': [self.id],
    #             'default_partner_ids': [store_partner.id],
    #             'default_subject': f"Requisition {self.name} - Request to Another Location",
    #             'default_body': self._prepare_store_mail_body(),
    #             'default_email_from': sender_email,
    #             'force_email': True,
    #         }
    #     }






    def _prepare_store_mail_body(self):
        body = f"""
            <p>Hello Store Team,</p>

            <p>Please find below requisition details:</p>

            <p>
            <b>Requisition No:</b> {self.name}<br/>
            <b>Company:</b> {self.company_id.name}<br/>
            <b>Required Date:</b> {self.required_date}
            </p>

            <table border="1" cellpadding="5" cellspacing="0">
                <tr>
                    <th>Product</th>
                    <th>Quantity</th>
                    <th>UOM</th>
                </tr>
        """

        for line in self.requisition_line_ids:
            body += f"""
                <tr>
                    <td>{line.product_id.name}</td>
                    <td>{line.quantity}</td>
                    <td>{line.uom_id.name}</td>
                </tr>
            """

        body += """
            </table>

            <p>Please arrange material accordingly.</p>

            <p>Regards,<br/>
            {user}</p>
        """.format(user=self.env.user.name)

        return body
    
    store_user_id = fields.Many2one(
        'res.users',
        string='Store Person',
        domain=lambda self: [
            ('company_ids', 'in', self.env.ref('base.main_company').id)
        ],
    )

