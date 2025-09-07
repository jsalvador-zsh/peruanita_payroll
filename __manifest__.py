{
    'name': 'Planilla de Sueldos',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Gestión de Planilla de Sueldos para Peruanita',
    'description': """
        Módulo de Planilla de Sueldos para Perú
        ========================================
        
        Características:
        ----------------
        * Registro mensual de planillas con cálculos actualizados 2025
        * Vista tree editable para gestión rápida de empleados
        * Cálculo automático de AFP con porcentajes actualizados (Integra, Prima, Profuturo, Habitat)
        * Cálculo correcto de ONP (13%)
        * Gestión de EsSalud y SCTR con base imponible correcta
        * Configuración de parámetros: RMV, UIT, Asignación Familiar, Topes AFP
        * Cálculo de bonificaciones y descuentos según normativa peruana
        * Integración con contratos y empleados de Odoo
        * Base imponible calculada según exclusiones normativas
        * Descuentos por tardanzas con fórmula del Excel
        * Aportes del empleador sobre base correcta (Sueldo + Asig.Fam + Vacaciones)
        
        Actualizaciones 2025:
        ---------------------
        * AFP Integra: Flujo 1.55%, Mixta 0.78%, Seguro 1.37%
        * AFP Prima: Flujo 1.60%, Mixta 1.25%, Seguro 1.37%
        * AFP Profuturo: Flujo 1.69%, Mixta 1.20%, Seguro 1.37%
        * AFP Habitat: Flujo 1.47%, Mixta 1.25%, Seguro 1.37%
        * RMV: S/. 1,130
        * UIT: S/. 5,350
        * Asignación Familiar: S/. 113
        * Tope Prima (Mixta): S/. 12,027.91
    """,
    'author': 'Juan Salvador',
    'website': 'https://jsalvador.dev',
    'depends': [
        'web',
        'hr',
        'hr_contract',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_payroll_data.xml',
        'views/hr_contract_views.xml',
        'views/hr_payroll_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_payroll_settings_views.xml',
        'reports/paperformat.xml',
        'reports/peruanita_layout_background_a5_vertical.xml',
        'reports/report_payslip_templates.xml',
        'reports/payslip_template.xml',
    ],
        "assets": {
        "web.assets_backend": [
            'peruanita_payroll/static/src/css/styles.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}