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

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums.instance_status import MongoDBStorageInstanceStatus
from backend.db_report.enums import ReportStateType

pytestmark = pytest.mark.django_db


def _capture_promql(module, condition):
    captured = {"promql": ""}

    def _mock_unify_query(params, use_admin=True):
        captured["promql"] = params["query_configs"][0]["promql"]
        return {"series": []}

    with patch.object(module.BKMonitorV3Api, "unify_query", side_effect=_mock_unify_query):
        module._instant_fetch_metric(condition, retry_times=1, sleep_time=0)
    return captured["promql"]


class TestInstantFetchMetricConditionBuild:
    def test_instance_list_escape_regex_meta(self, sync_instance_status_module):
        promql = _capture_promql(
            sync_instance_status_module,
            {"instance": ["127.0.0.1:27017", "127.0.0.2:27017"]},
        )
        assert 'instance=~"^(127\\\\.0\\\\.0\\\\.1\\\\-27017|127\\\\.0\\\\.0\\\\.2\\\\-27017)$"' in promql

    def test_instance_string_keeps_exact_match_selector(self, sync_instance_status_module):
        promql = _capture_promql(sync_instance_status_module, {"instance": "127.0.0.1:27017"})
        assert 'instance="127.0.0.1-27017"' in promql
        assert 'instance=~"' not in promql

    def test_other_keys_behavior_unchanged(self, sync_instance_status_module):
        promql = _capture_promql(
            sync_instance_status_module,
            {"cluster_domain": ["a.b", "c-d"], "shard": "rs0"},
        )
        assert 'cluster_domain=~"^(a.b|c-d)$"' in promql
        assert 'shard="rs0"' in promql


class TestChoosePeerReportedState:
    def test_abnormal_prefers_down(self, sync_instance_status_module):
        chosen = sync_instance_status_module._choose_peer_reported_state(
            {"127.0.0.1:27001": 8, "127.0.0.2:27001": 6},
            peer_min=2,
        )
        assert chosen == MongoDBStorageInstanceStatus.DOWN.value

    def test_abnormal_requires_peer_min(self, sync_instance_status_module):
        assert (
            sync_instance_status_module._choose_peer_reported_state(
                {"127.0.0.1:27001": 8},
                peer_min=2,
            )
            is None
        )

    def test_healthy_majority_not_used_for_discover(self, sync_instance_status_module):
        assert (
            sync_instance_status_module._choose_peer_reported_state(
                {"127.0.0.1:27001": 1, "127.0.0.2:27001": 1, "127.0.0.3:27001": 2},
                peer_min=2,
            )
            is None
        )

    def test_single_down_with_healthy_peer_not_enough(self, sync_instance_status_module):
        assert (
            sync_instance_status_module._choose_peer_reported_state(
                {"127.0.0.1:27001": 8, "127.0.0.2:27001": 2},
                peer_min=2,
            )
            is None
        )


class TestAggregatePeerTargets:
    def test_dead_secondary_aggregated(self, sync_instance_status_module):
        obs = [
            SimpleNamespace(
                name="127.0.0.3:27001",
                reporter="127.0.0.1:27001",
                state=8,
                cluster_domain="m1.example.db",
                shard="rs0",
                set_name="rs0",
            ),
            SimpleNamespace(
                name="127.0.0.3:27001",
                reporter="127.0.0.2:27001",
                state=8,
                cluster_domain="m1.example.db",
                shard="rs0",
                set_name="rs0",
            ),
        ]
        targets = sync_instance_status_module._aggregate_peer_targets(obs)
        assert len(targets) == 1
        assert targets[0]["ip"] == "127.0.0.3"
        assert targets[0]["port"] == 27001
        assert targets[0]["state_code"] == MongoDBStorageInstanceStatus.DOWN.value
        assert targets[0]["cluster_domain"] == "m1.example.db"
        assert targets[0]["shard"] == "rs0"

    def test_healthy_observations_not_aggregated(self, sync_instance_status_module):
        obs = [
            SimpleNamespace(
                name="127.0.0.1:27001",
                reporter="127.0.0.2:27001",
                state=1,
                cluster_domain="m1.example.db",
                shard="rs0",
                set_name="rs0",
            ),
            SimpleNamespace(
                name="127.0.0.1:27001",
                reporter="127.0.0.3:27001",
                state=1,
                cluster_domain="m1.example.db",
                shard="rs0",
                set_name="rs0",
            ),
        ]
        assert sync_instance_status_module._aggregate_peer_targets(obs) == []


