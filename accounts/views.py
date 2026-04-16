import base64
import csv
import os
import logging
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

from .models import Comment, LabAssistant, Project, Attendance, Computer, Room, Report, InventoryLock
from .forms import AttendanceForm, ProjectForm, ComputerForm, ReportForm, LabAssistantProfileForm

logger = logging.getLogger(__name__)


# =====================
# LOGIN / LOGOUT
# =====================
def login_view(request):
    if request.user.is_authenticated:
        try:
            la = LabAssistant.objects.get(user=request.user)
            return redirect('leader_dashboard' if la.role == 'leader' else 'dashboard')
        except LabAssistant.DoesNotExist:
            return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            try:
                la = LabAssistant.objects.get(user=user)
                if la.role == 'leader':
                    messages.success(request, f"Кош келиңиз, жетекчи {la.full_name}!")
                    return redirect('leader_dashboard')
                else:
                    messages.success(request, f"Кош келиңиз, лаборант {la.full_name}!")
                    return redirect('dashboard')
            except LabAssistant.DoesNotExist:
                LabAssistant.objects.create(
                    user=user,
                    full_name=user.get_full_name() or user.username,
                    role='laborant'
                )
                messages.info(request, "Сиздин профилиңиз автоматтык түрдө түзүлдү")
                return redirect('dashboard')
        else:
            messages.error(request, "Колдонуучу аты же сырсөз туура эмес!")

    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


# =====================
# DASHBOARD
# =====================
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


# =====================
# КЕЛҮҮ ЖУРНАЛЫ
# =====================
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
            arrival_time  = request.POST.get('arrival_time', '').strip()
            comment       = request.POST.get('comment', '').strip()
            photo_base64  = request.POST.get('photo_base64', '').strip()

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
        'labassistant':      labassistant,
        'today_attendance':  today_attendance,
        'attendance_history': attendance_history,
    })


# =====================
# ИШ ПЛАНДАР (ДОЛБООРЛОР)
# =====================
@login_required
def projects_list_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)

    if labassistant.role == 'leader':
        projects = Project.objects.all()\
            .select_related('labassistant')\
            .prefetch_related('comments__author')\
            .order_by('-start_date')
    else:
        projects = Project.objects.filter(
            Q(labassistant=labassistant) | Q(is_public=True)
        ).select_related('labassistant')\
         .prefetch_related('comments__author')\
         .order_by('-start_date')

    context = {
        'labassistant':      labassistant,
        'projects':          projects,
        'total_projects':    projects.count(),
        'active_projects':   projects.filter(status='active').count(),
        'paused_projects':   projects.filter(status='paused').count(),
        'completed_projects': projects.filter(status='completed').count(),
    }
    return render(request, 'accounts/projects_list.html', context)


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
        # FIX ката #3: end_date'ти авто өчүрбөйбүз
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


# =====================
# ОТЧЕТТОР
# =====================
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
        'form':         form,
        'page_title':   'Жаңы отчет түзүү',
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
        'form':         form,
        'report':       report,
        'page_title':   'Отчетту өзгөртүү',
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
    response = FileResponse(open(report.file.path, 'rb'), as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(report.file.path)}"'
    return response


