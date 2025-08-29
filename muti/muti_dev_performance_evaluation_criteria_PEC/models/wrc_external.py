# -*- coding: utf-8 -*-
from odoo import models, fields


class WRCExternal(models.Model):
    _name = 'wrc.external'
    _description = 'External WRC'

    name = fields.Char(string='WRC Number', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer')
    product_id = fields.Many2one('product.product', string='Product')
    purchase_date = fields.Datetime(string='Purchase Date')
    brand = fields.Char(string='Brand')
    model = fields.Char(string='Model')
    engine_no = fields.Char(string='Engine No.')
    frame_no = fields.Char(string='Frame No.')
    classification_id = fields.Many2one('wrc.classification', string='Classification')