class TestFetchPeerMemberTargets:
    def test_filters_by_cluster_domain(self, sync_instance_status_module):
        obs = [
            SimpleNamespace(
                name="127.0.0.3:27001",
                reporter="127.0.0.1:27001",
                state=8,
                cluster_domain="m1.keep.db",
                shard="rs0",
                set_name="rs0",
            ),
            SimpleNamespace(
                name="127.0.0.3:27001",
                reporter="127.0.0.2:27001",
                state=8,
                cluster_domain="m1.keep.db",
                shard="rs0",
                set_name="rs0",
            ),
            SimpleNamespace(
                name="127.0.0.9:27001",
                reporter="127.0.0.1:27001",
                state=8,
                cluster_domain="m1.drop.db",
                shard="rs0",
                set_name="rs0",
            ),
            SimpleNamespace(
                name="127.0.0.9:27001",
                reporter="127.0.0.2:27001",
                state=8,
                cluster_domain="m1.drop.db",
                shard="rs0",
                set_name="rs0",
            ),
        ]
        with patch(
            "backend.db_services.mongodb.autofix.metrics.query_peer_member_states",
            return_value=obs,
        ):
            targets = sync_instance_status_module.SyncStorageInstanceStatusTask().fetch_peer_member_targets(
                cluster_domain="m1.keep.db"
            )
        assert len(targets) == 1
        assert targets[0]["cluster_domain"] == "m1.keep.db"

    def test_unavailable_metrics_returns_empty(self, sync_instance_status_module):
        with patch(
            "backend.db_services.mongodb.autofix.metrics.query_peer_member_states",
            return_value=None,
        ):
            targets = sync_instance_status_module.SyncStorageInstanceStatusTask().fetch_peer_member_targets()
        assert targets == []


class TestSyncStorageInstanceStatusTaskStart:
    def test_cluster_domain_and_bk_biz_id_mutually_exclusive(self, sync_instance_status_module):
        with pytest.raises(ValueError, match="mutually exclusive"):
            sync_instance_status_module.SyncStorageInstanceStatusTask().start(
                cluster_domain="mongo.example.db",
                bk_biz_id=1,
            )

    def test_acquire_lock_false_skips_redis_lock(self, sync_instance_status_module):
        task = sync_instance_status_module.SyncStorageInstanceStatusTask()
        with patch.object(sync_instance_status_module.RedisConn, "set") as redis_set, patch.object(
            task, "fetch_peer_member_targets", return_value=[]
        ), patch.object(task, "apply_peer_member_updates", return_value=0), patch.object(
            task, "_list_shard_keys_for_scope", return_value=[]
        ), patch.object(
            task, "check_and_update_shards"
        ), patch.object(
            task, "fetch_changed_instance_list", return_value=[]
        ), patch.object(
            sync_instance_status_module, "RecordBatchOps"
        ) as record_ops_cls:
            record_ops_cls.return_value.bulk_create = MagicMock()
            task.start(cluster_domain="mongo.example.db", acquire_lock=False)

        redis_set.assert_not_called()

    def test_applies_peer_overlay_after_shard_my_state(self, sync_instance_status_module):
        task = sync_instance_status_module.SyncStorageInstanceStatusTask()
        order = []

        def _shards(*_args, **_kwargs):
            order.append("shards")

        def _peer(*_args, **_kwargs):
            order.append("peer")
            return 0

        def _instances(*_args, **_kwargs):
            order.append("instances")

        targets = [
            {
                "cluster_domain": "mongo.example.db",
                "shard": "rs0",
                "ip": "127.0.0.3",
                "port": 27001,
                "state_code": MongoDBStorageInstanceStatus.DOWN.value,
                "state": "DOWN",
            }
        ]

        with patch.object(sync_instance_status_module.RedisConn, "set"), patch.object(
            task, "fetch_peer_member_targets", return_value=targets
        ), patch.object(task, "apply_peer_member_updates", side_effect=_peer), patch.object(
            task, "check_and_update_shards", side_effect=_shards
        ), patch.object(
            task, "fetch_changed_instance_list", return_value=[]
        ), patch.object(
            task, "check_and_update_instance", side_effect=_instances
        ), patch.object(
            sync_instance_status_module, "RecordBatchOps"
        ) as record_ops_cls:
            record_ops_cls.return_value.bulk_create = MagicMock()
            task.start(cluster_domain="mongo.example.db", acquire_lock=False)

        assert order == ["shards", "instances", "peer"]


