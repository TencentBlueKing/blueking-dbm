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
from django.test import TestCase

from backend.db_meta.exceptions import ClusterExclusiveOperateException
from backend.db_meta.models.mysql_dts import MysqlDtsInfo, MysqlDtsStatus
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
                ticket_type=TicketType.MYSQL_TO_MYSQL_MIGRATE.value,
                details={"cluster_id": 20},
            )

    def test_no_overlap_passes(self):
        """AE4：活跃仅占用源 20；新单据仅含源 10 且目标不冲突 → 通过。"""
        self._create_active(source_cluster_ids=[20], target_cluster_id=300, ticket_id=1)
        MysqlDtsInfo.dts_info_clusive(
            ticket_id=2,
            ticket_type=TicketType.MYSQL_TO_MYSQL_MIGRATE.value,
            details={"cluster_id": 10, "target_cluster_id": 400},
        )

    def test_target_conflict_raises(self):
        self._create_active(source_cluster_ids=[10], target_cluster_id=300, ticket_id=1)
        with self.assertRaises(ClusterExclusiveOperateException):
            MysqlDtsInfo.dts_info_clusive(
                ticket_id=2,
                ticket_type=TicketType.MYSQL_TO_MYSQL_MIGRATE.value,
                details={"cluster_id": 99, "target_cluster_id": 300},
            )

    def test_same_ticket_excluded(self):
        self._create_active(source_cluster_ids=[10, 20], target_cluster_id=300, ticket_id=9)
        MysqlDtsInfo.dts_info_clusive(
            ticket_id=9,
            ticket_type=TicketType.MYSQL_TO_MYSQL_MIGRATE.value,
            details={"cluster_id": 20, "target_cluster_id": 300},
        )

    def test_full_online_raises(self):
        """FullOnline 为进行中状态，应触发互斥。"""
        self._create_active(source_cluster_ids=[10], target_cluster_id=300, ticket_id=874)
        with self.assertRaises(ClusterExclusiveOperateException):
            MysqlDtsInfo.dts_info_clusive(
                ticket_id=877,
                ticket_type=TicketType.MYSQL_TO_MYSQL_MIGRATE.value,
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
                ticket_type=TicketType.MYSQL_TO_MYSQL_MIGRATE.value,
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
            ticket_type=TicketType.MYSQL_TO_MYSQL_MIGRATE.value,
            details={"cluster_id": 10, "target_cluster_id": 300},
        )

    def test_check_exclusive_and_reserve_creates_todo(self):
        details = {
            "dts_resource": {"mode": "use_existing", "cluster_id": 1},
            "migrate": {
                "topology": "one_to_one",
                "one_to_one": {
                    "task_name": "mysql-dts-900-10-300",
                    "source": {"cluster_id": 10, "sync_scope": {"do_dbs": ["db_a"]}},
                    "target": {"cluster_id": 300},
                },
            },
            "task": {"task_mode": "all"},
        }
        MysqlDtsInfo.check_exclusive_and_reserve(
            ticket_id=900,
            ticket_type=TicketType.MYSQL_TO_MYSQL_MIGRATE.value,
            details=details,
            bk_biz_id=1,
            migrate_type="mysql_to_mysql",
            creator="tester",
        )
        row = MysqlDtsInfo.objects.get(ticket_id=900, dts_task_id="mysql-dts-900-10-300")
        self.assertEqual(row.status, MysqlDtsStatus.ToDo.value)
        self.assertEqual(row.source_cluster_ids, [10])
        self.assertEqual(row.target_cluster_id, 300)

    def test_check_exclusive_and_reserve_blocks_second_ticket(self):
        details_a = {
            "dts_resource": {"mode": "use_existing", "cluster_id": 1},
            "migrate": {
                "topology": "one_to_one",
                "one_to_one": {
                    "task_name": "mysql-dts-901-10-300",
                    "source": {"cluster_id": 10, "sync_scope": {"do_dbs": ["db_a"]}},
                    "target": {"cluster_id": 300},
                },
            },
            "task": {"task_mode": "all"},
        }
        details_b = {
            "dts_resource": {"mode": "use_existing", "cluster_id": 1},
            "migrate": {
                "topology": "one_to_one",
                "one_to_one": {
                    "task_name": "mysql-dts-902-10-400",
                    "source": {"cluster_id": 10, "sync_scope": {"do_dbs": ["db_a"]}},
                    "target": {"cluster_id": 400},
                },
            },
            "task": {"task_mode": "all"},
        }
        MysqlDtsInfo.check_exclusive_and_reserve(
            ticket_id=901,
            ticket_type=TicketType.MYSQL_TO_MYSQL_MIGRATE.value,
            details=details_a,
            bk_biz_id=1,
            migrate_type="mysql_to_mysql",
        )
        with self.assertRaises(ClusterExclusiveOperateException):
            MysqlDtsInfo.check_exclusive_and_reserve(
                ticket_id=902,
                ticket_type=TicketType.MYSQL_TO_MYSQL_MIGRATE.value,
                details=details_b,
                bk_biz_id=1,
                migrate_type="mysql_to_mysql",
            )
        # 冲突回滚：第二单不应留下 ToDo
        self.assertFalse(MysqlDtsInfo.objects.filter(ticket_id=902).exists())


class FetchClusterIdsSourceClusterIdsTest(TestCase):
    def test_fetch_source_cluster_ids_key(self):
        ids = fetch_cluster_ids({"source_cluster_ids": [1, 2]})
        self.assertEqual(sorted(ids), [1, 2])
