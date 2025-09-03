# -*- coding: utf-8 -*-

from odoo import models, fields, api

class HrAfpPension(models.Model):
    _name = 'hr.afp.pension'
    _description = 'Sistema de Pensiones AFP'
    _rec_name = 'name'
    
    name = fields.Char(string='Nombre AFP', required=True)
    code = fields.Char(string='Código', required=True)
    fund_percentage = fields.Float(string='% Fondo', digits=(5,2), default=10.0, help="Porcentaje del fondo de pensiones (normalmente 10%)")
    insurance_percentage = fields.Float(string='% Seguro', digits=(5,2), default=1.37, help="Porcentaje del seguro de invalidez y sobrevivencia")
    commission_flow_percentage = fields.Float(string='% Comisión Flujo', digits=(5,2), help="Porcentaje de comisión por flujo")
    commission_mixed_percentage = fields.Float(string='% Comisión Mixta', digits=(5,2), help="Porcentaje de comisión mixta")
    commission_type = fields.Selection([
        ('flow', 'Flujo'),
        ('mixed', 'Mixta')
    ], string='Tipo Comisión Default', default='flow', help="Tipo de comisión por defecto para nuevos empleados")
    active = fields.Boolean(string='Activo', default=True)
    tope_amount = fields.Float(string='Tope S/', digits=(10,2), default=12027.91, help="Tope máximo para cálculo de comisión mixta")
    
    # Campos computados para mostrar totales
    total_flow_percentage = fields.Float(
        string='% Total (Flujo)', 
        compute='_compute_total_percentages',
        store=True,
        digits=(5,2),
        help="Total: Fondo + Seguro + Comisión Flujo"
    )
    
    total_mixed_percentage = fields.Float(
        string='% Total (Mixta)', 
        compute='_compute_total_percentages',
        store=True,
        digits=(5,2),
        help="Total: Fondo + Seguro + Comisión Mixta"
    )
    
    @api.depends('fund_percentage', 'insurance_percentage', 'commission_flow_percentage', 'commission_mixed_percentage')
    def _compute_total_percentages(self):
        for record in self:
            record.total_flow_percentage = record.fund_percentage + record.insurance_percentage + record.commission_flow_percentage
            record.total_mixed_percentage = record.fund_percentage + record.insurance_percentage + record.commission_mixed_percentage
    
    def get_commission_percentage(self, commission_type):
        """Retorna el porcentaje de comisión según el tipo"""
        self.ensure_one()
        if commission_type == 'flow':
            return self.commission_flow_percentage
        else:
            return self.commission_mixed_percentage
    
    def calculate_afp_discounts(self, base_amount, commission_type='flow'):
        """
        Calcula los descuentos AFP para un monto base
        Retorna un diccionario con fondo, seguro, comisión y total
        """
        self.ensure_one()
        
        # Calcular descuentos
        fund_discount = base_amount * (self.fund_percentage / 100)
        insurance_discount = base_amount * (self.insurance_percentage / 100)
        
        # Determinar comisión según el tipo
        if commission_type == 'mixed' and base_amount > self.tope_amount:
            # Si es mixta y supera el tope, usar el tope para la comisión
            commission_discount = self.tope_amount * (self.commission_mixed_percentage / 100)
        elif commission_type == 'mixed':
            commission_discount = base_amount * (self.commission_mixed_percentage / 100)
        else:
            # Flujo
            commission_discount = base_amount * (self.commission_flow_percentage / 100)
        
        return {
            'fund': round(fund_discount, 2),
            'insurance': round(insurance_discount, 2),
            'commission': round(commission_discount, 2),
            'total': round(fund_discount + insurance_discount + commission_discount, 2)
        }