class TestSyncInstanceStatusHelpers:
    def test_group_shards_by_cluster_deduplicates(self, sync_instance_status_module):
        grouped = sync_instance_status_module._group_shards_by_cluster(
            ["cluster-a:rs0", "cluster-a:rs1", "cluster-a:rs0", "cluster-b:rs0"]
        )
        assert grouped == {"cluster-a": ["rs0", "rs1"], "cluster-b": ["rs0"]}

    def test_chunk_list(self, sync_instance_status_module):
        assert sync_instance_status_module._chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]

    def test_shard_list_condition_build(self, sync_instance_status_module):
        promql = _capture_promql(
            sync_instance_status_module,
            {"cluster_domain": "mongo.example", "shard": ["rs0", "rs1"]},
        )
        assert 'cluster_domain="mongo.example"' in promql
        assert 'shard=~"^(rs0|rs1)$"' in promql


class TestInstantFetchMetricLogging:
    def test_skipped_series_emits_single_dev_debug_not_warning(self, sync_instance_status_module, caplog):
        caplog.set_level(logging.DEBUG)
        series = [
            {"datapoints": [], "dimensions": {"bk_target_ip": "127.0.0.1", "instance_port": 27017}},
            {
                "datapoints": [[1]],
                "dimensions": {
                    "bk_target_ip": "127.0.0.2",
                    "instance_port": 27017,
                    "instance_role": "m1",
                    "cluster_domain": "c.example",
                },
            },
        ]

        with patch.object(
            sync_instance_status_module.BKMonitorV3Api, "unify_query", return_value={"series": series}
        ), patch.object(sync_instance_status_module, "dev_debug") as mock_dev_debug:
            result = sync_instance_status_module._instant_fetch_metric({"shard": "rs0"}, retry_times=1, sleep_time=0)

        assert result == []
        warning_msgs = [record.message for record in caplog.records if record.levelno == logging.WARNING]
        assert not any("_instant_fetch_metric" in msg for msg in warning_msgs)
        assert any(
            "empty_datapoints=1" in str(call.args[0]) and "empty_shard=1" in str(call.args[0])
            for call in mock_dev_debug.call_args_list
        )

    def test_retry_intermediate_failure_uses_dev_debug(self, sync_instance_status_module, caplog):
        caplog.set_level(logging.DEBUG)

        def _raise_then_succeed(params, use_admin=True):
            if not hasattr(_raise_then_succeed, "called"):
                _raise_then_succeed.called = True
                raise RuntimeError("temporary network error")
            return {"series": []}

        with patch.object(
            sync_instance_status_module.BKMonitorV3Api, "unify_query", side_effect=_raise_then_succeed
        ), patch.object(sync_instance_status_module, "dev_debug") as mock_dev_debug:
            result = sync_instance_status_module._instant_fetch_metric({"shard": "rs0"}, retry_times=2, sleep_time=0)

        assert result == []
        error_msgs = [record.message for record in caplog.records if record.levelno == logging.ERROR]
        assert not error_msgs
        assert any("query metric error (retry 1/2)" in str(call.args[0]) for call in mock_dev_debug.call_args_list)


def _make_mock_ext(ip="127.0.0.1", port=27017, state_code=2, state="SECONDARY", shard_name="rs0"):
    cluster = SimpleNamespace(
        id=100,
        bk_biz_id=1,
        bk_cloud_id=0,
        immute_domain="mongo.example.db",
        cluster_type="MongoReplicaSet",
    )
    machine = SimpleNamespace(ip=ip)
    # Mirror StorageInstance.cluster M2M: RelatedManager-like .first()
    cluster_manager = SimpleNamespace(first=lambda: cluster)
    instance = SimpleNamespace(port=port, machine=machine, cluster=cluster_manager)
    return SimpleNamespace(state=state, state_code=state_code, shard_name=shard_name, instance=instance)


