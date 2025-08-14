# WRC Duplicate Cleanup Script
# This script helps identify and remove duplicate WRC records

from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

def cleanup_wrc_duplicates(env):
    """Clean up duplicate WRC records"""
    wrc_model = env['wrc.record']
    
    # Find all WRC records grouped by sale_order_id
    all_records = wrc_model.search([('sale_order_id', '!=', False)])
    
    sale_order_groups = {}
    for record in all_records:
        so_id = record.sale_order_id.id
        if so_id not in sale_order_groups:
            sale_order_groups[so_id] = []
        sale_order_groups[so_id].append(record)
    
    duplicates_removed = 0
    duplicates_found = []
    
    # Process each group
    for so_id, records in sale_order_groups.items():
        if len(records) > 1:
            # Sort by creation date
            records_sorted = records.sorted('create_date')
            to_keep = records_sorted[0]  # Keep the first created
            to_remove = records_sorted[1:]  # Remove the rest
            
            duplicates_found.append({
                'sale_order': to_keep.sale_order_id.name,
                'keep_record': to_keep.wrc_no,
                'duplicate_records': [r.wrc_no for r in to_remove],
                'duplicate_count': len(to_remove)
            })
            
            # Remove duplicates that are in draft state
            draft_duplicates = to_remove.filtered(lambda r: r.state == 'draft')
            if draft_duplicates:
                try:
                    draft_duplicates.unlink()
                    duplicates_removed += len(draft_duplicates)
                    _logger.info(f"Removed {len(draft_duplicates)} duplicate WRC records for SO {to_keep.sale_order_id.name}")
                except Exception as e:
                    _logger.error(f"Failed to remove duplicates for SO {to_keep.sale_order_id.name}: {str(e)}")
    
    return {
        'duplicates_found': duplicates_found,
        'duplicates_removed': duplicates_removed,
        'total_duplicate_groups': len(duplicates_found)
    }

# Usage:
# In Odoo shell or server action:
# result = cleanup_wrc_duplicates(env)
# print(f"Cleanup results: {result}")
