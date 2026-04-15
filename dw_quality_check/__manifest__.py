{
    'name': 'DW Quality Check',
    'version': '1.0.0',
    'summary': 'Quality checklist for incoming shipments (stock pickings)',
    'category': 'Inventory/Quality',
    'author': 'Dreamwarez',
    'license': 'LGPL-3',
    'depends': ['stock', 'product', 'mail','mrp'],
    'data': [
        'security/quality_check_group.xml',
        'security/ir.model.access.csv',
        'reports/insp_menu.xml',
        'data/quality_check_sequence.xml',
        'views/quality_check.xml',
        'views/stock_picking.xml',
        'views/mrp_production.xml',
        'reports/insp_pallet.xml',
        'reports/insp_angleboard.xml',
        'reports/insp_woodpallet.xml',
        'reports/insp_screw.xml',
        'reports/insp_corrugation.xml',
        'reports/insp_metal.xml',
        'reports/insp_pinewood.xml',
        'reports/insp_polybag.xml',


        
        
    ],
    'installable': True,
    'application': False,
}