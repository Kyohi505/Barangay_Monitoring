from django.urls import path
from . import api_views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # public
    path('tasks/', api_views.PublicTaskListView.as_view(), name='api_tasks'),
    path('tasks/<int:task_id>/', api_views.PublicTaskDetailView.as_view(), name='api_task_detail'),
    path('equipment/', api_views.EquipmentListView.as_view(), name='api_equipment'),
    path('borrowing/', api_views.BorrowingListView.as_view(), name='api_borrowing'),
    
    # auth
    path('login/', api_views.LoginView.as_view(), name='api_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # personnel
    path('my-tasks/', api_views.MyTasksView.as_view(), name='api_my_tasks'),
    path('my-submissions/', api_views.MySubmissionsView.as_view(), name='api_my_submissions'),
    path('tasks/<int:task_id>/submit/', api_views.SubmitProofView.as_view(), name='api_submit'),
    path('tasks/<int:task_id>/report/', api_views.ReportTaskView.as_view(), name='api_report'),

    
]