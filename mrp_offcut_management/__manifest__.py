{
    'name': 'MRP Offcut Management',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Track and manage material offcuts from manufacturing orders',
    'description': """
        Manages leftover/offcut materials from manufacturing.
        - Manufacturing team logs planned vs actual material usage
        - Offcut quantities are auto-calculated
        - Offcut entries submitted to store team for approval
        - On approval, stock moves are created to transfer offcuts to store location
    """,
    'depends': ['mrp', 'stock', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_offcut_views.xml',
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
