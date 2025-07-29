# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ServicePerformed(models.Model):
    _name = 'service.performed'
    _description = 'Service Performed'
    _rec_name = 'name'
    _order = 'service_date desc'
    
    name = fields.Char(string='Service Reference', required=True, copy=False, readonly=True, default='New')
    
    pms_id = fields.Many2one('preventive.maintenance', string='PMS Reference', required=True, ondelete='cascade')
    
    wrc_record_id = fields.Many2one('wrc.record', string='WRC Record', related='pms_id.wrc_record_id', store=True, readonly=True)
    service_coupon_id = fields.Many2one('service.coupon', string='Registered Coupon Code', related='pms_id.service_coupon_id', store=True, readonly=True)
    servicing_branch_id = fields.Many2one('res.company', string='Servicing Branch', related='pms_id.servicing_branch_id', store=True, readonly=True)
    service_date = fields.Date(string='Actual Service Date', related='pms_id.service_date', store=True, readonly=True)
    mileage = fields.Float(string='Mileage (km)', related='pms_id.mileage', store=True, readonly=True)
    
    service_type = fields.Selection([
        ('oil_change', 'Oil Change'),
        ('brake_service', 'Brake Service'),
        ('tire_service', 'Tire Service'),
        ('engine_service', 'Engine Service'),
        ('electrical', 'Electrical Service'),
        ('transmission', 'Transmission Service'),
        ('general', 'General Maintenance'),
        ('repair', 'Repair'),
        ('other', 'Other')
    ], string='Service Type', required=True, default='general')
    
    service_description = fields.Text(string='Service Description', required=True)
    parts_replaced = fields.Text(string='Parts Replaced')
    mechanic_id = fields.Many2one('res.users', string='Mechanic')
    
    cost = fields.Float(string='Service Cost')
    labor_hours = fields.Float(string='Labor Hours')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True)
    
    notes = fields.Text(string='Additional Notes')
    warranty_period = fields.Integer(string='Warranty Period (Days)', default=30)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('service.performed') or 'SP-New'
        return super().create(vals)
    
    def action_start_service(self):
        """Start this specific service"""
        self.write({'state': 'in_progress'})
    
    def action_complete_service(self):
        """Complete this specific service"""
        self.write({'state': 'completed'})
    
    def action_cancel_service(self):
        """Cancel this specific service"""
        self.write({'state': 'cancelled'})
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name}"
            if record.service_type:
                name += f" - {dict(record._fields['service_type'].selection)[record.service_type]}"
            if record.service_date:
                name += f" ({record.service_date})"
            result.append((record.id, name))
        return result