# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PreventiveMaintenance(models.Model):
    _name = 'preventive.maintenance'
    _description = 'Preventive Maintenance (PMS)'
    _rec_name = 'name'
    _order = 'service_date desc, create_date desc'
    
    name = fields.Char(string='PMS Reference', required=True, copy=False, readonly=True, default='New')
    
    wrc_record_id = fields.Many2one('wrc.record', string='WRC Record', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer', related='wrc_record_id.partner_id', store=True, readonly=True)
    
    service_coupon_id = fields.Many2one('service.coupon', string='Registered Coupon Code', 
                                        domain="[('wrc_record_id', '=', wrc_record_id), ('state', 'in', ['draft', 'scheduled'])]",
                                        required=True)
    servicing_branch_id = fields.Many2one('res.company', string='Servicing Branch', required=True)
    service_date = fields.Date(string='Actual Service Date', required=True, default=fields.Date.today)
    mileage = fields.Float(string='Mileage (km)', help='Mileage during PMS')
    
    service_description = fields.Text(string='Service Description', required=True)
    parts_replaced = fields.Text(string='Parts Replaced')
    mechanic_id = fields.Many2one('res.users', string='Mechanic')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True)
    
    service_performed_ids = fields.One2many('service.performed', 'pms_id', string='Services Performed')
    
    total_service_cost = fields.Float(string='Total Service Cost', compute='_compute_total_cost', store=True)
    service_count = fields.Integer(string='Service Count', compute='_compute_service_count')
    
    @api.depends('service_performed_ids', 'service_performed_ids.cost')
    def _compute_total_cost(self):
        for record in self:
            record.total_service_cost = sum(record.service_performed_ids.mapped('cost'))
    
    @api.depends('service_performed_ids')
    def _compute_service_count(self):
        for record in self:
            record.service_count = len(record.service_performed_ids)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('preventive.maintenance') or 'PMS-New'
        return super().create(vals)
    
    @api.onchange('wrc_record_id')
    def _onchange_wrc_record(self):
        """Update domain for service coupon when WRC record changes"""
        if self.wrc_record_id:
            return {
                'domain': {
                    'service_coupon_id': [('wrc_record_id', '=', self.wrc_record_id.id), ('state', 'in', ['draft', 'scheduled'])]
                }
            }
        else:
            return {
                'domain': {
                    'service_coupon_id': [('id', '=', False)]
                }
            }
    
    def action_start_service(self):
        """Start the PMS service"""
        self.write({'state': 'in_progress'})
        if self.service_coupon_id:
            self.service_coupon_id.write({'state': 'scheduled'})
    
    def action_complete_service(self):
        """Complete the PMS service"""
        self.write({'state': 'completed'})
        if self.service_coupon_id:
            self.service_coupon_id.write({
                'state': 'completed',
                'actual_service_date': self.service_date,
                'mileage': self.mileage
            })
    
    def action_cancel_service(self):
        """Cancel the PMS service"""
        self.write({'state': 'cancelled'})
        if self.service_coupon_id:
            self.service_coupon_id.write({'state': 'draft'})
    
    def action_reset_to_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})
        if self.service_coupon_id:
            self.service_coupon_id.write({'state': 'draft'})