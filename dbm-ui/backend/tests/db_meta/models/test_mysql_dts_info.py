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
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from django.db import close_old_connections, connections, transaction
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from backend.db_meta.exceptions import ClusterExclusiveOperateException
from backend.db_meta.models.mysql_dts import MysqlDtsCluster, MysqlDtsClusterStatus, MysqlDtsInfo, MysqlDtsStatus
from backend.ticket.builders.common.base import fetch_cluster_ids
from backend.ticket.constants import TicketType


class MysqlDtsInfoModelTest(TestCase):
    def test_create_source_cluster_ids_roundtrip(self):
        row = MysqlDtsInfo.objects.create(
            bk_biz_id=1,
            source_cluster_ids=[101, 102],
            target_cluster_id=200,
            status=MysqlDtsStatus.FullOnline.value,
        )
        row.refresh_from_db()
        self.assertEqual(row.source_cluster_ids, [101, 102])
        data = row.to_dict()
        self.assertIn("source_cluster_ids", data)
        self.assertNotIn("source_cluster_id", data)


class MysqlDtsInfoClusiveTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dts_cluster = MysqlDtsCluster.objects.create(
            id=1, name="dts-reservation", bk_biz_id=1, status=MysqlDtsClusterStatus.RUNNING.value
        )

    def _create_active(self, *, source_cluster_ids, target_cluster_id, ticket_id):
        return MysqlDtsInfo.objects.create(
            bk_biz_id=1,
            source_cluster_ids=source_cluster_ids,
            target_cluster_id=target_cluster_id,
            ticket_id=ticket_id,
            status=MysqlDtsStatus.FullOnline.value,
        )

    def test_source_overlap_not_first_source_raises(self):
        """AE3：活跃行占用源 A=20（非首个源），新单据含 20 → 互斥。"""
        self._create_active(source_cluster_ids=[10, 20], target_cluster_id=300, ticket_id=1)
        with self.assertRaises(ClusterExclusiveOperateException):
            MysqlDtsInfo.dts_info_clusive(
                ticket_id=2,
                ticket_type=TicketType.MYSQL_DTS_DATA_MIGRATE.value,
                details={"cluster_id": 20},
            )

    def test_no_overlap_passes(self):
        """AE4：活跃仅占用源 20；新单据仅含源 10 且目标不冲突 → 通过。"""
        self._create_active(source_cluster_ids=[20], target_cluster_id=300, ticket_id=1)
        MysqlDtsInfo.dts_info_clusive(
            ticket_id=2,
            ticket_type=TicketType.MYSQL_DTS_DATA_MIGRATE.value,
            details={"cluster_id": 10, "target_cluster_id": 400},
        )

    def test_target_conflict_raises(self):
        self._create_active(source_cluster_ids=[10], target_cluster_id=300, ticket_id=1)
        with self.assertRaises(ClusterExclusiveOperateException):
            MysqlDtsInfo.dts_info_clusive(
                ticket_id=2,
                ticket_type=TicketType.MYSQL_DTS_DATA_MIGRATE.value,
                details={"cluster_id": 99, "target_cluster_id": 300},
            )

    def test_same_ticket_excluded(self):
        self._create_active(source_cluster_ids=[10, 20], target_cluster_id=300, ticket_id=9)
        MysqlDtsInfo.dts_info_clusive(
            ticket_id=9,
            ticket_type=TicketType.MYSQL_DTS_DATA_MIGRATE.value,
            details={"cluster_id": 20, "target_cluster_id": 300},
        )

    def test_full_online_raises(self):
        """FullOnline 为进行中状态，应触发互斥。"""
        self._create_active(source_cluster_ids=[10], target_cluster_id=300, ticket_id=874)
        with self.assertRaises(ClusterExclusiveOperateException):
            MysqlDtsInfo.dts_info_clusive(
                ticket_id=877,
                ticket_type=TicketType.MYSQL_DTS_DATA_MIGRATE.value,
                details={"cluster_id": 10, "target_cluster_id": 400},
            )

    def test_todo_raises(self):
        """ToDo 为入口预占态，应触发互斥。"""
        MysqlDtsInfo.objects.create(
            bk_biz_id=1,
            source_cluster_ids=[10],
            target_cluster_id=300,
            ticket_id=874,
            status=MysqlDtsStatus.ToDo.value,
            dts_task_id="mysql-dts-874-10-300",
        )
        with self.assertRaises(ClusterExclusiveOperateException):
            MysqlDtsInfo.dts_info_clusive(
                ticket_id=877,
                ticket_type=TicketType.MYSQL_DTS_DATA_MIGRATE.value,
                details={"cluster_id": 10, "target_cluster_id": 400},
            )

    def test_disconnected_does_not_block(self):
        """Disconnected 为切换完成终态，不应再互斥。"""
        MysqlDtsInfo.objects.create(
            bk_biz_id=1,
            source_cluster_ids=[10],
            target_cluster_id=300,
            ticket_id=874,
            status=MysqlDtsStatus.Disconnected.value,
        )
        MysqlDtsInfo.dts_info_clusive(
            ticket_id=877,
            ticket_type=TicketType.MYSQL_DTS_DATA_MIGRATE.value,
            details={"cluster_id": 10, "target_cluster_id": 300},
        )

    def test_check_exclusive_and_reserve_creates_todo(self):
        details = {
            "dts_resource": {"mode": "use_existing", "dts_cluster_id": 1},
            "migrate": {
                "topology": "one_to_one",
                "one_to_one": {
                    "task_name": "mysql-dts-900-10-300",
                    "source": {"cluster_id": 10, "sync_scope": {"db_patterns": ["db_a"], "table_patterns": ["*"]}},
                    "target": {"cluster_id": 300},
                },
            },
            "task": {"task_mode": "all"},
        }
        MysqlDtsInfo.check_exclusive_and_reserve(
            ticket_id=900,
            ticket_type=TicketType.MYSQL_DTS_DATA_MIGRATE.value,
            details=details,
            bk_biz_id=1,
            migrate_type="mysql_to_mysql",
            creator="tester",
        )
        row = MysqlDtsInfo.objects.get(ticket_id=900, dts_task_id="mysql-dts-900-10-300")
        self.assertEqual(row.status, MysqlDtsStatus.ToDo.value)
        self.assertEqual(row.source_cluster_ids, [10])
        self.assertEqual(row.target_cluster_id, 300)
        self.assertEqual(row.dts_cluster_id, self.dts_cluster.id)

    def test_check_exclusive_and_reserve_blocks_second_ticket(self):
        details_a = {
            "dts_resource": {"mode": "use_existing", "dts_cluster_id": 1},
            "migrate": {
                "topology": "one_to_one",
                "one_to_one": {
                    "task_name": "mysql-dts-901-10-300",
                    "source": {"cluster_id": 10, "sync_scope": {"db_patterns": ["db_a"], "table_patterns": ["*"]}},
                    "target": {"cluster_id": 300},
                },
            },
            "task": {"task_mode": "all"},
        }
        details_b = {
            "dts_resource": {"mode": "use_existing", "dts_cluster_id": 1},
            "migrate": {
                "topology": "one_to_one",
                "one_to_one": {
                    "task_name": "mysql-dts-902-10-400",
                    "source": {"cluster_id": 10, "sync_scope": {"db_patterns": ["db_a"], "table_patterns": ["*"]}},
                    "target": {"cluster_id": 400},
                },
            },
            "task": {"task_mode": "all"},
        }
        MysqlDtsInfo.check_exclusive_and_reserve(
            ticket_id=901,
            ticket_type=TicketType.MYSQL_DTS_DATA_MIGRATE.value,
            details=details_a,
            bk_biz_id=1,
            migrate_type="mysql_to_mysql",
        )
        with self.assertRaises(ClusterExclusiveOperateException):
            MysqlDtsInfo.check_exclusive_and_reserve(
                ticket_id=902,
                ticket_type=TicketType.MYSQL_DTS_DATA_MIGRATE.value,
                details=details_b,
                bk_biz_id=1,
                migrate_type="mysql_to_mysql",
            )
        # 冲突回滚：第二单不应留下 ToDo
        self.assertFalse(MysqlDtsInfo.objects.filter(ticket_id=902).exists())

    def _reservation_details(self):
        return {
            "dts_resource": {"dts_cluster_id": self.dts_cluster.id},
            "migrate": {
                "topology": "one_to_one",
                "one_to_one": {
                    "task_name": "reuse-task",
                    "source": {"cluster_id": 10, "sync_scope": {"db_patterns": ["db_a"], "table_patterns": ["*"]}},
                    "target": {"cluster_id": 300},
                },
            },
        }

    def test_reservation_rejects_destroying_destroyed_or_other_business(self):
        for status, bk_biz_id in (("destroying", 1), ("destroyed", 1), ("running", 2)):
            with self.subTest(status=status, bk_biz_id=bk_biz_id):
                self.dts_cluster.status = status
                self.dts_cluster.bk_biz_id = bk_biz_id
                self.dts_cluster.save(update_fields=["status", "bk_biz_id"])
                with self.assertRaises(ClusterExclusiveOperateException):
                    MysqlDtsInfo.reserve_todo_placeholders(
                        ticket_id=910, bk_biz_id=1, details=self._reservation_details()
                    )
                self.assertFalse(MysqlDtsInfo.objects.filter(ticket_id=910).exists())

    def test_retry_binds_legacy_reservation_without_downgrading_online(self):
        row = MysqlDtsInfo.objects.create(
            ticket_id=911, dts_task_id="reuse-task", dts_cluster_id=0, status=MysqlDtsStatus.FullOnline.value
        )
        MysqlDtsInfo.reserve_todo_placeholders(ticket_id=911, bk_biz_id=1, details=self._reservation_details())
        row.refresh_from_db()
        self.assertEqual(row.dts_cluster_id, self.dts_cluster.id)
        self.assertEqual(row.status, MysqlDtsStatus.FullOnline.value)
        row.status = MysqlDtsStatus.Terminated.value
        row.dts_cluster_id = 0
        row.save()
        MysqlDtsInfo.reserve_todo_placeholders(ticket_id=911, bk_biz_id=1, details=self._reservation_details())
        row.refresh_from_db()
        self.assertEqual(row.dts_cluster_id, self.dts_cluster.id)
        self.assertEqual(row.status, MysqlDtsStatus.ToDo.value)

    def test_unavailable_second_cluster_does_not_leave_partial_reservations(self):
        closed = MysqlDtsCluster.objects.create(
            bk_biz_id=1, name="closing", status=MysqlDtsClusterStatus.DESTROYING.value
        )
        first, second = self._reservation_details(), self._reservation_details()
        second["dts_resource"]["dts_cluster_id"] = closed.id
        with self.assertRaises(ClusterExclusiveOperateException):
            MysqlDtsInfo.reserve_todo_placeholders(ticket_id=912, bk_biz_id=1, details={"infos": [first, second]})
        self.assertFalse(MysqlDtsInfo.objects.filter(ticket_id=912).exists())


