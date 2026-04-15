
{
    'name': 'Sale Direct SO With PO History',
    'version': '17.0.1.0.0',
    'summary': 'Direct Sales Order creation with Customer PO history and repeat SO wizard',
    'category': 'Sales',
    'author': 'Custom',
    'depends': ['sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/sale_order_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
