from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    supplier_invoice_number = fields.Char(
        string="Supplier Invoice Number"
    )
    supplier_invoice_date = fields.Date(
        string="Supplier Invoice Date"
    )
    qc_done = fields.Boolean(string="QC Done", default=False)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _prepare_picking(self):
        vals = super()._prepare_picking()

        vals.update({
            'supplier_invoice_number': self.partner_ref,
            'supplier_invoice_date': self.supplier_invoice_date if self.supplier_invoice_date else False,
        })

        return vals