class TestInstanceChangeReport:
    def test_make_change_report_fields(self, sync_instance_status_module):
        ext = _make_mock_ext(state_code=2, state="SECONDARY")
        report = sync_instance_status_module._make_change_report(
            ext,
            report_day=20260706,
            sub_type="sync_storage_instance_status",
            shard="rs0",
            old_state="SECONDARY",
            old_state_code=2,
            new_state="PRIMARY",
            new_state_code=1,
        )
        assert report.subtype == "sync_storage_instance_status"
        assert report.report_day == 20260706
        assert report.instance == "127.0.0.1:27017"
        assert report.shard == "rs0"
        assert report.msg == "SECONDARY(2) -> PRIMARY(1)"
        assert report.state == ReportStateType.WARNING.value
        assert report.status is False

    def test_make_change_report_skips_when_cluster_missing(self, sync_instance_status_module):
        ext = _make_mock_ext()
        ext.instance.cluster = SimpleNamespace(first=lambda: None)
        report = sync_instance_status_module._make_change_report(
            ext,
            report_day=20260706,
            sub_type="sync_storage_instance_status",
            shard="rs0",
            old_state="SECONDARY",
            old_state_code=2,
            new_state="PRIMARY",
            new_state_code=1,
        )
        assert report is None

    def test_resolve_report_state_abnormal(self, sync_instance_status_module):
        state, status = sync_instance_status_module._resolve_report_state(MongoDBStorageInstanceStatus.UNKNOWN.value)
        assert state == ReportStateType.ABNORMAL.value
        assert status is False

    def test_check_and_update_instance_appends_on_change(self, sync_instance_status_module):
        ext = _make_mock_ext(state_code=1, state="PRIMARY")
        record_batch_ops = MagicMock()
        instance_list = [
            {
                "instance": "127.0.0.1:27017",
                "old_state_code": 1,
                "new_state_code": 2,
                "new_state": "SECONDARY",
                "new_shard_name": "rs0",
            }
        ]

        with patch.object(
            sync_instance_status_module, "_load_ext_map_by_ip_ports", return_value={"127.0.0.1:27017": ext}
        ), patch.object(sync_instance_status_module, "_bulk_update_ext_records", return_value=1):
            sync_instance_status_module.SyncStorageInstanceStatusTask().check_and_update_instance(
                instance_list, record_batch_ops, 20260706
            )

        record_batch_ops.append.assert_called_once()
        report = record_batch_ops.append.call_args[0][0]
        assert report.msg == "PRIMARY(1) -> SECONDARY(2)"

    def test_check_and_update_instance_skips_unchanged(self, sync_instance_status_module):
        record_batch_ops = MagicMock()
        instance_list = [
            {
                "instance": "127.0.0.1:27017",
                "old_state_code": 2,
                "new_state_code": 2,
                "new_state": "SECONDARY",
                "new_shard_name": "rs0",
            }
        ]

        sync_instance_status_module.SyncStorageInstanceStatusTask().check_and_update_instance(
            instance_list, record_batch_ops, 20260706
        )
        record_batch_ops.append.assert_not_called()

    def test_check_and_update_shards_skips_unchanged(self, sync_instance_status_module):
        ext = _make_mock_ext(state_code=2, state="SECONDARY")
        record_batch_ops = MagicMock()
        metric_val = [
            {
                "bk_target_ip": "127.0.0.1",
                "instance_port": 27017,
                "value": 2,
                "shard": "rs0",
            }
        ]

        with patch.object(sync_instance_status_module, "_instant_fetch_metric", return_value=metric_val), patch.object(
            sync_instance_status_module, "_load_ext_map_by_ip_ports", return_value={"127.0.0.1:27017": ext}
        ), patch.object(sync_instance_status_module, "_bulk_update_ext_records", return_value=0) as bulk_update:
            sync_instance_status_module.SyncStorageInstanceStatusTask().check_and_update_shards(
                ["mongo.example.db:rs0"], record_batch_ops, 20260706
            )

        record_batch_ops.append.assert_not_called()
        bulk_update.assert_called_once_with([])

    def test_check_and_update_shards_appends_when_state_code_changes(self, sync_instance_status_module):
        ext = _make_mock_ext(state_code=1, state="PRIMARY")
        record_batch_ops = MagicMock()
        metric_val = [
            {
                "bk_target_ip": "127.0.0.1",
                "instance_port": 27017,
                "value": 2,
                "shard": "rs0",
            }
        ]

        with patch.object(sync_instance_status_module, "_instant_fetch_metric", return_value=metric_val), patch.object(
            sync_instance_status_module, "_load_ext_map_by_ip_ports", return_value={"127.0.0.1:27017": ext}
        ), patch.object(sync_instance_status_module, "_bulk_update_ext_records", return_value=1):
            sync_instance_status_module.SyncStorageInstanceStatusTask().check_and_update_shards(
                ["mongo.example.db:rs0"], record_batch_ops, 20260706
            )

        record_batch_ops.append.assert_called_once()
        report = record_batch_ops.append.call_args[0][0]
        assert report.msg == "PRIMARY(1) -> SECONDARY(2)"


