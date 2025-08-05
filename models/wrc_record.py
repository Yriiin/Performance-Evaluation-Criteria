# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta

class WrcRecord(models.Model):
    _name = 'wrc.record'
    _description = 'WRC Record'
    _rec_name = 'wrc_no'
    _order = 'create_date desc'
    
    # Basic Information
    wrc_no = fields.Char('WRC No.', required=True, copy=False, readonly=True, default='New')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], default='draft', string='Status')
    
    sale_order_id = fields.Many2one('sale.order', 'Sale Order', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Customer', required=True)
    branch_id = fields.Many2one('res.company', 'Branch')
    
    # Customer Profile (Auto-filled fields become readonly when populated)
    customer_name = fields.Char('Customer Name')
    customer_address = fields.Text('Address')
    phone = fields.Char('Phone Number')
    email = fields.Char('Email')
    birthday = fields.Date('Birthday')
    age = fields.Integer('Age', compute='_compute_age', store=True)
    
    # Dealer Profile (Auto-filled fields become readonly when populated)
    selling_dealer = fields.Char('Selling Dealer')
    dealer_code = fields.Char('Dealer Code')
    dealer_address = fields.Text('Dealer Address')
    
    # Unit Info (Auto-filled where possible, editable if incomplete)
    model = fields.Char('Model')
    engine_no = fields.Char('Engine No.')
    frame_no = fields.Char('Frame No.')
    purchase_date = fields.Date('Date Purchased')
    color = fields.Char('Color')
    brand = fields.Selection([
        ('honda', 'Honda'),
        ('yamaha', 'Yamaha'),
        ('kawasaki', 'Kawasaki'),
        ('suzuki', 'Suzuki'),
        ('skygo', 'Skygo')
    ], string='Brand')
    coupon_number = fields.Char('Coupon Number', help='User-inputted coupon number for service tracking')
    payment_basis = fields.Selection([
        ('cash', 'Cash'),
        ('installment', 'Installment')
    ], string='Payment Basis')
    qty = fields.Float('Quantity', default=1.0)
    classification = fields.Selection([
        ('commuter', 'Commuter'),
        ('bigbike', 'BigBike')
    ], string='Classification')
    
    # Service Coupons
    service_coupon_ids = fields.One2many('service.coupon', 'wrc_record_id', string='Service Coupons')
    coupon_count = fields.Integer('Coupon Count', compute='_compute_coupon_count')
    
    @api.depends('birthday')
    def _compute_age(self):
        today = datetime.today().date()
        for record in self:
            if record.birthday:
                record.age = today.year - record.birthday.year - (
                    (today.month, today.day) < (record.birthday.month, record.birthday.day)
                )
            else:
                record.age = 0

    @api.depends('service_coupon_ids')
    def _compute_coupon_count(self):
        for record in self:
            record.coupon_count = len(record.service_coupon_ids)
    
    @api.model
    def create(self, vals):
        if vals.get('wrc_no', 'New') == 'New':
            # Get brand from the values or from sale order
            brand = vals.get('brand')
            
            # If no brand in vals, try to get from sale_order_id
            if not brand and vals.get('sale_order_id'):
                sale_order = self.env['sale.order'].browse(vals.get('sale_order_id'))
                brand = sale_order.wrc_brand
            
            # Generate brand-specific WRC number
            if brand:
                brand_sequence_map = {
                    'honda': 'wrc.record.honda',
                    'yamaha': 'wrc.record.yamaha', 
                    'kawasaki': 'wrc.record.kawasaki',
                    'suzuki': 'wrc.record.suzuki',
                    'skygo': 'wrc.record.skygo'
                }
                sequence_code = brand_sequence_map.get(brand, 'wrc.record')
                vals['wrc_no'] = self.env['ir.sequence'].next_by_code(sequence_code) or f'{brand.upper()}WRC-New'
            else:
                # Fallback to generic sequence
                vals['wrc_no'] = self.env['ir.sequence'].next_by_code('wrc.record') or 'WRC-New'
                
        return super().create(vals)

    def action_confirm(self):
        """Confirm WRC record"""
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        """Cancel WRC record"""
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})

    def action_view_coupons(self):
        """View Service Coupons"""
        self.ensure_one()
        action = self.env.ref('muti_dev_performance_evaluation_criteria.action_service_coupon').read()[0]
        action['domain'] = [('wrc_record_id', '=', self.id)]
        action['context'] = {
            'default_wrc_record_id': self.id,
        }
        return action

    def create_honda_service_coupons(self):
        """Create service coupons for Honda motorcycles using user-inputted coupon number"""
        self.ensure_one()
        if self.brand != 'honda' or not self.coupon_number:
            return
        
        # Check if service coupons already exist
        existing_coupons = self.service_coupon_ids.filtered(lambda c: c.state != 'disabled')
        if existing_coupons:
            return  # Don't create duplicates
        
        # Honda PMS Schedule - all using the same coupon number
        pms_schedule = [
            {
                'coupon_type': 'pms_1',
                'pms_km_min': 500,
                'pms_km_max': 2000,
                'pms_months': 3,
            },
            {
                'coupon_type': 'pms_2', 
                'pms_km_min': 2001,
                'pms_km_max': 6000,
                'pms_months': 7,
            },
            {
                'coupon_type': 'pms_3',
                'pms_km_min': 6001,
                'pms_km_max': 12000,
                'pms_months': 12,
            }
        ]
        
        # Create service coupons
        for pms in pms_schedule:
            # Calculate due date based on purchase date and months
            due_date = False
            if self.purchase_date:
                due_date = self.purchase_date + relativedelta(months=pms['pms_months'])
            
            # Use the user-inputted coupon number with PMS suffix
            coupon_number = f"{self.coupon_number}-{pms['coupon_type'].upper()}"
            
            self.env['service.coupon'].create({
                'coupon_number': coupon_number,
                'wrc_record_id': self.id,
                'coupon_type': pms['coupon_type'],
                'pms_km_min': pms['pms_km_min'],
                'pms_km_max': pms['pms_km_max'],
                'pms_months': pms['pms_months'],
                'due_date': due_date,
                'state': 'active',
            })

    def write(self, vals):
        """Override write to create Honda service coupons when coupon number is added"""
        res = super().write(vals)
        
        # If coupon_number is being set for Honda, create service coupons
        if vals.get('coupon_number') and self.brand == 'honda':
            self.create_honda_service_coupons()
            
        return res