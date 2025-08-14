# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class WrcRecord(models.Model):
    _name = 'wrc.record'
    _description = 'WRC Record'
    _rec_name = 'wrc_no'
    _order = 'create_date desc'
    
    # Basic Information
    wrc_no = fields.Char('WRC No.', copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], default='draft', string='Status')
    
    sale_order_id = fields.Many2one('sale.order', 'Sale Order', ondelete='cascade', 
                                   domain="[('awb_sale_type', '=', 'mc')]")
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
    
    @api.model
    def _get_available_sale_orders_domain(self):
        """Get domain for sale orders that don't have WRC records yet"""
        # Find sale orders that already have WRC records
        existing_wrc_sale_orders = self.search([]).mapped('sale_order_id').ids
        
        domain = [
            ('awb_sale_type', '=', 'mc'),  # Only motorcycle sales
            ('state', 'in', ['sale', 'done']),  # Only confirmed orders
        ]
        
        # Exclude sale orders that already have WRC records
        if existing_wrc_sale_orders:
            domain.append(('id', 'not in', existing_wrc_sale_orders))
            
        return domain
    
    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        """DISABLED: Auto-populate fields from selected sale order - Use manual refresh button instead"""
        # COMPLETELY DISABLED to prevent data loss during save operations
        # Users should use the "Refresh All Fields from Sale Order" button instead
        _logger.info(f"WRC Record: onchange triggered but disabled - use manual refresh button instead")
        return
    
    def _manual_auto_fill_from_sale_order(self):
        """Manual auto-fill method that prioritizes WRC tab fields from sale order"""
        if not self.sale_order_id:
            return
            
        so = self.sale_order_id
        _logger.info(f"WRC Record Manual Auto-fill: Processing sale order {so.name}")
        
        # PRIORITY 1: Use WRC Tab fields from Sale Order (these are the main data source)
        _logger.info(f"WRC Record: Checking WRC tab fields from sale order {so.name}")
        
        # Customer Information from WRC Tab
        if hasattr(so, 'wrc_customer_name') and so.wrc_customer_name and not self.customer_name:
            self.customer_name = so.wrc_customer_name
            _logger.info(f"WRC Record: Set customer name from WRC tab: {so.wrc_customer_name}")
        
        if hasattr(so, 'wrc_address') and so.wrc_address and not self.customer_address:
            self.customer_address = so.wrc_address
            _logger.info(f"WRC Record: Set address from WRC tab")
            
        if hasattr(so, 'wrc_phone') and so.wrc_phone and not self.phone:
            self.phone = so.wrc_phone
            _logger.info(f"WRC Record: Set phone from WRC tab: {so.wrc_phone}")
            
        if hasattr(so, 'wrc_email') and so.wrc_email and not self.email:
            self.email = so.wrc_email
            _logger.info(f"WRC Record: Set email from WRC tab: {so.wrc_email}")
            
        if hasattr(so, 'wrc_birthday') and so.wrc_birthday and not self.birthday:
            self.birthday = so.wrc_birthday
            _logger.info(f"WRC Record: Set birthday from WRC tab: {so.wrc_birthday}")
        
        # Unit Information from WRC Tab
        if hasattr(so, 'wrc_model') and so.wrc_model and not self.model:
            self.model = so.wrc_model
            _logger.info(f"WRC Record: Set model from WRC tab: {so.wrc_model}")
            
        if hasattr(so, 'wrc_engine') and so.wrc_engine and not self.engine_no:
            self.engine_no = so.wrc_engine
            _logger.info(f"WRC Record: Set engine from WRC tab: {so.wrc_engine}")
            
        if hasattr(so, 'wrc_frame') and so.wrc_frame and not self.frame_no:
            self.frame_no = so.wrc_frame
            _logger.info(f"WRC Record: Set frame from WRC tab: {so.wrc_frame}")
            
        if hasattr(so, 'wrc_color') and so.wrc_color and not self.color:
            self.color = so.wrc_color
            _logger.info(f"WRC Record: Set color from WRC tab: {so.wrc_color}")
            
        if hasattr(so, 'wrc_brand') and so.wrc_brand and not self.brand:
            self.brand = so.wrc_brand
            _logger.info(f"WRC Record: Set brand from WRC tab: {so.wrc_brand}")
            
        if hasattr(so, 'wrc_classification') and so.wrc_classification and not self.classification:
            self.classification = so.wrc_classification
            _logger.info(f"WRC Record: Set classification from WRC tab: {so.wrc_classification}")
            
        if hasattr(so, 'wrc_payment_basis') and so.wrc_payment_basis and not self.payment_basis:
            self.payment_basis = so.wrc_payment_basis
            _logger.info(f"WRC Record: Set payment basis from WRC tab: {so.wrc_payment_basis}")
            
        if hasattr(so, 'wrc_qty') and so.wrc_qty and (not self.qty or self.qty == 1.0):
            self.qty = so.wrc_qty
            _logger.info(f"WRC Record: Set quantity from WRC tab: {so.wrc_qty}")
            
        if hasattr(so, 'wrc_purchase_date') and so.wrc_purchase_date and not self.purchase_date:
            self.purchase_date = so.wrc_purchase_date
            _logger.info(f"WRC Record: Set purchase date from WRC tab: {so.wrc_purchase_date}")
        
        # Dealer Information from WRC Tab
        if hasattr(so, 'wrc_selling_dealer') and so.wrc_selling_dealer and not self.selling_dealer:
            self.selling_dealer = so.wrc_selling_dealer
            _logger.info(f"WRC Record: Set selling dealer from WRC tab: {so.wrc_selling_dealer}")
            
        if hasattr(so, 'wrc_dealer_code') and so.wrc_dealer_code and not self.dealer_code:
            self.dealer_code = so.wrc_dealer_code
            _logger.info(f"WRC Record: Set dealer code from WRC tab: {so.wrc_dealer_code}")
            
        if hasattr(so, 'wrc_dealer_address') and so.wrc_dealer_address and not self.dealer_address:
            self.dealer_address = so.wrc_dealer_address
            _logger.info(f"WRC Record: Set dealer address from WRC tab")
        
        # Set partner_id to match the sale order partner
        if so.partner_id and not self.partner_id:
            self.partner_id = so.partner_id
            _logger.info(f"WRC Record: Set partner from sale order: {so.partner_id.name}")
        
        # PRIORITY 2: Fallback to partner data if WRC tab fields are empty
        if not self.customer_name and so.partner_id:
            self.customer_name = so.partner_id.name
            _logger.info(f"WRC Record: Fallback - Set customer name from partner: {so.partner_id.name}")
            
        if not self.phone and so.partner_id:
            self.phone = so.partner_id.phone or so.partner_id.mobile
            if self.phone:
                _logger.info(f"WRC Record: Fallback - Set phone from partner: {self.phone}")
                
        if not self.email and so.partner_id:
            self.email = so.partner_id.email
            if self.email:
                _logger.info(f"WRC Record: Fallback - Set email from partner: {self.email}")
        
        # Set default quantity if still empty
        if not self.qty or self.qty == 0:
            self.qty = 1.0
        
        # Set purchase date from order date if not set
        if not self.purchase_date and so.date_order:
            self.purchase_date = so.date_order.date()
            _logger.info(f"WRC Record: Set purchase date from order date: {self.purchase_date}")
        
        # Log what was populated
        populated_fields = []
        if self.customer_name:
            populated_fields.append('Customer Name')
        if self.model:
            populated_fields.append('Model')
        if self.engine_no:
            populated_fields.append('Engine No.')
        if self.frame_no:
            populated_fields.append('Frame No.')
        if self.brand:
            populated_fields.append('Brand')
        if self.color:
            populated_fields.append('Color')
        if self.phone:
            populated_fields.append('Phone')
        if self.email:
            populated_fields.append('Email')
            
        _logger.info(f"WRC Record Auto-fill: Populated {len(populated_fields)} fields: {', '.join(populated_fields)}")
    
    def _check_required_fields_filled(self):
        """Check if all required fields are filled for confirmation"""
        required_fields = [
            self.customer_name, self.phone, self.model, 
            self.engine_no, self.frame_no, self.brand, 
            self.classification, self.purchase_date
        ]
        return all(field for field in required_fields)

    def action_confirm(self):
        """Confirm WRC record - validate all required fields are filled"""
        self.ensure_one()
                if so.partner_id.state_id:
                    address_parts.append(so.partner_id.state_id.name)
                if so.partner_id.zip:
                    address_parts.append(so.partner_id.zip)
                if so.partner_id.country_id:
                    address_parts.append(so.partner_id.country_id.name)
                
                self.customer_address = ', '.join(address_parts)
            
            # Set customer contact information - only if empty
            if not self.phone:
                if so.partner_id.phone:
                    self.phone = so.partner_id.phone
                elif so.partner_id.mobile:
                    self.phone = so.partner_id.mobile
                    
            if not self.email and so.partner_id.email:
                self.email = so.partner_id.email
        
        # Get motorcycle product from order line
        mc_line = so.order_line.filtered(lambda l: so._is_mc_product(l.product_id))
        if mc_line:
            mc_product = mc_line[0].product_id
            
            # Extract MODEL from product name - only if empty
            if mc_product and mc_product.name and not self.model:
                import re
                model_name = mc_product.name
                # Remove text inside brackets [...]
                model_name = re.sub(r'\[.*?\]', '', model_name)
                # Remove text inside parentheses (...)
                model_name = re.sub(r'\(.*?\)', '', model_name)
                # Clean up extra spaces and strip
                model_name = ' '.join(model_name.split()).strip()
                self.model = model_name
                _logger.info(f"WRC Record Auto-fill: Extracted model '{model_name}' from product name")
            
            # Extract BRAND from product internal reference (first 2 chars) - only if empty
            brand = False
            if mc_product and mc_product.default_code and len(mc_product.default_code) >= 2 and not self.brand:
                code = mc_product.default_code[:2].upper()
                brand_map = {
                    'HO': 'honda',
                    'YA': 'yamaha', 
                    'KA': 'kawasaki',
                    'SU': 'suzuki',
                    'SK': 'skygo'
                }
                brand = brand_map.get(code, False)
                if brand:
                    self.brand = brand
                    _logger.info(f"WRC Record Auto-fill: Set brand to {brand} from product code")
            
            # Set QUANTITY from sale order line - only if empty/zero
            if not self.qty or self.qty == 0:
                self.qty = mc_line[0].product_uom_qty
            
            # Find stock lot information for ENGINE and FRAME numbers
            pickings = self.env['stock.picking'].search([('origin', '=', so.name)])
            lot_info = None
            
            for picking in pickings:
                for move in picking.move_lines:
                    if move.product_id == mc_product:
                        # Get lot info from picking move
                        if hasattr(move, 'lot_ids') and move.lot_ids:
                            lot_info = move.lot_ids[0]
                        elif hasattr(move, 'move_line_ids'):
                            for move_line in move.move_line_ids:
                                if move_line.lot_id:
                                    lot_info = move_line.lot_id
                                    break
                        break
                if lot_info:
                    break
            
            # If no lot found through picking, search directly by product
            if not lot_info and mc_product:
                lots = self.env['stock.production.lot'].search([
                    ('product_id', '=', mc_product.id)
                ], limit=1)
                if lots:
                    lot_info = lots[0]
            
            # Extract ENGINE NUMBER from stock lot - only if empty
            if lot_info and not self.engine_no:
                if hasattr(lot_info, 'name'):  # Default lot name field
                    self.engine_no = lot_info.name
                elif hasattr(lot_info, 'engine_no'):
                    self.engine_no = lot_info.engine_no
                elif hasattr(lot_info, 'x_studio_engine_no'):
                    self.engine_no = lot_info.x_studio_engine_no
                    
                # Extract CHASSIS/FRAME NUMBER from stock lot - only if empty
                if lot_info and not self.frame_no:
                    if hasattr(lot_info, 'chasis_number'):
                        self.frame_no = lot_info.chasis_number
                    elif hasattr(lot_info, 'chassis_number'):
                        self.frame_no = lot_info.chassis_number
                    elif hasattr(lot_info, 'x_studio_chassis_no'):
                        self.frame_no = lot_info.x_studio_chassis_no
                    elif hasattr(lot_info, 'frame_no'):
                        self.frame_no = lot_info.frame_no
                    
                # Extract COLOR from stock lot - only if empty
                if lot_info and not self.color:
                    if hasattr(lot_info, 'color'):
                        self.color = lot_info.color
                        _logger.info(f"WRC Record Auto-fill: Set color from stock lot: {lot_info.color}")
                    elif hasattr(lot_info, 'x_studio_color'):
                        self.color = lot_info.x_studio_color
                        _logger.info(f"WRC Record Auto-fill: Set color from stock lot x_studio_color: {lot_info.x_studio_color}")
                    
                # Get brand from lot if not found in product - only if empty
                if lot_info and not brand and not self.brand and hasattr(lot_info, 'x_studio_brand'):
                    self.brand = lot_info.x_studio_brand
            
            # 4. Copy WRC Information tab fields (these should always be transferred if they exist)
            _logger.info(f"WRC Record Auto-fill: Checking WRC tab fields from sale order {so.name}")
            
            # Always transfer WRC tab fields if they exist and current field is empty
            if hasattr(so, 'wrc_color') and so.wrc_color and not self.color:
                wrc_color_value = so.wrc_color
                if str(wrc_color_value).strip():
                    self.color = str(wrc_color_value).strip()
                    _logger.info(f"WRC Record Auto-fill: Set color from WRC tab: '{self.color}'")
            
            if hasattr(so, 'wrc_engine') and so.wrc_engine and not self.engine_no:
                self.engine_no = so.wrc_engine
                _logger.info(f"WRC Record Auto-fill: Set engine from WRC tab: {so.wrc_engine}")
            
            if hasattr(so, 'wrc_frame') and so.wrc_frame and not self.frame_no:
                self.frame_no = so.wrc_frame
                _logger.info(f"WRC Record Auto-fill: Set frame from WRC tab: {so.wrc_frame}")
            
            # Copy classification from WRC tab if available and current field is empty
            if hasattr(so, 'wrc_classification') and so.wrc_classification and not self.classification:
                self.classification = so.wrc_classification
                _logger.info(f"WRC Record Auto-fill: Set classification from WRC tab: {so.wrc_classification}")
            
            # Copy other WRC tab fields that might be available (only if current fields are empty)
            if hasattr(so, 'wrc_model') and so.wrc_model and not self.model:
                self.model = so.wrc_model
                _logger.info(f"WRC Record Auto-fill: Set model from WRC tab: {so.wrc_model}")
            
            if hasattr(so, 'wrc_brand') and so.wrc_brand and not self.brand:
                self.brand = so.wrc_brand
                _logger.info(f"WRC Record Auto-fill: Set brand from WRC tab: {so.wrc_brand}")
            
            if hasattr(so, 'wrc_payment_basis') and so.wrc_payment_basis and not self.payment_basis:
                self.payment_basis = so.wrc_payment_basis
                _logger.info(f"WRC Record Auto-fill: Set payment basis from WRC tab: {so.wrc_payment_basis}")
            
            if hasattr(so, 'wrc_qty') and so.wrc_qty and (not self.qty or self.qty == 0):
                self.qty = so.wrc_qty
                _logger.info(f"WRC Record Auto-fill: Set quantity from WRC tab: {so.wrc_qty}")
            
            if hasattr(so, 'wrc_purchase_date') and so.wrc_purchase_date and not self.purchase_date:
                self.purchase_date = so.wrc_purchase_date
                _logger.info(f"WRC Record Auto-fill: Set purchase date from WRC tab: {so.wrc_purchase_date}")
            
            # Final color status log
            if not self.color:
                _logger.info("WRC Record Auto-fill: No color found - user can manually input")
            else:
                _logger.info(f"WRC Record Auto-fill: Final color value: '{self.color}'")
            
            # 5. Set PAYMENT BASIS from payment terms (only if not set from WRC tab)
            if not self.payment_basis and so.payment_term_id:
                payment_term_name = so.payment_term_id.name.lower()
                if 'cash' in payment_term_name or 'immediate' in payment_term_name:
                    self.payment_basis = 'cash'
                elif 'installment' in payment_term_name or 'term' in payment_term_name or 'credit' in payment_term_name:
                    self.payment_basis = 'installment'
                else:
                    # Default based on payment term characteristics
                    if so.payment_term_id.line_ids and len(so.payment_term_id.line_ids) > 1:
                        self.payment_basis = 'installment'  # Multiple payment lines suggest installment
                    else:
                        self.payment_basis = 'cash'  # Single payment line suggests cash
            elif not self.payment_basis:
                self.payment_basis = 'cash'  # Default to cash if no payment term and no WRC tab value
            
            # 6. Set PURCHASE DATE from order date (only if not set from WRC tab)
            if not self.purchase_date and so.date_order:
                self.purchase_date = so.date_order.date()
            
            # 7. Set DEALER INFORMATION from company (only if fields are empty)
            if so.company_id:
                if not self.selling_dealer:
                    self.selling_dealer = so.company_id.name
                
                # Generate dealer code (only if empty)
                if not self.dealer_code:
                    if hasattr(so.company_id, 'partner_id') and so.company_id.partner_id.ref:
                        self.dealer_code = so.company_id.partner_id.ref
                    else:
                        # Generate a simple dealer code based on company name
                        company_name = so.company_id.name.upper()
                        dealer_code = ''.join(word[:2] for word in company_name.split()[:2])
                        self.dealer_code = dealer_code
                
                # Build dealer address from company address (only if empty)
                if not self.dealer_address:
                    address_parts = []
                    if so.company_id.street:
                        address_parts.append(so.company_id.street)
                    if so.company_id.street2:
                        address_parts.append(so.company_id.street2)
                    if so.company_id.city:
                        address_parts.append(so.company_id.city)
                    if so.company_id.state_id:
                        address_parts.append(so.company_id.state_id.name)
                    if so.company_id.zip:
                        address_parts.append(so.company_id.zip)
                    if so.company_id.country_id:
                        address_parts.append(so.company_id.country_id.name)
                    
                    self.dealer_address = ', '.join(address_parts)
            
            # Note: Classification is now user-selectable, not auto-calculated
            
            # 8. Copy WRC number if it exists (only if empty)
            if hasattr(so, 'wrc_no') and so.wrc_no and not self.wrc_no:
                self.wrc_no = so.wrc_no
            
            # Log populated fields for feedback
            populated_fields = []
            if self.model:
                populated_fields.append('Model')
            if self.engine_no:
                populated_fields.append('Engine No.')
            if self.frame_no:
                populated_fields.append('Frame No.')
            if self.brand:
                populated_fields.append('Brand')
            if self.customer_name:
                populated_fields.append('Customer')
            if self.dealer_code:
                populated_fields.append('Dealer')
            
            _logger.info(f"WRC Record Auto-fill: Populated {len(populated_fields)} fields: {', '.join(populated_fields)}")
            
            if populated_fields:
                return {
                    'warning': {
                        'title': 'Auto-Fill Complete',
                        'message': f'Successfully populated {len(populated_fields)} fields from sale order data: {", ".join(populated_fields)}'
                    }
                }
            
            # Customer Profile Fields
            customer_name_val = getattr(so, 'wrc_customer_name', None)
            if customer_name_val:
                self.customer_name = customer_name_val
            elif so.partner_id:
                self.customer_name = so.partner_id.name
                
            address_val = getattr(so, 'wrc_address', None)
            if address_val:
                self.customer_address = address_val
            elif so.partner_id:
                self.customer_address = so.partner_id.contact_address
                
            phone_val = getattr(so, 'wrc_phone', None)
            if phone_val:
                self.phone = phone_val
            elif so.partner_id:
                self.phone = so.partner_id.phone or so.partner_id.mobile
                
            email_val = getattr(so, 'wrc_email', None)
            if email_val:
                self.email = email_val
            elif so.partner_id:
                self.email = so.partner_id.email
                
            birthday_val = getattr(so, 'wrc_birthday', None)
            if birthday_val:
                self.birthday = birthday_val

            # Dealer Profile Fields
            selling_dealer_val = getattr(so, 'wrc_selling_dealer', None)
            if selling_dealer_val:
                self.selling_dealer = selling_dealer_val
                
            dealer_code_val = getattr(so, 'wrc_dealer_code', None)
            if dealer_code_val:
                self.dealer_code = dealer_code_val
                
            dealer_address_val = getattr(so, 'wrc_dealer_address', None)
            if dealer_address_val:
                self.dealer_address = dealer_address_val
            
            # Set branch to sale order company
            if so.company_id:
                self.branch_id = so.company_id
                
            # Auto-populate coupon lines from sale order
            coupon_line_ids = getattr(so, 'wrc_coupon_line_ids', False)
            if coupon_line_ids:
                coupon_lines = []
                for line in coupon_line_ids:
                    coupon_lines.append((0, 0, {
                        'coupon_number': line.coupon_number,
                        'coupon_type': line.coupon_type,
                        'pms_km_min': line.pms_km_min,
                        'pms_km_max': line.pms_km_max,
                        'pms_months': line.pms_months,
                        'notes': line.notes,
                    }))
                self.coupon_line_ids = coupon_lines
                _logger.info(f"WRC Record Auto-fill: Added {len(coupon_line_ids)} coupon lines")
        else:
            # Clear fields when no sale order is selected
            _logger.info("WRC Record Auto-fill: Clearing fields - no sale order selected")
            self.partner_id = False
            self.customer_name = ''
            self.customer_address = ''
            self.phone = ''
            self.email = ''
            self.birthday = False
            self.selling_dealer = ''
            self.dealer_code = ''
            self.dealer_address = ''
            self.model = ''
            self.engine_no = ''
            self.frame_no = ''
            self.purchase_date = False
            self.color = ''
            self.brand = False
            self.classification = False
            self.payment_basis = False
            self.qty = 1.0
            self.coupon_number = ''
            self.branch_id = False
            self.coupon_line_ids = [(5, 0, 0)]  # Clear all coupon lines
    
    def _manual_auto_fill_from_sale_order(self):
        """Manual auto-fill method that doesn't trigger onchange issues"""
        if not self.sale_order_id:
            return
            
        so = self.sale_order_id
        _logger.info(f"WRC Record Manual Auto-fill: Processing sale order {so.name}")
        
        # Auto-populate customer information (always overwrite for manual action)
        if so.partner_id:
            self.partner_id = so.partner_id
            self.customer_name = so.partner_id.name
            
            # Build customer address from partner
            address_parts = []
            if so.partner_id.street:
                address_parts.append(so.partner_id.street)
            if so.partner_id.street2:
                address_parts.append(so.partner_id.street2)
            if so.partner_id.city:
                address_parts.append(so.partner_id.city)
            if so.partner_id.state_id:
                address_parts.append(so.partner_id.state_id.name)
            if so.partner_id.zip:
                address_parts.append(so.partner_id.zip)
            if so.partner_id.country_id:
                address_parts.append(so.partner_id.country_id.name)
            
            self.customer_address = ', '.join(address_parts)
            
            # Set customer contact information
            if so.partner_id.phone:
                self.phone = so.partner_id.phone
            elif so.partner_id.mobile:
                self.phone = so.partner_id.mobile
                
            if so.partner_id.email:
                self.email = so.partner_id.email
        
        # Get motorcycle product from order line
        mc_line = so.order_line.filtered(lambda l: so._is_mc_product(l.product_id))
        if mc_line:
            mc_product = mc_line[0].product_id
            
            # Extract MODEL from product name
            if mc_product and mc_product.name:
                import re
                model_name = mc_product.name
                model_name = re.sub(r'\[.*?\]', '', model_name)
                model_name = re.sub(r'\(.*?\)', '', model_name)
                model_name = ' '.join(model_name.split()).strip()
                self.model = model_name
            
            # Extract BRAND from product internal reference
            if mc_product and mc_product.default_code and len(mc_product.default_code) >= 2:
                code = mc_product.default_code[:2].upper()
                brand_map = {
                    'HO': 'honda',
                    'YA': 'yamaha', 
                    'KA': 'kawasaki',
                    'SU': 'suzuki',
                    'SK': 'skygo'
                }
                brand = brand_map.get(code, False)
                if brand:
                    self.brand = brand
            
            # Set QUANTITY from sale order line
            self.qty = mc_line[0].product_uom_qty
            
            # Extract stock lot information
            pickings = self.env['stock.picking'].search([('origin', '=', so.name)])
            lot_info = None
            
            for picking in pickings:
                for move in picking.move_lines:
                    if move.product_id == mc_product:
                        if hasattr(move, 'lot_ids') and move.lot_ids:
                            lot_info = move.lot_ids[0]
                        elif hasattr(move, 'move_line_ids'):
                            for move_line in move.move_line_ids:
                                if move_line.lot_id:
                                    lot_info = move_line.lot_id
                                    break
                        break
                if lot_info:
                    break
            
            if not lot_info and mc_product:
                lots = self.env['stock.production.lot'].search([
                    ('product_id', '=', mc_product.id)
                ], limit=1)
                if lots:
                    lot_info = lots[0]
            
            # Extract data from stock lot
            if lot_info:
                if hasattr(lot_info, 'name'):
                    self.engine_no = lot_info.name
                elif hasattr(lot_info, 'engine_no'):
                    self.engine_no = lot_info.engine_no
                elif hasattr(lot_info, 'x_studio_engine_no'):
                    self.engine_no = lot_info.x_studio_engine_no
                
                if hasattr(lot_info, 'chasis_number'):
                    self.frame_no = lot_info.chasis_number
                elif hasattr(lot_info, 'chassis_number'):
                    self.frame_no = lot_info.chassis_number
                elif hasattr(lot_info, 'x_studio_chassis_no'):
                    self.frame_no = lot_info.x_studio_chassis_no
                elif hasattr(lot_info, 'frame_no'):
                    self.frame_no = lot_info.frame_no
                
                if hasattr(lot_info, 'color'):
                    self.color = lot_info.color
                elif hasattr(lot_info, 'x_studio_color'):
                    self.color = lot_info.x_studio_color
        
        # Copy WRC Information tab fields if they exist
        if hasattr(so, 'wrc_color') and so.wrc_color:
            self.color = so.wrc_color
        if hasattr(so, 'wrc_engine') and so.wrc_engine:
            self.engine_no = so.wrc_engine
        if hasattr(so, 'wrc_frame') and so.wrc_frame:
            self.frame_no = so.wrc_frame
        if hasattr(so, 'wrc_classification') and so.wrc_classification:
            self.classification = so.wrc_classification
        if hasattr(so, 'wrc_model') and so.wrc_model:
            self.model = so.wrc_model
        if hasattr(so, 'wrc_brand') and so.wrc_brand:
            self.brand = so.wrc_brand
        if hasattr(so, 'wrc_payment_basis') and so.wrc_payment_basis:
            self.payment_basis = so.wrc_payment_basis
        if hasattr(so, 'wrc_qty') and so.wrc_qty:
            self.qty = so.wrc_qty
        if hasattr(so, 'wrc_purchase_date') and so.wrc_purchase_date:
            self.purchase_date = so.wrc_purchase_date
        
        # Set payment basis from payment terms
        if so.payment_term_id and not self.payment_basis:
            payment_term_name = so.payment_term_id.name.lower()
            if 'cash' in payment_term_name or 'immediate' in payment_term_name:
                self.payment_basis = 'cash'
            elif 'installment' in payment_term_name or 'term' in payment_term_name:
                self.payment_basis = 'installment'
            else:
                self.payment_basis = 'cash'
        
        # Set purchase date from order date
        if so.date_order and not self.purchase_date:
            self.purchase_date = so.date_order.date()
        
        # Set dealer information
        if so.company_id:
            self.selling_dealer = so.company_id.name
            
            if hasattr(so.company_id, 'partner_id') and so.company_id.partner_id.ref:
                self.dealer_code = so.company_id.partner_id.ref
            else:
                company_name = so.company_id.name.upper()
                dealer_code = ''.join(word[:2] for word in company_name.split()[:2])
                self.dealer_code = dealer_code
            
            address_parts = []
            if so.company_id.street:
                address_parts.append(so.company_id.street)
            if so.company_id.street2:
                address_parts.append(so.company_id.street2)
            if so.company_id.city:
                address_parts.append(so.company_id.city)
            if so.company_id.state_id:
                address_parts.append(so.company_id.state_id.name)
            if so.company_id.zip:
                address_parts.append(so.company_id.zip)
            if so.company_id.country_id:
                address_parts.append(so.company_id.country_id.name)
            
            self.dealer_address = ', '.join(address_parts)
        
        # Copy WRC number if it exists
        if hasattr(so, 'wrc_no') and so.wrc_no:
            self.wrc_no = so.wrc_no

    def action_auto_fill_from_sale_order(self):
        """Manual action to auto-fill fields from sale order - just fills form, doesn't save"""
        self.ensure_one()
        if self.sale_order_id:
            # Use a separate method to avoid onchange issues
            self._manual_auto_fill_from_sale_order()
            
            # Count how many fields were filled
            filled_fields = []
            if self.model:
                filled_fields.append('Model')
            if self.engine_no:
                filled_fields.append('Engine No.')
            if self.frame_no:
                filled_fields.append('Frame No.')
            if self.purchase_date:
                filled_fields.append('Purchase Date')
            if self.payment_basis:
                filled_fields.append('Payment Basis')
            if self.brand:
                filled_fields.append('Brand')
            if self.classification:
                filled_fields.append('Classification')
            if self.customer_name:
                filled_fields.append('Customer Name')
            if self.coupon_line_ids:
                filled_fields.append(f'{len(self.coupon_line_ids)} Coupon Lines')
                
            message = f'Auto-fill completed from Sale Order {self.sale_order_id.name}'
            if filled_fields:
                message += f'\n\nFields populated: {", ".join(filled_fields)}'
            else:
                message += '\n\nNo additional data found in the sale order to populate.'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '🔄 Auto-Fill Complete',
                    'message': message,
                    'type': 'success',
                    'sticky': True,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Sale Order Selected',
                    'message': 'Please select a sale order first to auto-fill the WRC fields',
                    'type': 'warning',
                }
            }

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

    def write(self, vals):
        """Override write to handle coupon line changes, prevent auto-fill during save, and create Honda service coupons"""
        # CRITICAL: Set context flag to prevent auto-fill onchange during save
        _logger.info(f"WRC Record Write: Setting skip_wrc_autofill context flag for record {self.id if self.id else 'new'}")
        self = self.with_context(skip_wrc_autofill=True, from_ui=True, no_onchange=True)
        
        # Log what fields are being written
        if vals:
            _logger.info(f"WRC Record Write: Writing fields {list(vals.keys())} for record {self.id if self.id else 'new'}")
            
        # CRITICAL: Prevent any onchange from clearing important fields during save
        # If this is a save operation and no important fields are being explicitly updated,
        # ensure we don't lose existing field values
        important_fields = ['customer_name', 'model', 'brand', 'engine_no', 'frame_no', 'phone', 'email', 'color']
        if self.id and vals:
            for field in important_fields:
                # If an important field is not being updated in this write, but it has a value,
                # make sure we preserve it by not allowing it to be cleared
                if field not in vals and hasattr(self, field) and getattr(self, field):
                    current_value = getattr(self, field)
                    if current_value:
                        _logger.info(f"WRC Record Write: Preserving existing {field}: {current_value}")
        
        res = super().write(vals)
        
        # If coupon lines are added and record is still in draft, suggest confirmation
        if 'coupon_line_ids' in vals and self.state == 'draft' and self.coupon_line_ids:
            # Auto-confirm if all required fields are filled
            if self._check_required_fields_filled():
                try:
                    self.action_confirm()
                    _logger.info(f"Auto-confirmed WRC record {self.wrc_no} after coupon lines added")
                except Exception as e:
                    _logger.warning(f"Failed to auto-confirm WRC record {self.wrc_no}: {str(e)}")
        
        # If coupon_number is being set for Honda, create service coupons
        if vals.get('coupon_number') and self.brand == 'honda':
            self.create_honda_service_coupons()
            
        return res
    
    def action_refresh_fields_from_sale_order(self):
        """Button action to manually refresh fields from sale order - safe alternative to onchange"""
        if not self.sale_order_id:
            raise UserError("Please select a Sale Order first before refreshing fields.")
        
        # This is a manual action, so we can safely populate fields
        _logger.info(f"WRC Record: Manual refresh requested for sale order {self.sale_order_id.name}")
        self._manual_auto_fill_from_sale_order()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Fields Refreshed',
                'message': 'Fields have been refreshed from the selected Sale Order.',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _check_required_fields_filled(self):
        """Check if all required fields are filled for confirmation"""
        required_fields = [
            self.customer_name, self.phone, self.model, 
            self.engine_no, self.frame_no, self.brand, 
            self.classification, self.purchase_date
        ]
        return all(field for field in required_fields)

    def action_confirm(self):
        """Confirm WRC record - validate all required fields are filled"""
        self.ensure_one()
        
        # Validate required fields
        missing_fields = []
        
        # Check WRC number is present
        if not self.wrc_no:
            missing_fields.append('WRC Number')
        
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
        
        # Create service coupons from coupon registration lines
        if self.coupon_line_ids:
            for line in self.coupon_line_ids:
                # Check if service coupon already exists (by coupon_number AND coupon_type)
                existing_coupon = self.service_coupon_ids.filtered(
                    lambda c: c.coupon_number == line.coupon_number and 
                             c.coupon_type == line.coupon_type and 
                             c.state != 'disabled'
                )
                if not existing_coupon:
                    service_coupon_vals = {
                        'wrc_record_id': self.id,
                        'coupon_number': line.coupon_number,
                        'coupon_type': line.coupon_type,
                        'pms_km_min': line.pms_km_min,
                        'pms_km_max': line.pms_km_max,
                        'pms_months': line.pms_months,
                        'service_notes': line.notes,
                        'state': 'active',
                    }
                    # Calculate due date based on purchase date and months
                    if self.purchase_date and line.pms_months:
                        service_coupon_vals['due_date'] = self.purchase_date + relativedelta(months=line.pms_months)
                    
                    self.env['service.coupon'].create(service_coupon_vals)
        
        self.write({'state': 'confirmed'})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'WRC record confirmed and {len(self.coupon_line_ids)} service coupons created',
                'type': 'success',
            }
        }

    def action_create_service_coupons(self):
        """Manual action to create service coupons from coupon registration lines"""
        self.ensure_one()
        
        if not self.coupon_line_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No coupon registration lines found to create service coupons',
                    'type': 'warning',
                }
            }
        
        created_coupons = 0
        for line in self.coupon_line_ids:
            # Check if service coupon already exists (by coupon_number AND coupon_type)
            existing_coupon = self.service_coupon_ids.filtered(
                lambda c: c.coupon_number == line.coupon_number and 
                         c.coupon_type == line.coupon_type and 
                         c.state != 'disabled'
            )
            if not existing_coupon:
                service_coupon_vals = {
                    'wrc_record_id': self.id,
                    'coupon_number': line.coupon_number,
                    'coupon_type': line.coupon_type,
                    'pms_km_min': line.pms_km_min,
                    'pms_km_max': line.pms_km_max,
                    'pms_months': line.pms_months,
                    'service_notes': line.notes,
                    'state': 'active',
                }
                # Calculate due date based on purchase date and months
                if self.purchase_date and line.pms_months:
                    service_coupon_vals['due_date'] = self.purchase_date + relativedelta(months=line.pms_months)
                
                self.env['service.coupon'].create(service_coupon_vals)
                created_coupons += 1
        
        if created_coupons > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Successfully created {created_coupons} service coupons',
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'All service coupons already exist',
                    'type': 'info',
                }
            }

    def action_cancel(self):
        """Cancel WRC record"""
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})
        
    @api.model
    def cleanup_duplicate_wrc_records(self):
        """Helper method to identify and clean up duplicate WRC records"""
        # Find records with the same sale_order_id
        all_records = self.search([('sale_order_id', '!=', False)])
        duplicates_found = []
        duplicates_removed = 0
        
        sale_order_groups = {}
        for record in all_records:
            so_id = record.sale_order_id.id
            if so_id not in sale_order_groups:
                sale_order_groups[so_id] = []
            sale_order_groups[so_id].append(record)
        
        # Identify and remove duplicates
        for so_id, records in sale_order_groups.items():
            if len(records) > 1:
                # Keep the first created record, mark others as duplicates
                records_sorted = records.sorted('create_date')
                to_keep = records_sorted[0]
                to_remove = records_sorted[1:]
                
                duplicates_found.append({
                    'sale_order': to_keep.sale_order_id.name,
                    'keep_record': to_keep.wrc_no,
                    'duplicate_records': [r.wrc_no for r in to_remove],
                    'duplicate_ids': to_remove.ids,
                    'duplicate_count': len(to_remove)
                })
                
                # Remove duplicates in draft state
                draft_duplicates = to_remove.filtered(lambda r: r.state == 'draft')
                if draft_duplicates:
                    try:
                        draft_duplicates.unlink()
                        duplicates_removed += len(draft_duplicates)
                        _logger.info(f"Removed {len(draft_duplicates)} duplicate WRC records for SO {to_keep.sale_order_id.name}")
                    except Exception as e:
                        _logger.error(f"Failed to remove duplicates for SO {to_keep.sale_order_id.name}: {str(e)}")
        
        return {
            'duplicates_found': duplicates_found,
            'duplicates_removed': duplicates_removed,
            'total_groups': len(duplicates_found),
            'message': f'Found {len(duplicates_found)} sale orders with duplicates. Removed {duplicates_removed} draft duplicates.'
        }
        
    def action_cleanup_duplicates(self):
        """Action to cleanup duplicates with user notification"""
        result = self.cleanup_duplicate_wrc_records()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': result['message'],
                'type': 'success' if result['duplicates_removed'] > 0 else 'info',
            }
        }

    def get_brand_pms_schedules(self, brand):
        """Get brand-specific PMS schedules"""
        schedules = {
            'honda': [
                ('pms_1', '1st PMS: 500–2,000 km or 3 months'),
                ('pms_2', '2nd PMS: 2,001–6,000 km or 7 months'),
                ('pms_3', '3rd PMS: 6,001–12,000 km or 12 months'),
            ],
            'kawasaki': [
                ('pms_1', '1st PMS: 1,000 km or 1 month'),
                ('pms_2', '2nd PMS: 4,000 km or 4 months'),
                ('pms_3', '3rd PMS: 8,000 km or 8 months'),
                ('pms_4', '4th PMS: 12,000 km or 12 months'),
            ],
            'suzuki': [
                ('pms_1', '1st PMS: 1,000 km or 1 month'),
                ('pms_2', '2nd PMS: 4,000 km or 4 months'),
                ('pms_3', '3rd PMS: 8,000 km or 8 months'),
                ('pms_4', '4th PMS: 12,000 km or 12 months'),
            ],
            'skygo': [
                ('pms_1', '1st PMS: 500 km or 1 month'),
                ('pms_2', '2nd PMS: 3,000 km or 3 months'),
                ('pms_3', '3rd PMS: 6,000 km or 6 months'),
                ('pms_4', '4th PMS: 10,000 km or 12 months'),
            ],
            'yamaha': [
                ('pms_1', '1st PMS: 0-1,500 kms or 1 month'),
                ('pms_2', '2nd PMS: 1,501-5,500 kms or 4 months'),
                ('pms_3', '3rd PMS: 5,501-8,500 kms or 8 months'),
                ('pms_4', '4th PMS: 8,501-11,500 kms or 12 months'),
            ],
        }
        return schedules.get(brand, [])

    def get_brand_pms_details(self, brand, pms_type):
        """Get specific PMS details for brand and type"""
        pms_data = {
            'honda': {
                'pms_1': {'km_min': 500, 'km_max': 2000, 'months': 3},
                'pms_2': {'km_min': 2001, 'km_max': 6000, 'months': 7},
                'pms_3': {'km_min': 6001, 'km_max': 12000, 'months': 12},
            },
            'kawasaki': {
                'pms_1': {'km_min': 1000, 'km_max': 1000, 'months': 1},
                'pms_2': {'km_min': 4000, 'km_max': 4000, 'months': 4},
                'pms_3': {'km_min': 8000, 'km_max': 8000, 'months': 8},
                'pms_4': {'km_min': 12000, 'km_max': 12000, 'months': 12},
            },
            'suzuki': {
                'pms_1': {'km_min': 1000, 'km_max': 1000, 'months': 1},
                'pms_2': {'km_min': 4000, 'km_max': 4000, 'months': 4},
                'pms_3': {'km_min': 8000, 'km_max': 8000, 'months': 8},
                'pms_4': {'km_min': 12000, 'km_max': 12000, 'months': 12},
            },
            'skygo': {
                'pms_1': {'km_min': 500, 'km_max': 500, 'months': 1},
                'pms_2': {'km_min': 3000, 'km_max': 3000, 'months': 3},
                'pms_3': {'km_min': 6000, 'km_max': 6000, 'months': 6},
                'pms_4': {'km_min': 10000, 'km_max': 10000, 'months': 12},
            },
            'yamaha': {
                'pms_1': {'km_min': 0, 'km_max': 1500, 'months': 1},
                'pms_2': {'km_min': 1501, 'km_max': 5500, 'months': 4},
                'pms_3': {'km_min': 5501, 'km_max': 8500, 'months': 8},
                'pms_4': {'km_min': 8501, 'km_max': 11500, 'months': 12},
            },
        }
        return pms_data.get(brand, {}).get(pms_type, {})

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


