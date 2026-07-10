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
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import TestCase

from backend.db_meta.models.mysql_dts import MysqlDtsInfo, MysqlDtsStatus
from backend.flow.plugins.components.collections.mysql.dts.migrate.update_meta import MysqlDtsUpdateMetaService
from backend.flow.utils.mysql.dts.migrate_plan import (
    DtsTaskConfig,
    DtsTaskSpec,
    SourceSpec,
    SyncScope,
    dts_task_spec_to_dict,
)


class MysqlDtsUpdateMetaServiceTest(TestCase):
    def _make_service(self):
        service = MysqlDtsUpdateMetaService()
        service.log_info = MagicMock()
        return service

    def _run(self, sources, *, target_cluster_id=200):
        task_spec = DtsTaskSpec(
            task_name="mysql-dts-test-task",
            target_cluster_id=target_cluster_id,
            sources=sources,
            dts_task_config=DtsTaskConfig(),
        )
        migrate_context = SimpleNamespace(
            registered_source_names=[],
            dts_cluster_id=1,
            dts_user="",
            grant_hosts=[],
            grant_targets=[],
            created_dts_info_ids=[],
        )
        trans_data = SimpleNamespace(migrate_context=migrate_context)
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": {
                "bk_biz_id": 1,
                "task_spec": dts_task_spec_to_dict(task_spec),
                "migrate_type": "mysql_to_mysql",
                "migrate_topology": "many_to_one",
                "ticket_id": 100,
                "root_id": "root-1",
                "task_name": task_spec.task_name,
                "dts_cluster_id": 1,
                "creator": "tester",
            },
            "global_data": {"root_id": "root-1"},
            "trans_data": trans_data,
        }.get(key)
        # pipeline DataObject 同时支持 outputs["k"]= 与 outputs.attr =
        data.outputs = MagicMock()
        ok = self._make_service()._execute(data, parent_data=None)
        self.assertTrue(ok)
        return MysqlDtsInfo.objects.get(id=data.outputs.dts_info_id), migrate_context

    def test_many_to_one_writes_all_source_ids(self):
        """AE1：两源一目标 → source_cluster_ids == [src1, src2]。"""
        sources = [
            SourceSpec(cluster_id=101, source_name="s1", sync_scope=SyncScope(do_dbs=["db_a"])),
            SourceSpec(cluster_id=102, source_name="s2", sync_scope=SyncScope(do_dbs=["db_b"])),
        ]
        row, unused_ctx = self._run(sources)
        self.assertEqual(row.source_cluster_ids, [101, 102])
        self.assertEqual(row.target_cluster_id, 200)
        self.assertEqual(row.sync_scope_snapshot, asdict(sources[0].sync_scope))

    def test_one_source_writes_single_id(self):
        """AE2：单源 → 长度为 1。"""
        sources = [SourceSpec(cluster_id=101, source_name="s1", sync_scope=SyncScope(do_dbs=["db_a"]))]
        row, unused_ctx = self._run(sources, target_cluster_id=201)
        self.assertEqual(row.source_cluster_ids, [101])

    def test_empty_sources_writes_empty_list(self):
        row, unused_ctx = self._run([])
        self.assertEqual(row.source_cluster_ids, [])
        self.assertEqual(row.sync_scope_snapshot, {})

    def test_promotes_todo_placeholder_to_full_online(self):
        MysqlDtsInfo.objects.create(
            bk_biz_id=1,
            source_cluster_ids=[101],
            target_cluster_id=200,
            ticket_id=100,
            status=MysqlDtsStatus.ToDo.value,
            dts_task_id="mysql-dts-test-task",
            creator="tester",
            updater="tester",
        )
        row, unused_ctx = self._run(
            [SourceSpec(cluster_id=101, source_name="s1", sync_scope=SyncScope(do_dbs=["db_a"]))]
        )
        self.assertEqual(MysqlDtsInfo.objects.filter(ticket_id=100, dts_task_id="mysql-dts-test-task").count(), 1)
        self.assertEqual(row.status, MysqlDtsStatus.FullOnline.value)
        self.assertEqual(row.source_cluster_ids, [101])
