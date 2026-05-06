from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from datetime import date

from .models import Task, TaskSubmission, BorrowingRecord

from .easyocr_processor import detect_validation_number_smart
import cloudinary.uploader

# Create your views here.

def login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('monitoring:tasks')
        else:
            return render(request, 'taskmonitor/login.html', {'error': 'Invalid email or password'})
    return render(request, 'taskmonitor/login.html')

def logout_view(request):
    logout(request)
    return redirect('monitoring:login')

@login_required
def tasks(request):
    my_tasks = request.user.assigned_tasks.all()
    for task in my_tasks:
        progress = task.get_progress()
        task.progress_pct = int(progress['approved'] / progress['total'] * 100) if progress['total'] > 0 else 0
    my_submissions = TaskSubmission.objects.filter(submitted_by=request.user).order_by('-submitted_time')
    return render(request, 'taskmonitor/tasks.html', {
        'tasks': my_tasks,
        'submissions': my_submissions,
    })

def task_detail(request, task_id):
    task = Task.objects.get(id=task_id)
    progress = task.get_progress()
    task.progress_pct = int(progress['approved'] / progress['total'] * 100) if progress['total'] > 0 else 0
    submissions = task.submissions.filter(validation_status='approved')
    return render(request, 'taskmonitor/task_detail.html', {
        'task': task,
        'submissions': submissions
    })

def task_detail_personnel(request, task_id):
    task = Task.objects.get(id=task_id)
    progress = task.get_progress()
    task.progress_pct = int(progress['approved'] / progress['total'] * 100) if progress['total'] > 0 else 0
    submissions = task.submissions.filter(submitted_by=request.user)
    return render(request, 'taskmonitor/task_detail_personnel.html', {
        'task': task,
        'submissions': submissions
    })

def submit_proof(request):
    my_tasks = request.user.assigned_tasks.all()
    if request.method == 'POST':
        task_id = request.POST['task']
        task = Task.objects.get(id=task_id)
        submission = TaskSubmission(
            task = task,
            submitted_by = request.user,
            latitude = request.POST.get('latitude'),
            longitude = request.POST.get('longitude'),
            image = request.FILES.get('image'),
        )
        submission.save()
        return redirect('monitoring:tasks')
    return render(request, 'taskmonitor/submit.html', {'tasks': my_tasks})

def public_progress(request):
    tasks = Task.objects.all()
    for task in tasks:
        progress = task.get_progress()
        task.progress_pct = int(progress['approved'] / progress['total'] * 100) if progress['total'] > 0 else 0
    total = tasks.count()
    completed = tasks.filter(status='completed').count()
    in_progress = tasks.filter(status='in_progress').count()
    return render(request, 'taskmonitor/public.html', {
        'tasks': tasks,
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
    })

@login_required
def submit_for_task(request, task_id):
    task = Task.objects.get(id=task_id)
    if request.method == 'POST':
        image = request.FILES.get('image')

        if not image:
            messages.error(request, 'Please attach a photo before submitting.')
            return redirect('monitoring:task_detail_personnel', task_id=task_id)

        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/heic', 'image/heif']
        if image.content_type not in allowed_types:
            messages.error(request, 'Only JPEG and PNG images are allowed.')
            return redirect('monitoring:task_detail_personnel', task_id=task_id)

        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')

        if not latitude or not longitude:
            messages.error(request, 'Location is required. Please enable GPS and try again.')
            return redirect('monitoring:task_detail_personnel', task_id=task_id)

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
        messages.success(request, 'Photo submitted successfully.')

    return redirect('monitoring:task_detail_personnel', task_id=task_id)

def equipment(request):
    from .models import Equipment, BorrowingRecord
    equipment_list = Equipment.objects.all()
    active_borrows = BorrowingRecord.objects.filter(returned=False)
    return render(request, 'taskmonitor/equipment.html', {
        'equipment_list': equipment_list,
        'active_borrows': active_borrows,
    })

def borrowing_history(request):
    records = BorrowingRecord.objects.all().order_by('-borrowed_date')
    return render(request, 'taskmonitor/borrowing.html', {'records': records})

@login_required
def report_task(request, task_id):
    task = Task.objects.get(id=task_id)
    if request.method == 'POST':
        from .models import TaskReport
        reason = request.POST.get('reason')
        details = request.POST.get('details')
        TaskReport.objects.create(
            task=task,
            reported_by=request.user,
            reason=reason,
            details=details,
        )
        messages.success(request, 'Report submitted. Admin has been notified.')
    return redirect('monitoring:task_detail_personnel', task_id=task_id)