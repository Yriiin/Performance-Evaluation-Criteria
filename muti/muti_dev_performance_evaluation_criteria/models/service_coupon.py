# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class ServiceCoupon(models.Model):
    _name = 'service.coupon'
    _description = 'Service Coupon'
    _rec_name = 'coupon_number'
    _order = 'create_date desc'
    
    # Basic Information
    coupon_number = fields.Char('Coupon Number', required=True, copy=False)
    wrc_record_id = fields.Many2one('wrc.record', 'WRC Record', required=True, ondelete='cascade')
    
    # Related fields from WRC Record
    classification = fields.Selection(related='wrc_record_id.classification', string='Classification', readonly=True, store=True)
    
    # Coupon Type and PMS Schedule
    coupon_type = fields.Selection([
        ('pms_1', 'PMS 1 (500-2,000 km / 3 months)'),
        ('pms_2', 'PMS 2 (2,001-6,000 km / 7 months)'),
        ('pms_3', 'PMS 3 (6,001-12,000 km / 12 months)'),
    ], string='Coupon Type', required=True)
    
    # PMS Criteria
    pms_km_min = fields.Integer('Min KM')
    pms_km_max = fields.Integer('Max KM')
    pms_months = fields.Integer('Months Schedule')
    due_date = fields.Date('Due Date')
    
    # Sequential PMS tracking
    previous_pms_coupon_id = fields.Many2one('service.coupon', 'Previous PMS Coupon')
    is_pms_1_based = fields.Boolean('PMS 1 Based', default=True, 
                                   help='True if scheduled based on months, False if based on previous PMS')
    
    # Status
    state = fields.Selection([
        ('active', 'Active'),
        ('used', 'Used'),
        ('expired', 'Expired'),
        ('disabled', 'Disabled'),
    ], default='active', string='Status')
    
    # Service Information (when coupon is used)
    servicing_branch_id = fields.Many2one('res.company', 'Servicing Branch')
    fsc_sequence = fields.Char('FSC NO./Coupon Code Sequence')
    fsc_code = fields.Char('FSC NO./Coupon Code')
    actual_service_date = fields.Date('Actual Service Date')
    accept_date = fields.Date('Accept Date')
    mileage = fields.Float('Mileage (km)')
    service_notes = fields.Text('Service Notes')
    
    # Computed fields
    is_overdue = fields.Boolean('Is Overdue', compute='_compute_overdue', store=True)
    can_use = fields.Boolean('Can Use', compute='_compute_can_use')
    
    @api.depends('due_date', 'state')
    def _compute_overdue(self):
        today = fields.Date.today()
        for record in self:
            record.is_overdue = (
                record.state == 'active' and 
                record.due_date and 
                record.due_date < today
            )

    @api.depends('state', 'is_overdue', 'pms_km_min', 'pms_km_max')
    def _compute_can_use(self):
        for record in self:
            # Can use if active and not overdue
            record.can_use = (
                record.state == 'active' and 
                not record.is_overdue
            )
    
    @api.model
    def create(self, vals):
        if vals.get('coupon_number', 'New') == 'New':
            vals['coupon_number'] = self.env['ir.sequence'].next_by_code('service.coupon') or 'SC-New'
        
        # Auto-populate FSC sequence based on coupon type
        if vals.get('coupon_type') and not vals.get('fsc_sequence'):
            type_map = {
                'pms_1': 'SC1',
                'pms_2': 'SC2', 
                'pms_3': 'SC3'
            }
            vals['fsc_sequence'] = type_map.get(vals['coupon_type'], 'SC')
        
        return super().create(vals)

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.coupon_number}"
            if record.coupon_type:
                type_display = dict(record._fields['coupon_type'].selection)[record.coupon_type]
                name += f" - {type_display}"
            if record.actual_service_date:
                name += f" (Used: {record.actual_service_date})"
            elif record.is_overdue:
                name += " (OVERDUE)"
            result.append((record.id, name))
        return result

    def action_use_coupon(self):
        """Open wizard to use the coupon"""
        self.ensure_one()
        
        if not self.can_use:
            if self.is_overdue:
                raise UserError("This coupon is overdue and cannot be used.")
            elif self.state != 'active':
                raise UserError("This coupon is not active and cannot be used.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Use Service Coupon',
            'res_model': 'service.coupon.use.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_coupon_id': self.id,
                'default_servicing_branch_id': self.servicing_branch_id.id,
                'default_fsc_sequence': self.fsc_sequence,
            }
        }

    def action_complete_service(self, service_data):
        """Complete the service with provided data"""
        self.ensure_one()
        
        vals = {
            'state': 'used',
            'servicing_branch_id': service_data.get('servicing_branch_id'),
            'fsc_code': service_data.get('fsc_code'),
            'actual_service_date': service_data.get('actual_service_date'),
            'accept_date': service_data.get('accept_date'),
            'mileage': service_data.get('mileage'),
            'service_notes': service_data.get('service_notes'),
        }
        
        self.write(vals)
        
        # Create next PMS coupon if this was PMS 1 or PMS 2
        self.create_next_pms_coupon(service_data)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success!',
                'message': f'Service coupon {self.coupon_number} has been used successfully.',
                'type': 'success',
            }
        }

    def create_next_pms_coupon(self, service_data):
        """Create next PMS coupon based on current PMS completion"""
        self.ensure_one()
        
        # Only create next coupon for PMS 1 and PMS 2
        if self.coupon_type not in ['pms_1', 'pms_2']:
            return
            
        # Determine next coupon type
        next_coupon_type = 'pms_2' if self.coupon_type == 'pms_1' else 'pms_3'
        
        # Check if next coupon already exists
        existing_next = self.search([
            ('wrc_record_id', '=', self.wrc_record_id.id),
            ('coupon_type', '=', next_coupon_type),
            ('state', 'in', ['active', 'used'])
        ])
        if existing_next:
            return  # Next coupon already exists
            
        # Calculate due date and mileage range based on current service
        actual_service_date = service_data.get('actual_service_date')
        current_mileage = service_data.get('mileage', 0)
        
        if next_coupon_type == 'pms_2':
            # PMS 2: Calculate based on PMS 1 completion
            due_date = actual_service_date + relativedelta(months=4) if actual_service_date else False  # 7-3=4 months from PMS 1
            pms_km_min = max(2001, current_mileage)
            pms_km_max = current_mileage + 4000  # Approximate 4000km range
            pms_months = 7
        else:  # PMS 3
            # PMS 3: Calculate based on PMS 2 completion  
            due_date = actual_service_date + relativedelta(months=5) if actual_service_date else False  # 12-7=5 months from PMS 2
            pms_km_min = max(6001, current_mileage)
            pms_km_max = current_mileage + 6000  # Approximate 6000km range
            pms_months = 12
            
        # Generate next coupon number
        base_coupon_number = self.coupon_number.replace('-PMS_1', '').replace('-PMS_2', '').replace('-PMS_3', '')
        next_coupon_number = f"{base_coupon_number}-{next_coupon_type.upper()}"
        
        # Create next PMS coupon
        self.env['service.coupon'].create({
            'coupon_number': next_coupon_number,
            'wrc_record_id': self.wrc_record_id.id,
            'coupon_type': next_coupon_type,
            'pms_km_min': pms_km_min,
            'pms_km_max': pms_km_max,
            'pms_months': pms_months,
            'due_date': due_date,
            'previous_pms_coupon_id': self.id,
            'is_pms_1_based': False,
            'state': 'active',
        })
        
        _logger.info(f"Created next PMS coupon {next_coupon_number} based on {self.coupon_number} completion")

    def action_reset_to_active(self):
        """Reset coupon to active state"""
        self.write({
            'state': 'active',
            'actual_service_date': False,
            'accept_date': False,
            'mileage': 0,
            'service_notes': False,
        })

    def action_disable(self):
        """Disable coupon"""
        self.write({'state': 'disabled'})

    @api.model
    def check_expired_coupons(self):
        """Cron job to auto-disable overdue coupons"""
        today = fields.Date.today()
        overdue_coupons = self.search([
            ('state', '=', 'active'),
            ('due_date', '<', today)
        ])
        # Auto-disable expired coupons
        overdue_coupons.write({'state': 'disabled'})
        
        # Log the auto-disabled coupons
        if overdue_coupons:
            _logger.info(f"Auto-disabled {len(overdue_coupons)} expired coupons")