# -*- coding: utf-8 -*-

def migrate(cr, version):
    """Clean up old model references"""
    
    import logging
    _logger = logging.getLogger(__name__)
    _logger.info("Starting pre-migration cleanup for version %s", version)
    
    # Clean up old model references
    old_models = ['wrc.service.coupon', 'wrc_service_coupon']
    
    for old_model in old_models:
        # Remove old model data
        cr.execute("""
            DELETE FROM ir_model_data 
            WHERE model = %s OR name LIKE %s
        """, (old_model, f'%{old_model.replace(".", "_")}%'))
        
        # Clean up old selection values
        cr.execute("""
            DELETE FROM ir_model_fields_selection 
            WHERE field_id IN (
                SELECT id FROM ir_model_fields 
                WHERE model = %s
            )
        """, (old_model,))
        
        # Clean up old model fields
        cr.execute("""
            DELETE FROM ir_model_fields 
            WHERE model = %s
        """, (old_model,))
        
        # Clean up old models
        cr.execute("""
            DELETE FROM ir_model 
            WHERE model = %s
        """, (old_model,))
        
        # Clean up old access rules
        cr.execute("""
            DELETE FROM ir_model_access 
            WHERE model_id NOT IN (SELECT id FROM ir_model)
        """, ())
        
        _logger.info("Cleaned up references to model: %s", old_model)
    
    # Clean up any orphaned records
    cr.execute("""
        DELETE FROM ir_model_access 
        WHERE model_id IS NULL OR model_id NOT IN (SELECT id FROM ir_model)
    """)
    
    # Remove any lingering is_mechanic field references
    cr.execute("""
        DELETE FROM ir_model_fields 
        WHERE name = 'is_mechanic' 
        AND model IN ('sale.order', 'wrc.record');
    """)
    
    # Remove any related data
    cr.execute("""
        DELETE FROM ir_model_data 
        WHERE name LIKE '%mechanic%' 
        AND model IN ('ir.model.fields', 'ir.model.fields.selection');
    """)
    
    cr.commit()
    _logger.info("Migration cleanup completed successfully")