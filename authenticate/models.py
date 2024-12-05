from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLES = (
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('employee', 'Employee'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLES, default='employee')

    def __str__(self):
        return f'{self.user.username} - {self.role}'

class Request(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.title} - {self.submitted_by.username}"

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - Created by {self.created_by.username}"

class Module(models.Model):
    course = models.ForeignKey(Course, related_name="modules", on_delete=models.CASCADE)
    heading = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.heading

class EmployeeEmail(models.Model):
    course = models.ForeignKey(Course, related_name="employee_emails", on_delete=models.CASCADE)
    email = models.EmailField()

    def __str__(self):
        return self.email

class UserModuleCompletion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.module.heading} completion"

class CourseFeedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course_name = models.CharField(max_length=255)
    feedback = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.course_name} by {self.user.username}"
        
class ManagerRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    )
    manager = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.manager.username}"
