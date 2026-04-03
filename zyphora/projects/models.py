from django.db import models
from users.models import Employee, CustomUser
from users.utils import create_notification
from django.urls import reverse
from django.utils import timezone
import os

# -------------------------------
# Project
# -------------------------------
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
        ('feasibility', 'Feasibility Study'),
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
    project_type = models.CharField(choices=PROJECT_TYPE_CHOICES, max_length=20, default='leakproof')
    description = models.TextField(blank=True, null=True)
    lead = models.ForeignKey('crm.Lead', on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    engineer = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='lead')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def update_status(self):

        # 🔹 INSTALLATION TASKS
        installation_tasks = self.installation_tasks.all()

        structure_steps = ['structure_fixing', 'panel_mounting']
        electrical_steps = ['wiring', 'inverter', 'testing']

        # ✅ STRUCTURE PHASE
        structure_tasks = installation_tasks.filter(step__in=structure_steps)
        if structure_tasks.exists() and all(t.status == 'completed' for t in structure_tasks):
            self.status = 'structure'

        # ✅ ELECTRICAL PHASE (YOUR MAIN REQUIREMENT)
        electrical_tasks = installation_tasks.filter(step__in=electrical_steps)
        if electrical_tasks.exists() and all(t.status == 'completed' for t in electrical_tasks):
            self.status = 'electrical'

        # 🔹 LICENSING TASKS
        licensing_tasks = self.licensing_tasks.all()
        if licensing_tasks.exists() and all(t.status == 'completed' for t in licensing_tasks):
            self.status = 'licensing'

        # 🔹 ENERGISATION
        if (
            installation_tasks.exists()
            and licensing_tasks.exists()
            and all(t.status == 'completed' for t in installation_tasks)
            and all(t.status == 'completed' for t in licensing_tasks)
        ):
            self.status = 'energisation'

        self.save()


    def save(self, *args, **kwargs):
        update_user = kwargs.pop('update_user', None)
        old_status = None
        if self.pk:
            old_status = Project.objects.get(pk=self.pk).status

        super().save(*args, **kwargs)

        # Activity Logging
        if old_status != self.status and self.status == 'lead':
            ProjectActivity.objects.create(
                project=self,
                title="New Project Update",
                description="Project created from the lead",
                created_by=update_user
            )
        elif old_status != self.status:
            ProjectActivity.objects.create(
                project=self,
                title=f"Status updated : {self.get_status_display()}",
                description=f"Project moved from {old_status} to {self.status}" if old_status else "Project created from the lead",
                created_by=update_user
            )

        # AUTOMATIC DESIGN DOCUMENT TO MEDIA
        if self.status in ['design_approval', 'design_costing', 'design_costing_review', 'project_costing', 'completed']:
            approved_docs = self.design_documents.filter(approved=True)
            for doc in approved_docs:
                # Avoid duplicates
                if not ProjectMedia.objects.filter(project=self, file=doc.file, category='design_document').exists():
                    doc.approve_and_move_to_media()

    def installation_steps(self):
        tasks = self.installation_tasks.all()
        if tasks.exists():
            return tasks
        # Return virtual tasks for new projects (unassigned)
        return [InstallationTask(step=step) for step, _ in InstallationTask.INSTALLATION_STEP_CHOICES]

    
    @property
    def progress_percent(self):
        status_order = [status[0] for status in Project.STATUS_CHOICES]
        total = len(status_order)
        progress_map = {status: int((i+1)/total * 100) for i, status in enumerate(status_order)}
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


