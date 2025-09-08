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
    exempt_afp_commission = fields.Boolean(related='employee_id.exempt_afp_commission', string='Exento Comisión AFP', readonly=True)
    
    # Días y asistencia
    worked_days = fields.Integer(string='Días Trabajados', default=30)
    tardiness_count = fields.Integer(string='Tardanzas', default=0)
    medical_rest_days = fields.Integer(string='Días Descanso Médico', default=0)
    vacation_days = fields.Integer(string='Días Vacaciones', default=0)
    
    # INGRESOS
    salary = fields.Float(string='Sueldo Base', digits=(10,2), required=True)
    family_allowance = fields.Float(string='Asignación Familiar', digits=(10,2), default=0.0)
    night_bonus = fields.Float(string='Bonificación', compute='_compute_night_bonus', store= True , digits=(10,2))
    medical_rest_amount = fields.Float(string='Monto Descanso Médico', default=0.0, store=True, compute='_compute_medical_rest_amount', digits=(10,2))
    other_bonus = fields.Float(string='Otras Bonificaciones', digits=(10,2), default=0.0)
    vacation_amount = fields.Float(string='Monto Vacaciones', compute='_compute_vacation_amount', store=True, digits=(10,2))
    overtime_amount = fields.Float(string='Horas Extras', digits=(10,2), default=0.0)
    
    # Total Ingresos
    total_income = fields.Float(string='Total Ingresos', compute='_compute_total_income', store=True, digits=(10,2))
    
    # Base imponible (ingresos - bonificaciones no imponibles)
    taxable_base = fields.Float(string='Base Imponible', compute='_compute_taxable_base', store=True, digits=(10,2))
    
    # DESCUENTOS - AFP
    afp_fund = fields.Float(string='AFP Fondo', compute='_compute_pension_discounts', store=True, digits=(10,2))
    afp_insurance = fields.Float(string='AFP Seguro', compute='_compute_pension_discounts', store=True, digits=(10,2))
    afp_commission = fields.Float(string='AFP Comisión', compute='_compute_pension_discounts', store=True, digits=(10,2))
    afp_total = fields.Float(string='Total AFP', compute='_compute_pension_discounts', store=True, digits=(10,2))
    afp_taxable_base = fields.Float('Base Imponible AFP', compute='_compute_taxable_bases', store=True)

    # DESCUENTOS - ONP
    onp_discount = fields.Float(string='ONP', compute='_compute_pension_discounts', store=True, digits=(10,2))
    onp_taxable_base = fields.Float('Base Imponible ONP', compute='_compute_taxable_bases', store=True)

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
    
    @api.depends('worked_days')
    def _compute_days_factor(self):
        """Calcula el factor proporcional de días trabajados"""
        for line in self:
            line.days_factor = line.worked_days / 30.0 if line.worked_days > 0 else 0.0
    
    @api.depends('contract_id.night_bonus', 'worked_days')
    def _compute_night_bonus(self):
        for line in self:
            if line.contract_id and line.contract_id.night_bonus > 0 and line.worked_days > 0:
                daily_night_bonus = line.contract_id.night_bonus / 30
                line.night_bonus = round(daily_night_bonus * line.worked_days, 2)
            else:
                line.night_bonus = 0.0

    @api.depends('contract_id', 'medical_rest_days')
    def _compute_medical_rest_amount(self):
        for line in self:
            if line.medical_rest_days > 0 and line.contract_id:
                # Usar solo el sueldo base del contrato (como en Excel)
                daily_wage = line.contract_id.wage / 30
                line.medical_rest_amount = round(daily_wage * line.medical_rest_days, 2)
            else:
                line.medical_rest_amount = 0.0

    @api.depends('taxable_base', 'vacation_days')
    def _compute_vacation_amount(self):
        """
        Cálculo automático de monto de vacaciones
        Fórmula: Sueldo / 30 * Días de Vacaciones
        
        Nota: Se calcula sobre sueldo + asignación familiar antes de calcular 
        la base imponible (que excluye las vacaciones)
        """
        for line in self:
            if line.vacation_days > 0:
                # Base para vacaciones: sueldo + asignación familiar
                vacation_base = line.taxable_base
                daily_amount = vacation_base / 30
                line.vacation_amount = round(daily_amount * line.vacation_days, 2)
            else:
                line.vacation_amount = 0.0

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
    
    @api.depends('total_income', 'night_bonus', 'medical_rest_amount')
    def _compute_taxable_base(self):
        """
        Calcula la base imponible según las reglas del Excel:
        Base imponible = Total ingresos - Bonificaciones no imponibles (otras bonificaciones)
        Para efectos de AFP/ONP, se excluyen bonificaciones extraordinarias
        """
        for line in self:
            # Base AFP: Total Ingresos - Bonificaciones
            line.afp_taxable_base = line.total_income - line.night_bonus
            
            # Base ONP: Total Ingresos - Bonificaciones - Descanso Médico  
            line.onp_taxable_base = line.total_income - line.night_bonus - line.medical_rest_amount
            
            # Mantener taxable_base para compatibilidad (usar base AFP)
            line.taxable_base = line.afp_taxable_base
    
    @api.depends('taxable_base', 'pension_system', 'afp_id', 'commission_type', 'exempt_afp_commission')
    def _compute_pension_discounts(self):
        for line in self:
            if line.pension_system == 'afp' and line.afp_id:
                # Calcular fondo y seguro normalmente
                fund_discount = line.taxable_base * (line.afp_id.fund_percentage / 100)
                insurance_discount = line.taxable_base * (line.afp_id.insurance_percentage / 100)
                
                # Calcular comisión según exención
                if line.exempt_afp_commission:
                    # Si está exento, comisión = 0
                    commission_discount = 0.0
                else:
                    # Calcular comisión normal según tipo
                    commission_type = line.commission_type or line.afp_id.commission_type
                    
                    if commission_type == 'mixed' and line.taxable_base > line.afp_id.tope_amount:
                        # Si es mixta y supera el tope, usar el tope para la comisión
                        commission_discount = line.afp_id.tope_amount * (line.afp_id.commission_mixed_percentage / 100)
                    elif commission_type == 'mixed':
                        commission_discount = line.taxable_base * (line.afp_id.commission_mixed_percentage / 100)
                    else:
                        # Flujo
                        commission_discount = line.taxable_base * (line.afp_id.commission_flow_percentage / 100)
                
                line.afp_fund = round(fund_discount, 2)
                line.afp_insurance = round(insurance_discount, 2)
                line.afp_commission = round(commission_discount, 2)
                line.afp_total = round(fund_discount + insurance_discount + commission_discount, 2)
                line.onp_discount = 0.0
                
            elif line.pension_system == 'onp':
                # Cálculo ONP: 13% sobre base imponible
                onp_base = line.total_income - line.night_bonus - line.medical_rest_amount
                onp_percentage = float(line.env['ir.config_parameter'].sudo().get_param('hr.payroll.onp_percentage', '13.0'))
                line.onp_discount = round(onp_base * (onp_percentage / 100), 2)
                line.afp_fund = 0.0
                line.afp_insurance = 0.0
                line.afp_commission = 0.0
                line.afp_total = 0.0
            else:
                # Sin sistema de pensiones
                line.afp_fund = 0.0
                line.afp_insurance = 0.0
                line.afp_commission = 0.0
                line.afp_total = 0.0
                line.onp_discount = 0.0
    
    @api.depends('tardiness_count', 'salary', 'family_allowance')
    def _compute_tardiness_discount(self):
        """
        Calcula el descuento por tardanzas según la fórmula del Excel:
        Descuento = ((Sueldo + Asig. Familiar) / 240) * Número de tardanzas
        """
        for line in self:
            if line.tardiness_count > 0:
                # Base para descuento de tardanzas: sueldo + asignación familiar
                base_tardiness = line.salary + line.family_allowance
                # Fórmula del Excel: (base / 240) * tardanzas
                line.tardiness_discount = round((base_tardiness / 240) * line.tardiness_count, 2)
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
    
    @api.depends('salary', 'family_allowance', 'vacation_amount', 'contract_id.essalud_percentage', 'contract_id.sctr_percentage', 'contract_id.has_sctr')
    def _compute_employer_contributions(self):
        """
        Calcula aportes del empleador:
        - EsSalud: 9% sobre el salary únicamente
        - SCTR: 1.23% sobre (Sueldo + Asignación Familiar + Vacaciones) si aplica
        """
        for line in self:
            # Obtener configuración actual
            settings = line.env['hr.payroll.settings'].get_current_settings()
            
            # EsSalud: Base = Sueldo + Vacaciones (como en Excel)
            essalud_base = line.salary + line.vacation_amount
            essalud_percentage = line.contract_id.essalud_percentage if line.contract_id else settings.essalud_percentage
            if essalud_percentage == 0:
                essalud_percentage = settings.essalud_percentage
            
            line.essalud = round(essalud_base * (essalud_percentage / 100), 2) if essalud_base > 0 else 0.0
            
            # SCTR: Base para SCTR (Sueldo + Asignación Familiar + Vacaciones) con mínimo RMV
            if line.contract_id and line.contract_id.has_sctr:
                sctr_base = line.salary + line.family_allowance + line.vacation_amount
                # La base SCTR no puede ser menor al RMV
                if sctr_base > 0:
                    sctr_base = max(sctr_base, settings.rmv_amount)
                
                sctr_percentage = line.contract_id.sctr_percentage or settings.sctr_percentage
                line.sctr = round(sctr_base * (sctr_percentage / 100), 2) if sctr_base > 0 else 0.0
            else:
                line.sctr = 0.0
            
            line.total_employer_contribution = line.essalud + line.sctr
    
    @api.depends('net_pay', 'total_employer_contribution')
    def _compute_total_employer_cost(self):
        """Calcula el costo total para el empleador (neto + aportes)"""
        for line in self:
            line.total_employer_cost = line.net_pay + line.total_employer_contribution
    
    @api.onchange('worked_days', 'contract_id')
    def _onchange_worked_days(self):
        """Ajusta el salario según días trabajados si es diferente a 30 días"""
        if self.contract_id and self.worked_days and self.worked_days != 30:
            daily_wage = self.contract_id.wage / 30
            self.salary = round(daily_wage * self.worked_days, 2)
        elif self.contract_id:
            self.salary = self.contract_id.wage
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Cargar datos por defecto del empleado"""
        if self.employee_id:
            # Asignación familiar
            family_allowance = float(self.env['ir.config_parameter'].sudo().get_param('hr.payroll.family_allowance_2025', '113.0'))
            self.family_allowance = family_allowance if self.employee_id.has_family_allowance else 0.0
            
            # Cargar contrato activo
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'open')
            ], limit=1)
            
            if contract:
                self.contract_id = contract.id
                self.salary = contract.wage
                self.night_bonus = contract.night_bonus
                self.other_bonus = contract.other_bonus
                self.fifth_category = contract.fifth_category
    
    def _compute_all_amounts(self):
        """Método para forzar el recálculo de todos los campos computados"""
        self._compute_total_income()
        self._compute_taxable_base()
        self._compute_pension_discounts()
        self._compute_tardiness_discount()
        self._compute_total_discount()
        self._compute_net_pay()
        self._compute_employer_contributions()
    
    def get_payroll_summary(self):
        """Retorna un resumen de la línea de planilla"""
        self.ensure_one()
        return {
            'employee': self.employee_id.name,
            'dni': self.identification_id,
            'total_income': self.total_income,
            'total_discount': self.total_discount,
            'net_pay': self.net_pay,
            'employer_contribution': self.total_employer_contribution,
            'pension_system': dict(self._fields['pension_system'].selection).get(self.pension_system, ''),
            'afp': self.afp_id.name if self.afp_id else '',
        }
    
    def action_print_payslip(self):
        """Generar boleta de pago individual"""
        self.ensure_one()
        return self.env.ref('peruanita_payroll.action_report_payslip').report_action(self)

    def get_payslip_data(self):
        """Obtener datos formateados para la boleta con codificación UTF-8 correcta"""
        self.ensure_one()
        
        # Función helper para limpiar texto y asegurar UTF-8
        def clean_text(text):
            """Limpiar y asegurar codificación correcta"""
            if not text:
                return ''
            # Asegurar que el texto esté en UTF-8
            if isinstance(text, str):
                return text.strip()
            return str(text).strip()
        
        # Obtener texto del sistema de pensiones
        pension_text = ''
        if self.pension_system == 'onp':
            pension_text = 'ONP'
        elif self.pension_system == 'afp':
            pension_text = 'AFP'
        
        # Formatear período en español
        period_text = ''
        if self.payroll_id.date_period:
            months_spanish = {
                1: 'ENERO', 2: 'FEBRERO', 3: 'MARZO', 4: 'ABRIL',
                5: 'MAYO', 6: 'JUNIO', 7: 'JULIO', 8: 'AGOSTO',
                9: 'SEPTIEMBRE', 10: 'OCTUBRE', 11: 'NOVIEMBRE', 12: 'DICIEMBRE'
            }
            month_num = self.payroll_id.date_period.month
            year = self.payroll_id.date_period.year
            period_text = f"{months_spanish.get(month_num, 'MES')} {year}"
        
        return {
            # Datos de la empresa
            'company_name': clean_text(self.payroll_id.company_id.name) or 'PERUANITA E.I.R.L.',
            'company_vat': clean_text(self.payroll_id.company_id.vat) or '20455005869',
            'company_address': clean_text(f"{self.payroll_id.company_id.street or ''} {self.payroll_id.company_id.street2 or ''}") or 'Calle Francia A 9 - APTASA Cerro Colorado',
            
            # Datos del empleado
            'employee_name': clean_text(self.employee_id.name) or '',
            'employee_identification': clean_text(self.identification_id) or '',
            'job_title': clean_text(self.job_id.name if self.job_id else '') or '',
            'date_start': self.contract_id.date_start.strftime('%d/%m/%y') if self.contract_id and self.contract_id.date_start else '',
            'employee_type': 'EMPLEADO',
            'department': clean_text(self.department_id.name if self.department_id else '') or 'PRODUCCIÓN',
            'pension_system': pension_text,
            'cuspp': clean_text(self.cuspp) or '',
            
            # Período
            'period': period_text,
            
            # Días trabajados
            'worked_days': f"{self.worked_days:.2f}",
            'vacation_days': f"{self.vacation_days:.2f}",
            'tardiness_count': f"{self.tardiness_count:.2f}",
            
            # Ingresos
            'basic_salary': f"{self.taxable_base:.2f}",
            'family_allowance': f"{self.family_allowance:.2f}",
            'vacation_pay': f"{self.vacation_amount:.2f}",
            'productivity_bonus': f"{self.other_bonus:.2f}",
            'medical_rest': f"{self.medical_rest_amount:.2f}",
            'overtime': f"{self.overtime_amount:.2f}",
            'night_bonus': f"{self.night_bonus:.2f}",
            'total_income': f"{self.total_income:.2f}",
            
            # Descuentos
            'onp_discount': f"{self.onp_discount:.2f}",
            'afp_fund': f"{self.afp_fund:.2f}",
            'afp_insurance': f"{self.afp_insurance:.2f}",
            'afp_commission': f"{self.afp_commission:.2f}",
            'fifth_category': f"{self.fifth_category:.2f}",
            'advance_payment': f"{self.advance_payment:.2f}",
            'tardiness_discount': f"{self.tardiness_discount:.2f}",
            'total_discount': f"{self.total_discount:.2f}",
            
            # Aportes del empleador
            'essalud': f"{self.essalud:.2f}",
            'total_contributions': f"{self.total_employer_contribution:.2f}",
            
            # Neto a pagar
            'net_pay': f"{self.net_pay:.2f}",
        }