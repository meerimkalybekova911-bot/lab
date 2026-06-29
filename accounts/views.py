import base64
import csv
import os
import logging
logger = logging.getLogger(__name__)
from datetime import date, datetime, timedelta
from django.core.files.base import ContentFile
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, FileResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q

from .models import (
    Comment, LabAssistant, Project, Attendance,
    Computer, Room, Report, InventoryLock,
    Practitioner, DailyPlan,
    PractitionerAttendance, PlanCompletion,
)
from .forms import (
    AttendanceForm, ProjectForm, ComputerForm,
    ReportForm, LabAssistantProfileForm,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# ЖАРДАМЧЫ: Колдонуучунун ролун аныктоо
# ─────────────────────────────────────────
def _get_role(user):
    """
    'leader' | 'laborant' | 'practitioner' | None
    """
    try:
        return user.labassistant.role
    except LabAssistant.DoesNotExist:
        pass
    try:
        user.practitioner
        return 'practitioner'
    except Practitioner.DoesNotExist:
        pass
    return None


# ─────────────────────────────────────────
# LOGIN / LOGOUT
# ─────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        role = _get_role(request.user)
        if role == 'leader':
            return redirect('leader_dashboard')
        if role == 'practitioner':
            return redirect('student_dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            role = _get_role(user)
            if role == 'leader':
                messages.success(request, f"Кош келиңиз, жетекчи {user.labassistant.full_name}!")
                return redirect('leader_dashboard')
            if role == 'practitioner':
                messages.success(request, f"Кош келиңиз, {user.practitioner.full_name}!")
                return redirect('student_dashboard')
            if role == 'laborant':
                messages.success(request, f"Кош келиңиз, лаборант {user.labassistant.full_name}!")
                return redirect('dashboard')
            # Профиль жок колдонуучу
            LabAssistant.objects.create(
                user=user,
                full_name=user.get_full_name() or user.username,
                role='laborant'
            )
            messages.info(request, "Профилиңиз автоматтык түрдө түзүлдү")
            return redirect('dashboard')
        else:
            messages.error(request, "Колдонуучу аты же сырсөз туура эмес!")

    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


# ─────────────────────────────────────────
# ЛАБОРАНТ DASHBOARD
# ─────────────────────────────────────────
@login_required
def dashboard_view(request):
    try:
        labassistant = LabAssistant.objects.get(user=request.user)
        if labassistant.role == 'leader':
            return redirect('leader_dashboard')
    except LabAssistant.DoesNotExist:
        labassistant = LabAssistant.objects.create(
            user=request.user,
            full_name=request.user.get_full_name() or request.user.username,
            role='laborant'
        )
    return render(request, 'accounts/dashboard.html', {'labassistant': labassistant})


# ─────────────────────────────────────────
# ЛАБОРАНТ: КЕЛҮҮ ЖУРНАЛЫ
# ─────────────────────────────────────────
@login_required
def attendance_create_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    today_attendance = Attendance.objects.filter(
        labassistant=labassistant, date=date.today()
    ).first()
    attendance_history = Attendance.objects.filter(
        labassistant=labassistant
    ).order_by('-date')[:20]

    if request.method == 'POST':
        if not today_attendance:
            arrival_time = request.POST.get('arrival_time', '').strip()
            comment      = request.POST.get('comment', '').strip()
            photo_base64 = request.POST.get('photo_base64', '').strip()

            if not arrival_time:
                messages.error(request, "Келүү убактысын жазыңыз")
                return redirect('attendance_page')
            try:
                h, m = map(int, arrival_time.split(':'))
                if not (0 <= h <= 23 and 0 <= m <= 59):
                    raise ValueError
            except (ValueError, AttributeError):
                messages.error(request, "Келүү убактысы туура эмес форматта (ЧЧ:ММ)")
                return redirect('attendance_page')

            is_late = (h > 8) or (h == 8 and m > 0)

            if not photo_base64 or not photo_base64.startswith('data:image'):
                messages.error(request, "Сүрөт тартуу милдеттүү!")
                return redirect('attendance_page')
            if len(photo_base64) > 5 * 1024 * 1024:
                messages.error(request, "Сүрөт өтө чоң (максималдуу 5MB)")
                return redirect('attendance_page')
            if is_late and not comment:
                messages.error(request, "Кечигүүнүн себебин жазыңыз")
                return redirect('attendance_page')

            photo = None
            try:
                fmt, imgstr = photo_base64.split(';base64,')
                ext = fmt.split('/')[-1]
                if ext.lower() not in ('jpeg', 'jpg', 'png', 'webp'):
                    ext = 'jpg'
                photo = ContentFile(
                    base64.b64decode(imgstr),
                    name=f'attendance_{date.today()}_{labassistant.id}.{ext}'
                )
            except (ValueError, base64.binascii.Error):
                messages.error(request, "Сүрөт туура эмес форматта, кайра тартыңыз")
                return redirect('attendance_page')

            Attendance.objects.create(
                labassistant=labassistant,
                date=date.today(),
                arrival_time=arrival_time,
                photo=photo,
                comment=comment,
                late=is_late
            )
            messages.success(request, "Келүү ийгиликтүү катталды!")
            return redirect('attendance_page')
        else:
            messages.error(request, "Бүгүнкү келүү мурунтан эле катталган")

    return render(request, 'accounts/attendance_page.html', {
        'labassistant':       labassistant,
        'today_attendance':   today_attendance,
        'attendance_history': attendance_history,
    })


# ─────────────────────────────────────────
# ИШ ПЛАНДАР
# ─────────────────────────────────────────
@login_required
def projects_list_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)

    if labassistant.role == 'leader':
        projects = Project.objects.all()
    else:
        projects = Project.objects.filter(
            Q(labassistant=labassistant) | Q(is_public=True)
        )

    projects = projects.select_related('labassistant') \
                       .prefetch_related('comments__author') \
                       .order_by('-start_date')

    return render(request, 'accounts/projects_list.html', {
        'labassistant':       labassistant,
        'projects':           projects,
        'total_projects':     projects.count(),
        'active_projects':    projects.filter(status='active').count(),
        'paused_projects':    projects.filter(status='paused').count(),
        'completed_projects': projects.filter(status='completed').count(),
    })


@login_required
def project_create_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)

    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        start_date  = request.POST.get('start_date', '').strip()
        end_date    = request.POST.get('end_date', '').strip() or None
        status      = request.POST.get('status', 'active')
        attachment  = request.FILES.get('attachment')
        is_public   = bool(request.POST.get('is_public'))

        if not title or not description or not start_date:
            messages.error(request, "Милдеттүү талааларды толтуруңуз!")
            return redirect('project_create')

        Project.objects.create(
            labassistant=labassistant,
            title=title, description=description,
            start_date=start_date, end_date=end_date,
            status=status, attachment=attachment,
            is_public=is_public
        )
        messages.success(request, "Иш план ийгиликтүү түзүлдү!")
        return redirect('projects_list')

    return render(request, 'accounts/project_form.html', {
        'labassistant': labassistant, 'editing': False
    })