# -------------------------------
# Unified Project Media
# -------------------------------
class ProjectMedia(models.Model):

    CATEGORY_CHOICES = (
        ('before_photo', 'Before Media (Photo / Video)'),
        ('after_photo', 'After Media (Photo / Video)'),
        ('design_document', 'Design File'),
        ('installation_photo', 'Installation Media'),
        ('issue_photo', 'Issue Media'),
        ('service_report_photo', 'Service Report Media'),
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='media')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(upload_to='project_media/')
    caption = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)

    site_photo = models.ForeignKey('crm.SitePhoto', on_delete=models.SET_NULL, null=True, blank=True)
    work_report = models.ForeignKey('WorkReport', on_delete=models.SET_NULL, null=True, blank=True)
    service_report = models.ForeignKey('ServiceReport', on_delete=models.SET_NULL, null=True, blank=True)
    issue = models.ForeignKey('InstallationIssue', on_delete=models.SET_NULL, null=True, blank=True)
    installation_task = models.ForeignKey('InstallationTask', on_delete=models.SET_NULL, null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.project.title} - {self.get_category_display()} ({self.caption or self.id})"

    # ✅ NEW METHODS
    def file_extension(self):
        return os.path.splitext(self.file.name)[1].lower()

    def is_image(self):
        return self.file_extension() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']

    def is_video(self):
        return self.file_extension() in ['.mp4', '.webm', '.ogg', '.mov']


# -------------------------------
# Project Activity
# -------------------------------
class ProjectActivity(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="activities")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.title} ({self.project.title})"


# -------------------------------
# Feasibility Report
# -------------------------------

class FeasibilityReport(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="feasibility")

    # 🟢 1. Site Details
    site_type = models.CharField(max_length=50, choices=[
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
    ])
    roof_type = models.CharField(max_length=50, choices=[
        ('rcc', 'RCC'),
        ('metal', 'Metal'),
        ('tile', 'Tile'),
    ])
    roof_area = models.FloatField(help_text="Area in sq.ft")

    # 🟢 2. Structural & Practical Feasibility
    structure_feasibility = models.BooleanField(default=True)
    accessibility_for_maintenance = models.BooleanField(default=True)

    # 🟢 3. Shadow & Orientation
    shadow_analysis = models.CharField(max_length=50, choices=[
        ('none', 'No Shading'),
        ('partial', 'Partial Shading'),
        ('heavy', 'Heavy Shading'),
    ])
    orientation = models.CharField(max_length=20, choices=[
        ('north', 'North'),
        ('south', 'South'),
        ('east', 'East'),
        ('west', 'West'),
    ])

    # 🟢 4. Electrical Details
    connection_type = models.CharField(max_length=20, choices=[
        ('single_phase', 'Single Phase'),
        ('three_phase', 'Three Phase'),
    ])
    monthly_consumption = models.IntegerField(null=True, blank=True)

    # 🟢 5. System Recommendation (CRITICAL LINK)
    suggested_capacity = models.FloatField(help_text="kW")
    system_type = models.CharField(max_length=20, choices=[
        ('on_grid', 'On-Grid'),
        ('off_grid', 'Off-Grid'),
        ('hybrid', 'Hybrid'),
    ])
    inverter_type = models.CharField(max_length=100, blank=True)

    # 🟢 6. Engineer Remarks
    remarks = models.TextField(blank=True)

    # 🟢 7. Approval Workflow
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name="feasibility_reports")
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_feasibilities")
    is_approved = models.BooleanField(default=False)
    approval_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


# -------------------------------
# Design Document
# -------------------------------

class ProjectDesignDocument(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='design_documents')
    file = models.FileField(upload_to='designs/')
    caption = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    discussion_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    approved = models.BooleanField(default=False)
    needs_correction = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def approve_and_move_to_media(self):
        """
        Move the approved design document into ProjectMedia.
        Avoid duplicates.
        """
        if not self.approved:
            raise ValueError("Document must be approved before moving to media")

        # Check if media already exists
        exists = ProjectMedia.objects.filter(project=self.project, file=self.file.name).exists()
        if exists:
            return  # Already added

        ProjectMedia.objects.create(
            project=self.project,
            uploaded_by=self.uploaded_by,
            file=self.file,
            caption=self.caption or "Design Document",
            category='design_document',
            work_report=None,
            site_photo=None,
            service_report=None,
            issue=None,
            installation_task=None,
        )


    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Automatically move to media if approved
        if self.approved:
            self.approve_and_move_to_media()

