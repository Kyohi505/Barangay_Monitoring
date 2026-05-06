from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone

from django.db.models.signals import pre_delete
from django.dispatch import receiver
import cloudinary.uploader
from cloudinary.models import CloudinaryField

# Create your models here.

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)

    id_number = models.CharField(max_length=12, blank=True)
    phone_number = models.CharField(max_length=12, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_set',
        blank=True
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_set',
        blank=True
    )

class Equipment(models.Model):
    name = models.CharField(max_length=64)
    quantity = models.IntegerField(default=1)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} (qty: {self.quantity})"

class Task(models.Model):
    TYPE_CHOICES = [
        ('validation', 'Validation'),
        ('non_validation', 'Manual Validation'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    task_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_items = models.IntegerField(default=1)

    assigned_to = models.ManyToManyField(CustomUser, related_name='assigned_tasks')

    date_created = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField(null=True, blank=True)
    
    is_borrowing = models.BooleanField(default=False)
    borrowed_by = models.CharField(max_length=128, blank=True)
    EQUIPMENT_ACTION_CHOICES = [
        ('checkout', 'Checkout'),
        ('return', 'Return'),
    ]

    equipment_action = models.CharField(max_length=10, choices=EQUIPMENT_ACTION_CHOICES, null=True, blank=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')

    def calculate_status(self):
        approved = self.submissions.filter(validation_status='approved').count()

        if approved >= self.total_items:
            return 'completed'
        if self.due_date and timezone.now() > self.due_date:
            return 'failed'
        if approved > 0:
            return 'in_progress'
        return 'pending'

    def get_progress(self):
        approved = self.submissions.filter(validation_status='approved').count()
        return {'approved': approved, 'total': self.total_items}

    def save(self, *args, **kwargs):
        if self.pk:
            self.status = self.calculate_status()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.task_type}) - {self.status}"

class TaskSubmission(models.Model):
    VALIDATION_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='submissions')
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='personnel_submitted')
    
    image = CloudinaryField('image', blank=True, null=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    submitted_time = models.DateTimeField(default=timezone.now)

    validation_status = models.CharField(max_length=20, choices=VALIDATION_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        old_status = None
        if self.pk:
            old_status = TaskSubmission.objects.get(pk=self.pk).validation_status
        
        super().save(*args, **kwargs)
        
        if old_status != 'approved' and self.validation_status == 'approved':
            if self.task.equipment:
                equipment = self.task.equipment
                if self.task.equipment_action == 'checkout':
                    if equipment.quantity > 0:
                        equipment.quantity -= 1
                        equipment.save()
                    if self.task.is_borrowing:
                        BorrowingRecord.objects.create(
                            equipment=self.task.equipment,
                            borrowed_by=self.task.borrowed_by,
                            quantity_borrowed=self.task.total_items,
                            proof_image=self.image,
                        )
                elif self.task.equipment_action == 'return':
                    equipment.quantity += 1
                    equipment.save()
                    if self.task.is_borrowing:
                        record = BorrowingRecord.objects.filter(
                            equipment=self.task.equipment,
                            returned=False
                        ).first()
                        if record:
                            record.mark_returned()
        
        self.task.save()

    def __str__(self):
        return f"{self.submitted_by} -> {self.task.name} [{self.validation_status}]"

class BorrowingRecord(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='borrowed_equipment')
    borrowed_by = models.CharField(max_length=64)
    quantity_borrowed = models.IntegerField(default=1)
    borrowed_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField(null=True, blank=True)
    returned_date = models.DateTimeField(null=True, blank=True)
    returned = models.BooleanField(default=False)
    proof_image = CloudinaryField('image', folder='barangay/borrowing', blank=True, null=True)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        old_returned = None
        if self.pk:
            old_returned = BorrowingRecord.objects.get(pk=self.pk).returned

        super().save(*args, **kwargs)

        if old_returned is None:
            self.equipment.quantity -= self.quantity_borrowed
            self.equipment.save()

        if old_returned == False and self.returned == True:
            self.equipment.quantity += self.quantity_borrowed
            self.equipment.save()

    def mark_returned(self):
        self.returned = True
        self.returned_date = timezone.now()
        self.save()

    def __str__(self):
        status = "returned" if self.returned else "not returned"
        return f"{self.borrowed_by} borrowed {self.equipment.name} ({status})"

@receiver(pre_delete, sender=TaskSubmission)
def delete_submission_image(sender, instance, **kwargs):
    if instance.image:
        cloudinary.uploader.destroy(str(instance.image))

class TaskReport(models.Model):
    REASON_CHOICES = [
        ('no_signal', 'No Signal'),
        ('bad_weather', 'Bad Weather'),
        ('location_issue', 'Location Issue'),
        ('equipment_issue', 'Equipment Issue'),
        ('other', 'Other'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='reports')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    details = models.TextField(blank=True)
    reported_at = models.DateTimeField(default=timezone.now)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.reported_by} reported {self.task.name} — {self.reason}"
