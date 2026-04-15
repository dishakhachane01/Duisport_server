{
    'name': 'Customer PO Approval Flow',
    'version': '1.0',
    'depends': ['sale'],
    'author': 'Custom',
    'category': 'Sales',
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/customer_po_views.xml',
    ],
    'installable': True,
}
