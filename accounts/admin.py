from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    Room, LabAssistant, Attendance,
    Project, Comment, Report,
    Computer, InventoryLock,
    Practitioner, DailyPlan,
    PractitionerAttendance, PlanCompletion,
)


# =====================
# Кабинеттер
# =====================
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display  = ('name', 'description')
    search_fields = ('name',)


# =====================
# Лаборанттар
# =====================
@admin.register(LabAssistant)
class LabAssistantAdmin(admin.ModelAdmin):
    list_display     = ('full_name', 'role', 'user', 'phone')
    list_filter      = ('role',)
    filter_horizontal = ('rooms',)
    search_fields    = ('full_name',)


# =====================
# Келүү журналы
# =====================
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display  = ('labassistant', 'date', 'arrival_time', 'late')
    list_filter   = ('date', 'late', 'labassistant')
    search_fields = ('labassistant__full_name',)


# =====================
# Иш пландар
# =====================
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display  = ('title', 'labassistant', 'status', 'start_date', 'end_date', 'is_public')
    list_filter   = ('status', 'is_public', 'start_date')
    search_fields = ('title', 'labassistant__full_name')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display  = ('author', 'project', 'created_at')
    list_filter   = ('created_at',)
    search_fields = ('text', 'author__full_name')


# =====================
# Отчеттор
# =====================
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display    = ('title', 'project', 'labassistant', 'created_at')
    list_filter     = ('created_at', 'project')
    search_fields   = ('title', 'description', 'comment', 'project__title')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Негизги маалыматтар', {
            'fields': ('title', 'project', 'labassistant')
        }),
        ('Мазмуну', {
            'fields': ('description', 'comment', 'file')
        }),
        ('Кошумча', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


# =====================
# Компьютерлер
# =====================
@admin.register(Computer)
class ComputerAdmin(admin.ModelAdmin):
    list_display = (
        'room', 'monitor_inv', 'monitor', 'block_inv',
        'motherboard', 'processor', 'ram',
        'video_card', 'hdd_size', 'hdd_type', 'power_supply',
    )
    list_filter   = ('room', 'hdd_type')
    search_fields = ('monitor_inv', 'block_inv', 'processor', 'motherboard', 'room__name')
    ordering      = ('room__name',)
    fieldsets = (
        ('Негизги маалыматтар',    {'fields': ('room',)}),
        ('Монитор',                {'fields': ('monitor_inv', 'monitor')}),
        ('Системалык блок',        {'fields': ('block_inv', 'power_supply')}),
        ('Техникалык маалыматтар', {
            'fields': ('motherboard', 'processor', 'ram', 'video_card', 'hdd_size', 'hdd_type')
        }),
    )


# =====================
# Инвентаризация
# =====================
@admin.register(InventoryLock)
class InventoryLockAdmin(admin.ModelAdmin):
    list_display    = ('is_locked', 'locked_by', 'changed_at')
    readonly_fields = ('changed_at',)
    actions         = ('lock_inventory', 'unlock_inventory')

    def has_add_permission(self, request):
        return not InventoryLock.objects.exists()

    def lock_inventory(self, request, queryset):
        for obj in queryset:
            obj.is_locked = True
            obj.locked_by = request.user
            obj.save()
        messages.success(request, "Инвентаризация жабылды. Лаборанттар компьютер кошуп же өзгөртө албайт.")

    def unlock_inventory(self, request, queryset):
        for obj in queryset:
            obj.is_locked = False
            obj.locked_by = request.user
            obj.save()
        messages.success(request, "Инвентаризация ачылды. Лаборанттар компьютер кошуп же өзгөртө алат.")

    lock_inventory.short_description   = "Кирүүнү жабуу"
    unlock_inventory.short_description = "Кирүүнү ачуу"


# ============================================================
# ПРАКТИКАНТ СИСТЕМАСЫ
# ============================================================

class PlanCompletionInline(admin.TabularInline):
    """Практиканттын карточкасында отчёттору"""
    model       = PlanCompletion
    extra       = 0
    readonly_fields = ('plan', 'report_text', 'submitted_at', 'status')
    fields      = ('plan', 'report_text', 'status', 'submitted_at')
    can_delete  = False
    show_change_link = True


class PractitionerAttendanceInline(admin.TabularInline):
    """Практиканттын карточкасында келүүлөрү"""
    model       = PractitionerAttendance
    extra       = 0
    readonly_fields = ('date', 'arrival_time', 'late', 'comment')
    fields      = ('date', 'arrival_time', 'late', 'comment')
    can_delete  = False


# =====================
# Практикант
# =====================
@admin.register(Practitioner)
class PractitionerAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'course', 'group',
        'supervisor', 'room',
        'practice_start', 'practice_end',
        'duration_days', 'is_active_display',
    )
    list_filter   = ('course', 'room', 'supervisor')
    search_fields = ('full_name', 'group', 'university')
    readonly_fields = ('practice_end', 'current_work_day_display')
    inlines     = [PractitionerAttendanceInline, PlanCompletionInline]

    fieldsets = (
        ('Жеке маалыматтар', {
            'fields': ('user', 'full_name', 'phone', 'photo')
        }),
        ('Окуу маалыматтары', {
            'fields': ('course', 'group', 'university')
        }),
        ('Практика', {
            'fields': (
                'room', 'supervisor',
                'practice_start', 'duration_days',
                'practice_end',           # readonly — авто эсептелет
                'current_work_day_display',
            )
        }),
    )

    def is_active_display(self, obj):
        return "✅ Активдүү" if obj.is_active_practice else "⏹ Бүттү"
    is_active_display.short_description = "Практика статусу"

    def current_work_day_display(self, obj):
        return f"{obj.current_work_day}-күн (жалпы {obj.duration_days} иш күн)"
    current_work_day_display.short_description = "Учурдагы иш күн"

    # Практикантты каттоодо Django User автоматтык түзүлсүн
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    # Практиканты жабуу: user.is_active = False
    actions = ('deactivate_practitioners', 'activate_practitioners')

    def deactivate_practitioners(self, request, queryset):
        for pract in queryset:
            pract.user.is_active = False
            pract.user.save()
        messages.success(
            request,
            f"{queryset.count()} практиканттын кирүүсү жабылды."
        )
    deactivate_practitioners.short_description = "Кирүүнү жабуу (практика бүттү)"

    def activate_practitioners(self, request, queryset):
        for pract in queryset:
            pract.user.is_active = True
            pract.user.save()
        messages.success(
            request,
            f"{queryset.count()} практиканттын кирүүсү ачылды."
        )
    activate_practitioners.short_description = "Кирүүнү ачуу (практика башталды)"


