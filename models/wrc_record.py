# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime

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
    
    # Customer Profile (Auto-filled, Read-only)
    customer_name = fields.Char('Customer Name', readonly=True)
    customer_address = fields.Text('Address', readonly=True)
    phone = fields.Char('Phone Number', readonly=True)
    email = fields.Char('Email', readonly=True)
    birthday = fields.Date('Birthday', readonly=True)
    age = fields.Integer('Age', compute='_compute_age', store=True)
    
    # Dealer Profile (Auto-filled, Read-only)
    selling_dealer = fields.Char('Selling Dealer', readonly=True)
    dealer_code = fields.Char('Dealer Code', readonly=True)
    dealer_address = fields.Text('Dealer Address', readonly=True)
    
    # Unit Info (Auto-filled where possible, editable if incomplete)
    model = fields.Char('Model', readonly=False)
    engine_no = fields.Char('Engine No.', readonly=False)
    frame_no = fields.Char('Frame No.', readonly=False)
    purchase_date = fields.Date('Date Purchased', readonly=True)
    color = fields.Char('Color', readonly=False)
    brand = fields.Selection([
        ('honda', 'Honda'),
        ('yamaha', 'Yamaha'),
        ('kawasaki', 'Kawasaki'),
        ('suzuki', 'Suzuki'),
        ('skygo', 'Skygo')
    ], string='Brand', readonly=True)
    payment_basis = fields.Selection([
        ('cash', 'Cash'),
        ('installment', 'Installment')
    ], string='Payment Basis', readonly=False)
    qty = fields.Float('Quantity', default=1.0, readonly=False)
    classification = fields.Selection([
        ('commuter', 'Commuter'),
        ('bigbike', 'BigBike')
    ], string='Classification', readonly=True)
    
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