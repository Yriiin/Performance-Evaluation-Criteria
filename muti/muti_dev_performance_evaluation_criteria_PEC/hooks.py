# -*- coding: utf-8 -*-
import logging
from psycopg2.extensions import AsIs

_logger = logging.getLogger(__name__)

def _drop_table_view(cr, table_name):
    """Helper function to safely drop both view and table if they exist."""
    try:
        # Check if it's a view
        cr.execute("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = 'public' 
            AND table_name = %s
        """, (table_name,))
        if cr.fetchone():
            cr.execute('DROP VIEW IF EXISTS %s CASCADE', (AsIs(table_name),))

        # Check if it's a table
        cr.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name = %s
        """, (table_name,))
        if cr.fetchone():
            cr.execute('DROP TABLE IF EXISTS %s CASCADE', (AsIs(table_name),))
    except Exception as e:
        _logger.warning("Error while dropping table/view %s: %s", table_name, str(e))

def pre_init_hook(cr):
    """
    This hook runs before module installation.
    It drops any existing wrc_preview view or table to ensure clean installation.
    """
    _drop_table_view(cr, 'wrc_preview')

def post_init_hook(cr, registry):
    """
    This hook runs after module installation/upgrade.
    It ensures data consistency after module updates.
    """
    from odoo import api, SUPERUSER_ID
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        with env.cr.savepoint():
            env['sale.order']._init_wrc_previews()
            _logger.info("Successfully initialized WRC preview records for existing motorcycle sales")
    except Exception as e:
        _logger.error("Error in post_init_hook: %s", str(e))

def uninstall_hook(cr, registry):
    """
    This hook runs when the module is uninstalled.
    It cleans up any remaining database objects.
    """
    _drop_table_view(cr, 'wrc_preview')
