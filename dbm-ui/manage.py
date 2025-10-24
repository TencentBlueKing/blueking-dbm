# -*- coding: utf-8 -*-
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

from django.db.backends.mysql.features import DatabaseFeatures
from blueking.mysql_patch import PatchFeatures

def main():
    """Run administrative tasks."""
    # 目前 Django 仅是对 5.7 做了软性的不兼容改动，在没有使用 8.0 特异的功能时，对 5.7 版本的使用无影响
    DatabaseFeatures.minimum_database_version = PatchFeatures.minimum_database_version
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.prod")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
