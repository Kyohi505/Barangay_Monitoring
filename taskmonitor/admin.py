from django.contrib import admin

from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Task, TaskSubmission, Equipment, BorrowingRecord, TaskReport

import cloudinary.uploader
from datetime import date

# Register your models here.

class CustomUserAdmin(UserAdmin):
    ordering = ['email']
    list_display = ['email', 'first_name', 'last_name', 'is_staff']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number', 'id_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

class TaskSubmissionAdmin(admin.ModelAdmin):
    list_display = ['task', 'submitted_by', 'validation_status', 'submitted_time']

class BorrowingRecordAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if 'proof_image' in form.changed_data and obj.proof_image:
            folder = f"barangay/borrowing/{date.today()}"
            upload_result = cloudinary.uploader.upload(
                form.cleaned_data['proof_image'],
                folder=folder
            )
            obj.proof_image = upload_result['public_id']
        super().save_model(request, obj, form, change)

class TaskReportAdmin(admin.ModelAdmin):
    list_display = ['task', 'reported_by', 'reason', 'reported_at', 'resolved']

admin.site.register(TaskReport, TaskReportAdmin)
admin.site.register(BorrowingRecord, BorrowingRecordAdmin)
admin.site.register(TaskSubmission, TaskSubmissionAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Task)
admin.site.register(Equipment)

