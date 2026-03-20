from django.contrib import admin
from .models import *


admin.site.register(Project)

admin.site.register(ProjectImage)

admin.site.register(ProjectActivity)

admin.site.register(ProjectDesignDocument)

admin.site.register(Task)

admin.site.register(ServiceRequest)

admin.site.register(ServiceReport)
