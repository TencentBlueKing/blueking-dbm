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

from django.test import SimpleTestCase, TestCase

from backend.db_meta.models.mysql_dts import MysqlDtsInfo, MysqlDtsStatus
from backend.flow.plugins.components.collections.mysql.dts.migrate.cutover_meta import MysqlDtsCutoverMetaService
from backend.flow.utils.mysql.dts.context import MysqlDtsTransData


class CutoverMetaResolvePositionTest(SimpleTestCase):
    def _service(self):
        return MysqlDtsCutoverMetaService()

    def test_prefer_nonempty_kwargs(self):
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "trans_data": MysqlDtsTransData(cutover_position={"task_name": "from-trans"}),
        }.get(key)
        snap = self._service()._resolve_position_snapshot(
            data, {"position_snapshot": {"task_name": "from-kwargs", "sources": []}}
        )
        self.assertEqual(snap["task_name"], "from-kwargs")

    def test_read_trans_data_when_kwargs_empty(self):
        position = {
            "task_name": "mysql-dts-1",
            "stopped_at": "2026-08-11T00:00:00Z",
            "sources": [{"source_name": "src1", "master_binlog": "(binlog.000001, 100)"}],
        }
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "trans_data": MysqlDtsTransData(cutover_position=position),
        }.get(key)
        snap = self._service()._resolve_position_snapshot(data, {})
        self.assertEqual(snap, position)

    def test_empty_kwargs_dict_falls_back_to_trans_data(self):
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "trans_data": MysqlDtsTransData(cutover_position={"task_name": "via-trans"}),
        }.get(key)
        snap = self._service()._resolve_position_snapshot(data, {"position_snapshot": {}})
        self.assertEqual(snap["task_name"], "via-trans")


class CutoverMetaExecuteTest(TestCase):
    def setUp(self):
        self.ticket_id = 99001
        self.task_name = "mysql-dts-cutover-meta-ut"
        MysqlDtsInfo.objects.create(
            bk_biz_id=3,
            source_cluster_ids=[1],
            target_cluster_id=2,
            dts_cluster_id=0,
            migrate_type="mysql_to_mysql",
            ticket_id=self.ticket_id,
            root_id="root-cutover-meta",
            status=MysqlDtsStatus.FullOnline.value,
            dts_task_id=self.task_name,
            dts_task_config_snapshot={},
            creator="tester",
            updater="tester",
        )

    def _run(self, *, position: dict):
        service = MysqlDtsCutoverMetaService()
        service.log_info = MagicMock()
        service.log_warning = MagicMock()
        service.log_error = MagicMock()
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": {"ticket_id": self.ticket_id, "task_name": self.task_name},
            "global_data": {},
            "trans_data": MysqlDtsTransData(cutover_position=position),
        }.get(key)
        ok = service._execute(data, parent_data=None)
        self.assertTrue(ok)
        return MysqlDtsInfo.objects.get(ticket_id=self.ticket_id, dts_task_id=self.task_name)

    def test_persists_cutover_position_from_trans_data(self):
        position = {
            "task_name": self.task_name,
            "sources": [{"source_name": "src1", "syncer_binlog": "(binlog.000001, 99)"}],
        }
        info = self._run(position=position)
        self.assertEqual(info.status, MysqlDtsStatus.Disconnected.value)
        self.assertEqual(info.dts_task_config_snapshot.get("cutover_position"), position)


class CutoverSubflowWiringTest(SimpleTestCase):
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cutover_subflow.resolve_dts_master_exec_target")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cutover_subflow.build_dts_cutover_payload")
    def test_actuator_act_writes_cutover_position_var(self, mock_payload, mock_exec):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cutover_subflow import mysql_dts_cutover_subflow
        from backend.flow.plugins.components.collections.mysql.dts.migrate.cutover_meta import (
            MysqlDtsCutoverMetaComponent,
        )
        from backend.flow.plugins.components.collections.mysql.exec_actuator_script import (
            ExecuteDBActuatorScriptComponent,
        )
        from backend.flow.utils.mysql.dts.context import MysqlDtsCutoverSubflowInput
        from backend.flow.utils.mysql.dts.migrate_plan import DtsTaskConfig, DtsTaskSpec, SourceSpec, SyncScope

        mock_exec.return_value = {"bk_cloud_id": 0, "ip": "127.0.0.1"}
        mock_payload.return_value = {}
        acts = []

        class FakeSub:
            def add_act(self, **kwargs):
                acts.append(kwargs)

            def build_sub_process(self, *a, **k):
                return self

        with patch(
            "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cutover_subflow.SubBuilder",
            return_value=FakeSub(),
        ):
            mysql_dts_cutover_subflow(
                inp=MysqlDtsCutoverSubflowInput(
                    root_id="r1",
                    bk_biz_id=3,
                    ticket_id=1,
                    master_addr="127.0.0.1:8261",
                    task_name="t1",
                    deploy_path="/data/dts/x",
                    dts_cluster_id=1,
                ),
                task_spec=DtsTaskSpec(
                    task_name="t1",
                    target_cluster_id=2,
                    sources=[SourceSpec(cluster_id=1, source_name="s1", sync_scope=SyncScope(do_dbs=["db"]))],
                    dts_task_config=DtsTaskConfig(),
                ),
                migrate_plan=SimpleNamespace(),
                dts_user="u",
                dts_password="p",
            )

        actuator = next(a for a in acts if a["act_component_code"] == ExecuteDBActuatorScriptComponent.code)
        self.assertEqual(actuator["write_payload_var"], MysqlDtsTransData.get_cutover_position_var_name())
        meta_act = next(a for a in acts if a["act_component_code"] == MysqlDtsCutoverMetaComponent.code)
        self.assertNotIn("position_snapshot", meta_act.get("kwargs") or {})
