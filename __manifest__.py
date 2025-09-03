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
        * Registro mensual de planillas
        * Vista tree editable para gestión rápida
        * Cálculo automático de AFP, ONP, EsSalud
        * Gestión de bonificaciones y descuentos
        * Integración con contratos y empleados
    """,
    'author': 'Juan Salvador',
    'website': 'https://jsalvador.dev',
    'depends': [
        'hr',
        'hr_contract',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_payroll_data.xml',
        'views/hr_contract_views.xml',
        'views/hr_payroll_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}