class MysqlDtsCleanupReservationRaceTest(TransactionTestCase):
    def setUp(self):
        self.cluster = MysqlDtsCluster.objects.create(
            name="dts-lock", bk_biz_id=1, status="running", master_nodes=[{"ip": "127.0.0.2"}]
        )
        self.details = {
            "dts_resource": {"dts_cluster_id": self.cluster.id},
            "migrate": {
                "topology": "one_to_one",
                "one_to_one": {
                    "task_name": "concurrent-reuse",
                    "source": {"cluster_id": 10, "sync_scope": {"db_patterns": ["db_a"], "table_patterns": ["*"]}},
                    "target": {"cluster_id": 300},
                },
            },
        }

    def _reserve(self):
        MysqlDtsInfo.reserve_todo_placeholders(ticket_id=901, bk_biz_id=1, details=self.details)

    def _claim(self):
        from backend.flow.plugins.components.collections.mysql.revoke.mysql_dts_migrate_revoke import (
            DeployRow,
            NodeHost,
            claim_cluster_for_cleanup,
        )

        row = DeployRow(
            cluster_name=self.cluster.name,
            bk_biz_id=1,
            deploy_path="/data/dts/dts-lock",
            hosts=(NodeHost(ip="127.0.0.2", bk_cloud_id=0, bk_host_id=102, roles=("master",)),),
            paths=("/data/dts/dts-lock",),
            use_myloader=False,
            myloader_markers=(),
        )
        return claim_cluster_for_cleanup(row, ticket_id=900)

    def _start_race(self, first, second):
        locked, release, second_started = Event(), Event(), Event()

        def run_first():
            close_old_connections()
            try:
                with transaction.atomic():
                    MysqlDtsCluster.objects.select_for_update().get(id=self.cluster.id)
                    result = first()
                    locked.set()
                    if not release.wait(10):
                        raise TimeoutError("test did not release DTS cluster lock")
                    return result
            finally:
                connections.close_all()

        def run_second():
            close_old_connections()
            try:
                second_started.set()
                return second()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(run_first)
            try:
                self.assertTrue(locked.wait(10))
                second_future = executor.submit(run_second)
                self.assertTrue(second_started.wait(10))
            finally:
                release.set()
            first_future.result(timeout=10)
            return second_future.result(timeout=10)

    @skipUnlessDBFeature("has_select_for_update")
    def test_reservation_wins_and_cleanup_does_not_claim_cluster(self):
        self.assertFalse(self._start_race(self._reserve, self._claim))
        self.cluster.refresh_from_db()
        self.assertEqual(self.cluster.status, "running")
        self.assertEqual(MysqlDtsInfo.objects.get(ticket_id=901).dts_cluster_id, self.cluster.id)

    @skipUnlessDBFeature("has_select_for_update")
    def test_cleanup_wins_and_new_reservation_is_rejected(self):
        with self.assertRaises(ClusterExclusiveOperateException):
            self._start_race(self._claim, self._reserve)
        self.cluster.refresh_from_db()
        self.assertEqual(self.cluster.status, "destroying")
        self.assertFalse(MysqlDtsInfo.objects.filter(ticket_id=901).exists())


class FetchClusterIdsSourceClusterIdsTest(TestCase):
    def test_fetch_source_cluster_ids_key(self):
        ids = fetch_cluster_ids({"source_cluster_ids": [1, 2]})
        self.assertEqual(sorted(ids), [1, 2])
