# -*- coding: utf-8 -*-
from odoo import models, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def create(self, vals):
        line = super(SaleOrderLine, self).create(vals)
        if line.order_id:
            try:
                line.order_id._sync_wrc_for_order(line.order_id)
            except Exception:
                pass
        return line

    def write(self, vals):
        res = super(SaleOrderLine, self).write(vals)
        for line in self:
            if line.order_id:
                try:
                    line.order_id._sync_wrc_for_order(line.order_id)
                except Exception:
                    pass
        return res

    def unlink(self):
        orders = list(set([l.order_id for l in self if l.order_id]))
        res = super(SaleOrderLine, self).unlink()
        for order in orders:
            try:
                order._sync_wrc_for_order(order)
            except Exception:
                pass
        return res
