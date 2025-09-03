# -*- coding: utf-8 -*-

from odoo import models, fields, api

class HrPayrollLine(models.Model):
    _name = 'hr.payroll.line'
    _description = 'Línea de Planilla'
    _rec_name = 'employee_id'
    _order = 'sequence, employee_id'
    
    sequence = fields.Integer(string='Secuencia', default=10)
    payroll_id = fields.Many2one('hr.payroll.monthly', string='Planilla', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    contract_id = fields.Many2one('hr.contract', string='Contrato', required=True)
    
    # Datos del empleado (readonly, traídos del empleado)
    identification_id = fields.Char(related='employee_id.identification_id', string='DNI', readonly=True)
    job_id = fields.Many2one(related='employee_id.job_id', string='Cargo', readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', string='Departamento', readonly=True)
    
    # Sistema de pensiones
    pension_system = fields.Selection(related='employee_id.pension_system', string='Sistema Pensión', readonly=True)
    afp_id = fields.Many2one(related='employee_id.afp_id', string='AFP', readonly=True)
    cuspp = fields.Char(related='employee_id.cuspp', string='CUSPP', readonly=True)
    commission_type = fields.Selection(related='employee_id.commission_type', string='Tipo Comisión', readonly=True)
    
    # Días y asistencia
    worked_days = fields.Integer(string='Días Trabajados', default=30)
    tardiness_count = fields.Integer(string='Tardanzas', default=0)
    medical_rest_days = fields.Integer(string='Días Descanso Médico', default=0)
    vacation_days = fields.Integer(string='Días Vacaciones', default=0)
    
    # INGRESOS
    salary = fields.Float(string='Sueldo Base', digits=(10,2), required=True)
    family_allowance = fields.Float(string='Asignación Familiar', digits=(10,2), default=0.0)
    night_bonus = fields.Float(string='Bonificación Nocturna', digits=(10,2), default=0.0)
    medical_rest_amount = fields.Float(string='Monto Descanso Médico', digits=(10,2), default=0.0)
    other_bonus = fields.Float(string='Otras Bonificaciones', digits=(10,2), default=0.0)
    vacation_amount = fields.Float(string='Monto Vacaciones', digits=(10,2), default=0.0)
    overtime_amount = fields.Float(string='Horas Extras', digits=(10,2), default=0.0)
    
    # Total Ingresos
    total_income = fields.Float(string='Total Ingresos', compute='_compute_total_income', store=True, digits=(10,2))
    
    # DESCUENTOS - AFP
    afp_fund = fields.Float(string='AFP Fondo', compute='_compute_pension_discounts', store=True, digits=(10,2))
    afp_insurance = fields.Float(string='AFP Seguro', compute='_compute_pension_discounts', store=True, digits=(10,2))
    afp_commission = fields.Float(string='AFP Comisión', compute='_compute_pension_discounts', store=True, digits=(10,2))
    afp_total = fields.Float(string='Total AFP', compute='_compute_pension_discounts', store=True, digits=(10,2))
    
    # DESCUENTOS - ONP
    onp_discount = fields.Float(string='ONP', compute='_compute_pension_discounts', store=True, digits=(10,2))
    
    # OTROS DESCUENTOS
    advance_gratification = fields.Float(string='Adelanto Gratificación', digits=(10,2), default=0.0)
    fifth_category = fields.Float(string='5ta Categoría', digits=(10,2), default=0.0)
    tardiness_discount = fields.Float(string='Descuento Tardanzas', compute='_compute_tardiness_discount', store=True, digits=(10,2))
    judicial_retention = fields.Float(string='Retención Judicial', digits=(10,2), default=0.0)
    advance_payment = fields.Float(string='Adelanto', digits=(10,2), default=0.0)
    
    # Total Descuentos
    total_discount = fields.Float(string='Total Descuentos', compute='_compute_total_discount', store=True, digits=(10,2))
    
    # NETO A PAGAR
    net_pay = fields.Float(string='Neto a Pagar', compute='_compute_net_pay', store=True, digits=(10,2))
    
    # APORTES DEL EMPLEADOR
    essalud = fields.Float(string='EsSalud', compute='_compute_employer_contributions', store=True, digits=(10,2))
    sctr = fields.Float(string='SCTR', compute='_compute_employer_contributions', store=True, digits=(10,2))
    total_employer_contribution = fields.Float(string='Total Aportes Empleador', compute='_compute_employer_contributions', store=True, digits=(10,2))
    
    # Datos de vacaciones
    vacation_from = fields.Date(string='Vacaciones Desde')
    vacation_to = fields.Date(string='Vacaciones Hasta')
    
    # Datos de descanso médico
    medical_rest_from = fields.Date(string='Descanso Médico Desde')
    medical_rest_to = fields.Date(string='Descanso Médico Hasta')
    
    @api.depends('salary', 'family_allowance', 'night_bonus', 'medical_rest_amount', 
                 'other_bonus', 'vacation_amount', 'overtime_amount')
    def _compute_total_income(self):
        for line in self:
            line.total_income = (
                line.salary + 
                line.family_allowance + 
                line.night_bonus + 
                line.medical_rest_amount + 
                line.other_bonus + 
                line.vacation_amount + 
                line.overtime_amount
            )
    
    @api.depends('total_income', 'pension_system', 'afp_id')
    def _compute_pension_discounts(self):
        for line in self:
            if line.pension_system == 'afp' and line.afp_id:
                # Cálculo AFP
                line.afp_fund = line.total_income * (line.afp_id.fund_percentage / 100)
                line.afp_insurance = line.total_income * (line.afp_id.insurance_percentage / 100)
                line.afp_commission = line.total_income * (line.afp_id.commission_percentage / 100)
                line.afp_total = line.afp_fund + line.afp_insurance + line.afp_commission
                line.onp_discount = 0.0
            elif line.pension_system == 'onp':
                # Cálculo ONP (13%)
                line.onp_discount = line.total_income * 0.13
                line.afp_fund = 0.0
                line.afp_insurance = 0.0
                line.afp_commission = 0.0
                line.afp_total = 0.0
            else:
                line.afp_fund = 0.0
                line.afp_insurance = 0.0
                line.afp_commission = 0.0
                line.afp_total = 0.0
                line.onp_discount = 0.0
    
    @api.depends('tardiness_count', 'salary', 'worked_days')
    def _compute_tardiness_discount(self):
        for line in self:
            if line.tardiness_count > 0 and line.worked_days > 0:
                # Descuento proporcional por tardanzas
                daily_salary = line.salary / 30
                line.tardiness_discount = (daily_salary / 8) * line.tardiness_count  # Asumiendo 8 horas por día
            else:
                line.tardiness_discount = 0.0
    
    @api.depends('afp_total', 'onp_discount', 'advance_gratification', 'fifth_category',
                 'tardiness_discount', 'judicial_retention', 'advance_payment')
    def _compute_total_discount(self):
        for line in self:
            line.total_discount = (
                line.afp_total + 
                line.onp_discount + 
                line.advance_gratification + 
                line.fifth_category + 
                line.tardiness_discount + 
                line.judicial_retention + 
                line.advance_payment
            )
    
    @api.depends('total_income', 'total_discount')
    def _compute_net_pay(self):
        for line in self:
            line.net_pay = line.total_income - line.total_discount
    
    @api.depends('total_income', 'contract_id.essalud_percentage', 'contract_id.sctr_percentage', 'contract_id.has_sctr')
    def _compute_employer_contributions(self):
        for line in self:
            # EsSalud (9% por defecto)
            essalud_percentage = line.contract_id.essalud_percentage if line.contract_id else 9.0
            line.essalud = line.total_income * (essalud_percentage / 100)
            
            # SCTR (1.23% por defecto si tiene)
            if line.contract_id and line.contract_id.has_sctr:
                sctr_percentage = line.contract_id.sctr_percentage or 1.23
                line.sctr = line.total_income * (sctr_percentage / 100)
            else:
                line.sctr = 0.0
            
            line.total_employer_contribution = line.essalud + line.sctr
    
    @api.onchange('worked_days', 'salary')
    def _onchange_worked_days(self):
        """Ajusta el salario según días trabajados"""
        if self.worked_days < 30 and self.worked_days > 0:
            self.salary = (self.contract_id.wage / 30) * self.worked_days if self.contract_id else 0.0
    
    def _compute_all_amounts(self):
        """Método para forzar el recálculo de todos los campos computados"""
        self._compute_total_income()
        self._compute_pension_discounts()
        self._compute_tardiness_discount()
        self._compute_total_discount()
        self._compute_net_pay()
        self._compute_employer_contributions()