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

    # --- Core lead info ---
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

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Lead score ---
    score = models.IntegerField(default=0)

    # --- Score calculation ---

    def calculate_score(self):
        score = 0

        # --- Contact info ---
        if self.phone:
            score += 20
        if self.location:
            score += 20
        if self.service:
            score += 30

        # --- Follow-ups completed ---
        completed_followups = self.followups.filter(status='done').count()
        if self.followups.exists():
            # each completed follow-up gives 20 points max
            followup_points = min(completed_followups * 20, 20)
            score += followup_points

        # --- Site visits completed ---
        completed_visits = self.site_visits.filter(status='done').count()
        if self.site_visits.exists():
            # each completed site visit gives 30 points max
            visit_points = min(completed_visits * 30, 30)
            score += visit_points

        return min(score, 100)


    # --- Save method with project creation ---
    def save(self, *args, **kwargs):

        is_new = self.pk is None

        old_status = None
        if not is_new:
            old_status = Lead.objects.filter(pk=self.pk).values_list('status', flat=True).first()

        super().save(*args, **kwargs)

        self.score = self.calculate_score()
        super().save(update_fields=['score'])

        # ✅ Convert to project (ONLY once)
        if self.status == 'converted' and old_status != 'converted':

            from projects.models import Project, ProjectMedia

            # Prevent duplicate project creation
            if not self.projects.exists():

                project = Project.objects.create(
                    title=f"{self.name} {self.service} Project",
                    lead=self,
                    project_type=self.service or 'leakproof',
                    location=self.location,
                    status='lead'
                )

                # ✅ 1. Link all site visits
                visits = self.site_visits.all()
                visits.update(project=project)

                # ✅ 2. Move photos → ProjectMedia (Before Media)
                media_to_create = []

                for visit in visits:
                    for photo in visit.photos.all():

                        # prevent duplicates
                        if not ProjectMedia.objects.filter(site_photo=photo).exists():
                            media_to_create.append(
                                ProjectMedia(
                                    project=project,
                                    uploaded_by=photo.uploaded_by,
                                    file=photo.photo,  # same file reference ✅
                                    caption="Site Visit Photo",
                                    category='before_photo',
                                    site_photo=photo
                                )
                            )

                ProjectMedia.objects.bulk_create(media_to_create)
    def __str__(self):
        return f"{self.name} ({self.location})" if self.location else self.name
    

class FollowUp(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    )

    lead = models.ForeignKey('Lead', on_delete=models.CASCADE, related_name='followups')
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    note = models.TextField(blank=True, null=True)
    added_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='followups_added')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def mark_done(self, user=None, note=None):
        self.status = 'done'
        self.completed_date = timezone.localdate()
        if note:
            timestamp = timezone.localtime().strftime("%Y-%m-%d %H:%M")
            self.note = (self.note or "") + f"\n[{timestamp}] {note}"
        if user:
            self.added_by = user
        self.save()

    @property
    def is_overdue(self):
        today = timezone.localdate()
        return self.status == 'pending' and self.scheduled_date < today

    @property
    def is_today(self):
        today = timezone.localdate()
        return self.status == 'pending' and self.scheduled_date == today

    @property
    def is_upcoming(self):
        today = timezone.localdate()
        return self.status == 'pending' and self.scheduled_date > today

    def __str__(self):
        return f"Follow-Up for {self.lead.name} on {self.scheduled_date}"
    

class SiteVisit(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    )

    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE, related_name='site_visits'
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='site_visits'
    )
    engineer = models.ForeignKey(
        CustomUser,on_delete=models.SET_NULL, null=True, blank=True,related_name='engineer'
    )

    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    notes = models.TextField(blank=True, null=True)
    added_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='site_visits_added'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def mark_done(self, user=None, note=None):
        self.status = 'done'
        self.completed_date = timezone.localdate()
        if note:
            timestamp = timezone.localtime().strftime("%Y-%m-%d %H:%M")
            self.notes = (self.notes or "") + f"\n[{timestamp}] {note}"
        if user:
            self.added_by = user
        self.save()

    def __str__(self):
        return f"Site Visit for {self.lead.name} ({'Project: ' + self.project.title if self.project else 'No Project'})"
    
class SitePhoto(models.Model):
    visit = models.ForeignKey(SiteVisit, on_delete=models.CASCADE, related_name='photos')
    photo = models.ImageField(upload_to='site_photos/')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

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