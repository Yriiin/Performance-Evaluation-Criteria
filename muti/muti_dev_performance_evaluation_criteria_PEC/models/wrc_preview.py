# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
import logging

class WRCPreview(models.Model):
    _name = 'wrc.preview'
    _description = 'WRC Information Preview'
    _order = 'sale_order_id, id'
    _auto = True  # Ensure table creation

    # WRC Information
    wrc_number = fields.Char(string='WRC No.')
    
    # Customer Profile
    customer_id = fields.Many2one('res.partner', string='Customer Name', related='sale_order_id.partner_id', store=True)
    customer_street = fields.Char(string='Street', related='customer_id.street', store=True)
    customer_street2 = fields.Char(string='Street2', related='customer_id.street2', store=True)
    customer_city = fields.Char(string='City', related='customer_id.city', store=True)
    customer_state_id = fields.Many2one('res.country.state', string='State', related='customer_id.state_id', store=True)
    customer_zip = fields.Char(string='ZIP', related='customer_id.zip', store=True)
    customer_phone = fields.Char(string='Phone Number', related='customer_id.phone', store=True)
    customer_email = fields.Char(string='Email', related='customer_id.email', store=True)
    customer_address = fields.Text(string='Full Address', compute='_compute_full_address', store=True)
    
    # Dealer Profile
    selling_dealer_id = fields.Many2one('res.partner', string='Selling Dealer', related='sale_order_id.company_id.partner_id', store=True)
    dealer_code = fields.Char(string='Dealer Code', related='selling_dealer_id.ref', store=True)
    dealer_street = fields.Char(string='Street', related='selling_dealer_id.street', store=True)
    dealer_street2 = fields.Char(string='Street2', related='selling_dealer_id.street2', store=True)
    dealer_city = fields.Char(string='City', related='selling_dealer_id.city', store=True)
    dealer_state_id = fields.Many2one('res.country.state', string='State', related='selling_dealer_id.state_id', store=True)
    dealer_zip = fields.Char(string='ZIP', related='selling_dealer_id.zip', store=True)
    dealer_address = fields.Text(string='Dealer Address', compute='_compute_dealer_address', store=True)
    
    # Unit Information
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
    product_id = fields.Many2one('product.product', string='Product')
    model = fields.Char(string='Model', compute='_compute_product_info', store=True)
    engine_no = fields.Char(string='Engine No.', compute='_compute_lot_info', store=True)
    chassis_no = fields.Char(string='Chassis No.', compute='_compute_lot_info', store=True)
    purchase_date = fields.Datetime(string='Date Purchased', related='sale_order_id.date_order', store=True)
    color = fields.Char(string='Color')
    brand = fields.Char(string='Brand', compute='_compute_product_info', store=True)
    payment_basis = fields.Char(related='sale_order_id.payment_term_id.name', string='Payment Basis', store=True)
    quantity = fields.Float(string='QTY', related='sale_order_line_id.product_uom_qty', store=True)
    classification_id = fields.Many2one('wrc.classification', string='Classification')

    def action_view_wrc(self):
        """Open the WRC record in a form view when clicking on a line."""
        self.ensure_one()
        wrc = self.env['wrc.information'].search([('sale_order_line_id', '=', self.sale_order_line_id.id)], limit=1)
        if wrc:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'wrC.information',
                'res_id': wrc.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False

    @api.depends('product_id')
    def _compute_product_info(self):
        for record in self:
            if record.product_id:
                record.model = record.product_id.name
                record.brand = record.product_id.brand
            else:
                record.model = False
                record.brand = False

    @api.depends('dealer_street', 'dealer_street2', 'dealer_city', 'dealer_state_id', 'dealer_zip')
    def _compute_dealer_address(self):
        for record in self:
            address_parts = []
            if record.dealer_street:
                address_parts.append(record.dealer_street)
            if record.dealer_street2:
                address_parts.append(record.dealer_street2)
            if record.dealer_city:
                address_parts.append(record.dealer_city)
            if record.dealer_state_id:
                address_parts.append(record.dealer_state_id.name)
            if record.dealer_zip:
                address_parts.append(record.dealer_zip)
            record.dealer_address = '\n'.join(filter(None, address_parts))

    @api.depends('customer_street', 'customer_street2', 'customer_city', 'customer_state_id', 'customer_zip')
    def _compute_full_address(self):
        for record in self:
            address_parts = []
            if record.customer_street:
                address_parts.append(record.customer_street)
            if record.customer_street2:
                address_parts.append(record.customer_street2)
            if record.customer_city:
                address_parts.append(record.customer_city)
            if record.customer_state_id:
                address_parts.append(record.customer_state_id.name)
            if record.customer_zip:
                address_parts.append(record.customer_zip)
            record.customer_address = '\n'.join(filter(None, address_parts))

    @api.depends('sale_order_line_id', 'product_id')
    def _compute_lot_info(self):
        """Compute the engine number and chassis number from the lot/serial number."""
        for record in self:
            if not record.sale_order_line_id or not record.product_id:
                record.engine_no = False
                record.chassis_no = False
                continue

            lot = False
            found_chassis = False
            
            # 1. Try to find through stock moves
            if record.sale_order_line_id.move_ids:
                for move in record.sale_order_line_id.move_ids:
                    move_lines = move.move_line_ids.filtered(
                        lambda l: l.product_id.id == record.product_id.id and l.lot_id
                    )
                    for line in move_lines:
                        if line.lot_id and line.lot_id.chassis_number:
                            lot = line.lot_id
                            found_chassis = True
                            break
                        elif line.lot_id and not lot:
                            lot = line.lot_id
                    if found_chassis:
                        break

            # 2. If no lot found through moves, try searching pickings
            if not found_chassis and record.sale_order_line_id.order_id.picking_ids:
                for picking in record.sale_order_line_id.order_id.picking_ids:
                    move_lines = picking.move_line_ids.filtered(
                        lambda l: l.product_id.id == record.product_id.id and l.lot_id
                    )
                    for line in move_lines:
                        if line.lot_id and line.lot_id.chassis_number:
                            lot = line.lot_id
                            found_chassis = True
                            break
                        elif line.lot_id and not lot:
                            lot = line.lot_id
                    if found_chassis:
                        break

            # 3. If no lot with chassis found, try direct search by engine number
            if not found_chassis and record.engine_no:
                lots = self.env['stock.production.lot'].search([
                    ('name', '=', record.engine_no),
                    ('product_id', '=', record.product_id.id)
                ], limit=1)
                if lots:
                    lot = lots[0]

            # Set values based on what we found
            if lot:
                record.engine_no = lot.name
                # Explicitly read the chassis_number to ensure we get the value
                chassis = self.env['stock.production.lot'].sudo().browse(lot.id).chassis_number
                record.chassis_no = chassis
            else:
                record.engine_no = False
                record.chassis_no = False

            # Log for debugging
            _logger = logging.getLogger(__name__)
            _logger.info('WRC Preview Compute Lot Info - Sale Order: %s, Product: %s, Found Lot: %s, Chassis: %s',
                        record.sale_order_id.name, record.product_id.name, lot and lot.name, record.chassis_no)

    @api.model_create_multi
    def create(self, vals_list):
        records = super(WRCPreview, self).create(vals_list)
        # Trigger compute methods immediately after creation
        records._compute_product_info()
        records._compute_lot_info()
        return records

    def write(self, vals):
        result = super(WRCPreview, self).write(vals)
        if any(field in vals for field in ['product_id', 'sale_order_line_id']):
            self._compute_product_info()
            self._compute_lot_info()
        return result

    @api.model
    def refresh_from_order(self, order_id):
        """Refresh preview records for a sale order."""
        order = self.env['sale.order'].browse(order_id)
        existing = self.search([('sale_order_id', '=', order.id)])
        existing.unlink()
        
        # Only process if it's a motorcycle sale
        if not order.awb_sale_type or order.awb_sale_type != 'mc':
            return True
            
        previews = []
        for line in order.order_line:
            # Create preview for all order lines in MC sales
            vals = {
                'sale_order_id': order.id,
                'sale_order_line_id': line.id,
                'product_id': line.product_id.id,
                'wrc_number': False
            }
            
            # Check for existing WRC information
            wrc = self.env['wrc.information'].search([
                ('sale_order_line_id', '=', line.id)
            ], limit=1)
            if wrc:
                vals['wrc_number'] = wrc.name
            
            previews.append(vals)
        
        if previews:
            # Create records and let computed fields do their work
            self.create(previews)
        return True

    @api.model
    def create_wrc_records(self, order_id):
        """Create WRC records for lines with WRC numbers."""
        previews = self.search([
            ('sale_order_id', '=', order_id),
            ('wrc_number', '!=', False)
        ])
        WRC = self.env['wrc.information']
        for preview in previews:
            # Skip if WRC already exists for this line
            if WRC.search([('sale_order_line_id', '=', preview.sale_order_line_id.id)]):
                continue
            
            vals = {
                'name': preview.wrc_number,
                'sale_order_id': preview.sale_order_id.id,
                'sale_order_line_id': preview.sale_order_line_id.id,
                'product_id': preview.product_id.id,
                'purchase_date': preview.purchase_date,
                'brand': preview.brand,
                'model': preview.model,
                'engine_no': preview.engine_no,
                'chassis_no': preview.chassis_no,
                'frame_no': preview.frame_no,
            }
            WRC.create(vals)
        return True
