# -*- coding: utf-8 -*-
"""
local_tasks 包在 import 时会注册周期任务并访问 DB；仅在解除 django_db 阻塞后再加载 cluster_portrait_report。
"""
import importlib

import pytest


@pytest.fixture(scope="module")
def portrait_pkg(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module("backend.db_periodic_task.local_tasks.cluster_portrait_report")


@pytest.fixture(scope="module")
def portrait_config(portrait_pkg):
    return importlib.import_module("backend.db_periodic_task.local_tasks.cluster_portrait_report.config")


@pytest.fixture(scope="module")
def portrait_task_module(portrait_pkg):
    return importlib.import_module("backend.db_periodic_task.local_tasks.cluster_portrait_report.task")
