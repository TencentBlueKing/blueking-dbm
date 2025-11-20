# -*- coding: utf-8 -*-
"""
WSGI config for backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from django.db.backends.mysql.features import DatabaseFeatures
from blueking.mysql_patch import PatchFeatures

DatabaseFeatures.minimum_database_version = PatchFeatures.minimum_database_version

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.prod")

application = get_wsgi_application()
