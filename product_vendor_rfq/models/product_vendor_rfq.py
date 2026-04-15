from tempfile import template
from odoo import models, fields, api
from odoo.exceptions import UserError


# =========================================================
# RFQ REQUEST
# =========================================================
class RFQ(models.Model):
    _name = 'rfq.request'
    _description = 'Request for Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    name = fields.Char(
        string='RFQ Number',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    date = fields.Date(
        string='RFQ Date',
        default=fields.Date.today,
        required=True,
        tracking=True
    )

    description = fields.Text('Description')

    deadline = fields.Date(string='Deadline', tracking=True)
    is_l1 = fields.Boolean(string="L1 Vendor", default=False)

    rfq_line_ids = fields.One2many(
        'rfq.request.line',
        'rfq_id',
        string='Products',
        copy=True
    )

    vendor_line_ids = fields.One2many(
        'rfq.vendor.line',
        'rfq_id',
        string='Vendors'
    )

    vendor_quote_ids = fields.One2many(
        'rfq.vendor.quote',
        'rfq_id',
        string='Vendor Quotes'
    )

    purchase_order_ids = fields.One2many(
        'purchase.order',
        'rfq_request_id',
        string='Purchase Orders'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('draft_saved', 'Draft (Saved)'),
        ('sent', 'RFQ Sent'),
        ('waiting','Waiting for Approval'),
        ('received', 'Quotes Received'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancelled')
        # ('reset_recieved','Reset to Quotes Recieved')
    ], default='draft', tracking=True)

    confirmed_quote_id = fields.Many2one(
        'rfq.vendor.quote',
        string='Confirmed Quote'
    )

   
    # def action_send_rfq(self):
    #     for vendor_line in self.vendor_line_ids:
    #         po = self.env['purchase.order'].create({
    #             'partner_id': vendor_line.vendor_id.id,
    #             'rfq_request_id': self.id,
    #             'origin': self.name,
    #             'order_line': [
    #                 (0, 0, {
    #                     'product_id': l.product_id.id,
    #                     'product_qty': l.quantity,
    #                     'product_uom': l.uom_id.id,
    #                     'price_unit': 0,
    #                 }) for l in self.rfq_line_ids
    #             ]
    #         })

    #         quote = self.env['rfq.vendor.quote'].create({
    #             'rfq_id': self.id,
    #             'vendor_id': vendor_line.vendor_id.id,
    #             'purchase_order_id': po.id,
    #         })

    #         for line in self.rfq_line_ids:
    #             self.env['rfq.vendor.quote.line'].create({
    #                 'quote_id': quote.id,
    #                 'product_id': line.product_id.id,
    #                 'quantity': line.quantity,
    #             })

    #         # -----------------------------
    #         # SEND EMAIL TO VENDOR
    #         # -----------------------------
    #         if vendor_line.vendor_id.email:
    #             # Get the email template
    #             template = self.env.ref('product_vendor_rfq.email_template_rfq_to_vendor')
                
    #             ctx = {
    #                 'vendor_name': vendor_line.vendor_id.name,
    #                 'vendor_email': vendor_line.vendor_id.email,
    #             }
    #             template.with_context(ctx).send_mail(
    #                 self.id,
    #                 force_send=True,
    #                 raise_exception=False
    #             )

    #     self.state = 'sent'
    
    def action_save_draft(self):
        """Save RFQ in draft state ignoring user access rights"""

        # Re-browse with sudo to bypass access rules
        rfqs = self.sudo()

        rfqs.write({
            'state': 'draft_saved'
        })

        return True


    def action_send_rfq(self):
        for vendor_line in self.vendor_line_ids:

            # -----------------------------
            # Create Purchase Order
            # -----------------------------
            po = self.env['purchase.order'].create({
                'partner_id': vendor_line.vendor_id.id,
                'rfq_request_id': self.id,
                'origin': self.name,
                'order_line': [
                    (0, 0, {
                        'product_id': l.product_id.id,
                        'product_qty': l.quantity,
                        'product_uom': l.uom_id.id,
                        'price_unit': 0,
                    }) for l in self.rfq_line_ids
                ]
            })

            # -----------------------------
            # Create Vendor Quote
            # -----------------------------
            quote = self.env['rfq.vendor.quote'].create({
                'rfq_id': self.id,
                'vendor_id': vendor_line.vendor_id.id,
                'purchase_order_id': po.id,
            })

            for line in self.rfq_line_ids:
                self.env['rfq.vendor.quote.line'].create({
                    'quote_id': quote.id,
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                })

            # -----------------------------
            # SEND EMAIL (NO TEMPLATE)
            # -----------------------------
            vendor = vendor_line.vendor_id

            if not vendor.email:
                continue

            # Build product rows
            rows = ""
            for line in self.rfq_line_ids:
                rows += f"""
                    <tr>
                        <td>{line.product_id.display_name or ''}</td>
                        <td align="right">{line.quantity or 0}</td>
                        <td>{line.uom_id.name or ''}</td>
                    </tr>
                """

            body_html = f"""
            <div style="font-family: Arial, sans-serif;">
                <p>
                    Dear <strong>{vendor.name}</strong>,
                </p>

                <p>
                    This is the RFQ mail for the below products.
                    Kindly share your quotation for further process.
                </p>

                <table border="1" cellpadding="6" cellspacing="0" width="100%"
                       style="border-collapse: collapse;">
                    <thead>
                        <tr style="background-color:#f0f0f0;">
                            <th align="left">Product</th>
                            <th align="right">Quantity</th>
                            <th align="left">UoM</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>

                <p>
                    Please mention delivery time, payment terms,
                    and validity in your quotation.
                </p>

                <br/>
                <p>
                    Thanks &amp; Regards,<br/>
                    {self.env.user.name}<br/>
                    {self.env.user.company_id.name}
                </p>
            </div>
            """

            mail = self.env['mail.mail'].sudo().create({
                'subject': f"RFQ: {self.name} - Request for Quotation",
                'email_from': self.env.user.email_formatted,
                'email_to': vendor.email,
                'body_html': body_html,
            })

            mail.sudo().send()

        self.state = 'sent'
    
    
    
    
    
    
    def set_draft(self):
        self.state = 'draft'
    
  
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'rfq.request'
            ) or 'New'
        return super().create(vals)
   
    def action_reset_to_received(self):
        for rec in self:
            if rec.state == 'cancel':
                rec.state = 'received'
                rec.message_post(body="State reset from Cancelled to Quotes Received.")
    
    
    # def action_view_comparison(self):
    #     for rec in self:
    #         rec.vendor_quote_ids.update_l_rankings()

    #     return {
    #         'name': 'Vendor Quote Comparison',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'rfq.vendor.quote',
    #         'view_mode': 'tree,form',
    #         'domain': [('rfq_id', '=', self.id)],
    #     }


    def action_view_comparison(self):
        self.ensure_one()
        self.vendor_quote_ids.update_l_rankings()
        return {
            'type': 'ir.actions.report',
            'report_name': 'product_vendor_rfq.rfq_vertical_comparison_template',
            'report_type': 'qweb-html',
            'context': self.env.context,
        }




    def action_send_rfq_email(self, vendor, vendor_email):
        """
        vendor       -> res.partner record
        vendor_email -> email string
        """

        self.ensure_one()

        if not vendor_email:
            raise UserError(_("Vendor email is missing."))

        # -----------------------------
        # Build product table rows
        # -----------------------------
        rows = ""
        for line in self.rfq_line_ids:
            rows += f"""
                <tr>
                    <td>{line.product_id.display_name or ''}</td>
                    <td align="right">{line.quantity or 0}</td>
                    <td>{line.uom_id.name or ''}</td>
                </tr>
            """

        # -----------------------------
        # Email body
        # -----------------------------
        body_html = f"""
        <div style="font-family: Arial, sans-serif;">
            <p>
                Dear <strong>{vendor.name or 'Vendor'}</strong>,
            </p>

            <p>
                This is the RFQ mail for the below products.
                Kindly share your quotation for further process.
            </p>

            <table border="1" cellpadding="6" cellspacing="0" width="100%"
                   style="border-collapse: collapse;">
                <thead>
                    <tr style="background-color:#f0f0f0;">
                        <th align="left">Product</th>
                        <th align="right">Quantity</th>
                        <th align="left">UoM</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>

            <p>
                Please mention delivery time, payment terms,
                and validity in your quotation.
            </p>

            <br/>
            <p>
                Thanks &amp; Regards,<br/>
                {self.env.user.name}<br/>
                {self.env.user.company_id.name}
            </p>
        </div>
        """

        # -----------------------------
        # Create & send mail
        # -----------------------------
        mail = self.env['mail.mail'].create({
            'subject': f"RFQ: {self.name} - Request for Quotation",
            'email_from': self.env.user.email_formatted,
            'email_to': vendor_email,
            'body_html': body_html,
        })

        mail.send()



