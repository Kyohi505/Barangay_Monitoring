from rest_framework import serializers
from .models import Task, TaskSubmission, Equipment, BorrowingRecord, CustomUser, TaskReport

class PersonnelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'email']

class TaskSubmissionSerializer(serializers.ModelSerializer):
    submitted_by = PersonnelSerializer(read_only=True)
    
    class Meta:
        model = TaskSubmission
        fields = ['id', 'submitted_by', 'image', 'latitude', 'longitude', 'submitted_time', 'validation_status', 'rejection_reason']

class TaskSerializer(serializers.ModelSerializer):
    assigned_to = PersonnelSerializer(many=True, read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'name', 'description', 'task_type', 'status', 'total_items', 'assigned_to', 'date_created', 'due_date', 'progress']

    def get_progress(self, obj):
        return obj.get_progress()

class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = ['id', 'name', 'quantity', 'description']

class BorrowingRecordSerializer(serializers.ModelSerializer):
    equipment = EquipmentSerializer(read_only=True)

    class Meta:
        model = BorrowingRecord
        fields = ['id', 'equipment', 'borrowed_by', 'quantity_borrowed', 'borrowed_date', 'due_date', 'returned', 'returned_date', 'notes']

class TaskReportSerializer(serializers.ModelSerializer):
    reported_by = PersonnelSerializer(read_only=True)
    
    class Meta:
        model = TaskReport
        fields = ['id', 'task', 'reported_by', 'reason', 'details', 'reported_at', 'resolved']