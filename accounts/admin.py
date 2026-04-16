from django.contrib import admin
from django.contrib import messages
from .models import Room, LabAssistant, Attendance, Project, Comment, Report, Computer, InventoryLock


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(LabAssistant)
class LabAssistantAdmin(admin.ModelAdmin):
    # FIX ката #8: 'role' кошулду
    list_display = ('full_name', 'role', 'user', 'phone')
    list_filter = ('role',)
    filter_horizontal = ('rooms',)
    search_fields = ('full_name',)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('labassistant', 'date', 'arrival_time', 'late')
    list_filter = ('date', 'late', 'labassistant')
    search_fields = ('labassistant__full_name',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'labassistant', 'status', 'start_date', 'end_date', 'is_public')
    list_filter = ('status', 'is_public', 'start_date')
    search_fields = ('title', 'labassistant__full_name')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'project', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('text', 'author__full_name')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'labassistant', 'created_at')
    list_filter = ('created_at', 'project')
    search_fields = ('title', 'description', 'comment', 'project__title')
    readonly_fields = ('created_at',)
    fieldsets = (
        # FIX КРИТИКАЛЫК #7: орус тили → кыргызча
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


@admin.register(Computer)
class ComputerAdmin(admin.ModelAdmin):
    list_display = (
        'room', 'monitor_inv', 'monitor', 'block_inv',
        'motherboard', 'processor', 'ram',
        'video_card', 'hdd_size', 'hdd_type', 'power_supply',
    )
    list_filter = ('room', 'hdd_type')
    search_fields = ('monitor_inv', 'block_inv', 'processor', 'motherboard', 'room__name')
    ordering = ('room__name',)
    readonly_fields = []
    fieldsets = (
        ('Негизги маалыматтар', {'fields': ('room',)}),
        ('Монитор',             {'fields': ('monitor_inv', 'monitor')}),
        ('Системалык блок',     {'fields': ('block_inv', 'power_supply')}),
        ('Техникалык маалыматтар', {
            'fields': ('motherboard', 'processor', 'ram', 'video_card', 'hdd_size', 'hdd_type')
        }),
    )


@admin.register(InventoryLock)
class InventoryLockAdmin(admin.ModelAdmin):
    list_display = ('is_locked', 'locked_by', 'changed_at')
    readonly_fields = ('changed_at',)
    actions = ('lock_inventory', 'unlock_inventory')

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