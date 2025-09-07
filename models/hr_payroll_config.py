# -*- coding: utf-8 -*-

from odoo import models, fields, api

class HrPayrollConfig(models.TransientModel):
    _name = 'hr.payroll.config'
    _description = 'Configuración de Planilla de Sueldos'
    
    # Parámetros generales
    rmv_amount = fields.Float(string='Remuneración Mínima Vital', digits=(10,2), default=1130.0)
    uit_amount = fields.Float(string='UIT (Unidad Impositiva Tributaria)', digits=(10,2), default=5350.0)
    family_allowance_amount = fields.Float(string='Asignación Familiar', digits=(10,2), default=113.0)
    
    # Parámetros de descuentos
    onp_percentage = fields.Float(string='% ONP', digits=(5,2), default=13.0)
    
    # Parámetros de aportes del empleador
    essalud_percentage = fields.Float(string='% EsSalud', digits=(5,2), default=9.0)
    sctr_percentage = fields.Float(string='% SCTR', digits=(5,2), default=1.23)
    
    # Topes y límites
    tope_prima_amount = fields.Float(string='Tope Prima (Comisión Mixta)', digits=(10,2), default=12027.91)
    
    @api.model
    def default_get(self, fields_list):
        """Carga los valores actuales desde ir.config_parameter"""
        res = super().default_get(fields_list)
        
        ICP = self.env['ir.config_parameter'].sudo()
        
        res.update({
            'rmv_amount': float(ICP.get_param('hr.payroll.rmv_2025', '1130.0')),
            'uit_amount': float(ICP.get_param('hr.payroll.uit_2025', '5350.0')),
            'family_allowance_amount': float(ICP.get_param('hr.payroll.family_allowance_2025', '113.0')),
            'onp_percentage': float(ICP.get_param('hr.payroll.onp_percentage', '13.0')),
            'essalud_percentage': float(ICP.get_param('hr.payroll.essalud_percentage', '9.0')),
            'sctr_percentage': float(ICP.get_param('hr.payroll.sctr_percentage', '1.23')),
            'tope_prima_amount': float(ICP.get_param('hr.payroll.tope_prima', '12027.91')),
        })
        
        return res
    
    def save_configuration(self):
        """Guarda la configuración en ir.config_parameter"""
        self.ensure_one()
        
        ICP = self.env['ir.config_parameter'].sudo()
        
        ICP.set_param('hr.payroll.rmv_2025', str(self.rmv_amount))
        ICP.set_param('hr.payroll.uit_2025', str(self.uit_amount))
        ICP.set_param('hr.payroll.family_allowance_2025', str(self.family_allowance_amount))
        ICP.set_param('hr.payroll.onp_percentage', str(self.onp_percentage))
        ICP.set_param('hr.payroll.essalud_percentage', str(self.essalud_percentage))
        ICP.set_param('hr.payroll.sctr_percentage', str(self.sctr_percentage))
        ICP.set_param('hr.payroll.tope_prima', str(self.tope_prima_amount))
        
        # Actualizar topes en AFP
        afp_prima = self.env.ref('peruanita_payroll.afp_prima', raise_if_not_found=False)
        if afp_prima:
            afp_prima.tope_amount = self.tope_prima_amount
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': 'Configuración guardada',
                'message': 'Los parámetros de planilla han sido actualizados exitosamente.',
                'sticky': False,
            }
        }