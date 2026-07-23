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
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import CommandError, call_command

pytestmark = pytest.mark.django_db


class TestMongodbLocalTaskCommand:
    def test_task_required(self, mongodb_local_task_cmd_module):
        cmd = mongodb_local_task_cmd_module.Command()
        parser = cmd.create_parser("manage.py", "mongodb_local_task")
        with pytest.raises(CommandError):
            parser.parse_args(["--all"])

    def test_dispatch_backup_cluster_domain(self, mongodb_local_task_cmd_module):
        cluster = SimpleNamespace(id=1, cluster_type="MongoReplicaSet")
        with patch.object(
            mongodb_local_task_cmd_module.Cluster.objects, "filter", return_value=MagicMock(first=lambda: cluster)
        ), patch.object(
            mongodb_local_task_cmd_module.CheckMongoBackupRecordTask, "start"
        ) as backup_start, patch.object(
            mongodb_local_task_cmd_module.SyncStorageInstanceStatusTask, "start"
        ) as sync_start:
            call_command(
                "mongodb_local_task",
                "--task",
                "backup",
                "--cluster-domain",
                "mongo.example.db",
            )

        backup_start.assert_called_once()
        kwargs = backup_start.call_args.kwargs
        assert kwargs["cluster_domain"] == "mongo.example.db"
        assert kwargs["bk_biz_id"] is None
        sync_start.assert_not_called()

    def test_dispatch_all_tasks_full_scope(self, mongodb_local_task_cmd_module):
        with patch.object(
            mongodb_local_task_cmd_module.SyncStorageInstanceStatusTask, "start"
        ) as sync_start, patch.object(
            mongodb_local_task_cmd_module.CheckMongoBackupRecordTask, "start"
        ) as backup_start, patch.object(
            mongodb_local_task_cmd_module.CheckMongodbUpMetricTask, "start"
        ) as metric_start, patch.object(
            mongodb_local_task_cmd_module.CheckMongodbAffinityTask, "start"
        ) as affinity_start:
            call_command("mongodb_local_task", "--task", "all", "--all")

        sync_start.assert_called_once()
        backup_start.assert_called_once()
        metric_start.assert_called_once()
        affinity_start.assert_called_once()
        assert sync_start.call_args.kwargs["cluster_domain"] is None
        assert sync_start.call_args.kwargs["bk_biz_id"] is None

    def test_unknown_cluster_raises(self, mongodb_local_task_cmd_module):
        with patch.object(
            mongodb_local_task_cmd_module.Cluster.objects, "filter", return_value=MagicMock(first=lambda: None)
        ):
            with pytest.raises(CommandError, match="not found"):
                call_command(
                    "mongodb_local_task",
                    "--task",
                    "sync_instance_status",
                    "--cluster-domain",
                    "missing.example.db",
                )
