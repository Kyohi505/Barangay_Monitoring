from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import Task, TaskSubmission, Equipment, BorrowingRecord
from .serializers import TaskSerializer, TaskSubmissionSerializer, EquipmentSerializer, BorrowingRecordSerializer

from .easyocr_processor import detect_validation_number_smart
import cloudinary.uploader
from datetime import date

# PUBLIC
class PublicTaskListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        tasks = Task.objects.all()
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

class PublicTaskDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, task_id):
        task = Task.objects.get(id=task_id)
        serializer = TaskSerializer(task)
        return Response(serializer.data)

class EquipmentListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        equipment = Equipment.objects.all()
        serializer = EquipmentSerializer(equipment, many=True)
        return Response(serializer.data)

# AUTH
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
            })
        return Response({'error': 'Invalid credentials'}, status=400)

# PERSONNEL
class MyTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tasks = request.user.assigned_tasks.all()
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

class MySubmissionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        submissions = TaskSubmission.objects.filter(submitted_by=request.user).order_by('-submitted_time')
        serializer = TaskSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

class SubmitProofView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        try:
            task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            return Response({'error': 'Task not found'}, status=404)

        if not task.assigned_to.filter(id=request.user.id).exists():
            return Response({'error': 'You are not assigned to this task'}, status=403)

        image = request.FILES.get('image')
        if not image:
            return Response({'error': 'Photo is required'}, status=400)

        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/heic', 'image/heif']
        if image.content_type not in allowed_types:
            return Response({'error': 'Only JPEG and PNG images allowed'}, status=400)

        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')

        if not latitude or not longitude:
            return Response({'error': 'Location is required'}, status=400)

        folder = f"barangay/{request.user.first_name}_{request.user.last_name}/{date.today()}"
        upload_result = cloudinary.uploader.upload(image, folder=folder)

        submission = TaskSubmission(
            task=task,
            submitted_by=request.user,
            latitude=latitude,
            longitude=longitude,
        )
        submission.image = upload_result['public_id']

        if task.task_type == 'validation':
            submission.validation_status = 'pending'

        submission.save()
        serializer = TaskSubmissionSerializer(submission)
        return Response(serializer.data, status=201)
    
class BorrowingListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from .models import BorrowingRecord
        from .serializers import BorrowingRecordSerializer
        records = BorrowingRecord.objects.all().order_by('-borrowed_date')
        serializer = BorrowingRecordSerializer(records, many=True)
        return Response(serializer.data)
    
class ReportTaskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        from .models import TaskReport
        from .serializers import TaskReportSerializer
        task = Task.objects.get(id=task_id)
        report = TaskReport.objects.create(
            task=task,
            reported_by=request.user,
            reason=request.data.get('reason'),
            details=request.data.get('details', ''),
        )
        serializer = TaskReportSerializer(report)
        return Response(serializer.data)