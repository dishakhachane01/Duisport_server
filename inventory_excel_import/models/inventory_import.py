from odoo import models, fields
import base64
import io
import pandas as pd


class InventoryImport(models.Model):
    _name = 'inventory.import'
    _description = 'Inventory Excel Import'

    file = fields.Binary(string="Upload Excel File", required=True)
    file_name = fields.Char(string="File Name")

    def action_import_excel(self):
        if not self.file:
            return

        data = base64.b64decode(self.file)
        file = io.BytesIO(data)
        df = pd.read_excel(file)

        location = self.env.ref('stock.stock_location_stock')

        for _, row in df.iterrows():

            category_name = str(
                row.get('Category') or 
                row.get('Catergory') or 
                ''
            ).strip()

            if not category_name or category_name.lower() == 'nan':
                category = self.env.ref('product.product_category_all')
            else:
                category = self.env['product.category'].search(
                    [('name', '=', category_name)], limit=1
                )
                if not category:
                    category = self.env['product.category'].create({
                        'name': category_name
                    })


            item_code = str(row.get('Item Code', '')).strip()
            description = str(row.get('Description', '')).strip()
            uom_name = str(row.get('UOM', '')).strip()
            opening_qty = float(row.get('Opening Qty', 0) or 0)

            # # Category
            # category = self.env['product.category'].search(
            #     [('name', '=', category_name)], limit=1
            # )
            # if not category and category_name:
            #     category = self.env['product.category'].create({
            #         'name': category_name
            #     })

            # UOM
            uom = self.env['uom.uom'].search(
                [('name', '=', uom_name)], limit=1
            )

            # Product
            product = self.env['product.product'].search(
                [('default_code', '=', item_code)], limit=1
            )

            if not product:
                product = self.env['product.product'].create({
                    'name': description or item_code or 'New Product',
                    'default_code': item_code,
                    'categ_id': category.id,  # NEVER False
                    'uom_id': uom.id if uom else self.env.ref('uom.product_uom_unit').id,
                    'uom_po_id': uom.id if uom else self.env.ref('uom.product_uom_unit').id,
                    'type': 'product',
                })

            # Update stock (Opening Qty)
            if opening_qty:
                self.env['stock.quant']._update_available_quantity(
                    product,
                    location,
                    opening_qty
                )


class InventoryImportView(models.TransientModel):
    _name = 'inventory.import.wizard'
    _description = 'Inventory Import Wizard'

    file = fields.Binary(string="Upload Excel File", required=True)
    file_name = fields.Char(string="File Name")

    def action_import_excel(self):
        record = self.env['inventory.import'].create({
            'file': self.file,
            'file_name': self.file_name,
        })
        record.action_import_excel()
