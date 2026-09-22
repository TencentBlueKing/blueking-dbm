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
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from backend.db_meta.enums import ClusterType
from backend.db_meta.models.cluster import Cluster
from backend.db_periodic_task.models import MySQLBackupRecoverTask, TaskPhase, TaskStatus


def _local_day_start():
    now_local = timezone.localtime()
    return now_local.replace(hour=0, minute=0, second=0, microsecond=0)


def _create_cluster(domain):
    return Cluster.objects.create(
        bk_biz_id=5005578,
        cluster_type=ClusterType.TenDBCluster.value,
        immute_domain=domain,
        name=domain.split(".")[0],
    )


def _create_task(cluster, create_at, task_status=TaskStatus.RECOVER_SUCCESS, phase=TaskPhase.DONE):
    now = timezone.now()
    task = MySQLBackupRecoverTask.objects.create(
        bk_biz_id=cluster.bk_biz_id,
        cluster_id=cluster.id,
        cluster_domain=cluster.immute_domain,
        cluster_type=cluster.cluster_type,
        backup_id="backup-{}".format(cluster.id),
        backup_begin_time=now,
        backup_end_time=now,
        task_id="root-{}".format(cluster.id),
        task_status=task_status,
        phase=phase,
        creator="system",
        updater="system",
    )
    MySQLBackupRecoverTask.objects.filter(pk=task.pk).update(create_at=create_at)
    return task


def _create_success_task(cluster, create_at):
    return _create_task(cluster, create_at)


class TestOncePerLocalDay(TestCase):
    def test_today_window_is_local_calendar_day(self):
        day_start = _local_day_start()
        included = _create_cluster("spider.included.exercise.db")
        yesterday_cluster = _create_cluster("spider.yesterday.exercise.db")
        tomorrow_cluster = _create_cluster("spider.tomorrow.exercise.db")
        _create_success_task(included, day_start)
        _create_success_task(yesterday_cluster, day_start - timedelta(seconds=1))
        _create_success_task(tomorrow_cluster, day_start + timedelta(days=1))

        cluster_ids = MySQLBackupRecoverTask.get_today_task_cluster_ids()

        self.assertIn(included.id, cluster_ids)
        self.assertNotIn(yesterday_cluster.id, cluster_ids)
        self.assertNotIn(tomorrow_cluster.id, cluster_ids)

    def test_fallback_skips_cluster_exercised_today(self):
        # 延迟导入，避免收集阶段执行 local_tasks 注册并访问数据库
        from backend.db_periodic_task.local_tasks.mysql_backup_rollback import gen_task

        day_start = _local_day_start()
        already_today = _create_cluster("spider.today.exercise.db")
        still_due = _create_cluster("spider.due.exercise.db")
        _create_success_task(already_today, day_start + timedelta(hours=1))
        _create_success_task(still_due, day_start - timedelta(seconds=1))

        queue = []
        real_filter = Cluster.objects.filter

        def only_these_clusters(*args, **kwargs):
            return real_filter(*args, **kwargs).filter(id__in=[already_today.id, still_due.id])

        with patch.object(Cluster.objects, "filter", side_effect=only_these_clusters):
            gen_task._collect_all_clusters(
                queue,
                {},
                0,
                2,
                set(),
                ignore_configs=None,
            )

        queued_ids = [item.cluster.id for item in queue]
        self.assertNotIn(already_today.id, queued_ids)
        self.assertIn(still_due.id, queued_ids)

    def test_unpracticed_skips_cluster_with_any_task_today(self):
        # 当天已建任务但未成功：不在 practiced / 近2天失败 / 运行中名单里，只能靠日限挡住
        from backend.db_periodic_task.local_tasks.mysql_backup_rollback import gen_task

        day_start = _local_day_start()
        already_today = _create_cluster("spider.unpracticed.today.db")
        still_due = _create_cluster("spider.unpracticed.due.db")
        _create_task(
            already_today,
            day_start + timedelta(hours=1),
            task_status=TaskStatus.COMMIT_SUCCESS,
            phase=TaskPhase.DONE,
        )

        queue = []
        real_exclude = Cluster.objects.exclude

        def only_these_clusters(*args, **kwargs):
            return real_exclude(*args, **kwargs).filter(id__in=[already_today.id, still_due.id])

        with patch.object(Cluster.objects, "exclude", side_effect=only_these_clusters):
            gen_task._collect_unpracticed_clusters(
                [],
                [],
                queue,
                ignore_configs=None,
            )

        queued_ids = [item.cluster.id for item in queue]
        self.assertNotIn(already_today.id, queued_ids)
        self.assertIn(still_due.id, queued_ids)

    def test_overlapping_run_is_skipped_while_lock_held(self):
        from django.core.cache import cache

        from backend.db_periodic_task.local_tasks.mysql_backup_rollback import task as task_mod

        cache.delete(task_mod.BACKUP_RECOVERY_LOCK_KEY)
        with patch.object(task_mod, "gen_rollback_task") as generate:
            task_mod.backup_data_recovery_task()
            self.assertFalse(cache.get(task_mod.BACKUP_RECOVERY_LOCK_KEY))
            cache.add(task_mod.BACKUP_RECOVERY_LOCK_KEY, 1, timeout=60)
            task_mod.backup_data_recovery_task()
        self.assertEqual(generate.call_count, 1)
        cache.delete(task_mod.BACKUP_RECOVERY_LOCK_KEY)
