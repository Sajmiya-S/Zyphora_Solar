from django.db import models
from users.models import Employee,CustomUser
from django.utils.text import slugify
from users.utils import create_notification
from django.urls import reverse
from django.utils import timezone



class Project(models.Model):
    PROJECT_TYPE_CHOICES = (
        ('ongrid','On-grid Solar'),
        ('offgrid','Off-grid Solar'),
        ('hybrid','Hybrid Solar'),
        ('leakproof','Leakproof Solar Roof'),
        ('commercial','Commercial Solar')
    )

    STATUS_CHOICES = (
        ('lead', 'Lead'),
        ('site_visit', 'Site Visit & Feasibility Study'),
        ('design_prep', 'Design Preparation'),
        ('design_approval', 'Design Approval'),
        ('design_costing', 'Design Costing'),
        ('costing_approval', 'Costing Approval'),
        ('structure', 'Structure Installation'),
        ('electrical', 'Electrical Work'),
        ('licensing', 'Licensing'),
        ('energisation', 'Energisation'),
        ('completed', 'Completed'),
    )

    title = models.CharField(max_length=100)
    project_type = models.CharField(choices=PROJECT_TYPE_CHOICES,max_length=20,default='leakproof')
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True,null=True)
    lead = models.ForeignKey('crm.Lead',on_delete=models.SET_NULL,null=True,blank=True,related_name='projects')
    engineer = models.ForeignKey(Employee,on_delete=models.SET_NULL,null=True,blank=True)

    revenue = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='lead'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def save(self, *args, **kwargs):
        update_user = kwargs.pop('update_user', None)  

        # Track old status
        old_status = None
        if self.pk:
            old_status = Project.objects.get(pk=self.pk).status

        # Auto-generate slug
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)  # Save project first

        if old_status != self.status and self.status == 'lead':
            ProjectActivity.objects.create(
                project=self,
                title=f"New Project Update",
                description="Project created from the lead",
                created_by=update_user
            )

        # Log activity if status changed or project just created
        elif old_status != self.status:
            ProjectActivity.objects.create(
                project=self,
                title=f"Status updated : {self.get_status_display()}",
                description=f"Project moved from {old_status} to {self.status}" if old_status else "Project created from the lead",
                created_by=update_user
            )

    @property
    def progress_percent(self):

        status_order = [status[0] for status in Project.STATUS_CHOICES]
        progress_map = {status: 5 + i*9 for i, status in enumerate(status_order)}
        return progress_map.get(self.status, 0)

    @property
    def completed_stages(self):
        status_order = [status[0] for status in self.STATUS_CHOICES]
        if self.status in status_order:
            current_index = status_order.index(self.status)
            return status_order[:current_index]
        return []
    
    def __str__(self):
        return self.title


class ProjectImage(models.Model):

    project = models.ForeignKey(Project,on_delete=models.CASCADE,related_name="gallery",null=True)

    image = models.ImageField(upload_to='project_gallery/')
    caption = models.CharField(max_length=200, blank=True)


    def __str__(self):
        return self.caption or f"Image {self.id}"


class ProjectActivity(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="activities")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.title} ({self.project.title})"


class ProjectDesignDocument(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='design_documents')
    file = models.FileField(upload_to='designs/')
    caption = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)  # admin approval


class Task(models.Model):
    STATUS_CHOICES = (
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tasks')
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='assigned_tasks',null=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):

        is_new = self.pk is None

        super().save(*args, **kwargs)

        # Notify when new task is created
        if is_new and self.assigned_to:

            create_notification(
                recipient=self.assigned_to,
                title=self.title,
                message=self.description,
                sender=self.assigned_by,
                link=reverse('my_tasks')
            )

    def __str__(self):
        return self.title
    

class ServiceRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='service_requests'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    requested_by = models.ForeignKey(
        'crm.Lead', on_delete=models.SET_NULL, null=True, blank=True, related_name='service_requests'
    )
    assigned_to = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_services'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Service Request"
        verbose_name_plural = "Service Requests"

    def save(self, *args, **kwargs):
        old_status = None
        if self.pk:
            old_status = ServiceRequest.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)

        # Notify assigned engineer when request is assigned or status changes
        if self.assigned_to and (old_status != self.status or old_status is None):
            create_notification(
                recipient=self.assigned_to.user,
                title=f"Service Request: {self.title}",
                message=f"Status: {self.get_status_display()}",
                sender=None,  # Could leave blank or assign project manager
                link=reverse('service_request_detail', kwargs={'pk': self.pk})
            )

    def __str__(self):
        return f"{self.title} ({self.project.title})"
    

class ServiceReport(models.Model):
    service_request = models.OneToOneField(
        ServiceRequest, on_delete=models.CASCADE, related_name='report'
    )
    report_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    report_text = models.TextField()
    images = models.ImageField(upload_to='service_reports/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Service Report"
        verbose_name_plural = "Service Reports"

    def __str__(self):
        return f"Report for {self.service_request.title}"
    




class InstallationTask(models.Model):
   # Predefined installation steps
    INSTALLATION_STEP_CHOICES = (
        ('site_inspection', 'Site Inspection Completed'),
        ('structure_fixing', 'Mounting Structure Fixed'),
        ('panel_mounting', 'Solar Panels Mounted'),
        ('wiring', 'DC & AC Wiring Completed'),
        ('inverter', 'Inverter Installed & Connected'),
        ('testing', 'System Testing & Commissioning Done'),
    )

    STATUS_CHOICES = (
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='installation_tasks')
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='installation_tasks')
    step = models.CharField(max_length=50, choices=INSTALLATION_STEP_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['project', 'created_at']
        unique_together = ('project', 'step')  # Only one task per step per project

    def mark_completed(self):
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.project.title} - {self.get_step_display()} ({self.assigned_to.username})"

    @staticmethod
    def project_progress(project):
        """
        Return completion percentage for a project based on completed installation tasks
        """
        total = InstallationTask.objects.filter(project=project).count()
        completed = InstallationTask.objects.filter(project=project, status='completed').count()
        if total == 0:
            return 0
        return round((completed / total) * 100)
    


class InstallationChecklist(models.Model):
    """
    Tracks completion of installation checklist items for a project.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='checklist_items')
    step_name = models.CharField(max_length=100)
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    is_done = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['project', 'created_at']

    def mark_done(self):
        self.is_done = True
        self.completed_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.project.title} - {self.step_name}"
    


class InstallationProgress(models.Model):
    """
    Tracks progress percentage snapshots for a project.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='progress_snapshots')
    progress_percent = models.PositiveIntegerField(default=0)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.project.title} - {self.progress_percent}% on {self.recorded_at.date()}"
    
    