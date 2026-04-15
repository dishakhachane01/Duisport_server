# -*- coding: utf-8 -*-
{
    'name': 'Engineering Team Analysis',
    'version': '1.0',
    'summary': 'Send CRM lead requirement to engineering team and capture engineering details',
    'author': 'You',
    'category': 'Tools',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'crm', 'dw_engineering_product','dw_stock_requisition','dw_quality_check'],
    'data': [
        'security/engineering_team_security.xml',
        'security/ir.model.access.csv',
        'data/uom_data.xml',
        'views/engineering_team_view.xml',
        'views/bom.xml',
        'views/material.xml',
        'views/bom_temp.xml',
        # 'views/heavy_pallet_bags.xml',
        # 'views/bom_details.xml',
        # 'views/crm_lead_inherit_view.xml',
    ],
    'installable': True,
    'application': False,
}