# morye.prasad@duisport.de, rohit.kumar@duisport.de, alok-kumar.pandey@duisport.de



    def action_send_comparison_to_md(self):
        self.ensure_one()

        self.state = 'waiting'

        # Update rankings before sending
        self.vendor_quote_ids.update_l_rankings()

        # Get MD email from system parameter or company settings
        # You can hardcode or fetch from ir.config_parameter
        md_email = self.env['ir.config_parameter'].sudo().get_param('rfq.md_email')

        if not md_email:
            raise UserError("MD email is not configured. Please set 'rfq.md_email' in System Parameters.")

        # Build comparison table rows
        quotes = self.vendor_quote_ids.sorted('total_amount')

        # Header row for products
        products = self.rfq_line_ids.mapped('product_id')

        quote_rows = ""
        for index, quote in enumerate(quotes):
            rank_label = ""
            if quote.is_l1:
                rank_label = "<span style='color:green;font-weight:bold;'>L1</span>"
            elif quote.is_l2:
                rank_label = "<span style='color:orange;font-weight:bold;'>L2</span>"
            elif quote.is_l3:
                rank_label = "<span style='color:#cc0000;font-weight:bold;'>L3</span>"
            elif quote.is_l4:
                rank_label = "L4"

            product_cells = ""
            for product in products:
                qline = quote.quote_line_ids.filtered(lambda l: l.product_id == product)
                if qline:
                    product_cells += f"<td align='center'>{qline[0].unit_price:.2f}<br/><small>({qline[0].quantity} {qline[0].product_id.uom_id.name})</small></td>"
                else:
                    product_cells += "<td align='center'>-</td>"

            quote_rows += f"""
                <tr>
                    <td><strong>{quote.vendor_id.name}</strong></td>
                    {product_cells}
                    <td align='right'><strong>{quote.total_amount:.2f} {quote.currency_id.symbol}</strong></td>
                    <td align='center'>{quote.delivery_time or '-'} days</td>
                    <td align='center'>{rank_label}</td>
                    <td>{quote.notes or '-'}</td>
                </tr>
            """

        # Build product column headers
        product_headers = "".join(
            f"<th align='center'>{p.display_name}</th>" for p in products
        )

        body_html = f"""
        <div style="font-family: Arial, sans-serif;">
            <p>Dear MD,</p>

            <p>
                Please find below the vendor quote comparison for RFQ 
                <strong>{self.name}</strong> dated {self.date}.
            </p>

            {"<p><strong>Deadline:</strong> " + str(self.deadline) + "</p>" if self.deadline else ""}
            {"<p><strong>Description:</strong> " + self.description + "</p>" if self.description else ""}

            <table border="1" cellpadding="6" cellspacing="0" width="100%"
                style="border-collapse: collapse;">
                <thead>
                    <tr style="background-color:#003366; color:white;">
                        <th align="left">Vendor</th>
                        {product_headers}
                        <th align="right">Total Amount</th>
                        <th align="center">Delivery Time</th>
                        <th align="center">Rank</th>
                        <th align="left">Notes</th>
                    </tr>
                </thead>
                <tbody>
                    {quote_rows}
                </tbody>
            </table>

            <p style="margin-top:16px;">
                <strong>L1</strong> = Lowest Quote &nbsp;|&nbsp;
                <strong>L2</strong> = 2nd Lowest &nbsp;|&nbsp;
                <strong>L3</strong> = 3rd Lowest
            </p>

            <br/>
            <p>
                Thanks &amp; Regards,<br/>
                {self.env.user.name}<br/>
                {self.env.user.company_id.name}
            </p>
        </div>
        """
       # email_to = f"{md_email}"
        email_to = f"{md_email}, morye.prasad@duisport.de, rohit.kumar@duisport.de, alok-kumar.pandey@duisport.de"
        mail = self.env['mail.mail'].sudo().create({
            'subject': f"RFQ Comparison: {self.name} - Vendor Quote Summary",
            'email_from': self.env.user.email_formatted,
            'email_to': email_to,
            'body_html': body_html,
        })
        mail.sudo().send()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Email Sent',
                'message': f'Comparison email sent to MD at {md_email}',
                'type': 'success',
                'sticky': False,
            }
        }