@login_required
def project_update_view(request, project_id):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    project = get_object_or_404(Project, id=project_id)

    if labassistant.role != 'leader' and project.labassistant != labassistant:
        messages.error(request, "Сиз бул иш планды өзгөртө албайсыз!")
        return redirect('projects_list')

    if request.method == 'POST':
        project.title       = request.POST.get('title', '').strip()
        project.description = request.POST.get('description', '').strip()
        project.status      = request.POST.get('status', 'active')
        project.start_date  = request.POST.get('start_date', '').strip()
        project.end_date    = request.POST.get('end_date', '').strip() or None
        project.is_public   = bool(request.POST.get('is_public'))

        attachment = request.FILES.get('attachment')
        if attachment:
            project.attachment = attachment
        if request.POST.get('attachment-clear') and project.attachment:
            project.attachment.delete(save=False)
            project.attachment = None

        project.save()
        messages.success(request, "Иш план ийгиликтүү жаңыртылды!")
        return redirect('projects_list')

    return render(request, 'accounts/project_form.html', {
        'labassistant': labassistant, 'project': project, 'editing': True
    })


@login_required
@require_POST
def update_project_status(request, project_id):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    project = get_object_or_404(Project, id=project_id)

    if labassistant.role != 'leader' and project.labassistant != labassistant:
        messages.error(request, "Сиз бул иш пландын статусун өзгөртө албайсыз!")
        return redirect('projects_list')

    new_status = request.POST.get('status')
    if new_status in ['active', 'paused', 'completed']:
        project.status = new_status
        if new_status == 'completed' and not project.end_date:
            project.end_date = date.today()
        project.save()
        messages.success(request, "Статус өзгөртүлдү")
    else:
        messages.error(request, "Жарамсыз статус")
    return redirect('projects_list')


