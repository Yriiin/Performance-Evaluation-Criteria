# -*- coding: utf-8 -*-
{
    'name': 'Service and WRC Management',
    'version': '1.0.0',
    'category': 'Services',
    'summary': 'WRC Management and Preventive Maintenance Services',
    'description': """
        This module extends the WRC (Warranty Record Card) functionality with:
        - Preventive Maintenance (PMS) Management
        - Service Performance Tracking
        - Integration with existing WRC records and service coupons
    """,
    'depends': ['base', 'muti_dev_performance_evaluation_criteria'],
    'data': [
        'security/ir.model.access.csv',
        'views/preventive_maintenance_views.xml',
        'views/service_performed_views.xml', 
        'views/menus.xml', 
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}