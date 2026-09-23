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
from backend.ticket.constants import FlowType, TicketFlowStatus, TicketType
from backend.ticket.flow_manager.inner import InnerFlow
from backend.ticket.models import Flow, Ticket

_MIGRATE_DETAILS = {
    "dts_resource": {"mode": "use_existing", "dts_cluster_id": 1},
    "migrate": {
        "topology": "one_to_one",
        "one_to_one": {
            "task_name": "mysql-dts-release-10-300",
            "source": {"cluster_id": 10, "sync_scope": {"db_patterns": ["db_a"], "table_patterns": ["*"]}},
            "target": {"cluster_id": 300},
        },
    },
    "task": {"task_mode": "all"},
}


class MysqlDtsTodoReleaseTest(TestCase):
    def _ticket(self, ticket_type, details=None):
        return Ticket.objects.create(
            bk_biz_id=1,
            ticket_type=ticket_type,
            creator="tester",
            updater="tester",
            remark="dts todo release",
            details=details or {},
        )

    def _flow(self, ticket):
        return Flow.objects.create(
            ticket=ticket,
            flow_type=FlowType.INNER_FLOW,
            flow_alias="inner",
            flow_obj_id="root-not-created",
            details={},
            status=TicketFlowStatus.RUNNING,
            context={},
        )

    def _row(self, ticket_id, status, source_cluster_id, target_cluster_id, dts_task_id):
        return MysqlDtsInfo.objects.create(
            bk_biz_id=1,
            source_cluster_ids=[source_cluster_id],
            target_cluster_id=target_cluster_id,
            ticket_id=ticket_id,
            status=status,
            dts_task_id=dts_task_id,
            creator="tester",
            updater="tester",
        )

    def test_revoke_without_pipeline_releases_only_todo(self):
        for ticket_type in (
            TicketType.MYSQL_DTS_DATA_MIGRATE,
            TicketType.MYSQL_HA_TO_CLUSTER_MIGRATE,
            TicketType.MYSQL_DTS_DATA_MIGRATE_RENAME,
        ):
            with self.subTest(ticket_type=ticket_type):
                ticket = self._ticket(ticket_type)
                flow = self._flow(ticket)
                todo = self._row(ticket.id, MysqlDtsStatus.ToDo.value, 10, 300, f"todo-{ticket.id}")
                online = self._row(ticket.id, MysqlDtsStatus.FullOnline.value, 11, 301, f"online-{ticket.id}")
                done = self._row(ticket.id, MysqlDtsStatus.Disconnected.value, 12, 302, f"done-{ticket.id}")
                other = self._row(ticket.id + 100000, MysqlDtsStatus.ToDo.value, 13, 303, f"other-{ticket.id}")

                InnerFlow(flow)._revoke("tester", "stop")
                InnerFlow(flow)._revoke("tester", "stop")

                todo.refresh_from_db()
                online.refresh_from_db()
                done.refresh_from_db()
                other.refresh_from_db()
                self.assertEqual(todo.status, MysqlDtsStatus.Terminated.value)
                self.assertEqual(online.status, MysqlDtsStatus.FullOnline.value)
                self.assertEqual(done.status, MysqlDtsStatus.Disconnected.value)
                self.assertEqual(other.status, MysqlDtsStatus.ToDo.value)
                MysqlDtsInfo.dts_info_clusive(
                    ticket_id=ticket.id + 1,
                    ticket_type=TicketType.MYSQL_DTS_DATA_MIGRATE.value,
                    details={"cluster_id": 10, "target_cluster_id": 300},
                )
                with self.assertRaises(ClusterExclusiveOperateException):
                    MysqlDtsInfo.dts_info_clusive(
                        ticket_id=ticket.id + 1,
                        ticket_type=TicketType.MYSQL_DTS_DATA_MIGRATE.value,
                        details={"cluster_id": 11, "target_cluster_id": 301},
                    )

    def test_revoke_other_ticket_type_keeps_todo(self):
        ticket = self._ticket(TicketType.MYSQL_SINGLE_APPLY)
        flow = self._flow(ticket)
        todo = self._row(ticket.id, MysqlDtsStatus.ToDo.value, 20, 400, f"keep-{ticket.id}")

        InnerFlow(flow)._revoke("tester", "stop")

        todo.refresh_from_db()
        self.assertEqual(todo.status, MysqlDtsStatus.ToDo.value)

    def test_run_failure_after_reserve_releases_todo(self):
        ticket = self._ticket(TicketType.MYSQL_DTS_DATA_MIGRATE, details=_MIGRATE_DETAILS)
        flow = self._flow(ticket)

        InnerFlow(flow).run()

        row = MysqlDtsInfo.objects.get(ticket_id=ticket.id)
        self.assertEqual(row.status, MysqlDtsStatus.Terminated.value)
        flow.refresh_from_db()
        self.assertEqual(flow.status, TicketFlowStatus.FAILED)
        MysqlDtsInfo.dts_info_clusive(
            ticket_id=ticket.id + 1,
            ticket_type=TicketType.MYSQL_DTS_DATA_MIGRATE.value,
            details={"cluster_id": 10, "target_cluster_id": 300},
        )
