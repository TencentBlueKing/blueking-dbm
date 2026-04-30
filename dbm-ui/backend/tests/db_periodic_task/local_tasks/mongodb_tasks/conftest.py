# -*- coding: utf-8 -*-
"""
local_tasks 包在 import 时会注册周期任务并访问 DB；仅在解除 django_db 阻塞后再加载 sync_instance_status。
"""
import importlib

import pytest


@pytest.fixture(scope="module")
def sync_instance_status_module(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.local_tasks.mongodb_tasks.sync_instance_status")


@pytest.fixture(scope="module")
def mongodb_tasks_task_module(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.local_tasks.mongodb_tasks.task")


@pytest.fixture(scope="module")
def check_affinity_module(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.local_tasks.mongodb_tasks.check_affinity")
