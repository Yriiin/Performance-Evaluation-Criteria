from odoo import models, fields, api
import logging
import re

_logger = logging.getLogger(__name__)

class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'
    
    # === WRC FIELDS ===
    # Customer Profile (Auto-filled, Read-only)
    wrc_customer_name = fields.Char('Customer Name', compute='_compute_customer_name', store=True)
    wrc_address = fields.Text('Customer Address')
    wrc_phone = fields.Char('Phone Number')
    wrc_email = fields.Char('Email')
    wrc_birthday = fields.Date('Birthday')
    
    # Dealer Profile (Auto-filled, Read-only)
    wrc_selling_dealer = fields.Char('Selling Dealer')
    wrc_dealer_code = fields.Char('Dealer Code')
    wrc_dealer_address = fields.Text('Dealer Address')
    
    # Unit Info - Some computed, some regular for easier editing
    wrc_model = fields.Char('Model')
    wrc_engine = fields.Char('Engine No.')
    wrc_frame = fields.Char('Frame No.')
    wrc_purchase_date = fields.Date('Date Purchased')
    wrc_color = fields.Char('Color')
    wrc_brand = fields.Selection([
        ('honda', 'Honda'),
        ('yamaha', 'Yamaha'),
        ('kawasaki', 'Kawasaki'),
        ('suzuki', 'Suzuki'),
        ('skygo', 'Skygo')
    ], string='Brand', compute='_compute_brand', store=True)
    wrc_payment_basis = fields.Selection([
        ('cash', 'Cash'),
        ('installment', 'Installment')
    ], string='Payment Basis')
    wrc_qty = fields.Float('Quantity', default=1.0)
    wrc_classification = fields.Selection([
        ('commuter', 'Commuter'),
        ('bigbike', 'BigBike')
    ], string='Classification', readonly=False)
    
    # Coupon Information
    wrc_coupon_number = fields.Char('Coupon Number', help='User-inputted coupon number for service tracking')
    
    # === CONTROL FIELDS ===
    awb_sale_type = fields.Selection([
        ('mc', 'Motorcycle'),
        ('sp', 'Spare Parts'),
        ('labour', 'Labour')
    ], string='Sale Type', compute='_compute_awb_sale_type', store=True)
    has_wrc = fields.Boolean('Has WRC', compute='_compute_has_wrc')
    wrc_count = fields.Integer('WRC Count', compute='_compute_wrc_count')
    coupon_count = fields.Integer('Coupon Count', compute='_compute_coupon_count')
    is_mc_sale = fields.Boolean('Is Motorcycle Sale', compute='_compute_sale_type', store=True)
    show_wrc = fields.Boolean('Show WRC', compute='_compute_show_wrc', store=True)
    wrc_transferred = fields.Boolean('WRC Transferred', default=False)
    wrc_auto_filled = fields.Boolean('WRC Auto-filled', default=False)
    wrc_data_available = fields.Boolean('WRC Data Available', compute='_compute_wrc_data_available')
    
    # === RELATIONS ===
    wrc_records = fields.One2many('wrc.record', 'sale_order_id', string='WRC Records')
    
    # === COMPUTE METHODS ===
    @api.depends('partner_id')
    def _compute_customer_name(self):
        for record in self:
            record.wrc_customer_name = record.partner_id.name if record.partner_id else ''

    @api.depends('invoice_status', 'is_mc_sale')
    def _compute_wrc_auto_save(self):
        """Auto-save WRC record when sale order is fully invoiced"""
        for record in self:
            if (record.is_mc_sale and 
                record.invoice_status == 'invoiced' and 
                not record.wrc_transferred):
                # Check if WRC record already exists
                existing_wrc = record.wrc_records.filtered(lambda r: r.state != 'cancelled')
                if not existing_wrc:
                    record._create_wrc_record()
                    record.wrc_transferred = True

    @api.depends('is_mc_sale', 'order_line', 'order_line.product_id')
    def _compute_brand(self):
        """Compute brand from product internal reference (first 2 chars) and auto-fill other WRC data"""
        for order in self:
            if order.is_mc_sale:
                mc_line = order.order_line.filtered(lambda l: order._is_mc_product(l.product_id))
                if mc_line:
                    mc_product = mc_line[0].product_id
                    brand = False
                    
                    # Extract brand from product default_code (internal reference)
                    if mc_product.default_code and len(mc_product.default_code) >= 2:
                        code = mc_product.default_code[:2].upper()
                        brand_map = {
                            'HO': 'honda',
                            'YA': 'yamaha', 
                            'KA': 'kawasaki',
                            'SU': 'suzuki',
                            'SK': 'skygo'
                        }
                        brand = brand_map.get(code, False)
                    
                    # Fallback: extract from product name
                    if not brand:
                        product_name = mc_product.name.lower()
                        if 'honda' in product_name:
                            brand = 'honda'
                        elif 'yamaha' in product_name:
                            brand = 'yamaha'
                        elif 'kawasaki' in product_name:
                            brand = 'kawasaki'
                        elif 'suzuki' in product_name:
                            brand = 'suzuki'
                        elif 'skygo' in product_name:
                            brand = 'skygo'
                    
                    order.wrc_brand = brand
                else:
                    order.wrc_brand = False
            else:
                order.wrc_brand = False

    def action_auto_fill_wrc(self):
        """Manual button to auto-fill WRC data from picking/lot info"""
        self.ensure_one()
        if not self.is_mc_sale:
            return
        
        try:
            # Get motorcycle product from order line
            mc_line = self.order_line.filtered(lambda l: self._is_mc_product(l.product_id))
            if not mc_line:
                return
                
            mc_product = mc_line[0].product_id
            
            # Find stock pickings for this sale order
            pickings = self.env['stock.picking'].search([('origin', '=', self.name)])
            
            # Get the motorcycle product from stock.picking
            picking_product = None
            target_picking = None
            lot_info = None
            
            for picking in pickings:
                # Try different field names for moves in picking
                moves = []
                if hasattr(picking, 'move_ids_without_package'):
                    moves = picking.move_ids_without_package
                elif hasattr(picking, 'move_lines'):
                    moves = picking.move_lines
                else:
                    moves = self.env['stock.move'].search([('picking_id', '=', picking.id)])
                
                for move in moves:
                    if self._is_mc_product(move.product_id):
                        picking_product = move.product_id
                        target_picking = picking
                        
                        # Get lot info from picking move
                        if hasattr(move, 'lot_ids') and move.lot_ids:
                            lot_info = move.lot_ids[0]
                        elif hasattr(move, 'move_line_ids'):
                            for move_line in move.move_line_ids:
                                if move_line.lot_id:
                                    lot_info = move_line.lot_id
                                    break
                        break
                if picking_product and lot_info:
                    break
            
            # If no lot found through picking, search directly by product
            if not lot_info and mc_product:
                lots = self.env['stock.production.lot'].search([
                    ('product_id', '=', mc_product.id)
                ], limit=1)
                if lots:
                    lot_info = lots[0]
            
            # DATA EXTRACTION - Following your specifications
            
            # 1. Grab MODEL from sale.order.line.product_id.name (extract text outside brackets and parentheses)
            if mc_product and mc_product.name:
                # Extract model name by removing text inside brackets [] and parentheses ()
                model_name = mc_product.name
                # Remove text inside brackets [...]
                model_name = re.sub(r'\[.*?\]', '', model_name)
                # Remove text inside parentheses (...)
                model_name = re.sub(r'\(.*?\)', '', model_name)
                # Clean up extra spaces and strip
                model_name = ' '.join(model_name.split()).strip()
                self.wrc_model = model_name
                _logger.info(f"WRC Auto-fill: Extracted model '{model_name}' from product name '{mc_product.name}'")
            elif mc_product and mc_product.default_code:
                self.wrc_model = mc_product.default_code
            elif mc_product:
                self.wrc_model = mc_product.name
            
            # 2. Grab BRAND from product internal reference (first 2 chars) or x_studio_brand
            brand = False
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
            
            # Alternative: get brand from lot x_studio_brand
            if not brand and lot_info and hasattr(lot_info, 'x_studio_brand'):
                brand = lot_info.x_studio_brand
                
            if brand:
                self.wrc_brand = brand
            
            # 3. Grab ENGINE NUMBER from stock.production.lot (engine_no field)
            if lot_info:
                if hasattr(lot_info, 'name'):  # Default lot name field
                    self.wrc_engine = lot_info.name
                elif hasattr(lot_info, 'engine_no'):
                    self.wrc_engine = lot_info.engine_no
                elif hasattr(lot_info, 'x_studio_engine_no'):
                    self.wrc_engine = lot_info.x_studio_engine_no
            
            # 4. Grab CHASSIS NUMBER from stock.production.lot.chasis_number
            if lot_info:
                if hasattr(lot_info, 'chasis_number'):
                    self.wrc_frame = lot_info.chasis_number
                elif hasattr(lot_info, 'chassis_number'):
                    self.wrc_frame = lot_info.chassis_number
                elif hasattr(lot_info, 'x_studio_chassis_no'):
                    self.wrc_frame = lot_info.x_studio_chassis_no
                elif hasattr(lot_info, 'frame_no'):
                    self.wrc_frame = lot_info.frame_no
            
            # 5. Grab COLOR from stock.production.lot.color
            if lot_info:
                if hasattr(lot_info, 'color'):
                    self.wrc_color = lot_info.color
                elif hasattr(lot_info, 'x_studio_color'):
                    self.wrc_color = lot_info.x_studio_color
            
            # 6. Grab QUANTITY from sale.order.line.product_uom_qty
            if mc_line and len(mc_line) > 0:
                self.wrc_qty = mc_line[0].product_uom_qty
                _logger.info(f"WRC Auto-fill: Set quantity to {self.wrc_qty} from sale line")
            else:
                _logger.warning("WRC Auto-fill: No motorcycle line found for quantity")
            
            # 6.1. Grab PAYMENT BASIS from sale.order.payment_term_id
            if self.payment_term_id:
                payment_term_name = self.payment_term_id.name.lower()
                if 'cash' in payment_term_name or 'immediate' in payment_term_name:
                    self.wrc_payment_basis = 'cash'
                elif 'installment' in payment_term_name or 'term' in payment_term_name or 'credit' in payment_term_name:
                    self.wrc_payment_basis = 'installment'
                else:
                    # Default based on payment term characteristics
                    if self.payment_term_id.line_ids and len(self.payment_term_id.line_ids) > 1:
                        self.wrc_payment_basis = 'installment'  # Multiple payment lines suggest installment
                    else:
                        self.wrc_payment_basis = 'cash'  # Single payment line suggests cash
                _logger.info(f"WRC Auto-fill: Set payment basis to {self.wrc_payment_basis} from payment term {self.payment_term_id.name}")
            else:
                self.wrc_payment_basis = 'cash'  # Default to cash if no payment term
                _logger.info("WRC Auto-fill: No payment term found, defaulting to cash")
            
            # Set purchase date from order date
            if not self.wrc_purchase_date and self.date_order:
                self.wrc_purchase_date = self.date_order.date()
            
            # === DEALER PROFILE AUTO-FILL ===
            # Set dealer information from sale order/company
            if not self.wrc_selling_dealer and self.company_id:
                self.wrc_selling_dealer = self.company_id.name
                _logger.info(f"WRC Auto-fill: Set selling dealer to {self.company_id.name}")
            
            if not self.wrc_dealer_code and self.company_id:
                # Try to extract dealer code from company or use a default pattern
                if hasattr(self.company_id, 'partner_id') and self.company_id.partner_id.ref:
                    self.wrc_dealer_code = self.company_id.partner_id.ref
                else:
                    # Generate a simple dealer code based on company name
                    company_name = self.company_id.name.upper()
                    dealer_code = ''.join(word[:2] for word in company_name.split()[:2])
                    self.wrc_dealer_code = dealer_code
                _logger.info(f"WRC Auto-fill: Set dealer code to {self.wrc_dealer_code}")
            
            if not self.wrc_dealer_address and self.company_id:
                # Build dealer address from company address
                address_parts = []
                if self.company_id.street:
                    address_parts.append(self.company_id.street)
                if self.company_id.street2:
                    address_parts.append(self.company_id.street2)
                if self.company_id.city:
                    address_parts.append(self.company_id.city)
                if self.company_id.state_id:
                    address_parts.append(self.company_id.state_id.name)
                if self.company_id.zip:
                    address_parts.append(self.company_id.zip)
                if self.company_id.country_id:
                    address_parts.append(self.company_id.country_id.name)
                
                self.wrc_dealer_address = ', '.join(address_parts)
                _logger.info(f"WRC Auto-fill: Set dealer address")
            
            # === CUSTOMER PROFILE AUTO-FILL ===
            # Set customer information from partner (customer_name is computed automatically)
            if not self.wrc_address and self.partner_id:
                # Build customer address from partner address
                address_parts = []
                if self.partner_id.street:
                    address_parts.append(self.partner_id.street)
                if self.partner_id.street2:
                    address_parts.append(self.partner_id.street2)
                if self.partner_id.city:
                    address_parts.append(self.partner_id.city)
                if self.partner_id.state_id:
                    address_parts.append(self.partner_id.state_id.name)
                if self.partner_id.zip:
                    address_parts.append(self.partner_id.zip)
                if self.partner_id.country_id:
                    address_parts.append(self.partner_id.country_id.name)
                
                self.wrc_address = ', '.join(address_parts)
                _logger.info(f"WRC Auto-fill: Set customer address")
            
            if not self.wrc_phone and self.partner_id:
                if self.partner_id.phone:
                    self.wrc_phone = self.partner_id.phone
                elif self.partner_id.mobile:
                    self.wrc_phone = self.partner_id.mobile
                _logger.info(f"WRC Auto-fill: Set customer phone")
            
            if not self.wrc_email and self.partner_id and self.partner_id.email:
                self.wrc_email = self.partner_id.email
                _logger.info(f"WRC Auto-fill: Set customer email")
            
            # Mark as auto-filled
            self.wrc_auto_filled = True
            
            return True
            
        except Exception as e:
            _logger.error(f"WRC Auto-fill error: {str(e)}")
            # If auto-fill fails, at least fill basic data
            try:
                mc_line = self.order_line.filtered(lambda l: self._is_mc_product(l.product_id))
                if mc_line:
                    mc_product = mc_line[0].product_id
                    if not self.wrc_model:
                        # Extract model name by removing text inside brackets [] and parentheses ()
                        model_name = mc_product.name
                        # Remove text inside brackets [...]
                        model_name = re.sub(r'\[.*?\]', '', model_name)
                        # Remove text inside parentheses (...)
                        model_name = re.sub(r'\(.*?\)', '', model_name)
                        # Clean up extra spaces and strip
                        model_name = ' '.join(model_name.split()).strip()
                        self.wrc_model = model_name
                    if not self.wrc_purchase_date:
                        self.wrc_purchase_date = self.date_order.date()
                    # Always set quantity from sale line
                    self.wrc_qty = mc_line[0].product_uom_qty
                    # Always set payment basis from payment term
                    if self.payment_term_id:
                        payment_term_name = self.payment_term_id.name.lower()
                        if 'cash' in payment_term_name or 'immediate' in payment_term_name:
                            self.wrc_payment_basis = 'cash'
                        elif 'installment' in payment_term_name or 'term' in payment_term_name:
                            self.wrc_payment_basis = 'installment'
                        else:
                            self.wrc_payment_basis = 'cash'
                    else:
                        self.wrc_payment_basis = 'cash'
                    _logger.info(f"WRC Auto-fill fallback: Set quantity to {self.wrc_qty}, payment basis to {self.wrc_payment_basis}")
            except Exception as ex:
                _logger.error(f"WRC Auto-fill fallback error: {str(ex)}")
            return True

    def action_refresh_wrc_data(self):
        """Manual refresh of WRC data and trigger auto-fill"""
        self.ensure_one()
        try:
            _logger.info(f"Manual refresh triggered for order {self.name}")
            
            # Force recompute of related fields
            self._compute_sale_type()
            self._compute_wrc_data_available()
            
            # Trigger auto-fill
            self.action_auto_fill_wrc()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'WRC data refreshed successfully',
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error(f"Manual refresh failed for {self.name}: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Refresh failed: {str(e)}',
                    'type': 'danger',
                }
            }

    @api.depends('wrc_records')
    def _compute_has_wrc(self):
        for record in self:
            record.has_wrc = bool(record.wrc_records)

    @api.depends('wrc_records')
    def _compute_wrc_count(self):
        for record in self:
            record.wrc_count = len(record.wrc_records)

    @api.depends('wrc_records', 'wrc_records.service_coupon_ids')
    def _compute_coupon_count(self):
        for record in self:
            coupon_count = 0
            for wrc in record.wrc_records:
                coupon_count += len(wrc.service_coupon_ids)
            record.coupon_count = coupon_count

    @api.depends('awb_sale_type', 'order_line', 'order_line.product_id')
    def _compute_sale_type(self):
        """Determine if this is a motorcycle sale based on awb_sale_type or product analysis"""
        for record in self:
            # First try to use awb_sale_type if available and populated
            if record.awb_sale_type:
                record.is_mc_sale = (record.awb_sale_type == 'mc')
            else:
                # Fallback to product analysis
                is_mc_sale = False
                for line in record.order_line:
                    if record._is_mc_product(line.product_id):
                        is_mc_sale = True
                        break
                record.is_mc_sale = is_mc_sale

    @api.depends('order_line', 'order_line.product_id')
    def _compute_awb_sale_type(self):
        """Determine sale type based on product analysis"""
        for record in self:
            sale_type = False
            for line in record.order_line:
                if record._is_mc_product(line.product_id):
                    sale_type = 'mc'
                    break
                elif record._is_spare_parts_product(line.product_id):
                    sale_type = 'sp'
                elif record._is_labour_product(line.product_id):
                    sale_type = 'labour'
            record.awb_sale_type = sale_type

    @api.depends('awb_sale_type', 'is_mc_sale', 'state', 'invoice_status')
    def _compute_show_wrc(self):
        """Determine if WRC functionality should be visible"""
        for record in self:
            # Only show WRC for motorcycle sales with valid invoice status
            # Check awb_sale_type first, fallback to is_mc_sale for compatibility
            is_motorcycle = False
            if record.awb_sale_type:
                is_motorcycle = (record.awb_sale_type == 'mc')
            else:
                is_motorcycle = record.is_mc_sale
            
            record.show_wrc = (
                is_motorcycle and 
                record.state in ['sale', 'done'] and
                record.invoice_status in ['invoiced', 'to invoice', 'no']
            )

    @api.depends('is_mc_sale', 'order_line', 'order_line.product_id', 'state', 'invoice_status')
    def _compute_wrc_data_available(self):
        """Check if WRC data is available and trigger auto-fill"""
        for record in self:
            data_available = False
            
            if record.is_mc_sale:
                # Simple check - just check if it's a MC sale
                data_available = True
                
                # Auto-fill WRC data if not already filled or if fields are empty
                if not record.wrc_auto_filled or not record.wrc_model or not record.wrc_brand:
                    try:
                        _logger.info(f"Triggering auto-fill for order {record.name}")
                        record.action_auto_fill_wrc()
                    except Exception as e:
                        # If auto-fill fails, continue without error
                        _logger.warning(f"Auto-fill failed for order {record.name}: {str(e)}")
                
                # Check for auto-save trigger (fully invoiced motorcycle sale)
                if record.invoice_status == 'invoiced' and not record.wrc_transferred:
                    # Check if WRC record already exists
                    existing_wrc = record.wrc_records.filtered(lambda r: r.state != 'cancelled')
                    if not existing_wrc:
                        # Check if all required data is available for auto-creation
                        can_auto_create = (
                            record.wrc_coupon_number and 
                            record.wrc_engine and 
                            record.wrc_frame
                        )
                        
                        if can_auto_create:
                            try:
                                _logger.info(f"Auto-save triggered for fully invoiced motorcycle sale {record.name} with coupon {record.wrc_coupon_number}")
                                record._create_wrc_record_auto()
                            except Exception as e:
                                _logger.error(f"Auto-save failed for order {record.name}: {str(e)}")
                        else:
                            _logger.info(f"Auto-save skipped for {record.name} - missing required data (coupon: {bool(record.wrc_coupon_number)}, engine: {bool(record.wrc_engine)}, frame: {bool(record.wrc_frame)})")
                    else:
                        _logger.info(f"WRC record already exists for {record.name}: {existing_wrc[0].wrc_no}")
            
            record.wrc_data_available = data_available

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

    def _is_spare_parts_product(self, product):
        """Check if product is spare parts"""
        if not product:
            return False
            
        name_lower = product.name.lower()
        if any(kw in name_lower for kw in ['spare', 'parts', 'part', 'component']):
            return True
            
        # Check product category for spare parts
        if hasattr(product, 'categ_id') and product.categ_id:
            categ_name = product.categ_id.name.lower()
            if any(kw in categ_name for kw in ['spare', 'parts', 'sp']):
                return True
        return False

    def _is_labour_product(self, product):
        """Check if product is labour/service"""
        if not product:
            return False
            
        name_lower = product.name.lower()
        if any(kw in name_lower for kw in ['labour', 'labor', 'service', 'work']):
            return True
            
        # Check product category for labour
        if hasattr(product, 'categ_id') and product.categ_id:
            categ_name = product.categ_id.name.lower()
            if any(kw in categ_name for kw in ['labour', 'labor', 'service']):
                return True
                
        # Check if it's a service type product
        if hasattr(product, 'type') and product.type == 'service':
            return True
        return False

    @api.model
    def create(self, vals):
        """Override create"""
        record = super().create(vals)
        return record

    def write(self, vals):
        """Override write to trigger auto-save when fully invoiced"""
        res = super().write(vals)
        
        # Check if invoice_status changed to 'invoiced' OR if coupon/engine/frame data is added
        if (vals.get('invoice_status') == 'invoiced' or 
            vals.get('wrc_coupon_number') or 
            vals.get('wrc_engine') or 
            vals.get('wrc_frame')):
            for record in self:
                if (record.is_mc_sale and 
                    not record.wrc_transferred and 
                    record.invoice_status == 'invoiced'):
                    # Check if WRC record already exists
                    existing_wrc = record.wrc_records.filtered(lambda r: r.state != 'cancelled')
                    if not existing_wrc:
                        # Check if all required data is available for auto-creation
                        can_auto_create = (
                            record.wrc_coupon_number and 
                            record.wrc_engine and 
                            record.wrc_frame
                        )
                        
                        if can_auto_create:
                            try:
                                _logger.info(f"Write method: Auto-save triggered for fully invoiced motorcycle sale {record.name} with coupon {record.wrc_coupon_number}")
                                record._create_wrc_record_auto()
                                record.wrc_transferred = True
                            except Exception as e:
                                _logger.error(f"Write method: Auto-save failed for {record.name}: {str(e)}")
                        else:
                            _logger.info(f"Write method: Auto-save skipped for {record.name} - missing required data (coupon: {bool(record.wrc_coupon_number)}, engine: {bool(record.wrc_engine)}, frame: {bool(record.wrc_frame)})")
                    else:
                        _logger.info(f"Write method: WRC record already exists for {record.name}: {existing_wrc[0].wrc_no}")
        
        return res

    def _create_wrc_record_auto(self):
        """Auto-create WRC record when sale order is fully invoiced"""
        self.ensure_one()
        
        # Check if WRC record already exists for this sale order
        existing_wrc = self.wrc_records.filtered(lambda r: r.state != 'cancelled')
        if existing_wrc:
            _logger.info(f"WRC record already exists for SO {self.name}: {existing_wrc[0].wrc_no}")
            return existing_wrc[0]
        
        # Auto-populate all fields first
        # Ensure auto-fill is executed to populate all WRC fields
        self.action_auto_fill_wrc()
        
        # Prepare comprehensive WRC data - mapping ALL WRC tab fields
        vals = {
            'state': 'draft',  # Always create as draft
            'sale_order_id': self.id,
            'partner_id': self.partner_id.id,
            'branch_id': self.company_id.id,
            
            # Customer Profile (auto-filled, read-only)
            'customer_name': self.wrc_customer_name,
            'customer_address': self.wrc_address,
            'phone': self.wrc_phone,
            'email': self.wrc_email,
            'birthday': self.wrc_birthday,
            
            # Dealer Profile (auto-filled, read-only)
            'selling_dealer': self.wrc_selling_dealer,
            'dealer_code': self.wrc_dealer_code,
            'dealer_address': self.wrc_dealer_address,
            
            # Unit Info (auto-filled where possible, editable if incomplete)
            'model': self.wrc_model,
            'engine_no': self.wrc_engine,
            'frame_no': self.wrc_frame,
            'purchase_date': self.wrc_purchase_date,
            'color': self.wrc_color,
            'brand': self.wrc_brand,
            'payment_basis': self.wrc_payment_basis,
            'qty': self.wrc_qty,
            'classification': self.wrc_classification,
            'coupon_number': self.wrc_coupon_number,  # Include coupon number
        }
        
        # Log the data being saved for debugging
        _logger.info(f"Auto-saving WRC record for SO {self.name} with data: {vals}")
        
        wrc_record = self.env['wrc.record'].create(vals)
        
        # Mark as transferred and log success
        self.wrc_transferred = True
        _logger.info(f"WRC record {wrc_record.wrc_no} auto-created for fully invoiced motorcycle sale {self.name}")
        
        # Note: Service coupons will be manually created later
        # Auto-generation only creates the WRC record with Customer Profile, Dealer Profile, and Unit Information
        
        return wrc_record

    def _create_wrc_record(self):
        """Create WRC record (wrapper for _create_wrc_record_auto)"""
        return self._create_wrc_record_auto()

    # === ACTION METHODS ===
    def action_view_wrc(self):
        """Open WRC records associated with this sale order"""
        self.ensure_one()
        action = self.env.ref('muti_dev_performance_evaluation_criteria.action_wrc_record').read()[0]
        if len(self.wrc_records) > 1:
            action['domain'] = [('id', 'in', self.wrc_records.ids)]
        elif len(self.wrc_records) == 1:
            action['views'] = [(self.env.ref('muti_dev_performance_evaluation_criteria.view_wrc_record_form').id, 'form')]
            action['res_id'] = self.wrc_records.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def action_view_coupons(self):
        """Open service coupons associated with WRC records"""
        self.ensure_one()
        action = self.env.ref('muti_dev_performance_evaluation_criteria.action_service_coupon').read()[0]
        action['domain'] = [('wrc_record_id', 'in', self.wrc_records.ids)]
        action['context'] = {
            'default_wrc_record_id': self.wrc_records[0].id if self.wrc_records else False,
        }
        return action

    def action_create_wrc_record(self):
        """Manually create WRC record for this motorcycle sale"""
        self.ensure_one()
        if not self.is_mc_sale:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'This is not a motorcycle sale order',
                    'type': 'warning',
                }
            }
        
        # Check if WRC record already exists for this sale order
        existing_wrc = self.wrc_records.filtered(lambda r: r.state != 'cancelled')
        if existing_wrc:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'WRC record already exists for this sale order: {existing_wrc[0].wrc_no}',
                    'type': 'warning',
                }
            }
        
        if self.wrc_transferred:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'WRC record already exists for this sale order',
                    'type': 'warning',
                }
            }
        
        # Auto-fill WRC data first
        self.action_auto_fill_wrc()
        
        # Create WRC record
        wrc_record = self._create_wrc_record()
        self.wrc_transferred = True
        
        if wrc_record:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'WRC record {wrc_record.wrc_no} created successfully',
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Failed to create WRC record',
                    'type': 'danger',
                }
            }
