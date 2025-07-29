# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime

class WrcRecord(models.Model):
    _name = 'wrc.record'
    _description = 'WRC Record'
    _rec_name = 'wrc_no'
    _order = 'create_date desc'
    
    wrc_no = fields.Char('WRC No.', required=True, copy=False, readonly=True, default='New')
    
    sale_order_id = fields.Many2one('sale.order', 'Sale Order', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Customer', required=True)
    branch_id = fields.Many2one('res.company', 'Branch')
    
    customer_address = fields.Text('Customer Address')
    birthdate = fields.Date('Birthdate')
    age = fields.Integer('Age', compute='_compute_age', store=True)
    sex = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Sex')
    contact_number = fields.Char('Contact #')
    
    dealers_code = fields.Char('Dealers Code')
    dealer = fields.Char('Dealer')
    dealer_address = fields.Text('Address of Dealer')
    
    engine_number = fields.Char('Engine Number', help='Enter the motorcycle engine number')
    frame_number = fields.Char('Frame Number', help='Enter the motorcycle frame number')
    model = fields.Char('Model')
    color = fields.Char('Color')
    date_of_purchase = fields.Date('Date of Purchase')
    
    coupon_codes = fields.Text('Service Coupon Codes', 
                               help='Service coupon codes provided with this motorcycle (one per line)')
    
    @api.depends('birthdate')
    def _compute_age(self):
        today = datetime.today().date()
        for record in self:
            if record.birthdate:
                record.age = today.year - record.birthdate.year - (
                    (today.month, today.day) < (record.birthdate.month, record.birthdate.day)
                )
            else:
                record.age = 0
    
    @api.model
    def create(self, vals):
        if vals.get('wrc_no', 'New') == 'New':
            vals['wrc_no'] = self.env['ir.sequence'].next_by_code('wrc.record') or 'WRC-New'
        return super().create(vals)