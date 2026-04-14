# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

"""
Shared fixtures for redis_backup tests.

Import from source modules lazily (inside fixtures/functions) to avoid
the import chain through ``local_tasks/__init__.py`` which registers
periodic tasks and requires DB access at import time.
"""


def _make_slave(ip, port, age_hours=72):
    return SimpleNamespace(
        machine=SimpleNamespace(ip=ip),
        port=port,
        create_at=timezone.now() - timedelta(hours=age_hours),
    )


def _make_master(ip, port, slave_ip, slave_port, slave_age_hours=72, tuple_age_hours=72):
    slave = _make_slave(slave_ip, slave_port, age_hours=slave_age_hours)
    return SimpleNamespace(
        machine=SimpleNamespace(ip=ip),
        port=port,
        ejector_tuples=[SimpleNamespace(receiver=slave, create_at=timezone.now() - timedelta(hours=tuple_age_hours))],
    )


@pytest.fixture
def mock_cluster():
    from backend.db_meta.enums import ClusterType

    cluster = MagicMock()
    cluster.bk_biz_id = 3
    cluster.bk_cloud_id = 0
    cluster.immute_domain = "test.example.db"
    cluster.cluster_type = ClusterType.TwemproxyTendisSSDInstance.value
    cluster.major_version = "7.0"
    cluster.storages = [
        _make_master("3.3.3.1", 30000, "3.3.3.2", 30000),
        _make_master("3.3.3.1", 30001, "3.3.3.2", 30001),
    ]
    return cluster


@pytest.fixture
def mock_config():
    from backend.db_periodic_task.local_tasks.redis_backup.config import RedisBackupCheckConfig

    return RedisBackupCheckConfig(
        target_bk_cloud_ids=[0],
        ignore_domains=[],
        min_instance_age_hours=48,
        max_schedule_deviation_hours=2.5,
        min_cluster_age_days=2,
        retention_days=180,
    )


def make_fullbackup_entry(*, status, ip, port, task_id="t1", uptime="2024-01-15T05:30:00+08:00", status_info=""):
    return {
        "backup_status": status,
        "redis_ip": ip,
        "redis_port": str(port),
        "task_id": task_id,
        "uptime": uptime,
        "backup_status_info": status_info,
    }


def make_binlog_entry(*, status, ip, port, task_id="t1", file_name="binlog-3.3.3.2-30000-0-1234567890.log.zst"):
    return {
        "backup_status": status,
        "redis_ip": ip,
        "redis_port": str(port),
        "task_id": task_id,
        "file_name": file_name,
    }
