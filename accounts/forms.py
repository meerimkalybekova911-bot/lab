from django import forms
from .models import (
    Attendance, Project, Report,
    Computer, Room, InventoryLock, LabAssistant,
    DailyPlan, PlanCompletion,
)
import re


# ─────────────────────────────────────────
# Лаборант келүүсү
# ─────────────────────────────────────────
class AttendanceForm(forms.ModelForm):
    class Meta:
        model  = Attendance
        fields = ['arrival_time', 'photo', 'comment']


# ─────────────────────────────────────────
# Иш план (лаборант)
# ─────────────────────────────────────────
class ProjectForm(forms.ModelForm):
    class Meta:
        model  = Project
        fields = ['title', 'description', 'attachment', 'start_date', 'end_date', 'status']
        widgets = {
            'start_date':  forms.DateInput(attrs={'type': 'date'}),
            'end_date':    forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['end_date'].required   = False
        self.fields['attachment'].required = False


# ─────────────────────────────────────────
# Отчёт (лаборант)
# ─────────────────────────────────────────
class ReportForm(forms.ModelForm):
    class Meta:
        model  = Report
        fields = ['title', 'project', 'description', 'file', 'comment']
        widgets = {
            'title':       forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Отчеттун атын киргизиңиз',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Отчеттун баяндамасы',
            }),
            'comment':     forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Кошумча маалымат',
            }),
            'file':        forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user     = kwargs.pop('user', None)
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)

        if user and hasattr(user, 'labassistant'):
            qs = Project.objects.filter(
                status='completed',
                labassistant=user.labassistant
            )
            if instance:
                qs = qs | Project.objects.filter(id=instance.project_id)
            self.fields['project'].queryset = qs

            self.fields['labassistant'] = forms.ModelChoiceField(
                queryset=LabAssistant.objects.filter(id=user.labassistant.id),
                initial=user.labassistant,
                widget=forms.HiddenInput()
            )


