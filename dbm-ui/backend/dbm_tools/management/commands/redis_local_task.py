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
import importlib
import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster

# language_finder 禁止对 local_tasks 使用 from-import；改用 importlib 动态加载。
_check_exporter = importlib.import_module("backend.db_periodic_task.local_tasks.redis_tasks.check_exporter")
CheckRedisUpMetricTask = _check_exporter.CheckRedisUpMetricTask

TASK_EXPORTER = "exporter"
TASK_CHOICES = [TASK_EXPORTER]

DEFAULT_CHECK_BATCH_SIZE = 20
LOG_LEVEL_CHOICES = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Command(BaseCommand):
    help = _("手动发起 Redis 本地巡检任务。" "--task 必选：exporter；" "作用域三选一：--cluster-domain / --bk-biz-id / --all。")

    def add_arguments(self, parser):
        parser.add_argument(
            "--task",
            type=str,
            required=True,
            choices=TASK_CHOICES,
            help=_("巡检任务：exporter（必选，无默认值）"),
        )
        scope = parser.add_mutually_exclusive_group(required=True)
        scope.add_argument(
            "--cluster-domain",
            type=str,
            default=None,
            help=_("仅巡检指定集群（immute_domain）"),
        )
        scope.add_argument(
            "--bk-biz-id",
            type=int,
            default=None,
            help=_("仅巡检指定业务下全部 Redis 集群"),
        )
        scope.add_argument(
            "--all",
            action="store_true",
            dest="run_all_scope",
            help=_("全量巡检全部 Redis 集群"),
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=None,
            help=_("批大小；未指定时默认 20"),
        )
        parser.add_argument(
            "--loglevel",
            type=str,
            default="INFO",
            choices=LOG_LEVEL_CHOICES,
            help=_("日志级别；可选 DEBUG/INFO/WARNING/ERROR/CRITICAL，默认 INFO"),
        )

    def handle(self, *args, **options):
        task_name = options["task"]
        cluster_domain = (options.get("cluster_domain") or "").strip() or None
        bk_biz_id = options.get("bk_biz_id")
        run_all_scope = bool(options.get("run_all_scope"))
        batch_size = options.get("batch_size")
        loglevel = options["loglevel"]

        if batch_size is not None and batch_size <= 0:
            raise CommandError("--batch-size must be > 0")

        self._configure_logging(loglevel)
        scope_kwargs = self._resolve_scope(cluster_domain=cluster_domain, bk_biz_id=bk_biz_id, run_all=run_all_scope)
        self._run_exporter_task(scope_kwargs=scope_kwargs, batch_size=batch_size)
        self.stdout.write(self.style.SUCCESS(f"redis_local_task: done task={task_name}"))

    def _resolve_scope(self, *, cluster_domain: str | None, bk_biz_id: int | None, run_all: bool) -> dict:
        redis_cluster_types = ClusterType.db_type_to_cluster_types(DBType.Redis.value)
        if cluster_domain:
            cluster = Cluster.objects.filter(
                immute_domain=cluster_domain,
                cluster_type__in=redis_cluster_types,
            ).first()
            if cluster is None:
                raise CommandError(
                    f"Redis cluster not found for immute_domain={cluster_domain!r} "
                    f"(types={','.join(redis_cluster_types)})"
                )
            self.stdout.write(
                self.style.NOTICE(
                    f"redis_local_task: scope=cluster_domain "
                    f"cluster_domain={cluster_domain} cluster_id={cluster.id} type={cluster.cluster_type}"
                )
            )
            return {"cluster_domain": cluster_domain, "bk_biz_id": None}
        if bk_biz_id is not None:
            cluster_count = Cluster.objects.filter(
                bk_biz_id=bk_biz_id,
                cluster_type__in=redis_cluster_types,
            ).count()
            if cluster_count == 0:
                raise CommandError(
                    f"no Redis cluster found for bk_biz_id={bk_biz_id} " f"(types={','.join(redis_cluster_types)})"
                )
            self.stdout.write(
                self.style.NOTICE(f"redis_local_task: scope=bk_biz_id bk_biz_id={bk_biz_id} clusters={cluster_count}")
            )
            return {"cluster_domain": None, "bk_biz_id": bk_biz_id}
        if run_all:
            self.stdout.write(self.style.NOTICE("redis_local_task: scope=all"))
            return {"cluster_domain": None, "bk_biz_id": None}
        raise CommandError("exactly one of --cluster-domain / --bk-biz-id / --all is required")

    def _run_exporter_task(self, *, scope_kwargs: dict, batch_size: int | None):
        self.stdout.write(self.style.NOTICE("redis_local_task: running task=exporter"))
        size = batch_size if batch_size is not None else DEFAULT_CHECK_BATCH_SIZE
        CheckRedisUpMetricTask().start(
            batch_size=size,
            cluster_domain=scope_kwargs["cluster_domain"],
            bk_biz_id=scope_kwargs["bk_biz_id"],
        )
        self.stdout.write(self.style.SUCCESS("redis_local_task: task=exporter finished"))

    def _configure_logging(self, loglevel: str):
        level = getattr(logging, loglevel.upper())
        logger_names = [
            "root",
            "celery",
            "backend.db_periodic_task.local_tasks.redis_tasks.check_exporter",
        ]
        for name in logger_names:
            logging.getLogger(name).setLevel(level)
        self.stdout.write(self.style.NOTICE(f"redis_local_task: loglevel={loglevel.upper()}"))
