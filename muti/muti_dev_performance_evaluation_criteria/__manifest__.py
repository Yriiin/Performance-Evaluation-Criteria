# -*- coding: utf-8 -*-
{
    'name': "Performance Evaluation Criteria",

    'summary': """
        WRC (Warranty Record Card) functionality for Motorcycle Sales""",

    'description': """
        V1.0 Draft - Complete WRC (Warranty Record Card) functionality for Motorcycle Sales:

        Key Features:
        - Auto-save WRC records when motorcycle sales are fully invoiced
        - Auto-filled fields are read-only, incomplete fields remain editable
        - Motorcycle classification system (Commuter vs BigBike)
        - Brand extraction from product names (HO=Honda, YA=Yamaha, etc.)
        - Automated PMS-based service coupon generation:
          * Coupon 1: 500-2,000 km or 3 months
          * Coupon 2: 2,001-6,000 km or 7 months
          * Coupon 3: 6,001-12,000 km or 12 months
        - Coupon use functionality with service tracking
        - Overdue coupon management and validation
        - Complete customer, dealer, and unit information management
    """,

    'author': "Yin",
    'website': "https://www.muti.com",

    'category': 'Sales',
    'version': '1.0.0',  # V1.0 Draft - Complete motorcycle sales WRC system

    'depends': ['base', 'sale'],

    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/cron_data.xml',
        'views/motorcycle_sales_views.xml',  # Motorcycle Sales view with WRC fields
        'views/sale_order_view.xml',  # Enabled - WRC tab for motorcycle sales only
        'views/sale_order_header_view.xml',  # Enabled - WRC action buttons
        'views/wrc_record_views.xml',
        'views/wrc_creation_wizard_views.xml',  # New WRC creation wizard
        'views/service_coupon_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
