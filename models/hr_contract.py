# -*- coding: utf-8 -*-

from odoo import models, fields, api

class HrContract(models.Model):
    _inherit = 'hr.contract'
    
    # Configuración de bonificaciones regulares
    night_bonus = fields.Float(string='Bonificación', digits=(10,2), default=0.0)
    other_bonus = fields.Float(string='Otras Bonificaciones', digits=(10,2), default=0.0)
    
    # Configuración de descuentos fijos
    fifth_category = fields.Float(string='5ta Categoría', digits=(10,2), default=0.0)
    
    # Configuración de seguros
    has_sctr = fields.Boolean(string='Tiene SCTR', default=False)
    sctr_percentage = fields.Float(string='% SCTR', digits=(5,2), default=1.23)
    essalud_percentage = fields.Float(string='% EsSalud', digits=(5,2), default=9.0)