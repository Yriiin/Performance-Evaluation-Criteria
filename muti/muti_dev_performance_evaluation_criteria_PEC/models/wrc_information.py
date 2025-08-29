# -*- coding: utf-8 -*-
from odoo import models, fields, api, _



class WRCInformation(models.Model):
    _name = 'wrc.information'
    _description = 'WRC Information'

    # WRC Information
    name = fields.Char(string='WRC Number')
    
    # Customer Profile
    customer_id = fields.Many2one('res.partner', string='Customer Name', related='sale_order_id.partner_id', store=True)
    customer_street = fields.Char(string='Street', related='customer_id.street', store=True)
    customer_street2 = fields.Char(string='Street2', related='customer_id.street2', store=True)
    customer_city = fields.Char(string='City', related='customer_id.city', store=True)
    customer_state_id = fields.Many2one('res.country.state', string='State', related='customer_id.state_id', store=True)
    customer_zip = fields.Char(string='ZIP', related='customer_id.zip', store=True)
    customer_phone = fields.Char(string='Phone Number', related='customer_id.phone', store=True)
    customer_email = fields.Char(string='Email', related='customer_id.email', store=True)
    
    # Computed full address
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
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', ondelete='cascade')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
    product_id = fields.Many2one('product.product', string='Product')
    model = fields.Char(string='Model')
    engine_no = fields.Char(string='Engine No.')
    chassis_no = fields.Char(string='Chassis No.')
    purchase_date = fields.Datetime(string='Date Purchased')
    color = fields.Char(string='Color')
    brand = fields.Char(string='Brand')
    payment_basis = fields.Char(related='sale_order_id.payment_term_id.name', string='Payment Basis', store=True)
    quantity = fields.Float(string='QTY', related='sale_order_line_id.product_uom_qty', store=True)
    classification_id = fields.Many2one('wrc.classification', string='Classification')

    _sql_constraints = [
        ('sale_line_unique', 'unique(sale_order_line_id)', 'WRC for this sale order line already exists.')
    ]

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



    @api.model
    def create_from_order_line(self, order, line):
        """Helper to create or update a WRC record from an order line."""
        lot = getattr(line, 'lot_id', False)
        engine_no = chassis_no = False
        if lot and getattr(lot, 'product_id', False) and lot.product_id.id == line.product_id.id:
            engine_no = lot.name
            chassis_no = getattr(lot, 'chassis_number', False)

        vals = {
            'name': False,
            'sale_order_id': order.id,
            'sale_order_line_id': line.id,
            'product_id': line.product_id.id or False,
            'purchase_date': order.date_order,
            'brand': getattr(line.product_id, 'brand', False) or (line.product_id.brand if hasattr(line.product_id, 'brand') else False) or False,
            'model': line.product_id.name or False,
            'engine_no': engine_no,
            'chassis_no': chassis_no,
            'frame_no': getattr(lot, 'frame_no', False) if lot else False,
            'classification': getattr(line.product_id, 'classification', False) or False,
        }
        # Convert classification string to classification record id if present
        class_name = vals.pop('classification', False)
        if class_name:
            cls = self.env['wrc.classification'].search([('name', '=', class_name)], limit=1)
            if not cls:
                cls = self.env['wrc.classification'].create({'name': class_name})
            vals['classification_id'] = cls.id

        if not vals.get('name'):
            vals['name'] = ''
        return self.create(vals)
