# -*- coding: utf-8 -*-

from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    # Sistema de Pensiones
    pension_system = fields.Selection([
        ('onp', 'ONP'),
        ('afp', 'AFP')
    ], string='Sistema de Pensión', default='onp')
    
    afp_id = fields.Many2one('hr.afp.pension', string='AFP')
    cuspp = fields.Char(string='Código CUSPP', size=12)
    commission_type = fields.Selection([
        ('flow', 'Flujo'),
        ('mixed', 'Mixta')
    ], string='Tipo Comisión AFP')
    
    # Datos adicionales
    has_family_allowance = fields.Boolean(string='Asignación Familiar', default=False)
    is_judicial_retention = fields.Boolean(string='Retención Judicial', default=False)
    judicial_retention_amount = fields.Float(string='Monto Retención Judicial', digits=(10,2))
    judicial_retention_percentage = fields.Float(string='% Retención Judicial', digits=(5,2))
    
    @api.onchange('pension_system')
    def _onchange_pension_system(self):
        if self.pension_system == 'onp':
            self.afp_id = False
            self.cuspp = False
            self.commission_type = False