@login_required
@require_POST
def add_comment(request, project_id):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    project = get_object_or_404(Project, id=project_id)

    if labassistant.role != 'leader':
        if project.labassistant != labassistant and not project.is_public:
            messages.error(request, "Бул иш планга комментарий жаза албайсыз")
            return redirect('projects_list')

    text = request.POST.get('comment', '').strip()
    if text:
        Comment.objects.create(project=project, author=labassistant, text=text)
        messages.success(request, "Комментарий кошулду")
    return redirect('projects_list')


# ─────────────────────────────────────────
# ОТЧЕТТОР
# ─────────────────────────────────────────
@login_required
def reports_list_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    reports = Report.objects.filter(labassistant=labassistant).order_by('-created_at')
    return render(request, 'accounts/reports_list.html', {
        'labassistant':  labassistant,
        'reports':       reports,
        'total_reports': reports.count(),
    })


@login_required
def report_create_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            report = form.save(commit=False)
            report.labassistant = labassistant
            report.save()
            messages.success(request, "Отчет ийгиликтүү түзүлдү!")
            return redirect('reports_list')
    else:
        form = ReportForm(user=request.user)
    return render(request, 'accounts/report_form.html', {
        'labassistant': labassistant,
        'form': form,
        'page_title': 'Жаңы отчет түзүү',
    })


@login_required
def report_update_view(request, report_id):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    report = get_object_or_404(Report, id=report_id, labassistant=labassistant)
    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES, instance=report, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Отчет ийгиликтүү жаңыртылды!")
            return redirect('reports_list')
    else:
        form = ReportForm(instance=report, user=request.user)
    return render(request, 'accounts/report_form.html', {
        'labassistant': labassistant,
        'form': form,
        'report': report,
        'page_title': 'Отчетту өзгөртүү',
    })

@login_required
def report_delete_view(request, report_id):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    report = get_object_or_404(Report, id=report_id, labassistant=labassistant)
    if request.method == 'POST':
        report.delete()
        messages.success(request, "Отчет ийгиликтүү өчүрүлдү!")
        return redirect('reports_list')
    return render(request, 'accounts/report_confirm_delete.html', {
        'labassistant': labassistant, 'report': report
    })


@login_required
def report_download_view(request, report_id):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    report = get_object_or_404(Report, id=report_id, labassistant=labassistant)
    if not report.file:
        messages.error(request, "Файл табылган жок")
        return redirect('reports_list')
 
    # FIX: report.file.path S3/Supabase storage'де иштебейт
    # (NotImplementedError: бул backend абсолюттук жолдорду колдобойт)
    # Ордуна Supabase'дин public URL'ине redirect кылабыз —
    # файл түз браузерден жүктөлөт.
    return redirect(report.file.url)
 
 
@login_required
def export_reports_csv(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    reports = Report.objects.filter(labassistant=labassistant)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="reports_{datetime.now().strftime("%Y%m%d")}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(['№', 'Отчеттун аты', 'Иш план', 'Түзүлгөн күнү', 'Кошумча маалымат'])
    for i, r in enumerate(reports, 1):
        writer.writerow([
            i, r.title, r.project.title,
            r.created_at.strftime('%d.%m.%Y %H:%M'),
            r.comment[:100] if r.comment else ''
        ])
    return response


# ─────────────────────────────────────────
# КОМПЬЮТЕРЛЕР
# ─────────────────────────────────────────
@login_required
def computers_list_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)

    inventory_status = {'is_locked': True}
    try:
        lock = InventoryLock.objects.first()
        if lock:
            inventory_status = {
                'is_locked':  lock.is_locked,
                'changed_at': lock.changed_at,
                'locked_by':  lock.locked_by,
            }
    except Exception:
        pass

    rooms = (
        labassistant.rooms.all().order_by('name')
        if labassistant.role == 'laborant'
        else Room.objects.all().order_by('name')
    )

    selected_room_id = request.GET.get('room')
    rooms_with_computers = [
        {'room': room, 'computers': room.computers.all()}
        for room in rooms
        if not selected_room_id or str(room.id) == selected_room_id
    ]

    return render(request, 'accounts/computers_list.html', {
        'labassistant':         labassistant,
        'rooms':                rooms,
        'rooms_with_computers': rooms_with_computers,
        'selected_room_id':     selected_room_id,
        'inventory_status':     inventory_status,
    })


