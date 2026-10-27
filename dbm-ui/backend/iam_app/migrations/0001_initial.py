# -*- coding: utf-8 -*-
import codecs
import json
import os

from django.conf import settings
from django.db import migrations
from iam.contrib.iam_migration.migrator import IAMMigrator

from backend import env


def forward_func(apps, schema_editor):
    # V4 模型由 services_init iam 注册，不能再向 V3 权限中心迁移
    if env.ENABLE_IAM_V4:
        return

    migrator = IAMMigrator(Migration.migration_json)
    migrator.migrate()


class Migration(migrations.Migration):
    migration_json = "initial.json"

    dependencies = []

    operations = [migrations.RunPython(forward_func)]
