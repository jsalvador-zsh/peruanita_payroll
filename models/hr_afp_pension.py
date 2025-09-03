# -*- coding: utf-8 -*-

from odoo import models, fields, api

class HrAfpPension(models.Model):
    _name = 'hr.afp.pension'
    _description = 'Sistema de Pensiones AFP'
    _rec_name = 'name'
    
    name = fields.Char(string='Nombre AFP', required=True)
    code = fields.Char(string='Código', required=True)
    fund_percentage = fields.Float(string='% Fondo', digits=(5,2), default=10.0)
    insurance_percentage = fields.Float(string='% Seguro', digits=(5,2), default=1.74)
    commission_percentage = fields.Float(string='% Comisión', digits=(5,2), default=1.20)
    commission_type = fields.Selection([
        ('flow', 'Flujo'),
        ('mixed', 'Mixta')
    ], string='Tipo Comisión', default='flow')
    active = fields.Boolean(string='Activo', default=True)
    
    @api.depends('fund_percentage', 'insurance_percentage', 'commission_percentage')
    def _compute_total_percentage(self):
        for record in self:
            record.total_percentage = record.fund_percentage + record.insurance_percentage + record.commission_percentage
    
    total_percentage = fields.Float(
        string='% Total', 
        compute='_compute_total_percentage',
        store=True,
        digits=(5,2)
    )