# =========================================================
# RFQ LINE (MULTIPLE PRODUCTS)
# =========================================================
class RFQRequestLine(models.Model):
    _name = 'rfq.request.line'
    _description = 'RFQ Product Line'

    rfq_id = fields.Many2one(
        'rfq.request',
        ondelete='cascade',
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        required=True
    )

    quantity = fields.Float(default=1.0, required=True)

    uom_id = fields.Many2one(
        'uom.uom',
        related='product_id.uom_id',
        readonly=True
    )

    description = fields.Text()


# =========================================================
# RFQ VENDOR LINE
# =========================================================
class RFQVendorLine(models.Model):
    _name = 'rfq.vendor.line'
    _description = 'RFQ Vendor Line'

    rfq_id = fields.Many2one(
        'rfq.request',
        ondelete='cascade'
    )

    vendor_id = fields.Many2one(
        'res.partner',
        domain=[
            ('supplier_rank', '>', 0),
            ('is_company', '=', True)
        ],
        required=True
    )

    email = fields.Char(
        related='vendor_id.email',
        readonly=True
    )

    phone = fields.Char(
        related='vendor_id.phone',
        readonly=True
    )


# =========================================================
# RFQ VENDOR QUOTE (HEADER LEVEL)
# =========================================================
class RFQVendorQuote(models.Model):
    _name = 'rfq.vendor.quote'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Quote Reference', compute='_compute_name', 
                       store=True)
    rfq_id = fields.Many2one('rfq.request', required=True)
    vendor_id = fields.Many2one('res.partner', required=True)

    purchase_order_id = fields.Many2one('purchase.order')

    quote_line_ids = fields.One2many(
        'rfq.vendor.quote.line',
        'quote_id',
        string='Quoted Products'
    )

    total_amount = fields.Float(
        compute='_compute_total_amount',
        store=True
    )

    state = fields.Selection([
        ('sent', 'Sent'),
        ('received', 'Received'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected')
    ], default='sent', tracking=True)

    delivery_time = fields.Integer()
    payment_terms = fields.Char()
    notes = fields.Text()
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    purchase_qty = fields.Float(
        string="Approved Purchase Qty",
        help="Quantity approved to purchase from this vendor"
    )





    total_amount = fields.Float(
        string="Total Amount",
        compute="_compute_total_amount",
        store=True,
        currency_field='currency_id'
    )

    is_l1 = fields.Boolean(string="L1")
    is_l2 = fields.Boolean(string="L2")
    is_l3 = fields.Boolean(string="L3")
    is_l4 = fields.Boolean(string="L4")

    @api.depends('rfq_id', 'vendor_id')
    def _compute_name(self):
        for rec in self:
            if rec.rfq_id and rec.vendor_id:
                rec.name = f"{rec.rfq_id.name}/{rec.vendor_id.name}"
            else:
                rec.name = 'New'


    def action_reset_to_received(self):
        self.ensure_one()

        if self.state != 'rejected':
            raise UserError("Only rejected quotes can be reset.")

        self.write({
            'state': 'received'
        })

        # Recalculate rankings
        self.update_l_rankings()

        return True



    # -----------------------------------------------------
    # SEND RFQ (Create PO per Vendor with multiple lines)
    # -----------------------------------------------------
    # def action_send_rfq(self):
    #     if not self.vendor_line_ids:
    #         raise UserError('Please select at least one vendor.')

    #     if not self.rfq_line_ids:
    #         raise UserError('Please add at least one product.')

    #     PurchaseOrder = self.env['purchase.order'].sudo()

    #     for vendor_line in self.vendor_line_ids:
    #         vendor = vendor_line.vendor_id
    #         order_lines = []

    #         for line in self.rfq_line_ids:
    #             order_lines.append((0, 0, {
    #                 'product_id': line.product_id.id,
    #                 'name': line.product_id.display_name,
    #                 'product_qty': line.quantity,
    #                 'product_uom': line.uom_id.id,
    #                 'price_unit': 0.0,
    #                 'date_planned': self.deadline or fields.Date.today(),
    #             }))

    #         po = PurchaseOrder.create({
    #             'partner_id': vendor.id,
    #             'rfq_request_id': self.id,
    #             'origin': self.name,
    #             'order_line': order_lines,
    #         })

    #         self.env['rfq.vendor.quote'].create({
    #             'rfq_id': self.id,
    #             'vendor_id': vendor.id,
    #             'purchase_order_id': po.id,
    #             'state': 'sent',
    #         })

    #     self.state = 'sent'

    @api.depends('quote_line_ids.total_price')
    def _compute_total_amount(self):
        for quote in self:
            quote.total_amount = sum(
                quote.quote_line_ids.mapped('total_price')
            )
    

    

    def action_receive_quote(self):
        self.ensure_one()
        self.state = 'received'

 




   

    def action_confirm_quote(self):
        self.ensure_one()

        if self.state != 'received':
            raise UserError("Only received quotes can be confirmed.")

        self.state = 'confirmed'

        po = self.purchase_order_id

        if po:
            for po_line in po.order_line:
                qline = self.quote_line_ids.filtered(
                    lambda q: q.product_id == po_line.product_id
                )[:1]

                if not qline:
                    continue

                # Use purchase_qty if filled, else fallback
                final_qty = qline.purchase_qty if qline.purchase_qty > 0 else qline.quantity

                po_line.write({
                    'product_qty': final_qty,
                    'price_unit': qline.unit_price,
                })

                # Sync quote line
                qline.write({
                    'quantity': final_qty,
                    'purchase_qty': final_qty,
                })

            # ❌ Removed direct PO confirmation
            # Now PO will remain in draft/sent state

            po.message_post(
                body=f"<p>RFQ <b>{self.rfq_id.name}</b> confirmed. Waiting for approval flow.</p>",
                subject="RFQ Confirmed"
            )

        self._compute_total_amount()
        self.update_l_rankings()

        return True

   
   
   
    # working 
    # def action_confirm_quote(self):
    #     self.ensure_one()

    #     if self.state != 'received':
    #         raise UserError("Only received quotes can be confirmed.")

    #     self.state = 'confirmed'

    #     po = self.purchase_order_id

    #     if po:
    #         for po_line in po.order_line:
    #             qline = self.quote_line_ids.filtered(
    #                 lambda q: q.product_id == po_line.product_id
    #             )[:1]

    #             if not qline:
    #                 continue

    #             # Use purchase_qty if filled, else fall back to demanded quantity
    #             final_qty = qline.purchase_qty if qline.purchase_qty > 0 else qline.quantity

    #             po_line.write({
    #                 'product_qty': final_qty,
    #                 'price_unit': qline.unit_price,
    #             })

    #             # Sync quote line so comparison table reflects final qty
    #             qline.write({
    #                 'quantity': final_qty,
    #                 'purchase_qty': final_qty,  # also set purchase_qty so it's consistent
    #             })

    #         if po.state in ('draft', 'sent'):
    #             po.button_confirm()
    #             po.message_post(
    #                 body=f"<p>Purchase Order confirmed based on RFQ <b>{self.rfq_id.name}</b></p>",
    #                 subject="PO Confirmed"
    #             )

    #     self._compute_total_amount()
    #     self.update_l_rankings()

    #     return True



    # def action_confirm_quote(self):
    #     self.ensure_one()

    #     if self.state != 'received':
    #         raise UserError("Only received quotes can be confirmed.")

    #     # --------------------------------------------------
    #     # Confirm Vendor Quote
    #     # --------------------------------------------------
    #     self.state = 'confirmed'

    #     po = self.purchase_order_id

    #     # --------------------------------------------------
    #     # Update Purchase Order Lines
    #     # --------------------------------------------------
    #     if po:
    #         for po_line in po.order_line:
    #             qline = self.quote_line_ids.filtered(
    #                 lambda q: q.product_id == po_line.product_id
    #             )[:1]

    #             if not qline:
    #                 continue

    #             # Remove line if purchase_qty = 0
    #             if qline.purchase_qty <= 0:
    #                 po_line.unlink()
    #                 continue

    #             po_line.write({
    #                 'product_qty': qline.purchase_qty,
    #                 'price_unit': qline.unit_price,
    #             })

    #         # --------------------------------------------------
    #         # Confirm PO
    #         # --------------------------------------------------
    #         if po.state in ('draft', 'sent'):
    #             po.button_confirm()

    #             po.message_post(
    #                 body=f"<p>Purchase Order confirmed based on RFQ <b>{self.rfq_id.name}</b></p>",
    #                 subject="PO Confirmed"
    #             )

    #     # --------------------------------------------------
    #     # Update rankings only
    #     # --------------------------------------------------
    #     self.update_l_rankings()

    #     return True




    
    # def action_confirm_quote(self):
    #     self.ensure_one()

    #     if self.state != 'received':
    #         raise UserError("Only received quotes can be confirmed.")

    #     # --------------------------------------------------
    #     # Confirm Vendor Quote & RFQ
    #     # --------------------------------------------------
    #     self.state = 'confirmed'
    #     self.rfq_id.state = 'confirmed'
    #     self.rfq_id.confirmed_quote_id = self.id

    #     po = self.purchase_order_id

    #     # --------------------------------------------------
    #     # Update Purchase Order prices
    #     # --------------------------------------------------
    #     if po:
    #         for po_line in po.order_line:
    #             qline = self.quote_line_ids.filtered(
    #                 lambda q: q.product_id == po_line.product_id
    #             )
    #             if qline:
    #                 po_line.write({'price_unit': qline.unit_price})

    #         # --------------------------------------------------
    #         # CONFIRM PURCHASE ORDER (THIS IS THE KEY PART)
    #         # --------------------------------------------------
    #         if po.state in ('draft', 'sent'):
    #             po.button_confirm()

    #             po.message_post(
    #                 body=f"<p>Purchase Order confirmed based on RFQ <b>{self.rfq_id.name}</b></p>",
    #                 subject="PO Confirmed"
    #             )

    #     # --------------------------------------------------
    #     # Reject other quotes
    #     # --------------------------------------------------
    #     other_quotes = self.rfq_id.vendor_quote_ids.filtered(lambda q: q.id != self.id)
    #     other_quotes.write({'state': 'rejected'})

    #     # --------------------------------------------------
    #     # Cancel other POs
    #     # --------------------------------------------------
    #     for quote in other_quotes:
    #         other_po = quote.purchase_order_id
    #         if other_po and other_po.state not in ('purchase', 'done', 'cancel'):
    #             try:
    #                 other_po.button_cancel()
    #             except Exception as e:
    #                 other_po.message_post(
    #                     body=f"Could not cancel automatically: {str(e)}",
    #                     subject="Cancellation Note"
    #                 )

    #     # --------------------------------------------------
    #     # Update L1/L2/L3 rankings
    #     # --------------------------------------------------
    #     self.update_l_rankings()

    #     return True





    def update_l_rankings(self):
        for rfq in self.mapped('rfq_id'):
            quotes = rfq.vendor_quote_ids.filtered(lambda q: q.total_amount > 0).sorted('total_amount')

            rfq.vendor_quote_ids.write({
                'is_l1': False,
                'is_l2': False,
                'is_l3': False,
                'is_l4': False,
            })

            for index, quote in enumerate(quotes):
                vals = {}
                if index == 0:
                    vals['is_l1'] = True
                elif index == 1:
                    vals['is_l2'] = True
                elif index == 2:
                    vals['is_l3'] = True
                elif index == 3:
                    vals['is_l4'] = True

                if vals:
                    quote.write(vals) 





    def action_reject_quote(self):
        """Reject this vendor quote"""
        self.ensure_one()

        if self.state not in ['sent', 'received']:
            raise UserError('Only sent or received quotes can be rejected.')

        # Reject this quote
        self.write({
            'state': 'rejected',
            'is_l1': False,
            'is_l2': False,
            'is_l3': False,
            'is_l4': False,
        })

        # Cancel associated purchase order (if not confirmed)
        po = self.purchase_order_id
        if po and po.state not in ('purchase', 'done', 'cancel'):
            try:
                po.button_cancel()
            except Exception as e:
                po.message_post(
                    body=f"Could not cancel automatically: {str(e)}",
                    subject="Cancellation Note"
                )

        # If all quotes are rejected, update RFQ state
        rfq = self.rfq_id
        if rfq and not rfq.vendor_quote_ids.filtered(lambda q: q.state != 'rejected'):
            rfq.state = 'cancelled'

        return True


# =========================================================
# PURCHASE ORDER EXTENSION
# =========================================================
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    rfq_request_id = fields.Many2one(
        'rfq.request',
        ondelete='set null'
    )



class RFQVendorQuoteLine(models.Model):
    _name = 'rfq.vendor.quote.line'
    _description = 'Vendor Quote Line'

    quote_id = fields.Many2one(
        'rfq.vendor.quote',
        ondelete='cascade',
        required=True
    )

    rfq_id = fields.Many2one(
        related='quote_id.rfq_id',
        store=True
    )

    vendor_id = fields.Many2one(
        related='quote_id.vendor_id',
        store=True
    )
    delivery_time = fields.Integer(string="Delivery (Days)")
    product_id = fields.Many2one(
        'product.product',
        required=True
    )

    quantity = fields.Float(required=True)

    unit_price = fields.Float(default=0.0)

    total_price = fields.Float(
        compute='_compute_total',
        store=True
    )

    purchase_qty = fields.Float(
        string="Approved Purchase Qty",
        help="Quantity approved to purchase from this vendor"
    )



    is_l1 = fields.Boolean(readonly=True)
    is_l2 = fields.Boolean(readonly=True)
    is_l3 = fields.Boolean(readonly=True)

    # @api.depends('quantity', 'unit_price')
    # def _compute_total(self):
    #     for rec in self:
    #         rec.total_price = rec.quantity * rec.unit_price

    @api.depends('quantity', 'unit_price', 'purchase_qty')
    def _compute_total(self):
        for rec in self:
            qty = rec.purchase_qty if rec.purchase_qty > 0 else rec.quantity
            rec.total_price = qty * rec.unit_price



# class PurchaseOrder(models.Model):
#     _inherit = 'purchase.order'

#     def button_confirm(self):

#         if not self.env.user.has_group('product_vendor_rfq.group_rfq_po_approver'):
#             raise UserError(
#                 "You are not allowed to confirm Purchase Orders.\n"
#                 "Please contact Purchase Manager."
#             )

#         return super().button_confirm()



# class PurchaseOrder(models.Model):
#     _inherit = 'purchase.order'

#     def button_confirm(self):
#         if not self.env.user.has_group('product_vendor_rfq.group_confirm_po'):
#             raise UserError("Only authorized users can confirm Purchase Orders.")
#         return super().button_confirm()
    













class RFQComparisonReport(models.AbstractModel):
    _name = 'report.product_vendor_rfq.rfq_vertical_comparison_template'
    _description = 'RFQ Vendor Comparison Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        rfq = self.env['rfq.request'].browse(docids)
        rfq.vendor_quote_ids.update_l_rankings()
        return {
            'rfq': rfq,
            'vendors': rfq.vendor_quote_ids.mapped('vendor_id'),
            'products': rfq.rfq_line_ids.mapped('product_id'),
            'quotes': rfq.vendor_quote_ids,
        }