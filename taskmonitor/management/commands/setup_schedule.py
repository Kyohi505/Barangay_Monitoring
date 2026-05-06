from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        from django_q.models import Schedule
        
        Schedule.objects.get_or_create(
            func='taskmonitor.task_sched.process_pending_validations',
            defaults={
                'schedule_type': Schedule.MINUTES,
                'minutes': 1,
                'name': 'Process Pending Validations',
            }
        )
        self.stdout.write('Schedule created.')