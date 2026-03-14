from django.db import models
from django.contrib.auth.models import AbstractUser



class CustomUser(AbstractUser):
    username = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('engineer', 'Engineer'),
        ('accountant', 'Accountant'),
        ('sales','Sales'),
        ('staff', 'Staff'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')
    must_change_password = models.BooleanField(default=False)



class Employee(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="employee")
    profile_pic = models.ImageField(upload_to='employees', blank=True, null=True)

    name = models.CharField(max_length=50,null=True,blank=True)
    phone = models.CharField(max_length=15,null=True,blank=True)
    address = models.TextField(blank=True,null=True)
    designation = models.CharField(max_length=50,null=True,blank=True)
    date_joined = models.DateField(null=True)
    is_active = models.BooleanField(default=True)

    # Role-specific fields
    specialization = models.CharField(max_length=100, blank=True,null=True)       # For engineers
    access_level = models.CharField(max_length=20, blank=True,null=True)          # For accountants
    supervisor = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={'role__in': ['admin','engineer']},
        related_name='supervised_staff'
    )  # For staff

    def __str__(self):
        return f"{self.user.username} - {self.user.get_role_display()}"
    


class Notification(models.Model):
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=150,null=True)
    message = models.TextField()
    category = models.CharField(max_length=50,null=True)
    link = models.URLField(blank=True, null=True) 
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Notification to {self.recipient.username} - Read: {self.is_read}'