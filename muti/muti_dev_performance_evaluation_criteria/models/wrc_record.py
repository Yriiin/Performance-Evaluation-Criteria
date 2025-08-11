# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta

class WrcRecord(models.Model):
    _name = 'wrc.record'
    _description = 'WRC Record'
    _rec_name = 'wrc_no'
    _order = 'create_date desc'
    
    # Basic Information
    wrc_no = fields.Char('WRC No.', required=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], default='draft', string='Status')
    
    sale_order_id = fields.Many2one('sale.order', 'Sale Order', ondelete='cascade', 
                                   domain="[('sale_type', '=', 'motorcycle')]")
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
    coupon_line_ids = fields.One2many('wrc.record.coupon.line', 'wrc_record_id', string='Coupon Registration Lines')
    coupon_count = fields.Integer('Coupon Count', compute='_compute_coupon_count')
    
    # Computed fields for readonly behavior
    is_confirmed = fields.Boolean('Is Confirmed', compute='_compute_is_confirmed')
    
    @api.depends('state')
    def _compute_is_confirmed(self):
        for record in self:
            record.is_confirmed = record.state == 'confirmed'
    
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
    
    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        """Auto-populate fields from selected sale order"""
        if self.sale_order_id:
            so = self.sale_order_id
            
            # Auto-populate customer information
            if so.partner_id:
                self.partner_id = so.partner_id
                self.customer_name = so.partner_id.name
                self.customer_address = so.partner_id.contact_address
                self.phone = so.partner_id.phone or so.partner_id.mobile
                self.email = so.partner_id.email
            
            # Auto-populate from WRC fields in sale order
            if hasattr(so, 'wrc_no') and so.wrc_no:
                self.wrc_no = so.wrc_no
            if hasattr(so, 'wrc_model') and so.wrc_model:
                self.model = so.wrc_model
            if hasattr(so, 'wrc_engine') and so.wrc_engine:
                self.engine_no = so.wrc_engine
            if hasattr(so, 'wrc_frame') and so.wrc_frame:
                self.frame_no = so.wrc_frame
            if hasattr(so, 'wrc_purchase_date') and so.wrc_purchase_date:
                self.purchase_date = so.wrc_purchase_date
            if hasattr(so, 'wrc_color') and so.wrc_color:
                self.color = so.wrc_color
            if hasattr(so, 'wrc_brand') and so.wrc_brand:
                self.brand = so.wrc_brand
            if hasattr(so, 'wrc_classification') and so.wrc_classification:
                self.classification = so.wrc_classification
            if hasattr(so, 'wrc_payment_basis') and so.wrc_payment_basis:
                self.payment_basis = so.wrc_payment_basis
            if hasattr(so, 'wrc_qty') and so.wrc_qty:
                self.qty = so.wrc_qty
            if hasattr(so, 'wrc_coupon_number') and so.wrc_coupon_number:
                self.coupon_number = so.wrc_coupon_number
                
            # Auto-populate coupon lines from sale order
            if hasattr(so, 'wrc_coupon_line_ids') and so.wrc_coupon_line_ids:
                coupon_lines = []
                for line in so.wrc_coupon_line_ids:
                    coupon_lines.append((0, 0, {
                        'coupon_number': line.coupon_number,
                        'coupon_type': line.coupon_type,
                        'pms_km_min': line.pms_km_min,
                        'pms_km_max': line.pms_km_max,
                        'pms_months': line.pms_months,
                        'notes': line.notes,
                    }))
                self.coupon_line_ids = coupon_lines
    
    @api.model
    def create(self, vals):
        # Only auto-generate WRC number if not provided
        if not vals.get('wrc_no'):
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
        """Confirm WRC record - validate all required fields are filled"""
        self.ensure_one()
        
        # Validate required fields
        missing_fields = []
        
        # Check customer information
        if not self.customer_name:
            missing_fields.append('Customer Name')
        if not self.phone:
            missing_fields.append('Phone Number')
            
        # Check unit information
        if not self.model:
            missing_fields.append('Model')
        if not self.engine_no:
            missing_fields.append('Engine No.')
        if not self.frame_no:
            missing_fields.append('Frame No.')
        if not self.brand:
            missing_fields.append('Brand')
        if not self.classification:
            missing_fields.append('Classification')
        if not self.purchase_date:
            missing_fields.append('Purchase Date')
            
        if missing_fields:
            raise UserError(f"Please fill in the following required fields before confirming: {', '.join(missing_fields)}")
        
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


class WrcRecordCouponLine(models.Model):
    _name = 'wrc.record.coupon.line'
    _description = 'WRC Record Coupon Registration Line'
    _rec_name = 'coupon_number'
    
    wrc_record_id = fields.Many2one('wrc.record', 'WRC Record', required=True, ondelete='cascade')
    coupon_number = fields.Char('Coupon Number', required=True)
    coupon_type = fields.Selection([
        ('pms_1', 'PMS 1 (500-2,000 km / 3 months)'),
        ('pms_2', 'PMS 2 (2,001-6,000 km / 7 months)'),
        ('pms_3', 'PMS 3 (6,001-12,000 km / 12 months)'),
    ], string='Coupon Type', required=True)
    pms_km_min = fields.Integer('Min KM')
    pms_km_max = fields.Integer('Max KM')
    pms_months = fields.Integer('Months Schedule')
    notes = fields.Text('Notes')
    
    @api.onchange('coupon_type')
    def _onchange_coupon_type(self):
        """Auto-populate KM and months based on coupon type"""
        if self.coupon_type == 'pms_1':
            self.pms_km_min = 500
            self.pms_km_max = 2000
            self.pms_months = 3
        elif self.coupon_type == 'pms_2':
            self.pms_km_min = 2001
            self.pms_km_max = 6000
            self.pms_months = 7
        elif self.coupon_type == 'pms_3':
            self.pms_km_min = 6001
            self.pms_km_max = 12000
            self.pms_months = 12