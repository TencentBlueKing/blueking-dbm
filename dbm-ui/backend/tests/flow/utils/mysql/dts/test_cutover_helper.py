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

from django.test import SimpleTestCase

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.flow.utils.mysql.dts.cutover_helper import (
    build_dts_cutover_payload,
    build_source_endpoints_for_cutover,
    merge_task_sync_scopes,
    sync_scope_to_dict,
)
from backend.flow.utils.mysql.dts.migrate_plan import DtsTaskConfig, DtsTaskSpec, SourceSpec, SyncScope


class CutoverHelperTest(SimpleTestCase):
    def test_sync_scope_to_dict_compact(self):
        scope = SyncScope(do_dbs=["db1"], do_tables=[{"schema": "*", "table": "*"}])
        d = sync_scope_to_dict(scope)
        self.assertEqual(d["do_dbs"], ["db1"])
        self.assertEqual(d["do_tables"], [{"schema": "*", "table": "*"}])
        self.assertNotIn("lock_tables", d)

    def test_merge_task_sync_scopes_from_first_source(self):
        task = DtsTaskSpec(
            task_name="task-a",
            target_cluster_id=2,
            sources=[
                SourceSpec(
                    cluster_id=1,
                    source_name="src1",
                    sync_scope=SyncScope(do_dbs=["app"], do_tables=[{"schema": "*", "table": "*"}]),
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
                    sync_scope=SyncScope(do_dbs=["app"], do_tables=[{"schema": "*", "table": "*"}]),
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
        self.assertNotIn("replica", payload["source_endpoints"][0])
        self.assertNotIn("backup_locale", payload["source_endpoints"][0])
        self.assertIn("sync_scope", payload["source_endpoints"][0])

    def test_build_payload_requires_master_addr(self):
        task = DtsTaskSpec(
            task_name="t",
            target_cluster_id=2,
            sources=[
                SourceSpec(
                    cluster_id=1,
                    source_name="s",
                    sync_scope=SyncScope(do_dbs=["a"], do_tables=[{"schema": "*", "table": "*"}]),
                )
            ],
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
            sources=[
                SourceSpec(
                    cluster_id=1,
                    source_name="s",
                    sync_scope=SyncScope(do_dbs=["a"], do_tables=[{"schema": "*", "table": "*"}]),
                )
            ],
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


class _RoleQS:
    def __init__(self, items):
        self._items = list(items)

    def filter(self, **kwargs):
        items = self._items
        if "instance_role" in kwargs:
            wanted = getattr(kwargs["instance_role"], "value", kwargs["instance_role"])
            items = [item for item in items if getattr(item.instance_role, "value", item.instance_role) == wanted]
        if "is_stand_by" in kwargs:
            items = [item for item in items if item.is_stand_by is kwargs["is_stand_by"]]
        if "status" in kwargs:
            wanted = getattr(kwargs["status"], "value", kwargs["status"])
            items = [item for item in items if getattr(item.status, "value", item.status) == wanted]
        return _RoleQS(items)

    def order_by(self, *fields):
        items = list(self._items)
        for field in reversed(fields):
            name = str(field)[1:] if str(field).startswith("-") else str(field)
            items.sort(key=lambda item, field_name=name: getattr(item, field_name))
        return _RoleQS(items)

    def first(self):
        return self._items[0] if self._items else None


def _role_instance(ip, port, role, ins_id, is_stand_by=False):
    return SimpleNamespace(
        id=ins_id,
        machine=SimpleNamespace(ip=ip),
        port=port,
        instance_role=role,
        is_stand_by=is_stand_by,
        status="running",
    )


def _ha_cluster():
    cluster = MagicMock()
    cluster.id = 1
    cluster.cluster_type = ClusterType.TenDBHA.value
    cluster.storageinstance_set = _RoleQS(
        [
            _role_instance("127.0.0.10", 20000, InstanceRole.BACKEND_MASTER.value, 1),
            _role_instance("127.0.0.12", 20000, InstanceRole.BACKEND_SLAVE.value, 2, is_stand_by=True),
        ]
    )
    return cluster


def _role_task(backup_locale, task_mode):
    return DtsTaskSpec(
        task_name="task-a",
        target_cluster_id=2,
        sources=[
            SourceSpec(
                cluster_id=1,
                source_name="src1",
                sync_scope=SyncScope(do_dbs=["app"], do_tables=[{"schema": "*", "table": "*"}]),
                backup_locale=backup_locale,
            )
        ],
        dts_task_config=DtsTaskConfig(task_mode=task_mode),
    )


class CutoverSourceRoleTest(SimpleTestCase):
    def _endpoints(self, backup_locale, task_mode):
        with patch(
            "backend.flow.utils.mysql.dts.cutover_helper.Cluster.objects.get",
            return_value=_ha_cluster(),
        ):
            return build_source_endpoints_for_cutover(
                task_spec=_role_task(backup_locale, task_mode),
                dts_user="dts_migrate_x",
                dts_password="secret",
            )

    def test_slave_locks_master_without_replica(self):
        endpoint = self._endpoints("slave", "all")[0]
        self.assertEqual(endpoint["host"], "127.0.0.10")
        self.assertEqual(endpoint["port"], 20000)
        self.assertNotIn("replica", endpoint)
        self.assertEqual(endpoint["user"], "dts_migrate_x")
        self.assertEqual(endpoint["password"], "secret")
        self.assertNotIn("backup_locale", endpoint)

    def test_slave_full_also_locks_master(self):
        endpoint = self._endpoints("slave", "full")[0]
        self.assertEqual((endpoint["host"], endpoint["port"]), ("127.0.0.10", 20000))
        self.assertNotIn("replica", endpoint)
        self.assertNotIn("backup_locale", endpoint)

    def test_master_has_no_replica(self):
        endpoint = self._endpoints("master", "incremental")[0]
        self.assertEqual((endpoint["host"], endpoint["port"]), ("127.0.0.10", 20000))
        self.assertNotIn("replica", endpoint)

    def test_empty_role_has_no_replica(self):
        endpoint = self._endpoints("", "all")[0]
        self.assertEqual((endpoint["host"], endpoint["port"]), ("127.0.0.10", 20000))
        self.assertNotIn("replica", endpoint)
