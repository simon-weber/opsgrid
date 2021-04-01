from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Alert, AlertAlarm, Host, IngestToken, User

admin.site.register(User, UserAdmin)
admin.site.register(IngestToken)
admin.site.register(Host)
admin.site.register(Alert)
admin.site.register(AlertAlarm)
