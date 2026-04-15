{
    'name': 'Vendor Approvals',
    'version': '1.0',
    'depends': ['base', 'mail','purchase','product_vendor_rfq'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_partner_vendor_approval_view.xml',
        'wizards/vendor_reject_wizard_view.xml'
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