# -------------------------------
# Task
# -------------------------------
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
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='assigned_tasks', null=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
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


# -------------------------------
# Service Request & Report
# -------------------------------
class ServiceRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='service_requests')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    requested_by = models.ForeignKey('crm.Lead', on_delete=models.SET_NULL, null=True, blank=True, related_name='service_requests')
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_services')
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
        if self.assigned_to and (old_status != self.status or old_status is None):
            create_notification(
                recipient=self.assigned_to.user,
                title=f"Service Request: {self.title}",
                message=f"Status: {self.get_status_display()}",
                sender=None,
                link=reverse('service_requests')
            )

    def __str__(self):
        return f"{self.title} ({self.project.title})"


class ServiceReport(models.Model):
    service_request = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name='report')
    report_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    report_text = models.TextField()
    images = models.ImageField(upload_to='service_reports/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Service Report"
        verbose_name_plural = "Service Reports"

    def __str__(self):
        return f"Report for {self.service_request.title}"


# -------------------------------
# Installation Tasks, Checklist, Progress, Issues
# -------------------------------
class InstallationTask(models.Model):
    INSTALLATION_STEP_CHOICES = (
        ('site_inspection', 'Site Inspection Completed'),
        ('structure_fixing', 'Mounting Structure Fixed'),
        ('panel_mounting', 'Solar Panels Mounted'),
        ('wiring', 'DC & AC Wiring Completed'),
        ('testing', 'System Testing '),
    )

    STATUS_CHOICES = (
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='installation_tasks')
    assigned_to = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='installation_tasks',
        null=True, blank=True
    )
    step = models.CharField(max_length=50, choices=INSTALLATION_STEP_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    notes = models.TextField(blank=True, null=True)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['project', 'created_at']
        unique_together = ('project', 'step')

    def mark_completed(self):
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()

    def __str__(self):
        assigned = self.assigned_to.username if self.assigned_to else "Unassigned"
        return f"{self.project.title} - {self.get_step_display()} ({assigned})"

    @staticmethod
    def project_progress(project):
        total = InstallationTask.objects.filter(project=project).count()
        completed = InstallationTask.objects.filter(project=project, status='completed').count()
        if total == 0:
            return 0
        return round((completed / total) * 100)
    



class InstallationChecklist(models.Model):
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
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='progress_snapshots')
    progress_percent = models.PositiveIntegerField(default=0)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.project.title} - {self.progress_percent}% on {self.recorded_at.date()}"


class InstallationIssue(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='issues')
    reported_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='issue_images/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.project.title} - {self.title}"


