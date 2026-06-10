#!/usr/bin/env bash
# Render'де автоматтык иштейт — deploy болгон сайын
 
set -o errexit  # Ката болсо токтот
 
# Пакеттерди орнотуу
pip install -r requirements.txt
 
# Static файлдарды жыйноо
python manage.py collectstatic --no-input
 
# Миграцияларды колдонуу
python manage.py migrate