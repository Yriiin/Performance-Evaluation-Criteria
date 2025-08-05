# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class ServiceCouponUseWizard(models.TransientModel):
    _name = 'service.coupon.use.wizard'
    _description = 'Service Coupon Use Wizard'
    
    coupon_id = fields.Many2one('service.coupon', 'Service Coupon', required=True)
    
    # Service Information
    servicing_branch_id = fields.Many2one('res.company', 'Servicing Branch', required=True)
    fsc_sequence = fields.Char('FSC NO./Coupon Code Sequence', readonly=True)
    fsc_code = fields.Char('FSC NO./Coupon Code', required=True)
    actual_service_date = fields.Date('Actual Service Date', required=True, default=fields.Date.today)
    accept_date = fields.Date('Accept Date', required=True, default=fields.Date.today)
    mileage = fields.Float('Mileage (km)', required=True)
    service_notes = fields.Text('Service Notes')
    
    # Coupon Information (readonly)
    coupon_type = fields.Selection(related='coupon_id.coupon_type', readonly=True)
    pms_km_min = fields.Integer(related='coupon_id.pms_km_min', readonly=True)
    pms_km_max = fields.Integer(related='coupon_id.pms_km_max', readonly=True)
    due_date = fields.Date(related='coupon_id.due_date', readonly=True)
    
    @api.onchange('coupon_id')
    def _onchange_coupon_id(self):
        if self.coupon_id:
            self.fsc_sequence = self.coupon_id.fsc_sequence
            self.servicing_branch_id = self.coupon_id.servicing_branch_id
    
    @api.constrains('mileage')
    def _check_mileage(self):
        for record in self:
            if record.mileage < record.pms_km_min or record.mileage > record.pms_km_max:
                raise UserError(
                    f"Mileage {record.mileage} km is outside the valid range "
                    f"({record.pms_km_min} - {record.pms_km_max} km) for this coupon."
                )
    
    def action_use_coupon(self):
        """Use the coupon with provided service information"""
        self.ensure_one()
        
        # Validate coupon can still be used
        if not self.coupon_id.can_use:
            raise UserError("This coupon cannot be used.")
        
        # Prepare service data
        service_data = {
            'servicing_branch_id': self.servicing_branch_id.id,
            'fsc_code': self.fsc_code,
            'actual_service_date': self.actual_service_date,
            'accept_date': self.accept_date,
            'mileage': self.mileage,
            'service_notes': self.service_notes,
        }
        
        # Complete the service
        return self.coupon_id.action_complete_service(service_data)
