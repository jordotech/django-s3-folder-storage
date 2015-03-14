"""
    Two classes for media storage
"""

from storages.backends.s3boto import S3BotoStorage, S3BotoStorageFile, parse_ts_extended
from django.conf import settings
import datetime

class FixedS3BotoStorage(S3BotoStorage):
    """
    fix the broken javascript admin resources with S3Boto on Django 1.4
    for more info see http://code.larlet.fr/django-storages/issue/121/s3boto-admin-prefix-issue-with-django-14
    """
    def url(self, name):
        url = super(FixedS3BotoStorage, self).url(name)
        if name.endswith('/') and not url.endswith('/'):
            url += '/'
        return url

class StaticStorage(FixedS3BotoStorage):
    """
    Storage for static files.
    The folder is defined in settings.STATIC_S3_PATH
    """

    def __init__(self, *args, **kwargs):
        kwargs['location'] = settings.STATIC_S3_PATH
        super(StaticStorage, self).__init__(*args, **kwargs)

class DefaultStorage(FixedS3BotoStorage):
    """
    Storage for uploaded media files.
    The folder is defined in settings.DEFAULT_S3_PATH
    """
    def move(self, old_file_name, new_file_name, allow_overwrite=False):
        if self.exists(new_file_name):
            if allow_overwrite:
                self.delete(new_file_name)
            else:
                raise "The destination file '%s' exists and allow_overwrite is False" % new_file_name

        old_key_name = self._encode_name(self._normalize_name(self._clean_name(old_file_name)))
        new_key_name = self._encode_name(self._normalize_name(self._clean_name(new_file_name)))
        k = self.bucket.copy_key(new_key_name, self.bucket.name, old_key_name)
        if not k:
            raise "Couldn't copy '%s' to '%s'" % (old_file_name, new_file_name)
        self.delete(old_file_name)

    def makedirs(self, name):
        # i can't create dirs still
        pass

    def rmtree(self, name):
        name = self._normalize_name(self._clean_name(name))
        dirlist = self.bucket.list(self._encode_name(name))
        for item in dirlist:
            item.delete()
    def modified_time(self, name):
        ISO8601 = '%Y-%m-%dT%H:%M:%SZ'
        ISO8601_MS = '%Y-%m-%dT%H:%M:%S.%fZ'
        name = self._normalize_name(self._clean_name(name))
        entry = self.entries.get(name)
        # only call self.bucket.get_key() if the key is not found
        # in the preloaded metadata.
        if entry is None:
            entry = self.bucket.get_key(self._encode_name(name))
        # Parse the last_modified string to a local datetime object.
        if not entry.last_modified:
            try:
                entry.last_modified = datetime.datetime.now().strftime(ISO8601)
            except ValueError:
                entry.last_modified = datetime.datetime.now().strftime(ISO8601_MS)
        return parse_ts_extended(entry.last_modified)
    def isfile(self, name):
        try:
            name = self._normalize_name(self._clean_name(name))
            f = S3BotoStorageFile(name, 'rb', self)
            if not f.key:
                return False
            return True
        except:
            return False
    def isdir(self, name):
        return not self.isfile(name)
    def path(self, name):
        name = self._normalize_name(self._clean_name(name))
        if self.custom_domain:
            return "%s//%s/%s" % (self.url_protocol,
                                  self.custom_domain, name)
        return self.connection.generate_url(self.querystring_expire,
            method='GET', bucket=self.bucket.name, key=self._encode_name(name),
            query_auth=self.querystring_auth, force_http=not self.secure_urls)
    def save(self, name, content):
        re = super(FixedS3BotoStorage, self).save(name, content)
        #key.copy(key.bucket, key.name, preserve_acl=True, metadata={'Content-Type': 'text/plain'})
        return re
    def __init__(self, *args, **kwargs):
        kwargs['location'] = settings.DEFAULT_S3_PATH
        super(DefaultStorage, self).__init__(*args, **kwargs)