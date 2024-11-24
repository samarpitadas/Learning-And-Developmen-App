# authenticate/roles.py

class UserRoles:
    ADMIN = 'admin'
    ACCOUNT_MANAGER = 'account_manager'
    EMPLOYEE = 'employee'

    CHOICES = [
        (ADMIN, 'Admin'),
        (ACCOUNT_MANAGER, 'Account Manager'),
        (EMPLOYEE, 'Employee'),
    ]
