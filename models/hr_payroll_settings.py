# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class HrPayrollSettings(models.Model):
    _name = 'hr.payroll.settings'
    _description = 'Configuración de Planilla de Sueldos'
    _rec_name = 'name'
    
    name = fields.Char(string='Descripción', required=True, default='Configuración de Planilla 2025')
    active = fields.Boolean(string='Activo', default=True)
    
    # Parámetros generales
    rmv_amount = fields.Float(string='Remuneración Mínima Vital (RMV)', digits=(10,2), default=1130.0, required=True,
                              help="Monto de la Remuneración Mínima Vital vigente")
    uit_amount = fields.Float(string='Unidad Impositiva Tributaria (UIT)', digits=(10,2), default=5350.0, required=True,
                              help="Valor de la UIT para el ejercicio fiscal")
    family_allowance_amount = fields.Float(string='Asignación Familiar', digits=(10,2), default=113.0, required=True,
                                          help="Monto de la asignación familiar mensual")
    
    # Parámetros de descuentos
    onp_percentage = fields.Float(string='Porcentaje ONP (%)', digits=(5,2), default=13.0, required=True,
                                  help="Porcentaje de descuento para ONP")
    
    # Parámetros de aportes del empleador
    essalud_percentage = fields.Float(string='Porcentaje EsSalud (%)', digits=(5,2), default=9.0, required=True,
                                     help="Porcentaje de aporte del empleador a EsSalud")
    sctr_percentage = fields.Float(string='Porcentaje SCTR (%)', digits=(5,2), default=1.23, required=True,
                                  help="Porcentaje de SCTR (Seguro Complementario de Trabajo de Riesgo)")
    
    # Topes y límites
    tope_prima_amount = fields.Float(string='Tope Prima (Comisión Mixta)', digits=(10,2), default=12027.91, required=True,
                                    help="Tope máximo para el cálculo de comisión mixta en AFP Prima")
    
    # Campos de control
    year = fields.Integer(string='Año', default=lambda self: fields.Date.today().year, required=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company, required=True)
    
    # Campos informativos calculados
    total_employee_cost_percentage = fields.Float(string='% Total Costo Empleado', compute='_compute_total_percentages', 
                                                  digits=(5,2), store=True,
                                                  help="Porcentaje total que representa el costo del empleador")
    
    @api.depends('essalud_percentage', 'sctr_percentage')
    def _compute_total_percentages(self):
        for record in self:
            record.total_employee_cost_percentage = record.essalud_percentage + record.sctr_percentage
    
    @api.model
    def get_current_settings(self):
        """Obtiene la configuración activa actual"""
        settings = self.search([
            ('active', '=', True),
            ('company_id', '=', self.env.company.id)
        ], limit=1, order='id desc')
        
        if not settings:
            # Crear configuración por defecto si no existe
            settings = self.create({
                'name': f'Configuración de Planilla {fields.Date.today().year}',
                'year': fields.Date.today().year,
            })
        
        return settings
    
    @api.model
    def get_parameter(self, parameter_name, default_value=0.0):
        """
        Obtiene un parámetro específico de la configuración activa
        
        Args:
            parameter_name (str): Nombre del campo del parámetro
            default_value: Valor por defecto si no se encuentra
            
        Returns:
            float: Valor del parámetro
        """
        settings = self.get_current_settings()
        return getattr(settings, parameter_name, default_value)
    
    def action_activate(self):
        """Activa esta configuración y desactiva las demás"""
        self.ensure_one()
        
        # Desactivar todas las configuraciones de la misma empresa
        other_settings = self.search([
            ('company_id', '=', self.company_id.id),
            ('id', '!=', self.id)
        ])
        other_settings.write({'active': False})
        
        # Activar esta configuración
        self.active = True
        
        # Actualizar topes en AFP si es necesario
        self._update_afp_topes()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _('Configuración Activada'),
                'message': _('La configuración ha sido activada exitosamente. Todos los cálculos de planilla usarán estos parámetros.'),
                'sticky': False,
            }
        }
    
    def _update_afp_topes(self):
        """Actualiza los topes en los registros de AFP"""
        # Actualizar AFP Prima con el nuevo tope
        afp_prima = self.env.ref('peruanita_payroll.afp_prima', raise_if_not_found=False)
        if afp_prima and hasattr(afp_prima, 'tope_amount'):
            afp_prima.tope_amount = self.tope_prima_amount
    
    @api.constrains('rmv_amount', 'uit_amount', 'family_allowance_amount')
    def _check_positive_amounts(self):
        """Validar que los montos sean positivos"""
        for record in self:
            if record.rmv_amount <= 0:
                raise models.ValidationError(_('La RMV debe ser mayor a cero'))
            if record.uit_amount <= 0:
                raise models.ValidationError(_('La UIT debe ser mayor a cero'))
            if record.family_allowance_amount < 0:
                raise models.ValidationError(_('La asignación familiar no puede ser negativa'))
    
    @api.constrains('onp_percentage', 'essalud_percentage', 'sctr_percentage')
    def _check_valid_percentages(self):
        """Validar que los porcentajes estén en rangos válidos"""
        for record in self:
            if not (10.0 <= record.onp_percentage <= 15.0):
                raise models.ValidationError(_('El porcentaje de ONP debe estar entre 10% y 15%'))
            if not (8.0 <= record.essalud_percentage <= 12.0):
                raise models.ValidationError(_('El porcentaje de EsSalud debe estar entre 8% y 12%'))
            if not (1.0 <= record.sctr_percentage <= 2.0):
                raise models.ValidationError(_('El porcentaje de SCTR debe estar entre 1% y 2%'))
    
    def name_get(self):
        """Personalizar el nombre mostrado"""
        result = []
        for record in self:
            name = f"{record.name} - {record.year}"
            if record.active:
                name += " (Activa)"
            result.append((record.id, name))
        return result