from django.db import models
from users.models import CustomUser
from projects.models import Project
from django.utils import timezone


class Review(models.Model):
    name = models.CharField(max_length=20)
    email = models.EmailField(null=True)
    location = models.CharField(max_length=100, blank=True,null=True)
    rating = models.IntegerField()
    review = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    



class Lead(models.Model):

    STATUS_CHOICES = (
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('site_visit_scheduled', 'Site Visit Scheduled'),
        ('converted', 'Converted to Project'),
        ('rejected', 'Rejected'),
    )

    PRIORITY_CHOICES = (
        ('low','Low'),
        ('medium','Medium'),
        ('high','High'),
    )

    SERVICES = (
        ('','Select Service'),
        ('ongrid','On-grid Solar'),
        ('offgrid','Off-grid Solar'),
        ('hybrid','Hybrid Solar'),
        ('leakproof','Leakproof Solar Roof'),
        ('commercial','Commercial Solar')
    )

    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    email = models.EmailField(null=True,blank=True)
    location = models.CharField(max_length=150, blank=True, null=True)
    service = models.CharField(choices=SERVICES,max_length=20)

    message = models.TextField(blank=True,null=True)
    notes = models.TextField(blank=True,null=True)

    status = models.CharField(max_length=30,choices=STATUS_CHOICES,default='new')
    priority = models.CharField(max_length=10,choices=PRIORITY_CHOICES,default='medium')
    assigned_to = models.ForeignKey(CustomUser,on_delete=models.SET_NULL,null=True,blank=True)

    site_visit_date = models.DateField(null=True,blank=True)
    site_visit_done = models.BooleanField(default=False)
    site_visit_completed_at = models.DateField(null=True, blank=True)

    follow_up_date = models.DateField(null=True,blank=True)
    follow_up_done = models.BooleanField(default=False)
    follow_up_completed_at = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    score = models.IntegerField(default=0)

    # --- Score calculation ---
    def calculate_score(self):
        score = 0
        if self.phone:
            score += 20
        if self.location:
            score += 20
        if self.service:
            score += 30
        if self.follow_up_date:
            score += 10
        if self.follow_up_done:
            score += 20
        if self.site_visit_done:
            score += 30
        return min(score,100)
    
    @property
    def site_visit_status(self):
        if self.site_visit_done:
            return "done"
        if not self.site_visit_date:
            return None
        today = timezone.localdate()
        if self.site_visit_date < today:
            return "overdue"
        elif self.site_visit_date == today:
            return "today"
        else:
            return "upcoming"

    @property
    def followup_status(self):
        """Return status of follow-up: pending, due today, or done"""
        if self.follow_up_done:
            return "done"
        if not self.follow_up_date:
            return None
        today = timezone.localdate()
        if self.follow_up_date < today:
            return "overdue"
        elif self.follow_up_date == today:
            return "today"
        else:
            return "upcoming"
        
        # --- Follow-up mark ---
    def mark_followup_done(self):
        self.follow_up_done = True
        self.follow_up_completed_at = timezone.localdate()
        # Automatically update status
        if self.status == 'new' or self.status is None:
            self.status = 'contacted'
        self.save()

    # --- Site visit mark ---
    def mark_site_visit_done(self):
        self.site_visit_done = True
        self.site_visit_completed_at = timezone.localdate()
        # Automatically update status
        if self.status in ['new', 'contacted']:
            self.status = 'site_visit_scheduled'
        self.save()

    def save(self, *args, **kwargs):
        # --- Calculate score ---
        self.score = self.calculate_score()

        # --- Automatic status updates ---
        if self.site_visit_date and not self.site_visit_done and self.status in ['new', 'contacted']:
            self.status = 'site_visit_scheduled'

        if self.follow_up_done and self.status in ['new']:
            self.status = 'contacted'

        # --- Check old status for conversion ---
        if self.pk:
            old_status = Lead.objects.get(pk=self.pk).status
        else:
            old_status = None

        super().save(*args, **kwargs)  # Save the lead first

        # --- Create project if lead just converted ---
        if self.status == 'converted' and old_status != 'converted':
            if not hasattr(self, 'projects') or not self.projects.exists():
                Project.objects.create(
                    title=f"{self.name} {self.service} Project",
                    lead=self,
                    project_type=self.service or 'leakproof',
                    location=self.location,
                    status='lead'
                )

        # --- Optionally mark follow-up done after conversion ---
        if self.follow_up_date and not self.follow_up_done:
            self.mark_followup_done()


    def __str__(self):
        return f"{self.name} ({self.location})" if self.location else self.name
    

class LeadActivity(models.Model):

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('users.CustomUser', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.title} ({self.lead.title})"