class TestSyncInstanceStatusFlapAndRestore:
    def test_missing_my_state_keeps_down(self, sync_instance_status_module):
        ext = SimpleNamespace(
            state_code=MongoDBStorageInstanceStatus.DOWN.value,
            instance=SimpleNamespace(machine=SimpleNamespace(ip="127.0.0.1"), port=27017),
        )
        chain = MagicMock()
        chain.exclude.return_value = chain
        chain.select_related.return_value = chain
        chain.distinct.return_value = chain
        chain.count.return_value = 1
        chain.iterator.return_value = [ext]
        with patch.object(
            sync_instance_status_module.MongoDBStorageInstanceExt.objects, "filter", return_value=chain
        ), patch.object(sync_instance_status_module, "_instant_fetch_metric", return_value=[]):
            changed = sync_instance_status_module.SyncStorageInstanceStatusTask().fetch_changed_instance_list()
        assert changed == []

    def test_missing_my_state_marks_primary_unknown(self, sync_instance_status_module):
        ext = SimpleNamespace(
            state_code=MongoDBStorageInstanceStatus.PRIMARY.value,
            instance=SimpleNamespace(machine=SimpleNamespace(ip="127.0.0.1"), port=27017),
        )
        chain = MagicMock()
        chain.exclude.return_value = chain
        chain.select_related.return_value = chain
        chain.distinct.return_value = chain
        chain.count.return_value = 1
        chain.iterator.return_value = [ext]
        with patch.object(
            sync_instance_status_module.MongoDBStorageInstanceExt.objects, "filter", return_value=chain
        ), patch.object(sync_instance_status_module, "_instant_fetch_metric", return_value=[]):
            changed = sync_instance_status_module.SyncStorageInstanceStatusTask().fetch_changed_instance_list()
        assert len(changed) == 1
        assert changed[0]["new_state_code"] == MongoDBStorageInstanceStatus.UNKNOWN.value
        assert changed[0]["new_state"] == "UNKNOWN"

    def test_peer_overlay_does_not_downgrade_down_to_unknown(self, sync_instance_status_module):
        ext = _make_mock_ext(state_code=MongoDBStorageInstanceStatus.DOWN.value, state="DOWN")
        record_batch_ops = MagicMock()
        targets = [
            {
                "ip": "127.0.0.1",
                "port": 27017,
                "state_code": MongoDBStorageInstanceStatus.UNKNOWN.value,
                "state": "UNKNOWN",
                "shard": "rs0",
                "peer_count": 2,
            }
        ]
        with patch.object(
            sync_instance_status_module, "_load_ext_map_by_ip_ports", return_value={"127.0.0.1:27017": ext}
        ), patch.object(sync_instance_status_module, "_bulk_update_ext_records", return_value=0) as bulk_update:
            updated = sync_instance_status_module.SyncStorageInstanceStatusTask().apply_peer_member_updates(
                targets, record_batch_ops, 20260706
            )
        assert updated == 0
        bulk_update.assert_called_once_with([])
        record_batch_ops.append.assert_not_called()
        assert ext.state_code == MongoDBStorageInstanceStatus.DOWN.value

    def test_shard_refresh_collects_unavailable_secondary(self, sync_instance_status_module):
        ext = _make_mock_ext(state_code=2, state="SECONDARY")
        ext.instance.id = 9
        ext.instance.status = "unavailable"
        bucket = set()
        metric_val = [
            {
                "bk_target_ip": "127.0.0.1",
                "instance_port": 27017,
                "value": 2,
                "shard": "rs0",
            }
        ]
        with patch.object(sync_instance_status_module, "_instant_fetch_metric", return_value=metric_val), patch.object(
            sync_instance_status_module, "_load_ext_map_by_ip_ports", return_value={"127.0.0.1:27017": ext}
        ), patch.object(sync_instance_status_module, "_bulk_update_ext_records", return_value=0):
            sync_instance_status_module.SyncStorageInstanceStatusTask().check_and_update_shards(
                ["mongo.example.db:rs0"], MagicMock(), 20260706, secondary_status_ids=bucket
            )
        assert bucket == {9}

    def test_state_change_queues_sync_log(self, sync_instance_status_module):
        ext = _make_mock_ext(state_code=8, state="DOWN")
        ext.instance.id = 9
        ext.instance.status = "unavailable"
        record_batch_ops = MagicMock()
        instance_list = [
            {
                "instance": "127.0.0.1:27017",
                "old_state_code": 8,
                "new_state_code": 2,
                "new_state": "SECONDARY",
                "new_shard_name": "rs0",
            }
        ]
        bucket = set()
        with patch.object(
            sync_instance_status_module, "_load_ext_map_by_ip_ports", return_value={"127.0.0.1:27017": ext}
        ), patch.object(sync_instance_status_module, "_bulk_update_ext_records", return_value=1), patch.object(
            sync_instance_status_module, "_bulk_create_sync_logs"
        ) as bulk_logs:
            sync_instance_status_module.SyncStorageInstanceStatusTask().check_and_update_instance(
                instance_list, record_batch_ops, 20260706, secondary_status_ids=bucket
            )
        assert bucket == {9}
        rows = bulk_logs.call_args[0][0]
        assert rows[0].source == "stale_my_state"
        assert rows[0].message == "DOWN(8) -> SECONDARY(2)"
        assert rows[0].instance_id == 9

    def test_restore_secondary_sets_running(self, sync_instance_status_module):
        cluster = SimpleNamespace(id=100, bk_biz_id=3, bk_cloud_id=0, immute_domain="mongo.example.db")
        ext = SimpleNamespace(state="SECONDARY", state_code=2, shard_name="rs0", instance=None)
        inst = SimpleNamespace(
            id=9,
            status="unavailable",
            port=27017,
            machine=SimpleNamespace(ip="127.0.0.1", bk_host_id=3),
            cluster=SimpleNamespace(first=lambda: cluster),
            mongodbstorageinstanceext=ext,
        )
        ext.instance = inst
        select_qs = MagicMock()
        select_qs.select_related.return_value.prefetch_related.return_value = [inst]
        update_qs = MagicMock()
        update_qs.update.return_value = 1

        def _filter(*_args, **kwargs):
            if "mongodbstorageinstanceext__state_code" in kwargs:
                return select_qs
            return update_qs

        with patch.object(
            sync_instance_status_module.StorageInstance.objects, "filter", side_effect=_filter
        ), patch.object(sync_instance_status_module, "_bulk_create_sync_logs") as bulk_logs:
            updated = sync_instance_status_module.SyncStorageInstanceStatusTask().restore_secondary_instance_status(
                {9}
            )
        assert updated == 1
        update_qs.update.assert_called_once_with(status="running")
        row = bulk_logs.call_args[0][0][0]
        assert row.source == "secondary_status"
        assert row.old_status == "unavailable"
        assert row.new_status == "running"
        assert row.message == "status unavailable -> running"

    def test_restore_empty_skips_query(self, sync_instance_status_module):
        with patch.object(sync_instance_status_module.StorageInstance.objects, "filter") as objects_filter:
            updated = sync_instance_status_module.SyncStorageInstanceStatusTask().restore_secondary_instance_status(
                set()
            )
        assert updated == 0
        objects_filter.assert_not_called()

    def test_restore_skips_operating_instances(self, sync_instance_status_module):
        """operating 是流程占用，成员即使是 SECONDARY 也不改回 running。"""
        select_qs = MagicMock()
        select_qs.select_related.return_value.prefetch_related.return_value = []

        def _filter(*_args, **kwargs):
            assert kwargs.get("status") == "unavailable"
            return select_qs

        with patch.object(sync_instance_status_module.StorageInstance.objects, "filter", side_effect=_filter):
            updated = sync_instance_status_module.SyncStorageInstanceStatusTask().restore_secondary_instance_status(
                {9}
            )
        assert updated == 0
