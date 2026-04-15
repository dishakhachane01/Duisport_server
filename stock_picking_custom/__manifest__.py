{
    'name': 'Stock Picking Custom Fields',
    'version': '17.0.1.0.0',
    'summary': 'Adds Supplier Invoice Number, Supplier Invoice Date, GRN Date, and Vendor columns to Receipts tree view',
    'category': 'Inventory',
    'author': 'Custom',
    'depends': [
        'stock',
        'purchase',
    ],
    'data': [
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
