"""
accounts/utils.py
 
Файл аттарын S3/Supabase'ге коопсуз кылып тазалоо.
Кириллица, боштук, атайын белгилерди алып салат.
"""
import os
import re
import uuid
from datetime import date
 
 
def safe_filename(filename):
    """
    'ЛАБОРАНТТАР_СИСТЕМАСЫ_БОЮНЧА_ОТЧЁТ__А._к._М..pdf'
    →  'laboranttar_sistemasy_boyuncha_otchot_a_k_m_<random>.pdf'
    """
    name, ext = os.path.splitext(filename)
 
    # Кириллица тамгаларын латынчага которуу таблицасы
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e',
        'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k',
        'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
        'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts',
        'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
        'э': 'e', 'ю': 'yu', 'я': 'ya',
        'ң': 'ng', 'ө': 'o', 'ү': 'u',  # кыргызча тамгалар
    }
 
    name_lower = name.lower()
    result = []
    for ch in name_lower:
        if ch in translit_map:
            result.append(translit_map[ch])
        elif ch.isalnum() and ch.isascii():
            result.append(ch)
        elif ch in ('_', '-'):
            result.append('_')
        else:
            result.append('_')  # боштук, чекит ж.б. → _
 
    clean_name = ''.join(result)
    # Бир нече "_" катары турса бирге кысуу
    clean_name = re.sub(r'_+', '_', clean_name).strip('_')
 
    if not clean_name:
        clean_name = 'file'
 
    # Аталыш өтө узун болбосун (50 символдон)
    clean_name = clean_name[:50]
 
    # Уникалдуулук үчүн кокусунан 6 символ кошуу
    unique_suffix = uuid.uuid4().hex[:6]
 
    return f"{clean_name}_{unique_suffix}{ext.lower()}"
def report_upload_path(instance, filename):
    filename = safe_filename(filename)
    today = date.today()
    return f"reports/{today.year}/{today.month:02d}/{filename}"


def daily_plan_upload_path(instance, filename):
    filename = safe_filename(filename)
    today = date.today()
    return f"daily_plans/{today.year}/{today.month:02d}/{filename}"


def project_upload_path(instance, filename):
    filename = safe_filename(filename)
    today = date.today()
    return f"projects/{today.year}/{today.month:02d}/{filename}"


def plan_completion_upload_path(instance, filename):
    filename = safe_filename(filename)
    today = date.today()
    return f"plan_completions/{today.year}/{today.month:02d}/{filename}"


def resume_upload_path(instance, filename):
    filename = safe_filename(filename)
    return f"resumes/{filename}"


def profile_image_upload_path(instance, filename):
    filename = safe_filename(filename)
    return f"profiles/{filename}"