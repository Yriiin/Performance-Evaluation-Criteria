# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class WrcCreationWizard(models.TransientModel):
    _name = 'wrc.creation.wizard'
    _description = 'WRC Record Creation Wizard'

    sale_order_id = fields.Many2one(
        'sale.order', 
        'Select Sale Order', 
        required=True,
        domain="[('awb_sale_type', '=', 'mc'), ('state', 'in', ['sale', 'done'])]"
    )
    
    @api.model
    def get_available_sale_orders_domain(self):
        """Get sale orders that don't already have WRC records"""
        # Find sale orders that already have WRC records
        existing_wrc_sale_orders = self.env['wrc.record'].search([]).mapped('sale_order_id').ids
        
        domain = [
            ('awb_sale_type', '=', 'mc'),  # Only motorcycle sales
            ('state', 'in', ['sale', 'done']),  # Only confirmed orders
        ]
        
        # Exclude sale orders that already have WRC records
        if existing_wrc_sale_orders:
            domain.append(('id', 'not in', existing_wrc_sale_orders))
            
        return domain

    def create_wrc_record(self):
        """Create WRC record with all data pre-filled from selected sale order"""
        self.ensure_one()
        
        if not self.sale_order_id:
            raise UserError("Please select a sale order.")
        
        so = self.sale_order_id
        _logger.info(f"WRC Wizard: Creating WRC record from sale order {so.name}")
        
        # Prepare all values from sale order
        vals = self._prepare_wrc_values_from_sale_order(so)
        
        # Create the WRC record
        wrc_record = self.env['wrc.record'].create(vals)
        _logger.info(f"WRC Wizard: Created WRC record {wrc_record.wrc_no} from sale order {so.name}")
        
        # Return action to open the newly created record
        return {
            'type': 'ir.actions.act_window',
            'name': 'WRC Record',
            'res_model': 'wrc.record',
            'res_id': wrc_record.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'create': False}  # Disable create mode since record is already created
        }

    def _prepare_wrc_values_from_sale_order(self, so):
        """Prepare all WRC record values from sale order"""
        vals = {
            'sale_order_id': so.id,
            'state': 'draft'
        }
        
        # Customer information
        if so.partner_id:
            vals['partner_id'] = so.partner_id.id
            vals['customer_name'] = so.partner_id.name
            
            # Build customer address
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
            
            if address_parts:
                vals['customer_address'] = ', '.join(address_parts)
            
            # Customer contact info
            if so.partner_id.phone:
                vals['phone'] = so.partner_id.phone
            elif so.partner_id.mobile:
                vals['phone'] = so.partner_id.mobile
                
            if so.partner_id.email:
                vals['email'] = so.partner_id.email
                
            # Birthday from partner
            if hasattr(so.partner_id, 'birthday') and so.partner_id.birthday:
                vals['birthday'] = so.partner_id.birthday

        # Get motorcycle product from order line
        mc_line = so.order_line.filtered(lambda l: so._is_mc_product(l.product_id))
        if mc_line:
            mc_product = mc_line[0].product_id
            vals['qty'] = mc_line[0].product_uom_qty
            
            # Extract model from product name
            if mc_product and mc_product.name:
                import re
                model_name = mc_product.name
                # Remove text inside brackets and parentheses
                model_name = re.sub(r'\[.*?\]', '', model_name)
                model_name = re.sub(r'\(.*?\)', '', model_name)
                model_name = ' '.join(model_name.split()).strip()
                vals['model'] = model_name
            
            # Extract brand from product code
            if mc_product and mc_product.default_code and len(mc_product.default_code) >= 2:
                code = mc_product.default_code[:2].upper()
                brand_map = {
                    'HO': 'honda',
                    'YA': 'yamaha',
                    'KA': 'kawasaki',
                    'SU': 'suzuki',
                    'SK': 'skygo'
                }
                brand = brand_map.get(code)
                if brand:
                    vals['brand'] = brand
            
            # Get stock lot information for engine and frame numbers
            self._add_stock_lot_info(vals, so, mc_product)
        
        # Get WRC tab information if available
        self._add_wrc_tab_info(vals, so)
        
        # Set branch from sale order
        if hasattr(so, 'company_id') and so.company_id:
            vals['branch_id'] = so.company_id.id
        
        _logger.info(f"WRC Wizard: Prepared {len(vals)} fields for WRC record")
        return vals

    def _add_stock_lot_info(self, vals, so, mc_product):
        """Add stock lot information to WRC values"""
        # Find stock lot information
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
        
        # If no lot found through picking, search directly
        if not lot_info and mc_product:
            lots = self.env['stock.production.lot'].search([
                ('product_id', '=', mc_product.id)
            ], limit=1)
            if lots:
                lot_info = lots[0]
        
        if lot_info:
            # Engine number
            if hasattr(lot_info, 'name'):
                vals['engine_no'] = lot_info.name
            elif hasattr(lot_info, 'engine_no'):
                vals['engine_no'] = lot_info.engine_no
            elif hasattr(lot_info, 'x_studio_engine_no'):
                vals['engine_no'] = lot_info.x_studio_engine_no
            
            # Frame number
            if hasattr(lot_info, 'chasis_number'):
                vals['frame_no'] = lot_info.chasis_number
            elif hasattr(lot_info, 'chassis_number'):
                vals['frame_no'] = lot_info.chassis_number
            elif hasattr(lot_info, 'x_studio_chassis_no'):
                vals['frame_no'] = lot_info.x_studio_chassis_no
            elif hasattr(lot_info, 'frame_no'):
                vals['frame_no'] = lot_info.frame_no
            
            # Color
            if hasattr(lot_info, 'color'):
                vals['color'] = lot_info.color
            elif hasattr(lot_info, 'x_studio_color'):
                vals['color'] = lot_info.x_studio_color
            
            # Brand from lot if not found from product
            if 'brand' not in vals and hasattr(lot_info, 'x_studio_brand'):
                vals['brand'] = lot_info.x_studio_brand

    def _add_wrc_tab_info(self, vals, so):
        """Add WRC tab information from sale order"""
        # Override with WRC tab data if available
        if hasattr(so, 'wrc_color') and so.wrc_color:
            vals['color'] = str(so.wrc_color).strip()
        
        if hasattr(so, 'wrc_engine') and so.wrc_engine:
            vals['engine_no'] = so.wrc_engine
        
        if hasattr(so, 'wrc_frame') and so.wrc_frame:
            vals['frame_no'] = so.wrc_frame
        
        if hasattr(so, 'wrc_classification') and so.wrc_classification:
            vals['classification'] = so.wrc_classification
        
        if hasattr(so, 'wrc_model') and so.wrc_model:
            vals['model'] = so.wrc_model
        
        if hasattr(so, 'wrc_brand') and so.wrc_brand:
            vals['brand'] = so.wrc_brand
        
        if hasattr(so, 'wrc_payment_basis') and so.wrc_payment_basis:
            vals['payment_basis'] = so.wrc_payment_basis
        
        if hasattr(so, 'wrc_qty') and so.wrc_qty:
            vals['qty'] = so.wrc_qty