# -------------------------------
# Work Report
# -------------------------------
class WorkReport(models.Model):
    STATUS_CHOICES = (
        ('completed', 'Completed'),
        ('in_progress', 'In Progress'),
        ('pending', 'Pending'),
    )

    WORK_TYPE_CHOICES = (
        ('panel', 'Panel Installation'),
        ('inverter', 'Inverter Setup'),
        ('wiring', 'Wiring'),
        ('maintenance', 'Maintenance'),
        ('inspection', 'Inspection'),
        ('other', 'Other'),
    )

    REPORT_TYPE_CHOICES = (
        ('daily', 'Daily Report'),
        ('weekly', 'Weekly Summary'),
        ('completion', 'Work Completion'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, default='daily')
    work_type = models.CharField(max_length=50, choices=WORK_TYPE_CHOICES)
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    date = models.DateField(default=timezone.now)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.PositiveIntegerField(default=0)
    before_image = models.ImageField(upload_to='reports/before/', null=True, blank=True)
    after_image = models.ImageField(upload_to='reports/after/', null=True, blank=True)
    issues = models.TextField(blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_reports')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.status == 'completed':
            self.progress = 100
        elif self.status == 'in_progress':
            self.progress = 50
        elif self.status == 'pending':
            self.progress = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.project.title} ({self.date})"
    


class LicensingTask(models.Model):

    # 🔹 PHASES (NEW)
    PHASE_CHOICES = (
        ('preparation', 'Preparation'),
        ('kseb', 'KSEB Processing'),
        ('mnre', 'MNRE Processing'),
        ('subsidy', 'Subsidy & Closure'),
    )

    # 🔹 STEPS (CLEANED)
    LICENSE_STEP_CHOICES = (
        ('customer_info', 'Customer Info Collection'),
        ('mnre_registration', 'MNRE Registration'),
        ('annex1', 'KSEB Annex I Submission'),
        ('equipment_info', 'Equipment Info Collection'),
        ('agreement', 'Agreement Preparation'),
        ('annex2', 'KSEB Annex II Submission'),
        ('annex3', 'KSEB Annex III Submission'),
        ('mnre_final', 'MNRE Final Submission'),
        ('subsidy', 'Subsidy Credit'),
    )

    STATUS_CHOICES = (
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
    )

    STEP_PHASE_MAP = {
        # Preparation
        'customer_info': 'preparation',
        'equipment_info': 'preparation',
        'agreement': 'preparation',

        # KSEB
        'annex1': 'kseb',
        'annex2': 'kseb',
        'annex3': 'kseb',

        # MNRE
        'mnre_registration': 'mnre',
        'mnre_final': 'mnre',

        # Subsidy
        'subsidy': 'subsidy',
    }

    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        related_name='licensing_tasks'
    )

    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, null =True)

    step = models.CharField(max_length=50, choices=LICENSE_STEP_CHOICES)

    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )

    notes = models.TextField(blank=True, null=True)
    due_date = models.DateField(null=True, blank=True)

    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'step')
        ordering = ['created_at']

    # 🔥 MARK COMPLETE
    def mark_completed(self):
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    # 🔥 AUTO HOOK
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None

        if self.pk:
            old_status = LicensingTask.objects.get(pk=self.pk).status

        if self.step in self.STEP_PHASE_MAP:
            self.phase = self.STEP_PHASE_MAP[self.step]
            
        super().save(*args, **kwargs)

        # 🔔 Notification (only when status changes or new)
        if self.assigned_to and (is_new or old_status != self.status):
            create_notification(
                recipient=self.assigned_to,
                title=f"Licensing Task: {self.get_step_display()}",
                message=f"Status: {self.get_status_display()}",
                sender=None,
                link=reverse('project_detail', args=[self.project.id]),
                category="tasks"
            )

        # 🔄 Update project status automatically
        self.project.update_status()

    # 📊 TOTAL PROGRESS
    @staticmethod
    def project_progress(project):
        tasks = LicensingTask.objects.filter(project=project)
        total = tasks.count()
        completed = tasks.filter(status='completed').count()

        if total == 0:
            return 0

        return round((completed / total) * 100)

    # 📊 PHASE PROGRESS
    @staticmethod
    def phase_progress(project, phase):
        tasks = LicensingTask.objects.filter(project=project, phase=phase)
        total = tasks.count()
        completed = tasks.filter(status='completed').count()

        if total == 0:
            return 0

        return round((completed / total) * 100)

    def __str__(self):
        assigned = self.assigned_to.username if self.assigned_to else "Unassigned"
        return f"{self.project.title} - {self.get_step_display()} ({assigned})"
    

class LicensingDocument(models.Model):

    DOCUMENT_TYPE_CHOICES = (
        ('annex1', 'Annex I'),
        ('annex2', 'Annex II'),
        ('annex3', 'Annex III'),
        ('agreement', 'Agreement'),
        ('mnre', 'MNRE Document'),
        ('other', 'Other'),
    )

    task = models.ForeignKey(
        LicensingTask,
        on_delete=models.CASCADE,
        related_name='documents'
    )

    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True
    )

    file = models.FileField(upload_to='licensing_docs/')

    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES,
        default='other'
    )

    caption = models.CharField(max_length=255, blank=True, null=True)

    is_verified = models.BooleanField(default=False)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task.project.title} - {self.get_document_type_display()}"