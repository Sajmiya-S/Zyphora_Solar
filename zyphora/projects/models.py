from django.db import models
from users.models import Employee,CustomUser
from django.utils.text import slugify




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
    

