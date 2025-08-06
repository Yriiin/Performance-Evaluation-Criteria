# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta

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
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success!',
                'message': f'Service coupon {self.coupon_number} has been used successfully.',
                'type': 'success',
            }
        }

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
        """Cron job to mark overdue coupons as expired"""
        today = fields.Date.today()
        overdue_coupons = self.search([
            ('state', '=', 'active'),
            ('due_date', '<', today)
        ])
        overdue_coupons.write({'state': 'expired'})