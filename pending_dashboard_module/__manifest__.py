{
    'name': 'Advanced Pending Dashboard',
    'version': '1.0',
    'depends': ['base','web','purchase','product_vendor_rfq','sale_management','stock','account','crm','mrp'],
    'data': [
        'security/ir.model.access.csv',
        'views/dashboard_menu.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'pending_dashboard_module/static/src/js/dashboard.js',
            'pending_dashboard_module/static/src/xml/dashboard.xml',
            'pending_dashboard_module/static/src/css/dashboard.css',

        ],
    },
    'installable': True,
    'application': True,
}
