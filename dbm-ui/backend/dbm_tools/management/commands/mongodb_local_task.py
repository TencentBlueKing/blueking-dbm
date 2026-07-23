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
import argparse
import importlib

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster

# language_finder 禁止对 local_tasks 使用 from-import；改用 importlib 动态加载。
_check_affinity = importlib.import_module("backend.db_periodic_task.local_tasks.mongodb_tasks.check_affinity")
_check_backup = importlib.import_module("backend.db_periodic_task.local_tasks.mongodb_tasks.check_backup")
_check_exporter = importlib.import_module("backend.db_periodic_task.local_tasks.mongodb_tasks.check_exporter")
_sync_instance_status = importlib.import_module(
    "backend.db_periodic_task.local_tasks.mongodb_tasks.sync_instance_status"
)
CheckMongodbAffinityTask = _check_affinity.CheckMongodbAffinityTask
CheckMongoBackupRecordTask = _check_backup.CheckMongoBackupRecordTask
CheckMongodbUpMetricTask = _check_exporter.CheckMongodbUpMetricTask
DEFAULT_FETCH_METRIC_BATCH_SIZE = _sync_instance_status.DEFAULT_FETCH_METRIC_BATCH_SIZE
SyncStorageInstanceStatusTask = _sync_instance_status.SyncStorageInstanceStatusTask

MONGO_CLUSTER_TYPES = [ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet]

TASK_SYNC_INSTANCE_STATUS = "sync_instance_status"
TASK_BACKUP = "backup"
TASK_EXPORTER = "exporter"
TASK_AFFINITY = "affinity"
TASK_ALL = "all"

TASK_CHOICES = [TASK_SYNC_INSTANCE_STATUS, TASK_BACKUP, TASK_EXPORTER, TASK_AFFINITY, TASK_ALL]
TASK_RUN_ORDER = [TASK_SYNC_INSTANCE_STATUS, TASK_BACKUP, TASK_EXPORTER, TASK_AFFINITY]

DEFAULT_CHECK_BATCH_SIZE = 20


class Command(BaseCommand):
    help = _(
        "手动发起 MongoDB 本地巡检任务。"
        "--task 必选：sync_instance_status|backup|exporter|affinity|all；"
        "作用域三选一：--cluster-domain / --bk-biz-id / --all。"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--task",
            type=str,
            required=True,
            choices=TASK_CHOICES,
            help=_("巡检任务：sync_instance_status|backup|exporter|affinity|all（必选，无默认值）"),
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
            help=_("仅巡检指定业务下全部 MongoDB 集群"),
        )
        scope.add_argument(
            "--all",
            action="store_true",
            dest="run_all_scope",
            help=_("全量巡检全部 MongoDB 集群"),
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=None,
            help=_("批大小；未指定时 sync_instance_status 默认 50，其它巡检默认 20"),
        )
        parser.add_argument(
            "--acquire-lock",
            action=argparse.BooleanOptionalAction,
            default=True,
            help=_("仅 sync_instance_status：是否抢占全局 Redis 锁（默认开启；用 --no-acquire-lock 关闭）"),
        )

    def handle(self, *args, **options):
        task_name = options["task"]
        cluster_domain = (options.get("cluster_domain") or "").strip() or None
        bk_biz_id = options.get("bk_biz_id")
        run_all_scope = bool(options.get("run_all_scope"))
        batch_size = options.get("batch_size")
        acquire_lock = bool(options["acquire_lock"])

        if batch_size is not None and batch_size <= 0:
            raise CommandError("--batch-size must be > 0")

        scope_kwargs = self._resolve_scope(cluster_domain=cluster_domain, bk_biz_id=bk_biz_id, run_all=run_all_scope)
        tasks = TASK_RUN_ORDER if task_name == TASK_ALL else [task_name]

        for name in tasks:
            self._run_one_task(
                name,
                scope_kwargs=scope_kwargs,
                batch_size=batch_size,
                acquire_lock=acquire_lock,
            )

        self.stdout.write(self.style.SUCCESS(f"mongodb_local_task: done tasks={tasks}"))

    def _resolve_scope(self, *, cluster_domain: str | None, bk_biz_id: int | None, run_all: bool) -> dict:
        if cluster_domain:
            cluster = Cluster.objects.filter(
                immute_domain=cluster_domain,
                cluster_type__in=MONGO_CLUSTER_TYPES,
            ).first()
            if cluster is None:
                raise CommandError(
                    f"MongoDB cluster not found for immute_domain={cluster_domain!r} "
                    f"(types={ClusterType.MongoShardedCluster}/{ClusterType.MongoReplicaSet})"
                )
            self.stdout.write(
                self.style.NOTICE(
                    f"mongodb_local_task: scope=cluster_domain "
                    f"cluster_domain={cluster_domain} cluster_id={cluster.id} type={cluster.cluster_type}"
                )
            )
            return {"cluster_domain": cluster_domain, "bk_biz_id": None}
        if bk_biz_id is not None:
            cluster_count = Cluster.objects.filter(
                bk_biz_id=bk_biz_id,
                cluster_type__in=MONGO_CLUSTER_TYPES,
            ).count()
            if cluster_count == 0:
                raise CommandError(
                    f"no MongoDB cluster found for bk_biz_id={bk_biz_id} "
                    f"(types={ClusterType.MongoShardedCluster}/{ClusterType.MongoReplicaSet})"
                )
            self.stdout.write(
                self.style.NOTICE(
                    f"mongodb_local_task: scope=bk_biz_id bk_biz_id={bk_biz_id} clusters={cluster_count}"
                )
            )
            return {"cluster_domain": None, "bk_biz_id": bk_biz_id}
        if run_all:
            self.stdout.write(self.style.NOTICE("mongodb_local_task: scope=all"))
            return {"cluster_domain": None, "bk_biz_id": None}
        raise CommandError("exactly one of --cluster-domain / --bk-biz-id / --all is required")

    def _run_one_task(self, task_name: str, *, scope_kwargs: dict, batch_size: int | None, acquire_lock: bool):
        self.stdout.write(self.style.NOTICE(f"mongodb_local_task: running task={task_name}"))
        if task_name == TASK_SYNC_INSTANCE_STATUS:
            size = batch_size if batch_size is not None else DEFAULT_FETCH_METRIC_BATCH_SIZE
            SyncStorageInstanceStatusTask().start(
                batch_size=size,
                cluster_domain=scope_kwargs["cluster_domain"],
                bk_biz_id=scope_kwargs["bk_biz_id"],
                acquire_lock=acquire_lock,
            )
        else:
            size = batch_size if batch_size is not None else DEFAULT_CHECK_BATCH_SIZE
            start_kwargs = {
                "batch_size": size,
                "cluster_domain": scope_kwargs["cluster_domain"],
                "bk_biz_id": scope_kwargs["bk_biz_id"],
            }
            if task_name == TASK_BACKUP:
                CheckMongoBackupRecordTask().start(**start_kwargs)
            elif task_name == TASK_EXPORTER:
                CheckMongodbUpMetricTask().start(**start_kwargs)
            elif task_name == TASK_AFFINITY:
                CheckMongodbAffinityTask().start(**start_kwargs)
            else:
                raise CommandError(f"unsupported task: {task_name}")
        self.stdout.write(self.style.SUCCESS(f"mongodb_local_task: task={task_name} finished"))
