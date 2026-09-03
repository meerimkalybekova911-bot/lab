import os
from storages.backends.s3boto3 import S3Boto3Storage


class SupabaseMediaStorage(S3Boto3Storage):

    default_acl = None

    def url(self, name, parameters=None, expire=None, http_method=None):
        public_base = os.environ.get('SUPABASE_PUBLIC_URL', '').rstrip('/')
        bucket = self.bucket_name

        return f"{public_base}/storage/v1/object/public/{bucket}/{name}"
