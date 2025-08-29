# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    wrc_information_ids = fields.One2many('wrc.information', 'sale_order_id', string='WRC Information')
    wrc_preview_ids = fields.One2many('wrc.preview', 'sale_order_id', string='WRC Preview Lines')
    awb_sale_type = fields.Char(string='Sale Type', store=True)
    has_honda_products = fields.Boolean(string='Has Honda Products', compute='_compute_has_honda_products', store=True)

    @api.depends('order_line.product_id')
    def _compute_has_honda_products(self):
        for order in self:
            # Initialize as False
            order.has_honda_products = False
            
            for line in order.order_line:
                if not line.product_id:
                    continue
                
                # Check if product default code starts with 'HO'
                default_code = line.product_id.default_code or ''
                if default_code.startswith('HO'):
                    order.has_honda_products = True
                    break
    @api.model
    def create(self, vals):
        record = super(SaleOrder, self).create(vals)
        if record.awb_sale_type == 'mc':
            self.env['wrc.preview'].refresh_from_order(record.id)
        return record

    def write(self, vals):
        result = super(SaleOrder, self).write(vals)
        if 'awb_sale_type' in vals or 'order_line' in vals:
            for order in self:
                # Refresh WRC preview if needed
                if order.awb_sale_type == 'mc':
                    self.env['wrc.preview'].refresh_from_order(order.id)
                # Force recompute has_honda_products
                order._compute_has_honda_products()
        return result

    @api.model
    def _init_wrc_previews(self):
        """Initialize WRC preview records for all existing motorcycle sales."""
        mc_orders = self.search([('awb_sale_type', '=', 'mc')])
        for order in mc_orders:
            self.env['wrc.preview'].refresh_from_order(order.id)
        return True

    @api.model
    def recompute_honda_products(self):
        """Recompute has_honda_products for sales orders."""
        # Find orders that might need recomputation
        orders = self.search([('awb_sale_type', 'ilike', 'motorcycle')])
        for order in orders:
            order._compute_has_honda_products()
        return True
