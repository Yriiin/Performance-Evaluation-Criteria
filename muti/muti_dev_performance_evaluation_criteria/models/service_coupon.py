# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ServiceCoupon(models.Model):
    _name = 'service.coupon'
    _description = 'Service Coupon'
    _rec_name = 'coupon_number'
    _order = 'create_date desc'
    
  
    coupon_number = fields.Char('Printable Coupon Number', required=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
    ], default='draft', string='Status')
    
    wrc_record_id = fields.Many2one('wrc.record', 'WRC Record', required=True, ondelete='cascade')
    servicing_branch_id = fields.Many2one('res.company', 'Servicing Branch')
    
   
    pms_schedule_months = fields.Float('PMS Schedule (Months)')
    pms_schedule_days = fields.Integer('PMS Schedule (Days)')
    actual_service_date = fields.Date('Actual Service Date')
    mileage = fields.Float('Mileage (km)', help='Mileage during PMS')
    notes = fields.Text('Service Notes')
    
    @api.model
    def create(self, vals):
        if not vals.get('coupon_number') or vals.get('coupon_number') == 'New':
            vals['coupon_number'] = self.env['ir.sequence'].next_by_code('service.coupon') or 'SC-New'
        return super().create(vals)
    
    def name_get(self):
        result = []
        for record in self:
            name = record.coupon_number
            if record.wrc_record_id:
                name += f" - {record.wrc_record_id.wrc_no}"
            if record.actual_service_date:
                name += f" ({record.actual_service_date})"
            result.append((record.id, name))
        return result
   
    def action_mark_completed(self):
        """Mark service as completed with today's date"""
        self.write({
            'actual_service_date': fields.Date.today(),
            'state': 'completed'
        })
    
    def action_schedule_service(self):
        """Mark coupon as scheduled"""
        self.write({'state': 'scheduled'})
    
    def action_reset_to_draft(self):
        """Reset coupon to draft state"""
        self.write({
            'state': 'draft',
            'actual_service_date': False
        })