# =====================
# Күнүмдүк иш план
# =====================
@admin.register(DailyPlan)
class DailyPlanAdmin(admin.ModelAdmin):
    list_display  = ('course', 'day_number', 'title', 'created_by', 'updated_at')
    list_filter   = ('course',)
    search_fields = ('title', 'description')
    ordering      = ('course', 'day_number')
    fieldsets = (
        ('Иш план', {
            'fields': ('course', 'day_number', 'title', 'description', 'attachment')
        }),
        ('Кошумча', {
            'fields': ('created_by',),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            # Adminден сактаганда түзгөн адамды белгилейт
            try:
                obj.created_by = request.user.labassistant
            except Exception:
                pass
        super().save_model(request, obj, form, change)


# =====================
# Практиканттын келүүсү
# =====================
@admin.register(PractitionerAttendance)
class PractitionerAttendanceAdmin(admin.ModelAdmin):
    list_display  = ('practitioner', 'date', 'arrival_time', 'late')
    list_filter   = ('date', 'late', 'practitioner__course')
    search_fields = ('practitioner__full_name',)
    readonly_fields = ('date',)


# =====================
# Иш план отчёту
# =====================
@admin.register(PlanCompletion)
class PlanCompletionAdmin(admin.ModelAdmin):
    list_display  = (
        'practitioner', 'plan', 'status',
        'lab_checked', 'leader_approved', 'submitted_at'
    )
    list_filter   = ('status', 'leader_approved', 'plan__course')
    search_fields = ('practitioner__full_name', 'plan__title')
    readonly_fields = ('submitted_at', 'lab_checked_at', 'leader_approved_at')

    fieldsets = (
        ('Отчёт', {
            'fields': ('practitioner', 'plan', 'report_text', 'attachment', 'submitted_at')
        }),
        ('Лаборанттын текшерүүсү', {
            'fields': ('status', 'lab_checked', 'lab_feedback', 'lab_checked_at')
        }),
        ('Жетекчинин бекитүүсү', {
            'fields': ('leader_approved', 'leader_feedback', 'leader_approved_at')
        }),
    )

    # Жетекчи adminден беките алат
    actions = ('approve_by_leader', 'reject_by_leader')

    def approve_by_leader(self, request, queryset):
        queryset.filter(status='lab_reviewed').update(
            leader_approved=True,
            status='approved',
            leader_approved_at=timezone.now(),
        )
        messages.success(request, "Тандалган отчёттор бекитилди.")
    approve_by_leader.short_description = "Жетекчи бекитет ✓"

    def reject_by_leader(self, request, queryset):
        queryset.update(
            leader_approved=False,
            status='rejected',
        )
        messages.success(request, "Тандалган отчёттор кайтарылды.")
    reject_by_leader.short_description = "Жетекчи кайтарат ✗"
