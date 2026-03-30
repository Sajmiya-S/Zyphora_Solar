from django.contrib import admin
from .models import *


admin.site.register(Project)

admin.site.register(ProjectMedia)

admin.site.register(ProjectActivity)

admin.site.register(ProjectDesignDocument)

admin.site.register(Task)

admin.site.register(ServiceRequest)

admin.site.register(ServiceReport)

admin.site.register(InstallationTask)

admin.site.register(InstallationChecklist)

admin.site.register(InstallationProgress)

admin.site.register(InstallationIssue)

admin.site.register(WorkReport)

admin.site.register(LicensingTask)

admin.site.register(LicensingDocument)
