"""
accounts/storage_backends.py
 
Supabase Storage'ге S3 протоколу аркылуу жазабыз,
бирок окуу үчүн Supabase'дин REST public URL'ин колдонобуз —
ал имза (signature) талап кылбайт.
"""
import os
from storages.backends.s3boto3 import S3Boto3Storage
 
 
class SupabaseMediaStorage(S3Boto3Storage):
    """
    S3Boto3Storage'дин .url() методун override кылабыз —
    S3-имзаланган URL ордуна Supabase'дин public REST URL'ин кайтарат.
    """
 
    def url(self, name, parameters=None, expire=None, http_method=None):
        public_base = os.environ.get('SUPABASE_PUBLIC_URL', '').rstrip('/')
        bucket = self.bucket_name
        # name мисалы: "attendance_photos/2026/06/attendance_2026-06-29_1.jpeg"
        return f"{public_base}/storage/v1/object/public/{bucket}/{name}"