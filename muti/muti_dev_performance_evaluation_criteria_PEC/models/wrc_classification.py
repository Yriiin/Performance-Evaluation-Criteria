# -*- coding: utf-8 -*-
from odoo import models, fields


class WRCClassification(models.Model):
    _name = 'wrc.classification'
    _description = 'WRC Classification'

    name = fields.Char(string='Classification', required=True)

