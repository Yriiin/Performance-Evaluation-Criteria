# -*- coding: utf-8 -*-

from odoo import models, fields, api

class WRCServiceCoupon(models.Model):
    _name = 'wrc.service.coupon'
    _description = 'WRC Service Coupon'
    _rec_name = 'coupon_number'
    _order = 'create_date desc'
    
   
    coupon_number = fields.Char(string='Printable Unique Coupon Number', required=True, copy=False, readonly=True, default='New')
    wrc_record_id = fields.Many2one('wrc.record', string='WRC Record', required=True)
    
   
    pms_schedule_months = fields.Float(string='PMS Schedule (Months)')
    pms_schedule_days = fields.Integer(string='PMS Schedule (Days)')
    
    actual_service_date = fields.Date(string='Actual Service Date')
    mileage = fields.Float(string='Mileage (km)')
    
   
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('expired', 'Expired')
    ], string='Status', default='draft', required=True)

    customer_id = fields.Many2one('res.partner', string='Customer', related='wrc_record_id.partner_id', store=True, readonly=True)
    
    @api.model
    def create(self, vals):
        if vals.get('coupon_number', 'New') == 'New':
            vals['coupon_number'] = self.env['ir.sequence'].next_by_code('wrc.service.coupon') or 'WSC-New'
        return super().create(vals)
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.coupon_number}"
            if record.wrc_record_id:
                name += f" - {record.wrc_record_id.name}"
            result.append((record.id, name))
        return result