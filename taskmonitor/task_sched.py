import urllib.request
from .easyocr_processor import detect_validation_number_smart

def process_pending_validations():
    from .models import TaskSubmission
    
    pending = TaskSubmission.objects.filter(
        validation_status='pending',
        task__task_type='validation'
    )
    
    for submission in pending:
        try:
            if not submission.image:
                continue
            
            TaskSubmission.objects.filter(id=submission.id).update(validation_status='processing')

            image_url = submission.image.url
            with urllib.request.urlopen(image_url) as response:
                image_bytes = response.read()
            
            result = detect_validation_number_smart(image_bytes)
            
            if result['status'] == 'success':
                submission.validation_status = 'approved'
            else:
                submission.validation_status = 'rejected'
                submission.rejected_reason = 'Could not detect validation number'
            
            submission.save()
        
        except Exception:
            continue