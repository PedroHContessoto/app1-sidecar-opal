package app1.authz

default allow = false

# Permite acesso se o funcionário for do departamento de 'engenharia'
allow {
    employee := data.employees[_]
    employee.department == "engenharia"
}
