{
    'name': 'Product Creator Group',
    'version': '17.0.1.0.0',
    'category': 'Custom',
    'summary': 'Restrict product creation from dropdowns to a specific group',
    'description': """
        Creates a 'Product Creator' group. Only users in this group will see
        'Create' and 'Create & Edit' options in product many2one dropdowns
        across Sales, Purchase, and Inventory modules.
    """,
    'depends': ['product', 'sale_management', 'purchase', 'stock'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/product_many2one_patch.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
