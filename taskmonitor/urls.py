from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = "monitoring"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password-change/", auth_views.PasswordChangeView.as_view(template_name='taskmonitor/password_change.html',success_url='/taskmonitor/password-change/done/'), name="password_change"),
    path("password-change/done/", auth_views.PasswordChangeDoneView.as_view(template_name='taskmonitor/password_change_done.html'), name="password_change_done"),

    path("tasks/", views.tasks, name="tasks"),
    path("submit/", views.submit_proof, name="submit"),
    path("tasks/<int:task_id>/", views.task_detail_personnel, name="task_detail_personnel"),
    path("tasks/<int:task_id>/submit/", views.submit_for_task, name="submit_for_task"),
    path("equipment/", views.equipment, name="equipment"),
    path("borrowing/", views.borrowing_history, name="borrowing"),

    path("tasks/<int:task_id>/report/", views.report_task, name="report_task"),

    path("progress/", views.public_progress, name="public"),
    path("progress/<int:task_id>/", views.task_detail, name="task_detail"),
]