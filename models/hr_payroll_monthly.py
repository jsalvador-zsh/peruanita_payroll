# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
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
    
    # Campos de control para estados
    validated_by = fields.Many2one('res.users', string='Validado por', readonly=True)
    validated_date = fields.Datetime(string='Fecha Validación', readonly=True)
    paid_by = fields.Many2one('res.users', string='Pagado por', readonly=True)
    paid_date = fields.Datetime(string='Fecha Pago', readonly=True)
    payment_method = fields.Selection([
        ('bank_transfer', 'Transferencia Bancaria'),
        ('cash', 'Efectivo'),
        ('check', 'Cheque'),
        ('mixed', 'Mixto')
    ], string='Método de Pago', tracking=True)
    payment_reference = fields.Char(string='Referencia de Pago', tracking=True)
    
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
    
    # RESTRICCIONES DE SEGURIDAD SEGÚN ESTADO
    
    @api.constrains('state')
    def _check_state_transitions(self):
        """Validar transiciones de estado permitidas"""
        for record in self:
            if record.state == 'validated' and not record.payroll_line_ids:
                raise ValidationError(_('No se puede validar una planilla sin empleados.'))
            
            if record.state == 'paid' and not record.payment_method:
                raise ValidationError(_('Debe especificar el método de pago antes de marcar como pagado.'))
    
    def unlink(self):
        """Prevenir eliminación de planillas validadas o pagadas"""
        for record in self:
            if record.state in ('validated', 'paid'):
                raise UserError(_(
                    'No se puede eliminar la planilla "%s" porque está en estado "%s". '
                    'Solo se pueden eliminar planillas en borrador, calculado o cancelado.'
                ) % (record.name, dict(record._fields['state'].selection)[record.state]))
        return super().unlink()
    
    def write(self, vals):
        """Controlar modificaciones según estado"""
        # Campos que no se pueden modificar en estado validado o pagado
        protected_fields = [
            'date_period', 'payroll_line_ids', 'company_id'
        ]
        
        for record in self:
            if record.state in ('validated', 'paid'):
                for field in protected_fields:
                    if field in vals:
                        raise UserError(_(
                            'No se puede modificar "%s" en una planilla %s. '
                            'Debe regresar a borrador para realizar cambios.'
                        ) % (record._fields[field].string, record.state))
        
        return super().write(vals)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nueva Planilla') == 'Nueva Planilla':
                date_period = vals.get('date_period', fields.Date.today())
                if isinstance(date_period, str):
                    date_period = fields.Date.from_string(date_period)
                vals['name'] = f"PLANILLA/{date_period.strftime('%Y/%m')}/{self.env['ir.sequence'].next_by_code('hr.payroll.monthly') or '0001'}"
        return super().create(vals_list)
    
    # RESTRICCIONES DE SEGURIDAD SEGÚN ESTADO
    
    @api.constrains('state')
    def _check_state_transitions(self):
        """Validar transiciones de estado permitidas"""
        for record in self:
            if record.state == 'validated' and not record.payroll_line_ids:
                raise ValidationError(_('No se puede validar una planilla sin empleados.'))
            
            if record.state == 'paid' and not record.payment_method:
                raise ValidationError(_('Debe especificar el método de pago antes de marcar como pagado.'))
    
    def unlink(self):
        """Prevenir eliminación de planillas validadas o pagadas"""
        for record in self:
            if record.state in ('validated', 'paid'):
                raise UserError(_(
                    'No se puede eliminar la planilla "%s" porque está en estado "%s". '
                    'Solo se pueden eliminar planillas en borrador, calculado o cancelado.'
                ) % (record.name, dict(record._fields['state'].selection)[record.state]))
        return super().unlink()
    
    def write(self, vals):
        """Controlar modificaciones según estado"""
        # Campos que no se pueden modificar en estado validado o pagado
        protected_fields = [
            'date_period', 'payroll_line_ids', 'company_id'
        ]
        
        for record in self:
            if record.state in ('validated', 'paid'):
                for field in protected_fields:
                    if field in vals:
                        raise UserError(_(
                            'No se puede modificar "%s" en una planilla %s. '
                            'Debe regresar a borrador para realizar cambios.'
                        ) % (record._fields[field].string, record.state))
        
        return super().write(vals)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nueva Planilla') == 'Nueva Planilla':
                date_period = vals.get('date_period', fields.Date.today())
                if isinstance(date_period, str):
                    date_period = fields.Date.from_string(date_period)
                vals['name'] = f"PLANILLA/{date_period.strftime('%Y/%m')}/{self.env['ir.sequence'].next_by_code('hr.payroll.monthly') or '0001'}"
        return super().create(vals_list)
    
    # RESTRICCIONES DE SEGURIDAD SEGÚN ESTADO
    
    @api.constrains('state')
    def _check_state_transitions(self):
        """Validar transiciones de estado permitidas"""
        for record in self:
            if record.state == 'validated' and not record.payroll_line_ids:
                raise ValidationError(_('No se puede validar una planilla sin empleados.'))
            
            if record.state == 'paid' and not record.payment_method:
                raise ValidationError(_('Debe especificar el método de pago antes de marcar como pagado.'))
    
    def unlink(self):
        """Prevenir eliminación de planillas validadas o pagadas"""
        for record in self:
            if record.state in ('validated', 'paid'):
                raise UserError(_(
                    'No se puede eliminar la planilla "%s" porque está en estado "%s". '
                    'Solo se pueden eliminar planillas en borrador, calculado o cancelado.'
                ) % (record.name, dict(record._fields['state'].selection)[record.state]))
        return super().unlink()
    
    def write(self, vals):
        """Controlar modificaciones según estado"""
        # Campos que no se pueden modificar en estado validado o pagado
        protected_fields = [
            'date_period', 'payroll_line_ids', 'company_id'
        ]
        
        for record in self:
            if record.state in ('validated', 'paid'):
                for field in protected_fields:
                    if field in vals:
                        raise UserError(_(
                            'No se puede modificar "%s" en una planilla %s. '
                            'Debe regresar a borrador para realizar cambios.'
                        ) % (record._fields[field].string, record.state))
        
        return super().write(vals)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nueva Planilla') == 'Nueva Planilla':
                date_period = vals.get('date_period', fields.Date.today())
                if isinstance(date_period, str):
                    date_period = fields.Date.from_string(date_period)
                vals['name'] = f"PLANILLA/{date_period.strftime('%Y/%m')}/{self.env['ir.sequence'].next_by_code('hr.payroll.monthly') or '0001'}"
        return super().create(vals_list)
    
    # ACCIONES DE ESTADO - SIN NOTIFICACIONES
    
    def action_generate_lines(self):
        """Genera las líneas de planilla basadas en contratos activos"""
        self.ensure_one()
        
        # Solo permitir en borrador
        if self.state != 'draft':
            raise UserError(_('Solo se pueden generar líneas en planillas en borrador.'))
        
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
        
        if not contracts:
            raise UserError(_('No se encontraron contratos activos para el período seleccionado.'))
        
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
        
        self.message_post(
            body=f'Se generaron {len(lines_to_create)} líneas de planilla automáticamente.',
            message_type='notification'
        )
        
        # Retornar True para que no haya notificación popup
        return True
    
    def action_calculate(self):
        """Calcula todos los montos de la planilla - SIN NOTIFICACIÓN"""
        self.ensure_one()
        
        if not self.payroll_line_ids:
            raise UserError(_('No hay líneas de planilla para calcular.'))
        
        # Forzar recálculo de todas las líneas
        for line in self.payroll_line_ids:
            line._compute_all_amounts()
        
        # Usar write() para actualizar la vista inmediatamente
        self.write({'state': 'calculated'})
        
        # Registro en chatter solamente
        self.message_post(
            body='Planilla calculada exitosamente. Todos los montos han sido actualizados.',
            message_type='notification'
        )
        
        # Retornar True - NO display_notification
        return True
        
    def action_validate(self):
        """Valida la planilla - SIN NOTIFICACIÓN"""
        self.ensure_one()
        
        if not self.payroll_line_ids:
            raise UserError(_('No se puede validar una planilla sin empleados.'))
        
        # Validar que no haya errores en los cálculos
        error_lines = []
        for line in self.payroll_line_ids:
            if line.net_pay < 0:
                error_lines.append(f"- {line.employee_id.name}: Neto negativo (S/ {line.net_pay:.2f})")
        
        if error_lines:
            raise UserError(_(
                'No se puede validar la planilla. Los siguientes empleados tienen errores:\n\n%s\n\n'
                'Por favor corrija los montos antes de validar.'
            ) % '\n'.join(error_lines))
        
        # Usar write() para actualizar múltiples campos y refrescar la vista
        self.write({
            'state': 'validated',
            'validated_by': self.env.user.id,
            'validated_date': fields.Datetime.now()
        })
        
        # Registro en chatter solamente
        self.message_post(
            body=f'Planilla validada por {self.env.user.name} el {fields.Datetime.now().strftime("%d/%m/%Y %H:%M")}',
            message_type='notification'
        )
        
        # Retornar True - NO display_notification
        return True
    
    def action_mark_as_paid(self):
        """Marcar planilla como pagada - SIN NOTIFICACIÓN"""
        self.ensure_one()
        
        if self.state != 'validated':
            raise UserError(_('Solo se pueden marcar como pagadas las planillas validadas.'))
        
        if not self.payment_method:
            raise UserError(_('Debe especificar el método de pago antes de marcar como pagado.'))
        
        # Usar write() para actualizar la vista
        self.write({
            'state': 'paid',
            'paid_by': self.env.user.id,
            'paid_date': fields.Datetime.now()
        })
        
        payment_method_name = dict(self._fields['payment_method'].selection)[self.payment_method]
        message = f'Planilla marcada como pagada por {self.env.user.name} el {fields.Datetime.now().strftime("%d/%m/%Y %H:%M")}'
        message += f'\nMétodo de pago: {payment_method_name}'
        if self.payment_reference:
            message += f'\nReferencia: {self.payment_reference}'
        
        # Registro en chatter solamente
        self.message_post(
            body=message,
            message_type='notification'
        )
        
        # Retornar True - NO display_notification
        return True
        
    def action_set_to_draft(self):
        """Regresa la planilla a borrador - SIN NOTIFICACIÓN"""
        self.ensure_one()
        
        if self.state == 'paid':
            raise UserError(_(
                'No se puede regresar a borrador una planilla ya pagada. '
                'Si necesita hacer cambios, debe crear una nueva planilla.'
            ))
        
        # Usar write() para actualizar la vista
        self.write({
            'state': 'draft',
            'validated_by': False,
            'validated_date': False
        })
        
        # Registro en chatter solamente
        self.message_post(
            body='Planilla regresada a borrador. Ahora se pueden realizar modificaciones.',
            message_type='notification'
        )
        
        # Retornar True - NO display_notification
        return True
        
    def action_cancel(self):
        """Cancela la planilla - SIN NOTIFICACIÓN"""
        self.ensure_one()
        
        if self.state == 'paid':
            raise UserError(_('No se puede cancelar una planilla ya pagada.'))
        
        # Usar write() para actualizar la vista
        self.write({'state': 'cancelled'})
        
        # Registro en chatter solamente
        self.message_post(
            body='Planilla cancelada.',
            message_type='notification'
        )
        
        # Retornar True - NO display_notification
        return True
    
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

    def action_print_all_payslips(self):
        """Generar todas las boletas de la planilla en un solo PDF"""
        self.ensure_one()
        if not self.payroll_line_ids:
            raise UserError(_('No hay empleados en esta planilla.'))
        
        return self.env.ref('peruanita_payroll.action_print_multiple_payslips').report_action(self)

    def action_print_payroll_summary(self):
        """Generar resumen de planilla en PDF"""
        self.ensure_one()
        if not self.payroll_line_ids:
            raise UserError(_('No hay empleados en esta planilla.'))
        
        return self.env.ref('peruanita_payroll.action_report_payroll_summary').report_action(self)

    def get_payroll_stats(self):
        """Obtener estadísticas de la planilla para reportes"""
        self.ensure_one()
        
        # Contadores por sistema de pensiones
        onp_count = len([line for line in self.payroll_line_ids if line.pension_system == 'onp'])
        afp_count = len([line for line in self.payroll_line_ids if line.pension_system == 'afp'])
        
        # Estadísticas por departamento
        departments = {}
        for line in self.payroll_line_ids:
            dept_name = line.department_id.name if line.department_id else 'Sin Departamento'
            if dept_name not in departments:
                departments[dept_name] = {
                    'count': 0,
                    'total_salary': 0,
                    'total_net': 0
                }
            departments[dept_name]['count'] += 1
            departments[dept_name]['total_salary'] += line.salary
            departments[dept_name]['total_net'] += line.net_pay
        
        return {
            'period': self.date_period,
            'total_employees': self.employee_count,
            'onp_employees': onp_count,
            'afp_employees': afp_count,
            'departments': departments,
            'totals': {
                'income': self.total_income,
                'discounts': self.total_employee_discount,
                'net_pay': self.total_net_pay,
                'employer_contributions': self.total_employer_contribution,
                'employer_cost': self.total_employer_cost,
            }
        }