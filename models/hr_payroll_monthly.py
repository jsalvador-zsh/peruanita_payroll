# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

class HrPayrollMonthly(models.Model):
    _name = 'hr.payroll.monthly'
    _description = 'Planilla Mensual'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date_period desc'
    
    name = fields.Char(string='Referencia', required=True, copy=False, readonly=True, default='Nueva Planilla')
    date_period = fields.Date(string='Periodo', required=True, default=fields.Date.today, tracking=True)
    date_from = fields.Date(string='Fecha Desde', compute='_compute_dates', store=True)
    date_to = fields.Date(string='Fecha Hasta', compute='_compute_dates', store=True)
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('calculated', 'Calculado'),
        ('validated', 'Validado'),
        ('paid', 'Pagado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', tracking=True)
    
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(
    'res.currency',
    string='Moneda',
    related='company_id.currency_id',
    store=True,
    readonly=False
)
    # Líneas de planilla
    payroll_line_ids = fields.One2many('hr.payroll.line', 'payroll_id', string='Líneas de Planilla')
    
    # Totales de Ingresos y Descuentos
    total_income = fields.Float(string='Total Ingresos', compute='_compute_totals', store=True, digits=(10,2))
    total_employee_discount = fields.Float(string='Total Descuentos', compute='_compute_totals', store=True, digits=(10,2))
    total_net_pay = fields.Float(string='Total Neto a Pagar', compute='_compute_totals', store=True, digits=(10,2))
    
    # Totales de Aportes del Empleador
    total_employer_contribution = fields.Float(string='Total Aportes Empleador', compute='_compute_totals', store=True, digits=(10,2))
    total_employer_cost = fields.Float(string='Costo Total Empleador', compute='_compute_totals', store=True, digits=(10,2))
    
    # Desglose de descuentos para análisis
    total_afp_discount = fields.Float(string='Total AFP', compute='_compute_detailed_totals', store=True, digits=(10,2))
    total_onp_discount = fields.Float(string='Total ONP', compute='_compute_detailed_totals', store=True, digits=(10,2))
    total_other_discounts = fields.Float(string='Otros Descuentos', compute='_compute_detailed_totals', store=True, digits=(10,2))
    
    # Desglose de aportes empleador
    total_essalud = fields.Float(string='Total EsSalud', compute='_compute_detailed_totals', store=True, digits=(10,2))
    total_sctr = fields.Float(string='Total SCTR', compute='_compute_detailed_totals', store=True, digits=(10,2))
    
    employee_count = fields.Integer(string='Número de Empleados', compute='_compute_employee_count', store=True)
    
    notes = fields.Text(string='Notas')
    
    @api.depends('date_period')
    def _compute_dates(self):
        for record in self:
            if record.date_period:
                # Primer día del mes
                record.date_from = date(record.date_period.year, record.date_period.month, 1)
                # Último día del mes
                next_month = record.date_from + relativedelta(months=1)
                record.date_to = next_month - relativedelta(days=1)
    
    @api.depends('payroll_line_ids')
    def _compute_employee_count(self):
        for record in self:
            record.employee_count = len(record.payroll_line_ids)
    
    @api.depends('payroll_line_ids.total_income', 'payroll_line_ids.total_discount', 
                 'payroll_line_ids.net_pay', 'payroll_line_ids.total_employer_contribution')
    def _compute_totals(self):
        for record in self:
            record.total_income = sum(line.total_income for line in record.payroll_line_ids)
            record.total_employee_discount = sum(line.total_discount for line in record.payroll_line_ids)
            record.total_net_pay = sum(line.net_pay for line in record.payroll_line_ids)
            record.total_employer_contribution = sum(line.total_employer_contribution for line in record.payroll_line_ids)
            # Costo total empleador = Neto a pagar + Aportes empleador
            record.total_employer_cost = record.total_net_pay + record.total_employer_contribution
    
    @api.depends('payroll_line_ids.afp_total', 'payroll_line_ids.onp_discount', 
                 'payroll_line_ids.advance_gratification', 'payroll_line_ids.fifth_category',
                 'payroll_line_ids.tardiness_discount', 'payroll_line_ids.judicial_retention',
                 'payroll_line_ids.advance_payment', 'payroll_line_ids.essalud', 'payroll_line_ids.sctr')
    def _compute_detailed_totals(self):
        for record in self:
            # Descuentos por categoría
            record.total_afp_discount = sum(line.afp_total for line in record.payroll_line_ids)
            record.total_onp_discount = sum(line.onp_discount for line in record.payroll_line_ids)
            record.total_other_discounts = sum(
                line.advance_gratification + line.fifth_category + line.tardiness_discount + 
                line.judicial_retention + line.advance_payment 
                for line in record.payroll_line_ids
            )
            
            # Aportes empleador por categoría
            record.total_essalud = sum(line.essalud for line in record.payroll_line_ids)
            record.total_sctr = sum(line.sctr for line in record.payroll_line_ids)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nueva Planilla') == 'Nueva Planilla':
                date_period = vals.get('date_period', fields.Date.today())
                if isinstance(date_period, str):
                    date_period = fields.Date.from_string(date_period)
                vals['name'] = f"PLANILLA/{date_period.strftime('%Y/%m')}/{self.env['ir.sequence'].next_by_code('hr.payroll.monthly') or '0001'}"
        return super().create(vals_list)
    
    def action_generate_lines(self):
        """Genera las líneas de planilla basadas en contratos activos"""
        self.ensure_one()
        
        # Eliminar líneas existentes
        self.payroll_line_ids.unlink()
        
        # Buscar contratos activos
        contracts = self.env['hr.contract'].search([
            ('state', '=', 'open'),
            ('date_start', '<=', self.date_to),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', self.date_from)
        ])
        
        lines_to_create = []
        for contract in contracts:
            employee = contract.employee_id
            
            # Calcular días trabajados (por defecto 30)
            worked_days = 30
            
            # Si el contrato empezó este mes
            if contract.date_start > self.date_from:
                worked_days = (self.date_to - contract.date_start).days + 1
            
            # Si el contrato terminó este mes
            if contract.date_end and contract.date_end < self.date_to:
                worked_days = min(worked_days, (contract.date_end - self.date_from).days + 1)
            
            # Asignación familiar desde configuración
            settings = self.env['hr.payroll.settings'].get_current_settings()
            family_allowance = settings.family_allowance_amount if employee.has_family_allowance else 0.0
            
            # Calcular bonificación nocturna proporcional a días trabajados
            night_bonus = 0.0
            if contract.night_bonus > 0:
                daily_night_bonus = contract.night_bonus / 30
                night_bonus = round(daily_night_bonus * worked_days, 2)
            
            # Calcular salario proporcional a días trabajados
            salary = contract.wage
            if worked_days != 30:
                daily_wage = contract.wage / 30
                salary = round(daily_wage * worked_days, 2)
            
            lines_to_create.append({
                'payroll_id': self.id,
                'employee_id': employee.id,
                'contract_id': contract.id,
                'worked_days': worked_days,
                'salary': salary,
                'family_allowance': family_allowance,
                'other_bonus': contract.other_bonus,
                'fifth_category': contract.fifth_category,
            })
        
        self.env['hr.payroll.line'].create(lines_to_create)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': 'Líneas generadas',
                'message': f'Se han generado {len(lines_to_create)} líneas de planilla',
                'sticky': False,
            }
        }
    
    def action_calculate(self):
        """Calcula todos los montos de la planilla"""
        self.ensure_one()
        for line in self.payroll_line_ids:
            line._compute_all_amounts()
        self.state = 'calculated'
        
    def action_validate(self):
        """Valida la planilla"""
        self.ensure_one()
        self.state = 'validated'
        
    def action_set_to_draft(self):
        """Regresa la planilla a borrador"""
        self.ensure_one()
        self.state = 'draft'
        
    def action_cancel(self):
        """Cancela la planilla"""
        self.ensure_one()
        self.state = 'cancelled'
    
    def get_payroll_summary(self):
        """Retorna un resumen completo de la planilla"""
        self.ensure_one()
        return {
            'period': self.date_period,
            'employees': self.employee_count,
            'total_income': self.total_income,
            'total_discounts': self.total_employee_discount,
            'net_pay': self.total_net_pay,
            'employer_contributions': self.total_employer_contribution,
            'total_cost': self.total_employer_cost,
            'breakdown': {
                'afp': self.total_afp_discount,
                'onp': self.total_onp_discount,
                'other_discounts': self.total_other_discounts,
                'essalud': self.total_essalud,
                'sctr': self.total_sctr,
            }
        }