class WrcRecordCouponLine(models.Model):
    _name = 'wrc.record.coupon.line'
    _description = 'WRC Record Coupon Registration Line'
    _rec_name = 'coupon_number'
    
    wrc_record_id = fields.Many2one('wrc.record', 'WRC Record', required=True, ondelete='cascade')
    coupon_number = fields.Char('Coupon Number', required=True)
    coupon_type = fields.Selection('_get_coupon_type_selection', string='Coupon Type', required=True)
    pms_km_min = fields.Integer('Min KM')
    pms_km_max = fields.Integer('Max KM')
    pms_months = fields.Integer('Months Schedule')
    notes = fields.Text('Notes')
    
    def _get_coupon_type_selection(self):
        """Get coupon type selection based on brand"""
        if self.wrc_record_id and self.wrc_record_id.brand:
            brand = self.wrc_record_id.brand
            if brand == 'honda':
                return [
                    ('pms_1', '1st PMS: 500–2,000 km or 3 months'),
                    ('pms_2', '2nd PMS: 2,001–6,000 km or 7 months'),
                    ('pms_3', '3rd PMS: 6,001–12,000 km or 12 months'),
                ]
            elif brand == 'kawasaki':
                return [
                    ('pms_1', '1st PMS: 1,000 km or 1 month'),
                    ('pms_2', '2nd PMS: 4,000 km or 4 months'),
                    ('pms_3', '3rd PMS: 8,000 km or 8 months'),
                    ('pms_4', '4th PMS: 12,000 km or 12 months'),
                ]
            elif brand == 'suzuki':
                return [
                    ('pms_1', '1st PMS: 1,000 km or 1 month'),
                    ('pms_2', '2nd PMS: 4,000 km or 4 months'),
                    ('pms_3', '3rd PMS: 8,000 km or 8 months'),
                    ('pms_4', '4th PMS: 12,000 km or 12 months'),
                ]
            elif brand == 'skygo':
                return [
                    ('pms_1', '1st PMS: 500 km or 1 month'),
                    ('pms_2', '2nd PMS: 3,000 km or 3 months'),
                    ('pms_3', '3rd PMS: 6,000 km or 6 months'),
                    ('pms_4', '4th PMS: 10,000 km or 12 months'),
                ]
            elif brand == 'yamaha':
                return [
                    ('pms_1', '1st PMS: 0-1,500 kms or 1 month'),
                    ('pms_2', '2nd PMS: 1,501-5,500 kms or 4 months'),
                    ('pms_3', '3rd PMS: 5,501-8,500 kms or 8 months'),
                    ('pms_4', '4th PMS: 8,501-11,500 kms or 12 months'),
                ]
        # Default options if no brand selected
        return [
            ('pms_1', 'PMS 1'),
            ('pms_2', 'PMS 2'),
            ('pms_3', 'PMS 3'),
            ('pms_4', 'PMS 4'),
        ]
    
    @api.onchange('coupon_type')
    def _onchange_coupon_type(self):
        """Auto-populate KM and months based on coupon type and brand"""
        if self.wrc_record_id and self.wrc_record_id.brand and self.coupon_type:
            pms_details = self.wrc_record_id.get_brand_pms_details(self.wrc_record_id.brand, self.coupon_type)
            if pms_details:
                self.pms_km_min = pms_details.get('km_min', 0)
                self.pms_km_max = pms_details.get('km_max', 0)
                self.pms_months = pms_details.get('months', 0)
                
                # Update notes with brand-specific description
                schedules = self.wrc_record_id.get_brand_pms_schedules(self.wrc_record_id.brand)
                for pms_type, pms_desc in schedules:
                    if pms_type == self.coupon_type:
                        self.notes = pms_desc
                        break