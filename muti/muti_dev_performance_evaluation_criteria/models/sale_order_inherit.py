# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
import re
import logging

_logger = logging.getLogger(__name__)

class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'
    
    # === WRC FORM FIELDS ===
    # Customer Information
    wrc_address = fields.Text('Customer Address')
    wrc_birthdate = fields.Date('Birthdate')
    wrc_age = fields.Integer('Age', compute='_compute_age')
    wrc_sex = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Sex')
    wrc_phone = fields.Char('Contact #')
    
    # Dealer Information
    wrc_dealer_code = fields.Char('Dealers Code')
    wrc_dealer = fields.Char('Dealer')
    wrc_dealer_address = fields.Text('Address of Dealer')
    
    # Motorcycle Details
    wrc_engine = fields.Char('Engine Number')
    wrc_frame = fields.Char('Frame Number')
    wrc_model = fields.Char('Model')
    wrc_color = fields.Char('Color')
    wrc_purchase_date = fields.Date('Date of Purchase')
    
    # Service Coupon Codes
    wrc_coupon_1 = fields.Char('Service Coupon 1')
    wrc_coupon_2 = fields.Char('Service Coupon 2')
    wrc_coupon_3 = fields.Char('Service Coupon 3')
    wrc_coupons_extra = fields.Text('Additional Coupon Codes')
    
    # === COMPUTED/RELATED FIELDS ===
    wrc_records = fields.One2many('wrc.record', 'sale_order_id', 'WRC Records')
    wrc_count = fields.Integer('WRC Record Count', compute='_compute_counts')
    has_wrc = fields.Boolean('Has WRC Record', compute='_compute_counts')
    
    coupon_count = fields.Integer('Service Coupon Count', compute='_compute_coupon_counts')
    coupon_draft = fields.Integer('Draft Coupons', compute='_compute_coupon_counts')
    coupon_scheduled = fields.Integer('Scheduled Coupons', compute='_compute_coupon_counts')
    coupon_done = fields.Integer('Completed Coupons', compute='_compute_coupon_counts')
    
    wrc_sale_type = fields.Selection([
        ('mc', 'Motorcycle'), ('sp', 'Spare Parts'), 
        ('labour', 'Labour'), ('other', 'Other')
    ], 'WRC Sale Type', compute='_compute_sale_type', store=True)
    
    is_mc_sale = fields.Boolean(
        'Is Motorcycle Sale', compute='_compute_mc_details', store=True
    )
    
    # Auto-population triggers
    wrc_trigger = fields.Boolean('Auto Populate Trigger', compute='_compute_trigger')
    wrc_tab_trigger = fields.Boolean('WRC Tab Trigger', compute='_compute_tab_trigger', store=False)
    
    # === COMPUTED METHODS ===
    @api.depends('wrc_birthdate')
    def _compute_age(self):
        """Calculate age from birthdate"""
        today = datetime.today().date()
        for rec in self:
            if rec.wrc_birthdate:
                rec.wrc_age = today.year - rec.wrc_birthdate.year - (
                    (today.month, today.day) < (rec.wrc_birthdate.month, rec.wrc_birthdate.day)
                )
            else:
                rec.wrc_age = 0
    
    @api.depends('wrc_records')
    def _compute_counts(self):
        """Compute WRC record counts"""
        for rec in self:
            rec.wrc_count = len(rec.wrc_records)
            rec.has_wrc = bool(rec.wrc_records)
    
    @api.depends('wrc_records')
    def _compute_coupon_counts(self):
        """Compute service coupon counts by state"""
        for rec in self:
            if not rec.wrc_records:
                rec.update({
                    'coupon_count': 0, 'coupon_draft': 0,
                    'coupon_scheduled': 0, 'coupon_done': 0,
                })
                continue
                
            coupons = self.env['service.coupon'].search([
                ('wrc_record_id', 'in', rec.wrc_records.ids)
            ])
            
            rec.coupon_count = len(coupons)
            rec.coupon_draft = len(coupons.filtered(lambda c: c.state == 'draft'))
            rec.coupon_scheduled = len(coupons.filtered(lambda c: c.state == 'scheduled'))
            rec.coupon_done = len(coupons.filtered(lambda c: c.state == 'completed'))
    
    @api.depends('order_line', 'order_line.product_id')
    def _compute_sale_type(self):
        """Determine sale type based on products"""
        for rec in self:
            # Check AWB field first if it exists
            if hasattr(rec, 'awb_sale_type') and rec.awb_sale_type:
                rec.wrc_sale_type = rec.awb_sale_type
                continue
            
            # Determine from products
            sale_type = 'other'
            for line in rec.order_line:
                if rec._is_mc_product(line.product_id):
                    sale_type = 'mc'
                    break
                elif rec._is_spare_product(line.product_id):
                    sale_type = 'sp'
                elif rec._is_labour_product(line.product_id):
                    sale_type = 'labour'
            
            rec.wrc_sale_type = sale_type
    
    @api.depends('order_line', 'wrc_sale_type')
    def _compute_mc_details(self):
        """Compute motorcycle-related details"""
        for rec in self:
            is_motorcycle = rec.wrc_sale_type == 'mc'
            
            # Auto-populate model from motorcycle product.model field
            if is_motorcycle and not rec.wrc_model:
                mc_product = rec._find_mc_product()
                if mc_product:
                    model_value = rec._get_product_model(mc_product)
                    if model_value:
                        rec.wrc_model = model_value
            
            rec.is_mc_sale = is_motorcycle
    
    @api.depends('partner_id', 'is_mc_sale', 'wrc_address', 'wrc_phone', 'wrc_engine', 'wrc_frame', 'wrc_purchase_date')
    def _compute_tab_trigger(self):
        """Auto-populate when WRC tab is accessed"""
        for rec in self:
            # Auto-populate customer info
            if (rec.partner_id and rec.is_mc_sale and 
                (not rec.wrc_address or not rec.wrc_phone)):
                rec._populate_customer()
            
            # Auto-populate model from product.model field
            if rec.is_mc_sale and not rec.wrc_model:
                mc_product = rec._find_mc_product()
                if mc_product:
                    model_value = rec._get_product_model(mc_product)
                    if model_value:
                        rec.wrc_model = model_value
            
            # Auto-populate color from product name
            if rec.is_mc_sale and not rec.wrc_color:
                mc_product = rec._find_mc_product()
                if mc_product:
                    rec.wrc_color = rec._extract_color(mc_product.name)
            
            # Auto-populate engine and frame numbers
            if rec.is_mc_sale and (not rec.wrc_engine or not rec.wrc_frame):
                try:
                    engine, frame = rec._extract_engine_frame()
                    if not rec.wrc_engine and engine:
                        rec.wrc_engine = engine
                    if not rec.wrc_frame and frame:
                        rec.wrc_frame = frame
                except Exception as e:
                    _logger.warning(f"Failed to auto-populate engine/frame: {str(e)}")
            
            # Auto-populate purchase date
            if rec.is_mc_sale and not rec.wrc_purchase_date:
                try:
                    delivery_date = rec._extract_delivery_date()
                    if delivery_date:
                        rec.wrc_purchase_date = delivery_date
                    else:
                        # Fallback to order dates
                        rec.wrc_purchase_date = (
                            getattr(rec, 'commitment_date', None) and rec.commitment_date.date() or
                            rec.date_order and rec.date_order.date() or
                            fields.Date.today()
                        )
                except Exception as e:
                    _logger.warning(f"Failed to auto-populate purchase date: {str(e)}")
        
            rec.wrc_tab_trigger = True
    
    @api.depends('partner_id', 'is_mc_sale')
    def _compute_trigger(self):
        """Auto-populate customer info when conditions are met"""
        for rec in self:
            if (rec.partner_id and rec.is_mc_sale and not rec.has_wrc and
                (not rec.wrc_address or not rec.wrc_phone)):
                rec._populate_customer()
            rec.wrc_trigger = True
    
    # === HELPER METHODS ===
    def _is_mc_product(self, product):
        """Check if product is a motorcycle"""
        if not product:
            return False
            
        name_lower = product.name.lower()
        if any(kw in name_lower for kw in ['motorcycle', 'motorbike', 'scooter', 'bike']):
            return True
            
        # Check product category for motorcycle/MC
        if hasattr(product, 'categ_id') and product.categ_id:
            categ_name = product.categ_id.name.lower()
            if 'mc' in categ_name or 'motorcycle' in categ_name:
                return True
            
        if hasattr(product, 'analytic_tag_ids'):
            for tag in product.analytic_tag_ids:
                if 'motorcycle' in tag.name.lower():
                    return True
        return False
    
    def _is_spare_product(self, product):
        """Check if product is a spare part"""
        if not product or not hasattr(product, 'analytic_tag_ids'):
            return False
        return any('spare' in tag.name.lower() for tag in product.analytic_tag_ids)
    
    def _is_labour_product(self, product):
        """Check if product is labour"""
        if not product or not hasattr(product, 'analytic_tag_ids'):
            return False
        return any('labour' in tag.name.lower() for tag in product.analytic_tag_ids)
    
    def _find_mc_product(self):
        """Find motorcycle product in order lines"""
        for line in self.order_line:
            if self._is_mc_product(line.product_id):
                return line.product_id
        return False
    
    def _get_product_model(self, product):
        """Get model value from product with fallback options"""
        if not product:
            return None
        
        # First try: Direct model field from product.product object
        if hasattr(product, 'model') and product.model:
            model_value = str(product.model).strip()
            if model_value:
                return model_value  # This will return "CT125"
        
        # Second try: Check if there's a model_id field (Many2one relation)
        if hasattr(product, 'model_id') and product.model_id:
            if hasattr(product.model_id, 'name') and product.model_id.name:
                return str(product.model_id.name).strip()
        
        # Third try: Check product attributes for model
        if hasattr(product, 'product_template_attribute_value_ids'):
            for attr_val in product.product_template_attribute_value_ids:
                if hasattr(attr_val, 'attribute_id') and attr_val.attribute_id:
                    if 'model' in attr_val.attribute_id.name.lower():
                        if hasattr(attr_val, 'name') and attr_val.name:
                            return str(attr_val.name).strip()
        
        # Fourth try: Extract from product name using patterns
        return self._extract_model_from_product_name(product.name)
    
    def _extract_model_from_product_name(self, product_name):
        """Extract model from product name as fallback"""
        if not product_name:
            return None
            
        # For products like "[KA0071] [KA0071] CT125AE CT125A (BLACK/BLUE)"
        # Extract CT125AE or CT125A as the model
        
        # Method 1: Look for pattern after brackets
        match = re.search(r'\]\s*([A-Z0-9]+)', product_name)
        if match:
            potential_model = match.group(1).strip()
            # Check if it looks like a model (contains letters and numbers)
            if re.search(r'[A-Z].*\d|\d.*[A-Z]', potential_model) and len(potential_model) >= 3:
                return potential_model
        
        # Method 2: Look for common motorcycle model patterns
        model_patterns = [
            r'\b([A-Z]+\d+[A-Z]*)\b',  # e.g., CT125AE, PCX160, BEAT125
            r'\b([A-Z]{2,}\d+)\b',     # e.g., PCX160, CBR150
        ]
        
        for pattern in model_patterns:
            matches = re.findall(pattern, product_name)
            for match in matches:
                # Skip generic codes and focus on likely model names
                if len(match) >= 4 and not match.startswith('KA'):
                    return match
        
        return None
    
    def _format_address(self, partner):
        """Format complete address from partner"""
        if not partner:
            return ''
        
        parts = []
        if partner.street:
            parts.append(partner.street)
        if hasattr(partner, 'barangay_id') and partner.barangay_id:
            parts.append(partner.barangay_id.name)
        if hasattr(partner, 'city_id') and partner.city_id:
            parts.append(partner.city_id.name)
        elif hasattr(partner, 'city') and partner.city:
            parts.append(partner.city)
        if hasattr(partner, 'state_id') and partner.state_id:
            parts.append(partner.state_id.name)
        if hasattr(partner, 'country_id') and partner.country_id:
            parts.append(partner.country_id.name)
        
        return '\n'.join(filter(None, parts))
    
    def _extract_color(self, text):
        """Extract color from text using common patterns"""
        if not text:
            return None
            
        color_map = {
            'Red': ['red', 'crimson', 'cherry'], 
            'Blue': ['blue', 'navy', 'azure'],
            'Black': ['black', 'matte black'], 
            'White': ['white', 'pearl white'],
            'Silver': ['silver', 'metallic'], 
            'Yellow': ['yellow', 'gold'],
            'Green': ['green', 'forest'], 
            'Orange': ['orange', 'amber'],
            'Gray': ['gray', 'grey'], 
            'Brown': ['brown', 'bronze']
        }
        
        text_lower = text.lower()
        
        # Check parentheses first (e.g., "(BLACK/BLUE)")
        match = re.search(r'\(([^)]+)\)', text)
        if match:
            content = match.group(1).lower()
            for color, patterns in color_map.items():
                if any(pattern in content for pattern in patterns):
                    return color
            # If parentheses contain color words, return the first one
            color_words = content.split('/')
            if color_words:
                return color_words[0].strip().title()
        
        # Check for color patterns in the text
        for color, patterns in color_map.items():
            if any(pattern in text_lower for pattern in patterns):
                return color
        
        return None
    
    def _get_dealer_info(self):
        """Extract dealer information from order/lines"""
        dealer_fields = ['dealer_id', 'branch_id', 'warehouse_id']
        
        # Check order lines first
        for line in self.order_line:
            for field_name in dealer_fields:
                if hasattr(line, field_name):
                    dealer = getattr(line, field_name)
                    if dealer and hasattr(dealer, 'name'):
                        return {
                            'name': dealer.name,
                            'code': getattr(dealer, 'ref', None) or getattr(dealer, 'code', None),
                            'address': self._format_dealer_address(dealer)
                        }
        
        # Fallback to sale order level
        for field_name in dealer_fields:
            if hasattr(self, field_name):
                dealer = getattr(self, field_name)
                if dealer and hasattr(dealer, 'name'):
                    return {
                        'name': dealer.name,
                        'code': getattr(dealer, 'ref', None),
                        'address': self._format_dealer_address(dealer)
                    }
        
        # Final fallback to company
        return {
            'name': self.company_id.name,
            'code': self.company_id.partner_id.ref or self.company_id.name[:10],
            'address': self._format_dealer_address(self.company_id.partner_id)
        }
    
    def _format_dealer_address(self, partner):
        """Format partner address for dealer info"""
        if not partner or not hasattr(partner, 'street'):
            return None
            
        parts = [
            partner.street, 
            partner.street2 if hasattr(partner, 'street2') else None,
            partner.city if hasattr(partner, 'city') else None,
            partner.state_id.name if hasattr(partner, 'state_id') and partner.state_id else None,
            partner.zip if hasattr(partner, 'zip') else None,
            partner.country_id.name if hasattr(partner, 'country_id') and partner.country_id else None
        ]
        return ', '.join(filter(None, parts))
    
    def _get_coupon_codes(self):
        """Get all coupon codes combined"""
        codes = []
        for field in ['wrc_coupon_1', 'wrc_coupon_2', 'wrc_coupon_3']:
            value = getattr(self, field)
            if value:
                codes.append(str(value).strip())
        
        if self.wrc_coupons_extra:
            codes.extend([code.strip() for code in str(self.wrc_coupons_extra).split('\n') if code.strip()])
        
        return codes
    
    def _create_coupons(self, wrc_record, coupon_codes):
        """Create service coupons from codes"""
        for code in coupon_codes:
            if code:
                self.env['service.coupon'].create({
                    'wrc_record_id': wrc_record.id,
                    'coupon_number': code,
                    'servicing_branch_id': self.company_id.id,
                    'state': 'draft'
                })
    
    def _validate_wrc(self):
        """Validate WRC data before saving"""
        errors = []
        
        required_fields = [
            ('wrc_engine', 'Engine Number'),
            ('wrc_frame', 'Frame Number')
        ]
        
        for field_name, field_label in required_fields:
            value = str(getattr(self, field_name) or '').strip()
            if not value:
                errors.append(f"• {field_label} is required")
            elif len(value) < 3:
                errors.append(f"• {field_label} must be at least 3 characters long")
        
        if errors:
            raise UserError("Please fix the following issues:\n\n" + "\n".join(errors))
    
    # === POPULATION METHODS ===
    def _populate_customer(self):
        """Immediately populate customer information"""
        if not self.partner_id:
            return
        
        partner = self.partner_id
        
        # Format address and phone
        formatted_address = self._format_address(partner)
        phone = partner.phone or partner.mobile or ''
        
        # Get birthdate
        birthdate = None
        for field_name in ['birthdate', 'birth_date', 'date_of_birth', 'birthday']:
            if hasattr(partner, field_name):
                value = getattr(partner, field_name)
                if value:
                    birthdate = value
                    break
        
        # Get sex/gender
        sex = None
        for field_name in ['gender', 'sex']:
            if hasattr(partner, field_name):
                value = getattr(partner, field_name)
                if value and str(value).lower() in ['male', 'female']:
                    sex = str(value).lower()
                    break
        
        # Direct assignment (no write() to avoid recursion)
        if not self.wrc_address and formatted_address:
            self.wrc_address = formatted_address
        if not self.wrc_phone and phone:
            self.wrc_phone = phone
        if not self.wrc_birthdate and birthdate:
            self.wrc_birthdate = birthdate
        if not self.wrc_sex and sex:
            self.wrc_sex = sex
    
    def _populate_all(self):
        """Auto-populate all WRC fields"""
        # Customer information
        if self.partner_id:
            partner = self.partner_id
            vals = {}
            
            if not self.wrc_address:
                address = self._format_address(partner)
                if address:
                    vals['wrc_address'] = address
            
            if not self.wrc_phone:
                phone = partner.phone or partner.mobile or ''
                if phone:
                    vals['wrc_phone'] = phone
            
            if not self.wrc_birthdate:
                for field in ['birthdate', 'birth_date', 'date_of_birth', 'birthday']:
                    if hasattr(partner, field):
                        value = getattr(partner, field)
                        if value:
                            vals['wrc_birthdate'] = value
                            break
            
            if not self.wrc_sex:
                for field in ['gender', 'sex']:
                    if hasattr(partner, field):
                        value = getattr(partner, field)
                        if value and str(value).lower() in ['male', 'female']:
                            vals['wrc_sex'] = str(value).lower()
                            break
            
            if vals:
                self.write(vals)
        
        # Purchase date - prioritize delivery date
        if not self.wrc_purchase_date:
            delivery_date = self._extract_delivery_date()
            if delivery_date:
                self.wrc_purchase_date = delivery_date
            else:
                self.wrc_purchase_date = (
                    getattr(self, 'commitment_date', None) and self.commitment_date.date() or
                    self.date_order and self.date_order.date() or
                    fields.Date.today()
                )
        
        # Dealer information
        dealer_info = self._get_dealer_info()
        if not self.wrc_dealer:
            self.wrc_dealer = dealer_info['name']
        if not self.wrc_dealer_code:
            self.wrc_dealer_code = dealer_info['code']
        if not self.wrc_dealer_address:
            self.wrc_dealer_address = dealer_info['address']
        
        # Motorcycle model and color from product
        if self.is_mc_sale:
            mc_product = self._find_mc_product()
            if mc_product:
                # Get model from product.model field with fallbacks
                if not self.wrc_model:
                    model_value = self._get_product_model(mc_product)
                    if model_value:
                        self.wrc_model = model_value
                # Get color from product name
                if not self.wrc_color:
                    self.wrc_color = self._extract_color(mc_product.name)
        
        # Engine and frame numbers
        if not self.wrc_engine or not self.wrc_frame:
            engine, frame = self._extract_engine_frame()
            if not self.wrc_engine and engine:
                self.wrc_engine = engine
            if not self.wrc_frame and frame:
                self.wrc_frame = frame
        
        # Alternative lot info method
        if not self.wrc_engine or not self.wrc_frame:
            lot_info = self._get_lot_info()
            if not self.wrc_engine and lot_info.get('engine_number'):
                self.wrc_engine = lot_info['engine_number']
            if not self.wrc_frame and lot_info.get('chassis_number'):
                self.wrc_frame = lot_info['chassis_number']
        
        # Fallback: order line fields
        mc_fields = {
            'engine_number': 'wrc_engine',
            'frame_number': 'wrc_frame', 
            'chassis_number': 'wrc_frame',
            'motorcycle_model': 'wrc_model',
            'motorcycle_color': 'wrc_color'
        }
        
        for line in self.order_line:
            for line_field, wrc_field in mc_fields.items():
                if not getattr(self, wrc_field) and hasattr(line, line_field):
                    value = getattr(line, line_field)
                    if value:
                        setattr(self, wrc_field, str(value))
    
    def _extract_engine_frame(self):
        """Extract engine and frame numbers from delivery operations"""
        engine_number = None
        frame_number = None
        
        pickings = self.picking_ids.filtered(lambda p: p.state in ['done', 'assigned', 'partially_available'])
        
        for picking in pickings:
            for move_line in picking.move_line_ids:
                if move_line.lot_id:
                    lot = move_line.lot_id
                    
                    # Engine number extraction
                    if not engine_number and lot.name:
                        if 'eng.' in lot.name.lower() or 'engine' in lot.name.lower():
                            engine_number = lot.name.replace('Eng.#', '').replace('eng.#', '').replace('Eng.', '').replace('eng.', '').strip()
                        else:
                            engine_number = lot.name.strip()
                    
                    # Frame number extraction
                    if not frame_number:
                        if hasattr(lot, 'chassis_number') and lot.chassis_number:
                            frame_number = lot.chassis_number.strip()
                        elif lot.name and ('chass.' in lot.name.lower() or 'chassis' in lot.name.lower()):
                            frame_number = lot.name.replace('Chass.#', '').replace('chass.#', '').replace('Chass.', '').replace('chass.', '').strip()
                        elif hasattr(lot, 'serial_number') and lot.serial_number and 'chass' in str(lot.serial_number).lower():
                            frame_number = str(lot.serial_number).strip()
                    
                    if engine_number and frame_number:
                        break
            
            if engine_number and frame_number:
                break

        return engine_number, frame_number

    def _get_lot_info(self):
        """Get motorcycle lot information (alternative method)"""
        lot_info = {}
        
        domain = [
            ('product_id', 'in', self.order_line.mapped('product_id').ids),
            ('company_id', '=', self.company_id.id)
        ]
        
        lots = self.env['stock.production.lot'].search(domain)
        
        for lot in lots:
            move_lines = self.env['stock.move.line'].search([
                ('lot_id', '=', lot.id),
                ('picking_id', 'in', self.picking_ids.ids)
            ])
            
            if move_lines:
                # Extract engine number
                if lot.name and not lot_info.get('engine_number'):
                    engine_num = lot.name.replace('Eng.#', '').replace('eng.#', '').replace('Eng.', '').replace('eng.', '').strip()
                    if engine_num:
                        lot_info['engine_number'] = engine_num
                
                # Extract chassis number
                if not lot_info.get('chassis_number'):
                    if hasattr(lot, 'chassis_number') and lot.chassis_number:
                        lot_info['chassis_number'] = lot.chassis_number.strip()
                    elif lot.name and ('chass.' in lot.name.lower() or 'chassis' in lot.name.lower()):
                        chassis_num = lot.name.replace('Chass.#', '').replace('chass.#', '').replace('Chass.', '').replace('chass.', '').strip()
                        if chassis_num:
                            lot_info['chassis_number'] = chassis_num
                
                # Extract other fields
                for field in ['motor_number', 'serial_number', 'plate_number', 'cr_number']:
                    if hasattr(lot, field) and not lot_info.get(field):
                        value = getattr(lot, field)
                        if value:
                            lot_info[field] = str(value).strip()
                
                if lot_info.get('engine_number') and lot_info.get('chassis_number'):
                    break
        
        return lot_info
    
    def _extract_delivery_date(self):
        """Extract effective date from delivery operations"""
        pickings = self.picking_ids.filtered(lambda p: p.state in ['done', 'assigned', 'partially_available']).sorted(
            key=lambda p: (p.state == 'done', p.date_done or p.scheduled_date), reverse=True
        )
        
        for picking in pickings:
            if hasattr(picking, 'date_done') and picking.date_done:
                return picking.date_done.date()
            elif hasattr(picking, 'scheduled_date') and picking.scheduled_date:
                return picking.scheduled_date.date()
            elif hasattr(picking, 'effective_date') and picking.effective_date:
                return picking.effective_date if isinstance(picking.effective_date, type(fields.Date.today())) else picking.effective_date.date()
        
        return None
    
    # === ACTION METHODS ===
    def action_save_wrc(self):
        """Save WRC Record"""
        self.ensure_one()
        
        # Auto-populate and validate
        self._populate_all()
        self._validate_wrc()
        
        # Prepare WRC data
        coupon_codes = self._get_coupon_codes()
        wrc_vals = {
            'customer_address': self.wrc_address,
            'birthdate': self.wrc_birthdate,
            'sex': self.wrc_sex,
            'contact_number': self.wrc_phone,
            'dealers_code': self.wrc_dealer_code,
            'dealer': self.wrc_dealer,
            'dealer_address': self.wrc_dealer_address,
            'engine_number': str(self.wrc_engine or '').strip(),
            'frame_number': str(self.wrc_frame or '').strip(),
            'model': self.wrc_model,
            'color': self.wrc_color,
            'date_of_purchase': self.wrc_purchase_date,
            'coupon_codes': '\n'.join(coupon_codes),
        }
        
        try:
            if self.has_wrc:
                # Update existing
                self.wrc_records[0].write(wrc_vals)
                message = "WRC Record updated successfully!"
            else:
                # Create new
                wrc_vals.update({
                    'sale_order_id': self.id,
                    'partner_id': self.partner_id.id,
                    'branch_id': self.company_id.id,
                })
                wrc_record = self.env['wrc.record'].create(wrc_vals)
                self._create_coupons(wrc_record, coupon_codes)
                message = "WRC Record created successfully!"
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success!',
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            raise UserError(f"Error saving WRC Record: {str(e)}")
    
    def action_view_wrc(self):
        """View WRC Records"""
        self.ensure_one()
        action = self.env.ref('muti_dev_performance_evaluation_criteria.action_wrc_record').read()[0]
        
        if len(self.wrc_records) == 1:
            action['views'] = [(False, 'form')]
            action['res_id'] = self.wrc_records[0].id
        else:
            action['domain'] = [('sale_order_id', '=', self.id)]
        
        return action
    
    def action_view_coupons(self):
        """View Service Coupons"""
        self.ensure_one()
        action = self.env.ref('muti_dev_performance_evaluation_criteria.action_service_coupon').read()[0]
        action['domain'] = [('wrc_record_id', 'in', self.wrc_records.ids)]
        action['context'] = {
            'default_wrc_record_id': self.wrc_records[0].id if self.wrc_records else False,
        }
        return action