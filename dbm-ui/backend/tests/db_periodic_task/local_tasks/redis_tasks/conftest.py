# -*- coding: utf-8 -*-
"""
local_tasks 包在 import 时会注册周期任务并访问 DB；仅在解除 django_db 阻塞后再加载 check_exporter。
"""
import importlib

import pytest


@pytest.fixture(scope="module")
def check_exporter(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.local_tasks.redis_tasks.check_exporter")
