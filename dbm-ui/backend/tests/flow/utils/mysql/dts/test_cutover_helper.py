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
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.utils.mysql.dts.cutover_helper import (
    build_dts_cutover_payload,
    merge_task_sync_scopes,
    sync_scope_to_dict,
)
from backend.flow.utils.mysql.dts.migrate_plan import DtsTaskConfig, DtsTaskSpec, SourceSpec, SyncScope


class CutoverHelperTest(SimpleTestCase):
    def test_sync_scope_to_dict_compact(self):
        scope = SyncScope(do_dbs=["db1"], do_tables=[{"db": "db1", "table": "t1"}])
        d = sync_scope_to_dict(scope)
        self.assertEqual(d["do_dbs"], ["db1"])
        self.assertNotIn("lock_tables", d)

    def test_merge_task_sync_scopes_from_first_source(self):
        task = DtsTaskSpec(
            task_name="task-a",
            target_cluster_id=2,
            sources=[
                SourceSpec(
                    cluster_id=1,
                    source_name="src1",
                    sync_scope=SyncScope(do_dbs=["app"]),
                )
            ],
            dts_task_config=DtsTaskConfig(),
        )
        self.assertEqual(merge_task_sync_scopes(task)["do_dbs"], ["app"])

    @patch("backend.flow.utils.mysql.dts.cutover_helper.Cluster.objects.get")
    @patch("backend.flow.utils.mysql.dts.cutover_helper.resolve_source_endpoint", return_value=("127.0.0.10", 20000))
    def test_build_payload_has_sync_scope_no_lock_tables(self, _resolve, mock_get):
        mock_get.return_value = MagicMock()
        task = DtsTaskSpec(
            task_name="task-a",
            target_cluster_id=2,
            sources=[
                SourceSpec(
                    cluster_id=1,
                    source_name="src1",
                    sync_scope=SyncScope(do_dbs=["app"], do_tables=[{"db": "app", "table": "*"}]),
                )
            ],
            dts_task_config=DtsTaskConfig(),
        )
        payload = build_dts_cutover_payload(
            master_addr="127.0.0.2:18301",
            deploy_path="/data/dts/demo",
            task_name="task-a",
            task_spec=task,
            dts_user="dts_migrate_x",
            dts_password="secret",
            checksum_passed=True,
        )
        self.assertEqual(payload["dts_master_addr"], "127.0.0.2:18301")
        self.assertIn("sync_scope", payload)
        self.assertIn("api_timeout_sec", payload)
        self.assertTrue(payload["checksum_passed"])
        self.assertFalse(payload["skip_checksum"])
        self.assertNotIn("dmctl_timeout_sec", payload)
        self.assertNotIn("lock_tables", payload)
        self.assertNotIn("target_endpoints", payload)
        self.assertEqual(len(payload["source_endpoints"]), 1)
        self.assertEqual(payload["source_endpoints"][0]["host"], "127.0.0.10")
        self.assertIn("sync_scope", payload["source_endpoints"][0])

    def test_build_payload_requires_master_addr(self):
        task = DtsTaskSpec(
            task_name="t",
            target_cluster_id=2,
            sources=[SourceSpec(cluster_id=1, source_name="s", sync_scope=SyncScope(do_dbs=["a"]))],
        )
        with self.assertRaises(ValueError):
            build_dts_cutover_payload(
                master_addr="",
                task_name="t",
                task_spec=task,
                dts_user="u",
                dts_password="p",
                checksum_passed=True,
            )

    def test_build_payload_requires_checksum_or_skip(self):
        task = DtsTaskSpec(
            task_name="t",
            target_cluster_id=2,
            sources=[SourceSpec(cluster_id=1, source_name="s", sync_scope=SyncScope(do_dbs=["a"]))],
        )
        with self.assertRaises(ValueError):
            build_dts_cutover_payload(
                master_addr="127.0.0.2:18301",
                task_name="t",
                task_spec=task,
                dts_user="u",
                dts_password="p",
                checksum_passed=False,
                skip_checksum=False,
            )
