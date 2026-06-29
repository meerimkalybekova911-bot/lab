from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [

    # ─────────────────────────────────────────
    # AUTH
    # ─────────────────────────────────────────
    path('',        views.login_view,  name='home'),
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password-change/', auth_views.PasswordChangeView.as_view(), name='password_change'),

    # ─────────────────────────────────────────
    # ЛАБОРАНТ
    # ─────────────────────────────────────────
    path('dashboard/',   views.dashboard_view,  name='dashboard'),
    path('attendance/',  views.attendance_create_view, name='attendance_page'),
    path('profile/',     views.profile_view,    name='profile'),

    # Иш пландар
    path('projects/',                                    views.projects_list_view,    name='projects_list'),
    path('projects/create/',                             views.project_create_view,   name='project_create'),
    path('projects/<int:project_id>/update/',            views.project_update_view,   name='project_update'),
    path('projects/<int:project_id>/update-status/',     views.update_project_status, name='update_project_status'),
    path('projects/<int:project_id>/comment/',           views.add_comment,           name='add_comment'),
    path('projects/<int:project_id>/reports/create/',    views.report_create_view,    name='report_create_for_project'),

    # Отчеттор
    path('reports/',                           views.reports_list_view,   name='reports_list'),
    path('reports/create/',                    views.report_create_view,  name='report_create'),
    path('reports/export-csv/',                views.export_reports_csv,  name='export_reports_csv'),
    path('reports/<int:report_id>/update/',    views.report_update_view,  name='report_update'),
    path('reports/<int:report_id>/delete/',    views.report_delete_view,  name='report_delete'),
    path('reports/<int:report_id>/download/',  views.report_download_view, name='report_download'),

    # Компьютерлер
    path('computers/',                               views.computers_list_view,    name='computers_list'),
    path('computers/create/',                        views.computer_create_view,   name='computer_create'),
    path('computers/<int:computer_id>/update/',      views.computer_update_view,   name='computer_update'),
    path('inventory/toggle/',                        views.toggle_inventory_lock,  name='toggle_inventory_lock'),

    # Практиканттарды башкаруу (лаборант)
    path('practitioners/',                                   views.practitioners_list,    name='practitioners_list'),
    path('practitioners/<int:practitioner_id>/',             views.practitioner_detail,   name='practitioner_detail'),
    path('practitioners/completions/<int:completion_id>/review/', views.lab_review_completion, name='lab_review_completion'),

    # Күнүмдүк иш пландар
    path('daily-plans/',                        views.daily_plans_list,   name='daily_plans_list'),
    path('daily-plans/create/',                 views.daily_plan_create,  name='daily_plan_create'),
    path('daily-plans/<int:plan_id>/update/',   views.daily_plan_update,  name='daily_plan_update'),

    # ─────────────────────────────────────────
    # ЖЕТЕКЧИ
    # ─────────────────────────────────────────
    path('leader/',          views.leader_dashboard_view, name='leader_dashboard'),
    path('leader/profile/',  views.leader_profile_view,   name='leader_profile'),

    # Жетекчи: отчётту бекитүү
    path('practitioners/completions/<int:completion_id>/approve/', views.leader_approve_completion, name='leader_approve_completion'),

    # ─────────────────────────────────────────
    # ПРАКТИКАНТ (СТУДЕНТ)
    # ─────────────────────────────────────────
    path('student/',                                        views.student_dashboard,       name='student_dashboard'),
    path('student/attendance/',                             views.student_attendance,      name='student_attendance'),
    path('student/plans/',                                  views.student_plans,           name='student_plans'),
    path('student/plans/<int:plan_id>/submit/',             views.student_submit_report,   name='student_submit_report'),
    path('student/profile/',                                views.student_profile,         name='student_profile'),
]