@login_required
def computer_create_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    try:
        lock = InventoryLock.objects.first()
        if lock and lock.is_locked:
            messages.error(request, "Инвентаризация жабык! Жаңы компьютер кошуу мүмкүн эмес.")
            return redirect('computers_list')
    except Exception:
        pass

    if request.method == 'POST':
        form = ComputerForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Компьютер ийгиликтүү кошулду!")
            return redirect('computers_list')
    else:
        form = ComputerForm(user=request.user)
    return render(request, 'accounts/computer_form.html', {
        'labassistant': labassistant, 'form': form, 'editing': False
    })


@login_required
def computer_update_view(request, computer_id):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    computer = get_object_or_404(Computer, id=computer_id)

    if labassistant.role == 'laborant' and computer.room not in labassistant.rooms.all():
        messages.error(request, "Бул компьютерди өзгөртүүгө уруксат жок!")
        return redirect('computers_list')

    try:
        lock = InventoryLock.objects.first()
        if lock and lock.is_locked:
            messages.error(request, "Инвентаризация жабык! Компьютерди өзгөртүү мүмкүн эмес.")
            return redirect('computers_list')
    except Exception:
        pass

    if request.method == 'POST':
        form = ComputerForm(request.POST, instance=computer, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Компьютер ийгиликтүү жаңыртылды!")
            return redirect('computers_list')
    else:
        form = ComputerForm(instance=computer, user=request.user)
    return render(request, 'accounts/computer_form.html', {
        'labassistant': labassistant, 'computer': computer,
        'form': form, 'editing': True
    })


@login_required
def toggle_inventory_lock(request):
    if not request.user.is_superuser:
        messages.error(request, "Бул функцияга администратор гана кире алат!")
        return redirect('computers_list')

    lock, _ = InventoryLock.objects.get_or_create(defaults={'is_locked': True})

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'enable':
            lock.is_locked = False
            lock.locked_by = request.user
            messages.success(request, "Инвентаризация режими ачылды!")
        elif action == 'disable':
            lock.is_locked = True
            lock.locked_by = request.user
            messages.success(request, "Инвентаризация режими жабылды!")
        lock.save()
        return redirect('computers_list')

    return render(request, 'accounts/inventory_lock.html', {'lock': lock})


# ─────────────────────────────────────────
# ПРОФИЛЬ
# ─────────────────────────────────────────
@login_required
def profile_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
 
    if request.method == 'POST':
        # DEBUG: эмне келип жатканын логго жазабыз
        logger.warning(f"POST FILES: {request.FILES}")
        logger.warning(f"profile_image in FILES: {'profile_image' in request.FILES}")
        logger.warning(f"resume in FILES: {'resume' in request.FILES}")
 
        form = LabAssistantProfileForm(
            request.POST, request.FILES, instance=labassistant
        )
 
        if form.is_valid():
            logger.warning(f"Form valid. Cleaned profile_image: {form.cleaned_data.get('profile_image')}")
            logger.warning(f"Form valid. Cleaned resume: {form.cleaned_data.get('resume')}")
 
            saved = form.save()
 
            logger.warning(f"After save. profile_image: {saved.profile_image}")
            logger.warning(f"After save. resume: {saved.resume}")
 
            messages.success(request, "Профиль ийгиликтүү жаңыртылды!")
            return redirect('profile')
        else:
            logger.warning(f"Form errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = LabAssistantProfileForm(instance=labassistant)
 
    return render(request, 'accounts/profile.html', {
        'form': form, 'labassistant': labassistant,
    })
 
 
 
@login_required
def leader_profile_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    if labassistant.role != 'leader':
        messages.error(request, "Уруксат жок!")
        return redirect('dashboard')
 
    if request.method == 'POST':
        form = LabAssistantProfileForm(
            request.POST, request.FILES, instance=labassistant
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Профиль сакталды!")
            return redirect('leader_profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = LabAssistantProfileForm(instance=labassistant)
 
    return render(request, 'accounts/leader_profile.html', {
        'form': form, 'labassistant': labassistant
    })


# ─────────────────────────────────────────
# ЖЕТЕКЧИНИН ПАНЕЛИ
# ─────────────────────────────────────────
@login_required
def leader_dashboard_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    if labassistant.role != 'leader':
        messages.error(request, "Бул баракчага кирүүгө уруксат жок!")
        return redirect('dashboard')

    laborants = LabAssistant.objects.filter(role='laborant').prefetch_related('rooms', 'projects', 'reports', 'attendances')
    selected_laborant_id = request.GET.get('laborant', 'all')
    selected_laborant = None
    if selected_laborant_id != 'all':
        selected_laborant = get_object_or_404(LabAssistant, id=selected_laborant_id, role='laborant')

    week_ago = date.today() - timedelta(days=7)
    late_arrivals = Attendance.objects.filter(
        date__gte=week_ago, late=True
    ).order_by('-date')[:5]

    if selected_laborant:
        attendance_data = Attendance.objects.filter(labassistant=selected_laborant)
        projects_data   = Project.objects.filter(labassistant=selected_laborant)
        reports_data    = Report.objects.filter(labassistant=selected_laborant)
    else:
        attendance_data = Attendance.objects.all()
        projects_data   = Project.objects.all().select_related('labassistant').prefetch_related('comments__author')
        reports_data    = Report.objects.all()

    computers_by_laborant = {}
    for lab in ([selected_laborant] if selected_laborant else laborants):
        if lab.rooms.exists():
            rooms_dict = {
                room: Computer.objects.filter(room=room)
                for room in lab.rooms.all()
                if Computer.objects.filter(room=room).exists()
            }
            if rooms_dict:
                computers_by_laborant[lab] = rooms_dict

    # ── ПРАКТИКАНТ МААЛЫМАТТАРЫ ──────────────────────────
    practitioners = Practitioner.objects.all().select_related(
        'room', 'supervisor', 'user'
    ).order_by('course', 'full_name')

    # Бекитилүүнү күткөн отчёттор
    pending_completions = PlanCompletion.objects.filter(
        status__in=['submitted', 'lab_reviewed']
    ).select_related('practitioner', 'plan').order_by('-submitted_at')

    # Практиканттардын кечиккен келүүлөрү (акыркы 7 күн)
    pract_late_arrivals = PractitionerAttendance.objects.filter(
        date__gte=week_ago, late=True
    ).select_related('practitioner').order_by('-date')[:10]

    # Бүгүн келген практиканттар
    today_pract_attendance = PractitionerAttendance.objects.filter(
        date=date.today()
    ).count()

    return render(request, 'accounts/leader_dashboard.html', {
        'labassistant':            labassistant,
        'laborants':               laborants,
        'selected_laborant':       selected_laborant,
        'selected_laborant_id':    selected_laborant_id,

        # Статистика
        'total_laborants':         laborants.count(),
        'active_projects':         Project.objects.filter(status='active').count(),
        'today_attendance':        Attendance.objects.filter(date=date.today()).count(),
        'bad_computers':           Computer.objects.count(),
        'late_arrivals':           late_arrivals,

        # Лаборант маалыматтары
        'attendance_data':         attendance_data.order_by('-date'),
        'projects_data':           projects_data.order_by('-start_date'),
        'reports_data':            reports_data.order_by('-created_at'),
        'computers_by_laborant':   computers_by_laborant,

        # Практикант маалыматтары
        'practitioners':           practitioners,
        'pending_completions':     pending_completions,
        'pract_late_arrivals':     pract_late_arrivals,
        'today_pract_attendance':  today_pract_attendance,
        'total_practitioners':     practitioners.count(),
        'active_practitioners':    practitioners.filter(
            practice_start__lte=date.today(),
            practice_end__gte=date.today()
        ).count(),
    })

# ═══════════════════════════════════════════════════
# ПРАКТИКАНТ СИСТЕМАСЫ
# ═══════════════════════════════════════════════════

def _practitioner_required(view_func):
    """Практикант гана кире алат деген декоратор."""
    @login_required
    def wrapper(request, *args, **kwargs):
        try:
            practitioner = request.user.practitioner
        except Practitioner.DoesNotExist:
            messages.error(request, "Бул бет практиканттар үчүн гана!")
            return redirect('login')
        return view_func(request, *args, practitioner=practitioner, **kwargs)
    return wrapper


def _lab_or_leader_required(view_func):
    """Лаборант же жетекчи гана кире алат."""
    @login_required
    def wrapper(request, *args, **kwargs):
        try:
            la = request.user.labassistant
        except LabAssistant.DoesNotExist:
            messages.error(request, "Уруксат жок!")
            return redirect('login')
        return view_func(request, *args, labassistant=la, **kwargs)
    return wrapper


# ─────────────────────────────────────────
# СТУДЕНТТИН ПАНЕЛИ
# ─────────────────────────────────────────
@_practitioner_required
def student_dashboard(request, practitioner):
    today_plan = None
    today_attendance = None
    day = practitioner.current_work_day

    if day > 0:
        today_plan = DailyPlan.objects.filter(
            course=practitioner.course,
            day_number=day
        ).first()

    today_attendance = PractitionerAttendance.objects.filter(
        practitioner=practitioner,
        date=date.today()
    ).first()

    # Бүгүнкү иш пландын отчётун жиберди беле?
    today_completion = None
    if today_plan:
        today_completion = PlanCompletion.objects.filter(
            practitioner=practitioner,
            plan=today_plan
        ).first()

    return render(request, 'accounts/student_dashboard.html', {
        'practitioner':     practitioner,
        'today_plan':       today_plan,
        'today_attendance': today_attendance,
        'today_completion': today_completion,
        'current_day':      day,
    })


# ─────────────────────────────────────────
# СТУДЕНТ: КЕЛҮҮ КАТТОО
# ─────────────────────────────────────────
@_practitioner_required
def student_attendance(request, practitioner):
    today_att = PractitionerAttendance.objects.filter(
        practitioner=practitioner,
        date=date.today()
    ).first()

    history = PractitionerAttendance.objects.filter(
        practitioner=practitioner
    ).order_by('-date')[:20]

    if request.method == 'POST' and not today_att:
        arrival_time = request.POST.get('arrival_time', '').strip()
        comment      = request.POST.get('comment', '').strip()
        photo_base64 = request.POST.get('photo_base64', '').strip()

        if not arrival_time:
            messages.error(request, "Келүү убактысын жазыңыз")
            return redirect('student_attendance')
        try:
            h, m = map(int, arrival_time.split(':'))
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
        except (ValueError, AttributeError):
            messages.error(request, "Убакыт туура эмес форматта (ЧЧ:ММ)")
            return redirect('student_attendance')

        is_late = (h > 8) or (h == 8 and m > 0)

        if not photo_base64 or not photo_base64.startswith('data:image'):
            messages.error(request, "Сүрөт тартуу милдеттүү!")
            return redirect('student_attendance')
        if len(photo_base64) > 5 * 1024 * 1024:
            messages.error(request, "Сүрөт өтө чоң (макс. 5MB)")
            return redirect('student_attendance')
        if is_late and not comment:
            messages.error(request, "Кечигүүнүн себебин жазыңыз")
            return redirect('student_attendance')

        photo = None
        try:
            fmt, imgstr = photo_base64.split(';base64,')
            ext = fmt.split('/')[-1]
            if ext.lower() not in ('jpeg', 'jpg', 'png', 'webp'):
                ext = 'jpg'
            photo = ContentFile(
                base64.b64decode(imgstr),
                name=f'pract_{date.today()}_{practitioner.id}.{ext}'
            )
        except (ValueError, base64.binascii.Error):
            messages.error(request, "Сүрөт туура эмес форматта, кайра тартыңыз")
            return redirect('student_attendance')

        PractitionerAttendance.objects.create(
            practitioner=practitioner,
            date=date.today(),
            arrival_time=arrival_time,
            photo=photo,
            comment=comment,
            late=is_late
        )
        messages.success(request, "Келүү катталды!")
        return redirect('student_dashboard')

    return render(request, 'accounts/student_attendance.html', {
        'practitioner': practitioner,
        'today_att':    today_att,
        'history':      history,
    })


# ─────────────────────────────────────────
# СТУДЕНТ: КҮНҮМДҮК ИШ ПЛАН
# ─────────────────────────────────────────
@_practitioner_required
def student_plans(request, practitioner):
    """Практиканттын курсуна тиешелүү бардык иш пландар."""
    plans = DailyPlan.objects.filter(
        course=practitioner.course
    ).order_by('day_number')

    # Ар бир планга отчёт статусун кошуу
    completions = {
        c.plan_id: c
        for c in PlanCompletion.objects.filter(practitioner=practitioner)
    }

    plans_with_status = [
        {
            'plan':       plan,
            'completion': completions.get(plan.id),
            'is_today':   plan.day_number == practitioner.current_work_day,
        }
        for plan in plans
    ]

    return render(request, 'accounts/student_plans.html', {
        'practitioner':      practitioner,
        'plans_with_status': plans_with_status,
        'current_day':       practitioner.current_work_day,
    })


# ─────────────────────────────────────────
# СТУДЕНТ: ОТЧЁТ ЖҮКТӨӨ
# ─────────────────────────────────────────
@_practitioner_required
def student_submit_report(request, practitioner, plan_id):
    plan = get_object_or_404(DailyPlan, id=plan_id, course=practitioner.course)

    # Мурда жиберилген отчёт бар болсо
    existing = PlanCompletion.objects.filter(
        practitioner=practitioner, plan=plan
    ).first()

    # Кайтарылган отчётту кайра жиберүүгө болот
    if existing and existing.status not in ('rejected',):
        messages.info(request, "Бул иш пландын отчёту мурунтан жиберилген.")
        return redirect('student_plans')

    if request.method == 'POST':
        report_text = request.POST.get('report_text', '').strip()
        attachment  = request.FILES.get('attachment')

        if not report_text:
            messages.error(request, "Отчёт текстин жазыңыз")
            return redirect('student_submit_report', plan_id=plan_id)

        if existing:
            # Кайтарылган → кайра жиберүү
            existing.report_text  = report_text
            existing.status       = 'submitted'
            existing.attachment   = attachment or existing.attachment
            existing.submitted_at = timezone.now()
            existing.leader_approved    = False
            existing.leader_feedback    = ''
            existing.lab_feedback       = ''
            existing.save()
            messages.success(request, "Отчёт кайра жиберилди!")
        else:
            PlanCompletion.objects.create(
                practitioner=practitioner,
                plan=plan,
                report_text=report_text,
                attachment=attachment,
            )
            messages.success(request, "Отчёт ийгиликтүү жиберилди!")

        return redirect('student_plans')

    return render(request, 'accounts/student_submit_report.html', {
        'practitioner': practitioner,
        'plan':         plan,
        'existing':     existing,
    })


# ─────────────────────────────────────────
# ЛАБОРАНТ: ПРАКТИКАНТТАР ТИЗМЕСИ
# ─────────────────────────────────────────
@_lab_or_leader_required
def practitioners_list(request, labassistant):
    if labassistant.role == 'leader':
        practitioners = Practitioner.objects.all()
    else:
        practitioners = Practitioner.objects.filter(supervisor=labassistant)

    practitioners = practitioners.select_related('room', 'supervisor') \
                                 .order_by('course', 'full_name')

    # Курс боюнча чыпкалоо
    course_filter = request.GET.get('course')
    if course_filter:
        practitioners = practitioners.filter(course=course_filter)

    return render(request, 'accounts/practitioners_list.html', {
        'labassistant':  labassistant,
        'practitioners': practitioners,
        'course_filter': course_filter,
        'total':         practitioners.count(),
    })


# ─────────────────────────────────────────
# ЛАБОРАНТ: ПРАКТИКАНТТЫН ДЕТАЛДАРЫ
# ─────────────────────────────────────────
@_lab_or_leader_required
def practitioner_detail(request, labassistant, practitioner_id):
    if labassistant.role == 'leader':
        practitioner = get_object_or_404(Practitioner, id=practitioner_id)
    else:
        practitioner = get_object_or_404(
            Practitioner, id=practitioner_id, supervisor=labassistant
        )

    attendances  = practitioner.attendances.order_by('-date')
    completions  = practitioner.completions.select_related('plan').order_by('-submitted_at')

    return render(request, 'accounts/practitioner_detail.html', {
        'labassistant':  labassistant,
        'practitioner':  practitioner,
        'attendances':   attendances,
        'completions':   completions,
    })


# ─────────────────────────────────────────
# ЛАБОРАНТ: ОТЧЁТТУ ТЕКШЕРҮҮ
# ─────────────────────────────────────────
@_lab_or_leader_required
@require_POST
def lab_review_completion(request, labassistant, completion_id):
    if labassistant.role == 'leader':
        completion = get_object_or_404(PlanCompletion, id=completion_id)
    else:
        completion = get_object_or_404(
            PlanCompletion,
            id=completion_id,
            practitioner__supervisor=labassistant
        )

    action   = request.POST.get('action')  # 'approve' | 'reject'
    feedback = request.POST.get('feedback', '').strip()

    if action == 'approve':
        completion.status         = 'lab_reviewed'
        completion.lab_checked    = labassistant
        completion.lab_feedback   = feedback
        completion.lab_checked_at = timezone.now()
        completion.save()
        messages.success(request, "Отчёт текшерилди. Жетекчи бекитүүсүн күтүүдө.")
    elif action == 'reject':
        completion.status         = 'rejected'
        completion.lab_checked    = labassistant
        completion.lab_feedback   = feedback
        completion.lab_checked_at = timezone.now()
        completion.save()
        messages.warning(request, "Отчёт кайтарылды. Студент кайра жиберет.")
    else:
        messages.error(request, "Жарамсыз аракет")

    return redirect('practitioner_detail', practitioner_id=completion.practitioner_id)


# ─────────────────────────────────────────
# ЖЕТЕКЧИ: ОТЧЁТТУ БЕКИТҮҮ
# ─────────────────────────────────────────
@login_required
@require_POST
def leader_approve_completion(request, completion_id):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    if labassistant.role != 'leader':
        messages.error(request, "Уруксат жок!")
        return redirect('dashboard')

    completion = get_object_or_404(
        PlanCompletion, id=completion_id, status='lab_reviewed'
    )
    action   = request.POST.get('action')
    feedback = request.POST.get('feedback', '').strip()

    if action == 'approve':
        completion.leader_approved    = True
        completion.status             = 'approved'
        completion.leader_feedback    = feedback
        completion.leader_approved_at = timezone.now()
        completion.save()
        messages.success(request, "Отчёт бекитилди!")
    elif action == 'reject':
        completion.leader_approved    = False
        completion.status             = 'rejected'
        completion.leader_feedback    = feedback
        completion.leader_approved_at = timezone.now()
        completion.save()
        messages.warning(request, "Отчёт кайтарылды.")

    return redirect('practitioner_detail', practitioner_id=completion.practitioner_id)


# ─────────────────────────────────────────
# ЛАБОРАНТ: КҮНҮМДҮК ИШ ПЛАНДАР
# ─────────────────────────────────────────
@_lab_or_leader_required
def daily_plans_list(request, labassistant):
    course_filter = request.GET.get('course')
    plans = DailyPlan.objects.all().order_by('course', 'day_number')
    if course_filter:
        plans = plans.filter(course=course_filter)

    return render(request, 'accounts/daily_plans_list.html', {
        'labassistant':  labassistant,
        'plans':         plans,
        'course_filter': course_filter,
    })


@_lab_or_leader_required
def daily_plan_create(request, labassistant):
    if request.method == 'POST':
        course      = request.POST.get('course')
        day_number  = request.POST.get('day_number')
        title       = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        attachment  = request.FILES.get('attachment')

        if not all([course, day_number, title, description]):
            messages.error(request, "Бардык талааларды толтуруңуз!")
            return redirect('daily_plan_create')

        # Бул курстун бул күнү мурун бар болсо — ката
        if DailyPlan.objects.filter(course=course, day_number=day_number).exists():
            messages.error(
                request,
                f"{course}-курстун {day_number}-күнүнүн иш планы мурунтан бар!"
            )
            return redirect('daily_plan_create')

        DailyPlan.objects.create(
            course=course,
            day_number=day_number,
            title=title,
            description=description,
            attachment=attachment,
            created_by=labassistant,
        )
        messages.success(request, "Иш план түзүлдү!")
        return redirect('daily_plans_list')

    return render(request, 'accounts/daily_plan_form.html', {
        'labassistant': labassistant, 'editing': False
    })


@_lab_or_leader_required
def daily_plan_update(request, labassistant, plan_id):
    plan = get_object_or_404(DailyPlan, id=plan_id)

    if request.method == 'POST':
        plan.title       = request.POST.get('title', '').strip()
        plan.description = request.POST.get('description', '').strip()
        attachment = request.FILES.get('attachment')
        if attachment:
            plan.attachment = attachment
        if request.POST.get('attachment-clear') and plan.attachment:
            plan.attachment.delete(save=False)
            plan.attachment = None
        plan.save()
        messages.success(request, "Иш план жаңыртылды!")
        return redirect('daily_plans_list')

    return render(request, 'accounts/daily_plan_form.html', {
        'labassistant': labassistant, 'plan': plan, 'editing': True
    })

