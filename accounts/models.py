from django.db import models
from django.contrib.auth.models import User
from datetime import date as today_date
# =====================
# Кабинеттер
# =====================
class Room(models.Model):
    name = models.CharField("Кабинет", max_length=100)
    description = models.TextField("Сүрөттөмө", blank=True)

    def __str__(self):
        return self.name

# =====================
# Лаборант
# =====================
class LabAssistant(models.Model):
    USER_ROLES = (
        ('laborant', 'Лаборант'),
        ('leader', 'Жетекчи'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField("Ролу", max_length=10, choices=USER_ROLES, default='laborant')
    full_name = models.CharField("ФИО", max_length=100)
    phone = models.CharField("Телефон", max_length=20, blank=True, null=True)
    notes = models.TextField("Эскертүү", blank=True, null=True)
    rooms = models.ManyToManyField(Room, verbose_name="Кабинеттер", blank=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    resume = models.FileField("Резюме", upload_to='resumes/', blank=True, null=True)
    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

# =====================
# Келүү журналы (Attendance)
# =====================
class Attendance(models.Model):
    labassistant = models.ForeignKey(
        'LabAssistant',  
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Лаборант"
    )
    date = models.DateField(
        "Дата",
        default=today_date.today
    )
    arrival_time = models.TimeField("Келүү убактысы")
    photo = models.ImageField(
        "Сүрөт",
        upload_to='attendance_photos/%Y/%m/',
        null=True,
        blank=True
    )
    comment = models.TextField(
        "Кечигүүнүн себеби",
        blank=True
    )
    late = models.BooleanField(
        "Кечикти",
        default=False
    )

    class Meta:
        unique_together = [('labassistant', 'date')]
        verbose_name = "Келүү жазуусу"
        verbose_name_plural = "Келүү журналы"
        ordering = ['-date']

    def __str__(self):
        return f"{self.labassistant.full_name} — {self.date} ({self.arrival_time})"


# =====================
# Долбоорлор (Project)
# =====================
class Project(models.Model):
    STATUS_CHOICES = (
        ('active', 'Активдүү'),
        ('paused', 'Паузада'),
        ('completed', 'Бүткөн'),
    )
    labassistant = models.ForeignKey(LabAssistant, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    attachment = models.FileField(upload_to='projects/', null=True, blank=True)
    is_public = models.BooleanField(default=False)
    def __str__(self):
        return self.title
    
class Comment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(LabAssistant, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

# =====================
# Отчёттор (Report)
# =====================
class Report(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name="Иш план",
        limit_choices_to={'status': 'completed'}  
    )
    
    labassistant = models.ForeignKey(
        LabAssistant,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name="Лаборант"
    )
    
    title = models.CharField("Отчеттун аты", max_length=255)
    description = models.TextField("Баяндама", blank=True)
    file = models.FileField("Файл", upload_to='reports/', blank=True, null=True)
    comment = models.TextField("Комментарий", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.project.title}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Отчёт"
        verbose_name_plural = "Отчёттор"

# =====================
# Компьютер / Инвентаризация
# =====================
class Computer(models.Model):
    HDD_TYPE_CHOICES = [
        ('HDD', 'HDD'),
        ('SSD', 'SSD'),
        ('HDD+SSD', 'HDD + SSD'),
    ]

    room = models.ForeignKey(
        'Room',
        on_delete=models.CASCADE,
        related_name='computers',
        verbose_name="Кабинет"
    )
    # number алынып салынды — таблицада forloop.counter колдонулат

    # --- Монитор ---
    monitor_inv = models.CharField(
        "Монитор инв. №",
        max_length=50,
        help_text="Монитордун инвентардык номери"
    )
    monitor = models.CharField(
        "Монитор",
        max_length=100,
        help_text="Монитордун маркасы же модели (мис.: Acer V206HQL)"
    )

    # --- Системалык блок инв. № ---
    block_inv = models.CharField(
        "Системалык блок инв. №",
        max_length=50,
        help_text="Системалык блоктун инвентардык номери"
    )

    # --- Комплектующие ---
    motherboard = models.CharField(
        "Эне плата",
        max_length=100,
        help_text="Эне платанын аты же модели (мис.: ASUS H110M-K)"
    )
    processor = models.CharField(
        "Процессор",
        max_length=100,
        help_text="Процессордун аты же модели (мис.: Intel Core i5-9400F)"
    )
    ram = models.CharField(
        "Оперативдүү эс (RAM)",
        max_length=100,
        help_text="RAM өлчөмү жана ылдамдыгы (мис.: 8 ГБ DDR4)"
    )
    video_card = models.CharField(
        "Видеокарта",
        max_length=100,
        help_text="Видеокартанын аты же модели (мис.: NVIDIA GeForce GTX 1050)",
        blank=True
    )

    # Катуу диск: өлчөмү + түрү өзүнчө
    hdd_size = models.CharField(
        "Катуу дисктин өлчөмү",
        max_length=50,
        help_text="Дисктин өлчөмү (мис.: 500 ГБ)"
    )
    hdd_type = models.CharField(
        "Катуу дисктин түрү",
        max_length=10,
        choices=HDD_TYPE_CHOICES,
        default='HDD'
    )

    power_supply = models.CharField(
        "Системалык блок",
        max_length=100,
        help_text="Системалык блоктун маркасы же кубаты (мис.: 500W)"
    )

    # created_at алынып салынды

    def __str__(self):
        return f"Кабинет {self.room.name} — инв. {self.block_inv}"

    class Meta:
        ordering = ['room__name', 'block_inv']
        verbose_name = "Компьютер"
        verbose_name_plural = "Компьютерлер"


# =====================
# Инвентаризация блогу
# =====================
class InventoryLock(models.Model):
    """Инвентаризацияга кирүүнү башкаруу"""
    is_locked = models.BooleanField(
        default=True,
        verbose_name="Кирүү жабык"
    )
    locked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Аткарган колдонуучу"
    )
    changed_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Өзгөртүлгөн убакыт"
    )

    class Meta:
        verbose_name = "Инвентаризациянын блоктоосу"
        verbose_name_plural = "Инвентаризациянын блоктоолору"

    def __str__(self):
        return "Жабык" if self.is_locked else "Ачык"
    
    
    

    
