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


class TestRedisLocalTaskCommand:
    def test_task_required(self, redis_local_task_cmd_module):
        cmd = redis_local_task_cmd_module.Command()
        parser = cmd.create_parser("manage.py", "redis_local_task")
        with pytest.raises(CommandError):
            parser.parse_args(["--all"])

    def test_dispatch_exporter_cluster_domain(self, redis_local_task_cmd_module):
        cluster = SimpleNamespace(id=1, cluster_type="TwemproxyRedisInstance")
        with patch.object(
            redis_local_task_cmd_module.Cluster.objects, "filter", return_value=MagicMock(first=lambda: cluster)
        ), patch.object(redis_local_task_cmd_module.CheckRedisUpMetricTask, "start") as exporter_start:
            call_command(
                "redis_local_task",
                "--task",
                "exporter",
                "--cluster-domain",
                "redis.example.db",
            )

        exporter_start.assert_called_once()
        kwargs = exporter_start.call_args.kwargs
        assert kwargs["cluster_domain"] == "redis.example.db"
        assert kwargs["bk_biz_id"] is None
        assert kwargs["batch_size"] == 20

    def test_loglevel_configured(self, redis_local_task_cmd_module):
        with patch.object(redis_local_task_cmd_module.CheckRedisUpMetricTask, "start"), patch.object(
            redis_local_task_cmd_module.logging, "getLogger"
        ) as get_logger:
            call_command("redis_local_task", "--task", "exporter", "--all", "--loglevel", "DEBUG")

        configured_names = [call.args[0] for call in get_logger.call_args_list]
        assert "root" in configured_names
        assert "celery" in configured_names
        assert "backend.db_periodic_task.local_tasks.redis_tasks.check_exporter" in configured_names
        for call in get_logger.return_value.setLevel.call_args_list:
            assert call.args == (redis_local_task_cmd_module.logging.DEBUG,)

    def test_dispatch_exporter_full_scope(self, redis_local_task_cmd_module):
        with patch.object(redis_local_task_cmd_module.CheckRedisUpMetricTask, "start") as exporter_start:
            call_command("redis_local_task", "--task", "exporter", "--all")

        exporter_start.assert_called_once()
        assert exporter_start.call_args.kwargs["cluster_domain"] is None
        assert exporter_start.call_args.kwargs["bk_biz_id"] is None

    def test_unknown_cluster_raises(self, redis_local_task_cmd_module):
        with patch.object(
            redis_local_task_cmd_module.Cluster.objects, "filter", return_value=MagicMock(first=lambda: None)
        ):
            with pytest.raises(CommandError, match="not found"):
                call_command(
                    "redis_local_task",
                    "--task",
                    "exporter",
                    "--cluster-domain",
                    "missing.example.db",
                )
