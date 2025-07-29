# -*- coding: utf-8 -*-
{
    'name': "Performance Evaluation Criteria",

    'summary': """
        WRC (Warranty Record Card) functionality for Motorcycle Sales""",

    'description': """
        This module provides WRC (Warranty Record Card) functionality:
        - WRC Records for motorcycle sales integrated into Sale Orders
        - Auto-population of motorcycle details from order lines
        - Integration with Sales module
        - Embedded WRC form in Sale Order with manual save
        - Service Coupon generation
    """,

    'author': "Yin",
    'website': "https://www.muti.com",

    'category': 'Sales',
    'version': '14.0.2.0.0',  # Major version bump for cleanup

    'depends': ['base', 'sale'],

    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/sale_order_view.xml',
        'views/wrc_record_views.xml',
        'views/service_coupon_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