# ─────────────────────────────────────────
# Компьютер
# ─────────────────────────────────────────
class ComputerForm(forms.ModelForm):
    class Meta:
        model  = Computer
        fields = [
            'room',
            'monitor_inv', 'monitor',
            'block_inv',
            'motherboard', 'processor', 'ram', 'video_card',
            'hdd_size', 'hdd_type',
            'power_supply',
        ]
        widgets = {
            'room':         forms.Select(attrs={'class': 'form-control', 'required': 'required'}),
            'monitor_inv':  forms.TextInput(attrs={'class': 'form-control', 'required': 'required', 'placeholder': 'мис.: 32226'}),
            'monitor':      forms.TextInput(attrs={'class': 'form-control', 'required': 'required', 'placeholder': 'мис.: Acer V206HQL'}),
            'block_inv':    forms.TextInput(attrs={'class': 'form-control', 'required': 'required', 'placeholder': 'мис.: 32226'}),
            'motherboard':  forms.TextInput(attrs={'class': 'form-control', 'required': 'required', 'placeholder': 'мис.: ASUS H110M-K'}),
            'processor':    forms.TextInput(attrs={'class': 'form-control', 'required': 'required', 'placeholder': 'мис.: Intel Core i5-9400F'}),
            'ram':          forms.TextInput(attrs={'class': 'form-control', 'required': 'required', 'placeholder': 'мис.: 8 ГБ DDR4'}),
            'video_card':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'мис.: NVIDIA GeForce GTX 1050'}),
            'hdd_size':     forms.TextInput(attrs={'class': 'form-control', 'required': 'required', 'placeholder': 'мис.: 500 ГБ'}),
            'hdd_type':     forms.Select(attrs={'class': 'form-control', 'required': 'required'}),
            'power_supply': forms.TextInput(attrs={'class': 'form-control', 'required': 'required', 'placeholder': 'мис.: 500W'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.inventory_locked = True
        try:
            lock = InventoryLock.objects.first()
            if lock:
                self.inventory_locked = lock.is_locked
        except Exception:
            pass

        if self.instance.pk and self.inventory_locked:
            for field_name in self.fields:
                self.fields[field_name].widget.attrs['readonly'] = True
                self.fields[field_name].widget.attrs['disabled'] = True
                self.fields[field_name].required = False

        if self.user and hasattr(self.user, 'labassistant'):
            role = self.user.labassistant.role
            if role == 'laborant':
                self.fields['room'].queryset = self.user.labassistant.rooms.all()
            elif role == 'leader':
                self.fields['room'].queryset = Room.objects.all().order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk and self.inventory_locked:
            raise forms.ValidationError(
                "Инвентаризация жабык. Компьютерди өзгөртүү мүмкүн эмес!"
            )
        return cleaned_data


# ─────────────────────────────────────────
# Лаборант профили
# ─────────────────────────────────────────
class LabAssistantProfileForm(forms.ModelForm):
    class Meta:
        model  = LabAssistant
        fields = ['full_name', 'phone', 'profile_image', 'resume', 'notes']
        widgets = {
            'full_name':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Аты-жөнүңүздү жазыңыз'}),
            'phone':         forms.TextInput(attrs={'class': 'form-control', 'id': 'phone', 'placeholder': '+996XXXXXXXXX'}),
            'notes':         forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Өзүңүз жөнүндө кыскача жазыңыз'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'resume':        forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            clean = phone.replace(' ', '')
            if not re.match(r'^\+996\d{9}$', clean):
                raise forms.ValidationError("Телефон форматы: +996XXXXXXXXX (9 цифра)")
            return clean
        return phone

    def clean_resume(self):
        file = self.cleaned_data.get('resume')
        if file and hasattr(file, 'size'):
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Файлдын өлчөмү 5 МБдан ашпоосу керек")
            if not any(file.name.lower().endswith(e) for e in ('.pdf', '.doc', '.docx')):
                raise forms.ValidationError("Жол берилген форматтар: PDF, DOC же DOCX")
        return file


# ═══════════════════════════════════════════════════
# ПРАКТИКАНТ ФОРМАЛАРЫ — ЖАҢЫ КОШУЛДУ
# ═══════════════════════════════════════════════════

# ─────────────────────────────────────────
# Практиканттын отчёту
# ─────────────────────────────────────────
class PlanCompletionForm(forms.ModelForm):
    class Meta:
        model  = PlanCompletion
        fields = ['report_text', 'attachment']
        widgets = {
            'report_text': forms.Textarea(attrs={
                'class':       'form-control',
                'rows':        6,
                'placeholder': 'Бүгүн эмне аткарылды? Кандай натыйжаларга жеттиңиз? Кандай кыйынчылыктар болду?',
            }),
            'attachment': forms.FileInput(attrs={
                'class':  'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.zip',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['attachment'].required  = False
        self.fields['report_text'].label    = 'Отчёт тексти'
        self.fields['attachment'].label     = 'Файл тиркеме (милдеттүү эмес)'

    def clean_report_text(self):
        text = self.cleaned_data.get('report_text', '').strip()
        if len(text) < 20:
            raise forms.ValidationError(
                "Отчёт өтө кыска. Жок дегенде 20 символ жазыңыз."
            )
        return text

    def clean_attachment(self):
        file = self.cleaned_data.get('attachment')
        if file and hasattr(file, 'size'):
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Файл өтө чоң (макс. 10 МБ)")
        return file


# ─────────────────────────────────────────
# Лаборанттын текшерүү формасы
# ─────────────────────────────────────────
class LabReviewForm(forms.Form):
    action = forms.ChoiceField(
        choices=[('approve', 'Кабыл алуу'), ('reject', 'Кайтаруу')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Чечим',
    )
    feedback = forms.CharField(
        widget=forms.Textarea(attrs={
            'class':       'form-control',
            'rows':        3,
            'placeholder': 'Комментарий же түзөтүү боюнча нускама жазыңыз...',
        }),
        required=False,
        label='Комментарий',
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('action') == 'reject' and not cleaned.get('feedback', '').strip():
            raise forms.ValidationError(
                "Отчётту кайтарганда себебин жазуу милдеттүү."
            )
        return cleaned


# ─────────────────────────────────────────
# Жетекчинин бекитүү формасы
# ─────────────────────────────────────────
class LeaderApproveForm(forms.Form):
    action = forms.ChoiceField(
        choices=[('approve', 'Бекитүү'), ('reject', 'Кайтаруу')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Чечим',
    )
    feedback = forms.CharField(
        widget=forms.Textarea(attrs={
            'class':       'form-control',
            'rows':        3,
            'placeholder': 'Кошумча комментарий (милдеттүү эмес)',
        }),
        required=False,
        label='Комментарий',
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('action') == 'reject' and not cleaned.get('feedback', '').strip():
            raise forms.ValidationError(
                "Отчётту кайтарганда себебин жазуу милдеттүү."
            )
        return cleaned


# ─────────────────────────────────────────
# Күнүмдүк иш план формасы (лаборант/жетекчи)
# ─────────────────────────────────────────
class DailyPlanForm(forms.ModelForm):
    class Meta:
        model  = DailyPlan
        fields = ['course', 'day_number', 'title', 'description', 'attachment']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-control'}),
            'day_number': forms.NumberInput(attrs={
                'class':       'form-control',
                'min':         1,
                'max':         48,
                'placeholder': 'мис.: 1',
            }),
            'title': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'мис.: Linux буйруктары менен иштөө',
            }),
            'description': forms.Textarea(attrs={
                'class':       'form-control',
                'rows':        5,
                'placeholder': 'Практиканттар эмне аткарышы керек?',
            }),
            'attachment': forms.FileInput(attrs={
                'class':  'form-control',
                'accept': '.pdf,.doc,.docx,.ppt,.pptx',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['attachment'].required = False

    def clean(self):
        cleaned    = super().clean()
        course     = cleaned.get('course')
        day_number = cleaned.get('day_number')
        if course and day_number:
            qs = DailyPlan.objects.filter(course=course, day_number=day_number)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"{course}-курстун {day_number}-күнүнүн иш планы мурунтан бар!"
                )
        return cleaned