@login_required
def export_reports_csv(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    reports = Report.objects.filter(labassistant=labassistant)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="reports_{datetime.now().strftime("%Y%m%d")}.csv"'
    writer = csv.writer(response)
    writer.writerow(['№', 'Отчеттун аты', 'Иш план', 'Түзүлгөн күнү', 'Кошумча маалымат'])
    for i, report in enumerate(reports, 1):
        writer.writerow([
            i,
            report.title,
            report.project.title,
            report.created_at.strftime('%d.%m.%Y %H:%M'),
            report.comment[:100] if report.comment else ''
        ])
    return response


# =====================
# КОМПЬЮТЕРЛЕР
# =====================
@login_required
def computers_list_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)

    # FIX КРИТИКАЛЫК #2: locked_until жок — changed_at колдонулат
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

    if labassistant.role == 'laborant':
        rooms = labassistant.rooms.all().order_by('name')
    else:
        rooms = Room.objects.all().order_by('name')

    selected_room_id = request.GET.get('room')

    # FIX КРИТИКАЛЫК #1: rooms_with_computers берилет
    rooms_with_computers = []
    for room in rooms:
        if selected_room_id and str(room.id) != selected_room_id:
            continue
        rooms_with_computers.append({
            'room':      room,
            'computers': room.computers.all(),
        })

    return render(request, 'accounts/computers_list.html', {
        'labassistant':          labassistant,
        'rooms':                 rooms,
        'rooms_with_computers':  rooms_with_computers,
        'selected_room_id':      selected_room_id,
        'inventory_status':      inventory_status,
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

    # FIX ката #2: "өзгөртүүгА" → "өзгөртүүгө"
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


# =====================
# ПРОФИЛЬ
# =====================
@login_required
def profile_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
 
    if request.method == 'POST':
        form = LabAssistantProfileForm(
            request.POST,
            request.FILES,   # FIX: файлдар үчүн request.FILES берилет
            instance=labassistant
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Профиль ийгиликтүү жаңыртылды!")
            return redirect('profile')
        else:
            messages.error(request, "Ката кетти. Маалыматты текшериңиз.")
    else:
        form = LabAssistantProfileForm(instance=labassistant)
 
    return render(request, 'accounts/profile.html', {
        'form':         form,
        'labassistant': labassistant,
    })

@login_required
def leader_profile_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)

    if labassistant.role != 'leader':
        messages.error(request, "Уруксат жок!")
        return redirect('dashboard')

    if request.method == 'POST':
        form = LabAssistantProfileForm(
            request.POST,
            request.FILES,
            instance=labassistant
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Профиль сакталды!")
            return redirect('leader_profile')
        else:
            messages.error(request, "Форманы туура толтуруңуз!")
    else:
        form = LabAssistantProfileForm(instance=labassistant)

    return render(request, 'accounts/leader_profile.html', {
        'form': form,
        'labassistant': labassistant
    })


# =====================
# ЖЕТЕКЧИНИН ПАНЕЛИ
# =====================
@login_required
def leader_dashboard_view(request):
    labassistant = get_object_or_404(LabAssistant, user=request.user)
    if labassistant.role != 'leader':
        messages.error(request, "Бул баракчага кирүүгө уруксат жок!")
        return redirect('dashboard')

    laborants = LabAssistant.objects.filter(role='laborant')
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
        projects_data   = Project.objects.all()
        reports_data    = Report.objects.all()

    computers_by_laborant = {}
    target_laborants = [selected_laborant] if selected_laborant else laborants
    for lab in target_laborants:
        if lab.rooms.exists():
            computers_by_laborant[lab] = {}
            for room in lab.rooms.all():
                qs = Computer.objects.filter(room=room)
                if qs.exists():
                    computers_by_laborant[lab][room] = qs

    return render(request, 'accounts/leader_dashboard.html', {
        'labassistant':          labassistant,
        'laborants':             laborants,
        'selected_laborant':     selected_laborant,
        'selected_laborant_id':  selected_laborant_id,
        'total_laborants':       laborants.count(),
        # FIX КРИТИКАЛЫК #4: 'aktiv' → 'active'
        'active_projects':       Project.objects.filter(status='active').count(),
        'today_attendance':      Attendance.objects.filter(date=date.today()).count(),
        'bad_computers':         Computer.objects.count(),
        'late_arrivals':         late_arrivals,
        'attendance_data':       attendance_data.order_by('-date'),
        'projects_data':         projects_data.order_by('-start_date'),
        'reports_data':          reports_data.order_by('-created_at'),
        # FIX КРИТИКАЛЫК #3: 'number' → 'block_inv'
        'computers_data':        Computer.objects.all().order_by('room__name', 'block_inv'),
        'computers_by_laborant': computers_by_laborant,
    })