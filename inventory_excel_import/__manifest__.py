{
    'name': 'Inventory Excel Import',
    'version': '17.0.1.0.0',
    'summary': 'Import products and stock from Excel',
    'category': 'Inventory',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['base', 'product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/inventory_import_views.xml',
    ],
    'external_dependencies': {
        'python': ['pandas', 'openpyxl'],
    },
    'installable': True,
    'application': False,
}