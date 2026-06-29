from django.db import models
from django.contrib.auth.models import User
from datetime import date as today_date, timedelta
from datetime import date
from .utils import (
    report_upload_path,
    daily_plan_upload_path,
    project_upload_path,
    plan_completion_upload_path,
    resume_upload_path,
    profile_image_upload_path,
    practitioner_photo_upload_path,
)

# =====================
# Кабинеттер
# =====================
class Room(models.Model):
    name = models.CharField("Кабинет", max_length=100)
    description = models.TextField("Сүрөттөмө", blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Кабинет"
        verbose_name_plural = "Кабинеттер"
        ordering = ['name']


# =====================
# Лаборант
# =====================
class LabAssistant(models.Model):
    USER_ROLES = (
        ('laborant', 'Лаборант'),
        ('leader',   'Жетекчи'),
    )

    user         = models.OneToOneField(User, on_delete=models.CASCADE)
    role         = models.CharField("Ролу", max_length=10, choices=USER_ROLES, default='laborant')
    full_name    = models.CharField("ФИО", max_length=100)
    phone        = models.CharField("Телефон", max_length=20, blank=True, null=True)
    notes        = models.TextField("Эскертүү", blank=True, null=True)
    rooms        = models.ManyToManyField(Room, verbose_name="Кабинеттер", blank=True)
    profile_image = models.ImageField(upload_to=profile_image_upload_path, blank=True, null=True)
    resume       = models.FileField("Резюме", upload_to=resume_upload_path, blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

    class Meta:
        verbose_name = "Лаборант"
        verbose_name_plural = "Лаборанттар"


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
    date         = models.DateField("Дата", default=today_date.today)
    arrival_time = models.TimeField("Келүү убактысы")
    photo        = models.ImageField(
        "Сүрөт", upload_to='attendance_photos/%Y/%m/',
        null=True, blank=True
    )
    comment = models.TextField("Кечигүүнүн себеби", blank=True)
    late    = models.BooleanField("Кечикти", default=False)

    class Meta:
        unique_together  = [('labassistant', 'date')]
        verbose_name     = "Келүү жазуусу"
        verbose_name_plural = "Келүү журналы"
        ordering         = ['-date']

    def __str__(self):
        return f"{self.labassistant.full_name} — {self.date} ({self.arrival_time})"


# =====================
# Иш пландар (Project)
# =====================
class Project(models.Model):
    STATUS_CHOICES = (
        ('active',    'Активдүү'),
        ('paused',    'Паузада'),
        ('completed', 'Бүткөн'),
    )

    labassistant = models.ForeignKey(
        LabAssistant, on_delete=models.CASCADE,
        related_name='projects', verbose_name="Лаборант"
    )
    title       = models.CharField("Аталышы", max_length=255)
    description = models.TextField("Сүрөттөмө")
    start_date  = models.DateField("Башталган күнү")
    end_date    = models.DateField("Аяктоо күнү", null=True, blank=True)
    status      = models.CharField(
        "Статус", max_length=20,
        choices=STATUS_CHOICES, default='active'
    )
    attachment = models.FileField("Тиркеме", upload_to=project_upload_path, null=True, blank=True)

    is_public = models.BooleanField("Жарыяланган", default=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.end_date:
            self.end_date = today_date.today()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name        = "Иш план"
        verbose_name_plural = "Иш пландар"
        ordering            = ['-start_date']


class Comment(models.Model):
    project    = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='comments', verbose_name="Иш план")
    author     = models.ForeignKey(LabAssistant, on_delete=models.CASCADE, related_name='comments', verbose_name="Автор")
    text       = models.TextField("Комментарий")
    created_at = models.DateTimeField("Жазылган убакыт", auto_now_add=True)

    def __str__(self):
        return f"{self.author.full_name} — {self.project.title}"

    class Meta:
        verbose_name        = "Комментарий"
        verbose_name_plural = "Комментарийлер"
        ordering            = ['created_at']


# =====================
# Отчеттор (Report)
# =====================
class Report(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name='reports', verbose_name="Иш план",
        limit_choices_to={'status': 'completed'}
    )
    labassistant = models.ForeignKey(
        LabAssistant, on_delete=models.CASCADE,
        related_name='reports', verbose_name="Лаборант"
    )
    title       = models.CharField("Отчеттун аты", max_length=255)
    description = models.TextField("Баяндама", blank=True)
    file = models.FileField("Файл", upload_to=report_upload_path, blank=True, null=True)
    comment     = models.TextField("Кошумча маалымат", blank=True)
    created_at  = models.DateTimeField("Түзүлгөн убакыт", auto_now_add=True)

    def __str__(self):
        return f"{self.title} — {self.project.title}"

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = "Отчет"
        verbose_name_plural = "Отчеттор"


# =====================
# Компьютер
# =====================
class Computer(models.Model):
    HDD_TYPE_CHOICES = [
        ('HDD',     'HDD'),
        ('SSD',     'SSD'),
        ('HDD+SSD', 'HDD + SSD'),
    ]

    room        = models.ForeignKey('Room', on_delete=models.CASCADE, related_name='computers', verbose_name="Кабинет")
    monitor_inv = models.CharField("Монитор инв. №", max_length=50, help_text="Монитордун инвентардык номери")
    monitor     = models.CharField("Монитор", max_length=100, help_text="Монитордун маркасы же модели (мис.: Acer V206HQL)")
    block_inv   = models.CharField("Системалык блок инв. №", max_length=50, help_text="Системалык блоктун инвентардык номери")
    motherboard = models.CharField("Эне плата", max_length=100, help_text="Эне платанын аты же модели (мис.: ASUS H110M-K)")
    processor   = models.CharField("Процессор", max_length=100, help_text="Процессордун аты же модели (мис.: Intel Core i5-9400F)")
    ram         = models.CharField("Оперативдүү эс (RAM)", max_length=100, help_text="RAM өлчөмү жана ылдамдыгы (мис.: 8 ГБ DDR4)")
    video_card  = models.CharField("Видеокарта", max_length=100, help_text="Видеокартанын аты же модели", blank=True)
    hdd_size    = models.CharField("Катуу дисктин өлчөмү", max_length=50, help_text="Дисктин өлчөмү (мис.: 500 ГБ)")
    hdd_type    = models.CharField("Катуу дисктин түрү", max_length=10, choices=HDD_TYPE_CHOICES, default='HDD')
    power_supply = models.CharField("Системалык блок", max_length=100, help_text="Системалык блоктун маркасы же кубаты (мис.: 500W)")

    def __str__(self):
        return f"Кабинет {self.room.name} — инв. {self.block_inv}"

    class Meta:
        ordering            = ['room__name', 'block_inv']
        verbose_name        = "Компьютер"
        verbose_name_plural = "Компьютерлер"


# =====================
# Инвентаризация блогу
# =====================
class InventoryLock(models.Model):
    is_locked  = models.BooleanField("Кирүү жабык", default=True)
    locked_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Аткарган колдонуучу")
    changed_at = models.DateTimeField("Өзгөртүлгөн убакыт", auto_now=True)

    def __str__(self):
        return "Жабык" if self.is_locked else "Ачык"

    class Meta:
        verbose_name        = "Инвентаризациянын блоктоосу"
        verbose_name_plural = "Инвентаризациянын блоктоолору"


# ============================================================
# ПРАКТИКАНТ СИСТЕМАСЫ
# ============================================================

def _default_practice_end(start, duration_days):
    """
    Практиканын аяктоо күнүн эсептейт:
    жекшемби күндөрдү эске АЛБАЙ, иш күндөрдү гана санайт.
    """
    current   = start
    work_days = 0
    while work_days < duration_days:
        current += timedelta(days=1)
        if current.weekday() != 6:   # 6 = жекшемби
            work_days += 1
    return current


# =====================
# Практикант
# =====================
class Practitioner(models.Model):
    COURSE_CHOICES = (
        (1, '1-курс'),
        (2, '2-курс'),
        (3, '3-курс'),
        (4, '4-курс'),
    )
    # Демейки мөөнөттөр (иш күндөр, жекшемби эске алынбайт)
    DURATION_BY_COURSE = {
        1: 12,
        2: 36,
        3: 48,   # 3-курстун варианттары: 48 же 36 — каттоодо тандалат
        4: 36,
    }

    user          = models.OneToOneField(
        User, on_delete=models.CASCADE,
        verbose_name="Колдонуучу"
    )
    full_name     = models.CharField("ФИО", max_length=150)
    phone         = models.CharField("Телефон", max_length=20, blank=True, null=True)
    photo         = models.ImageField(upload_to=practitioner_photo_upload_path, blank=True, null=True)
    course        = models.IntegerField("Курс", choices=COURSE_CHOICES)
    group         = models.CharField("Топ", max_length=50, help_text="мис.: КИ-21")
    university    = models.CharField("Окуу жайы", max_length=200, blank=True)

    room          = models.ForeignKey(
        Room, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='practitioners',
        verbose_name="Кабинет"
    )
    supervisor    = models.ForeignKey(
        LabAssistant, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='supervised_practitioners',
        verbose_name="Жооптуу лаборант"
    )

    practice_start = models.DateField("Практика башталышы")
    practice_end   = models.DateField(
        "Практика аяктоосу",
        blank=True, null=True,
        help_text="Бош калтырсаңыз автоматтык эсептелет"
    )
    # Иш күндөрдүн саны (жекшемби эске алынбайт)
    duration_days  = models.PositiveIntegerField(
        "Мөөнөт (иш күн)",
        help_text="1-курс: 12, 2-курс: 36, 3-курс: 48 же 36, 4-курс: 36"
    )

    def save(self, *args, **kwargs):
        # duration_days толтурулбаса — курска жараша демейки маани
        if not self.duration_days:
            self.duration_days = self.DURATION_BY_COURSE.get(self.course, 12)
        # practice_end автоматтык эсептелет
        if self.practice_start and not self.practice_end:
            self.practice_end = _default_practice_end(
                self.practice_start, self.duration_days
            )
        super().save(*args, **kwargs)
    @property
    def current_work_day(self):
        today = date.today()

    # дата жок болсо
        if not self.practice_start or not self.practice_end:
            return 0

    # практика баштала элек болсо
        if today < self.practice_start:
            return 0

    # практика бүтсө
        if today > self.practice_end:
            return self.duration_days
        return (today - self.practice_start).days + 1

    @property
    def is_active_practice(self):
        today = date.today()

        if not self.practice_start:
            return False

        if self.practice_end:
            return self.practice_start <= today <= self.practice_end

        return self.practice_start <= today

# =====================
# Күнүмдүк иш план
# =====================
class DailyPlan(models.Model):
    COURSE_CHOICES = (
        (1, '1-курс'),
        (2, '2-курс'),
        (3, '3-курс'),
        (4, '4-курс'),
    )

    course      = models.IntegerField("Курс", choices=COURSE_CHOICES)
    day_number  = models.PositiveIntegerField(
        "Күн номери",
        help_text="Практиканын нечинчи иш күнүнүн планы (1-ден башталат)"
    )
    title       = models.CharField("Иш пландын аты", max_length=255)
    description = models.TextField("Мазмуну")
    attachment  = models.FileField(
        "Файл (нускамалар, материалдар)",
        upload_to=daily_plan_upload_path,
        blank=True, null=True
    )
    created_by  = models.ForeignKey(
        LabAssistant, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_plans',
        verbose_name="Түзгөн"
    )
    created_at  = models.DateTimeField("Түзүлгөн убакыт", auto_now_add=True)
    updated_at  = models.DateTimeField("Жаңыртылган убакыт", auto_now=True)

    def __str__(self):
        return f"{self.get_course_display()} — {self.day_number}-күн: {self.title}"

    class Meta:
        # Бир курстун бир күнүндө бир гана план болсун
        unique_together     = [('course', 'day_number')]
        verbose_name        = "Күнүмдүк иш план"
        verbose_name_plural = "Күнүмдүк иш пландар"
        ordering            = ['course', 'day_number']


# =====================
# Практиканттын келүүсү
# =====================
class PractitionerAttendance(models.Model):
    practitioner = models.ForeignKey(
        Practitioner, on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name="Практикант"
    )
    date         = models.DateField("Дата", default=today_date.today)
    arrival_time = models.TimeField("Келүү убактысы")
    photo        = models.ImageField(
        "Сүрөт", upload_to='pract_attendance/%Y/%m/',
        null=True, blank=True
    )
    late    = models.BooleanField("Кечикти", default=False)
    comment = models.TextField("Кечигүүнүн себеби", blank=True)

    def __str__(self):
        return f"{self.practitioner.full_name} — {self.date} ({self.arrival_time})"

    class Meta:
        unique_together     = [('practitioner', 'date')]
        verbose_name        = "Практиканттын келүүсү"
        verbose_name_plural = "Практиканттардын келүүлөрү"
        ordering            = ['-date']


# =====================
# Иш план аткаруу отчёту
# =====================
class PlanCompletion(models.Model):
    STATUS_CHOICES = (
        ('submitted',    'Жиберилди'),
        ('lab_reviewed', 'Лаборант текшерди'),
        ('approved',     'Бекитилди'),
        ('rejected',     'Кайтарылды'),
    )

    practitioner = models.ForeignKey(
        Practitioner, on_delete=models.CASCADE,
        related_name='completions',
        verbose_name="Практикант"
    )
    plan = models.ForeignKey(
        DailyPlan, on_delete=models.CASCADE,
        related_name='completions',
        verbose_name="Иш план"
    )

    # Студент толтурат
    report_text = models.TextField(
        "Отчёт тексти",
        help_text="Бүгүн эмне аткарылды?"
    )
    attachment  = models.FileField(
        "Файл (скриншот, документ)",
        upload_to=plan_completion_upload_path,
        blank=True, null=True
    )
    submitted_at = models.DateTimeField("Жиберилген убакыт", auto_now_add=True)

    # Лаборант толтурат
    status      = models.CharField(
        "Статус", max_length=20,
        choices=STATUS_CHOICES, default='submitted'
    )
    lab_checked = models.ForeignKey(
        LabAssistant, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='checked_completions',
        verbose_name="Текшерген лаборант"
    )
    lab_feedback = models.TextField("Лаборанттын комментарийи", blank=True)
    lab_checked_at = models.DateTimeField(
        "Лаборант текшерген убакыт",
        null=True, blank=True
    )

    # Жетекчи толтурат
    leader_approved    = models.BooleanField("Жетекчи бекитти", default=False)
    leader_feedback    = models.TextField("Жетекчинин комментарийи", blank=True)
    leader_approved_at = models.DateTimeField(
        "Жетекчи бекиткен убакыт",
        null=True, blank=True
    )

    def __str__(self):
        return f"{self.practitioner.full_name} — {self.plan}"

    class Meta:
        # Бир практикант бир планды бир жолу гана жиберет
        unique_together     = [('practitioner', 'plan')]
        verbose_name        = "Иш план отчёту"
        verbose_name_plural = "Иш план отчёттору"
        ordering            = ['-submitted_at']
