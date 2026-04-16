from django import forms
from .models import Attendance, Project, Report, Computer, Room, InventoryLock, LabAssistant
from django.utils import timezone
import re

# Лаборант келүүсү
class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['arrival_time', 'photo', 'comment', 'late']

# Долбоор формасы
class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'title', 
            'description', 
            'attachment', 
            'start_date', 
            'end_date', 
            'status'       
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['end_date'].required = False
        self.fields['attachment'].required = False

# Отчёт
class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['title', 'project', 'description', 'file', 'comment']
        # status талаасын алып салуу!
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Отчеттун атын киргизиңиз'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Отчеттун баяндамасы'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Кошумча комментарий'}),
            # status виджетини алып салуу!
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'labassistant'):
            self.fields['project'].queryset = Project.objects.filter(
                status='completed',
                labassistant=user.labassistant
            )
            self.fields['labassistant'] = forms.ModelChoiceField(
                queryset=LabAssistant.objects.filter(id=user.labassistant.id),
                initial=user.labassistant,
                widget=forms.HiddenInput()
            )
            
            if instance:
                self.fields['project'].queryset = Project.objects.filter(
                    status='completed',
                    labassistant=user.labassistant
                ) | Project.objects.filter(id=instance.project.id)
                                           
# Компьютер формасы

class ComputerForm(forms.ModelForm):
    class Meta:
        model = Computer
        fields = [
            'room',
            'monitor_inv', 'monitor',
            'block_inv',
            'motherboard', 'processor', 'ram', 'video_card',
            'hdd_size', 'hdd_type',
            'power_supply',
        ]
        # 'number' алынды — автоматтык эсептелет
        # 'block'  алынды — моделден өчүрүлгөн
        widgets = {
            'room': forms.Select(attrs={
                'class': 'form-control',
                'required': 'required',
            }),
            'monitor_inv': forms.TextInput(attrs={
                'class': 'form-control',
                'required': 'required',
                # FIX: placeholder кыргызча мисал
                'placeholder': 'мис.: 32226',
            }),
            'monitor': forms.TextInput(attrs={
                'class': 'form-control',
                'required': 'required',
                'placeholder': 'мис.: Acer V206HQL',
            }),
            'block_inv': forms.TextInput(attrs={
                'class': 'form-control',
                'required': 'required',
                # FIX: "Блок инвентар номер" → так мисал
                'placeholder': 'мис.: 32226',
            }),
            'motherboard': forms.TextInput(attrs={
                'class': 'form-control',
                'required': 'required',
                'placeholder': 'мис.: ASUS H110M-K',
            }),
            'processor': forms.TextInput(attrs={
                'class': 'form-control',
                'required': 'required',
                'placeholder': 'мис.: Intel Core i5-9400F',
            }),
            'ram': forms.TextInput(attrs={
                'class': 'form-control',
                'required': 'required',
                # FIX: "GB" → "ГБ" кыргызча/орусча стандарт
                'placeholder': 'мис.: 8 ГБ DDR4',
            }),
            'video_card': forms.TextInput(attrs={
                'class': 'form-control',
                # FIX: required жок — модельде blank=True
                'placeholder': 'мис.: NVIDIA GeForce GTX 1050',
            }),
            # Катуу диск: өлчөм + түр өзүнчө
            'hdd_size': forms.TextInput(attrs={
                'class': 'form-control',
                'required': 'required',
                'placeholder': 'мис.: 500 ГБ',
            }),
            'hdd_type': forms.Select(attrs={
                'class': 'form-control',
                'required': 'required',
            }),
            'power_supply': forms.TextInput(attrs={
                'class': 'form-control',
                'required': 'required',
                'placeholder': 'мис.: 500W',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Инвентаризация статусун текшерүү
        self.inventory_locked = True
        try:
            lock = InventoryLock.objects.first()
            if lock:
                self.inventory_locked = lock.is_locked
        except Exception:
            pass

        # Өзгөртүү режими + инвентаризация жабык → бардык талаалар read-only
        if self.instance.pk and self.inventory_locked:
            for field_name in self.fields:
                self.fields[field_name].widget.attrs['readonly'] = True
                self.fields[field_name].widget.attrs['disabled'] = True
                self.fields[field_name].required = False

        # Кабинет тандоосун ролго жараша чектөө
        if self.user and hasattr(self.user, 'labassistant'):
            role = self.user.labassistant.role
            if role == 'laborant':
                self.fields['room'].queryset = self.user.labassistant.rooms.all()
            elif role == 'leader':
                self.fields['room'].queryset = Room.objects.all().order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        # Инвентаризация жабык болсо — өзгөртүүгө тыюу
        if self.instance.pk and self.inventory_locked:
            raise forms.ValidationError(
                "Инвентаризация жабык. Компьютерди өзгөртүү мүмкүн эмес!"
            )
        return cleaned_data
# Лаборант профили
class LabAssistantProfileForm(forms.ModelForm):
 
    class Meta:
        model = LabAssistant
        fields = ['full_name', 'phone', 'profile_image', 'resume', 'notes']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Аты-жөнүңүздү жазыңыз',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'id':    'phone',
                # FIX: placeholder форматка дал келет
                'placeholder': '+996XXXXXXXXX',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows':  4,
                'placeholder': 'Өзүңүз жөнүндө кыскача жазыңыз',
            }),
            # FIX: profile_image жана resume — form виджеттери аркылуу
            'profile_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'resume': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx',
            }),
        }
 
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            # FIX: "+996 " префикси JS тарабынан кошулат —
            # боштукту алып салып гана текшеребиз
            phone_clean = phone.replace(' ', '')
            if not re.match(r'^\+996\d{9}$', phone_clean):
                raise forms.ValidationError(
                    "Телефон форматы: +996XXXXXXXXX (9 цифра)"
                )
            return phone_clean  # базага боштуксуз сакталат
        return phone
 
    def clean_resume(self):
        file = self.cleaned_data.get('resume')
        if file and hasattr(file, 'size'):
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    "Файлдын өлчөмү 5 МБдан ашпоосу керек"
                )
            allowed = ('.pdf', '.doc', '.docx')
            if not any(file.name.lower().endswith(ext) for ext in allowed):
                raise forms.ValidationError(
                    "Жол берилген форматтар: PDF, DOC же DOCX"
                )
        return file