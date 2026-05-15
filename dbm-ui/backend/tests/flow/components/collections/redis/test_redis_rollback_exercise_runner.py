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
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from bamboo_engine.api import EngineAPIResult

from backend.flow.consts import StateType
from backend.flow.plugins.components.collections.redis.redis_rollback_exercise import (
    CHILD2RUNNER_CACHE_PREFIX,
    RedisExerciseBestEffortCleanupService,
    RedisExerciseFlowRunnerService,
)


class FakeData:
    def __init__(self, outputs=None, inputs=None):
        self.outputs = SimpleNamespace(**(outputs or {}))
        self.inputs = SimpleNamespace(**(inputs or {}))

    def get_one_of_outputs(self, key):
        return getattr(self.outputs, key, None)

    def get_one_of_inputs(self, key):
        return getattr(self.inputs, key, None)


def _build_schedule_data(start_delta_seconds=10, polling_timeout=3600, child_root_id="child_root_id"):
    return FakeData(
        outputs={
            "child_root_id": child_root_id,
            "start_time": (datetime.now() - timedelta(seconds=start_delta_seconds)).isoformat(),
            "polling_timeout": polling_timeout,
            "output_var": "rollback_code",
        }
    )


def _build_execute_kwargs(**overrides):
    defaults = {
        "flow_identifier": "redis_data_structure",
        "flow_data": {"infos": []},
        "report_id": 1,
        "flow_id_field": "rollback_flow_obj_id",
        "polling_timeout": 3600,
        "output_var": "rollback_code",
        "polling_interval": 10,
    }
    defaults.update(overrides)
    return defaults


# ==================== Schedule: callback fast-path ====================


@patch(
    "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.FlowTree.objects.get",
    return_value=SimpleNamespace(status=StateType.FINISHED),
)
def test_callback_data_terminal_finishes_early_skipping_flowtree_poll(_mock_flowtree_get):
    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = _build_schedule_data()

    service._schedule_inner_captured(
        data,
        parent_data=None,
        callback_data={"child_root_id": "child_root_id", "child_state": StateType.FINISHED},
    )

    assert data.outputs.rollback_code == 0
    service.finish_schedule.assert_called_once()
    _mock_flowtree_get.assert_not_called()


@pytest.mark.parametrize("child_state", [StateType.FAILED, StateType.REVOKED])
@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.FlowTree.objects.get")
def test_callback_failed_or_revoked_sets_code_1(mock_flowtree_get, child_state):
    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = _build_schedule_data()

    service._schedule_inner_captured(
        data,
        parent_data=None,
        callback_data={"child_root_id": "child_root_id", "child_state": child_state},
    )

    assert data.outputs.rollback_code == 1
    service.finish_schedule.assert_called_once()
    mock_flowtree_get.assert_not_called()


@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.FlowTree.objects.get")
def test_callback_without_child_root_id_falls_through_to_poll(mock_flowtree_get):
    """callback_data missing child_root_id should warn and fall through to FlowTree polling."""
    mock_flowtree_get.return_value = SimpleNamespace(status=StateType.FINISHED)
    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = _build_schedule_data()

    service._schedule_inner_captured(data, parent_data=None, callback_data={"child_state": StateType.FINISHED})

    assert data.outputs.rollback_code == 0
    mock_flowtree_get.assert_called_once_with(root_id="child_root_id")


@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.FlowTree.objects.get")
def test_callback_mismatched_child_root_id_falls_through_to_poll(mock_flowtree_get):
    """callback_data with wrong child_root_id should warn and fall through to FlowTree polling."""
    mock_flowtree_get.return_value = SimpleNamespace(status=StateType.FINISHED)
    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = _build_schedule_data()

    service._schedule_inner_captured(
        data, parent_data=None, callback_data={"child_root_id": "wrong_id", "child_state": StateType.FINISHED}
    )

    assert data.outputs.rollback_code == 0
    mock_flowtree_get.assert_called_once_with(root_id="child_root_id")


# ==================== Schedule: FlowTree polling ====================


@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.FlowTree.objects.get")
def test_flowtree_terminal_finishes_schedule(mock_flowtree_get):
    mock_flowtree_get.return_value = SimpleNamespace(status=StateType.FINISHED)

    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = _build_schedule_data()

    service._schedule_inner_captured(data, parent_data=None)

    assert data.outputs.rollback_code == 0
    service.finish_schedule.assert_called_once()
    mock_flowtree_get.assert_called_once_with(root_id="child_root_id")


@pytest.mark.parametrize("status", [StateType.FAILED, StateType.REVOKED])
@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.FlowTree.objects.get")
def test_flowtree_failed_or_revoked_sets_code_1(mock_flowtree_get, status):
    mock_flowtree_get.return_value = SimpleNamespace(status=status)
    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = _build_schedule_data()

    service._schedule_inner_captured(data, parent_data=None)

    assert data.outputs.rollback_code == 1
    service.finish_schedule.assert_called_once()


@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.FlowTree.objects.get")
def test_flowtree_running_keeps_polling(mock_flowtree_get):
    """RUNNING child should not finish the schedule (keeps polling)."""
    mock_flowtree_get.return_value = SimpleNamespace(status=StateType.RUNNING)
    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = _build_schedule_data()

    result = service._schedule_inner_captured(data, parent_data=None)

    assert result is True
    service.finish_schedule.assert_not_called()


@patch(
    "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.FlowTree.objects.get",
    side_effect=Exception("DoesNotExist"),
)
def test_flowtree_does_not_exist_keeps_polling(_mock):
    """When FlowTree is not yet created, the schedule should keep polling."""
    from backend.flow.models import FlowTree

    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = _build_schedule_data()

    with patch(
        "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.FlowTree.objects.get",
        side_effect=FlowTree.DoesNotExist,
    ):
        result = service._schedule_inner_captured(data, parent_data=None)

    assert result is True
    service.finish_schedule.assert_not_called()


# ==================== Schedule: edge cases ====================


def test_schedule_no_child_root_id_finishes_immediately():
    """When child_root_id is absent (execute failed early), schedule should finish."""
    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = FakeData(outputs={"output_var": "rollback_code"})

    result = service._schedule_inner_captured(data, parent_data=None)

    assert result is True
    service.finish_schedule.assert_called_once()


def test_schedule_missing_start_time_sets_code_1():
    """Missing start_time should produce an error with code=1."""
    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = FakeData(outputs={"child_root_id": "child_root_id", "output_var": "rollback_code"})

    service._schedule_inner_captured(data, parent_data=None)

    assert data.outputs.rollback_code == 1
    service.finish_schedule.assert_called_once()


# ==================== Schedule: timeout ====================


@patch(
    "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.BambooEngine.revoke_pipeline",
    return_value=EngineAPIResult(result=True, data={}, message=""),
)
def test_timeout_revoke_child_and_fail(_mock_revoke):
    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = _build_schedule_data(start_delta_seconds=20, polling_timeout=10)

    service._schedule_inner_captured(data, parent_data=None)

    assert data.outputs.rollback_code == 1
    service.finish_schedule.assert_called_once()
    _mock_revoke.assert_called_once()


@patch(
    "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.BambooEngine.revoke_pipeline",
    return_value=EngineAPIResult(result=False, data={}, message="revoke failed"),
)
def test_timeout_revoke_failure_still_sets_code_1(mock_revoke):
    """Even if revoke fails, the runner should still set code=1 and finish."""
    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = _build_schedule_data(start_delta_seconds=20, polling_timeout=10)

    service._schedule_inner_captured(data, parent_data=None)

    assert data.outputs.rollback_code == 1
    service.finish_schedule.assert_called_once()
    mock_revoke.assert_called_once()


@patch(
    "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.BambooEngine.revoke_pipeline",
    side_effect=Exception("network error"),
)
def test_timeout_revoke_exception_still_sets_code_1(mock_revoke):
    """Even if revoke raises an exception, the runner should still set code=1 and finish."""
    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = _build_schedule_data(start_delta_seconds=20, polling_timeout=10)

    service._schedule_inner_captured(data, parent_data=None)

    assert data.outputs.rollback_code == 1
    service.finish_schedule.assert_called_once()


# ==================== Execute ====================


def test_execute_stores_child_flow_id_in_report():
    service = RedisExerciseFlowRunnerService()
    data = FakeData()
    data.outputs = SimpleNamespace()
    data.get_one_of_inputs = MagicMock(return_value=_build_execute_kwargs())

    service._runtime_attrs = {"id": "runner_node_id", "root_pipeline_id": "parent_root_id"}

    with patch(
        "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.generate_root_id",
        return_value="child_root_id",
    ), patch(
        "backend.flow.plugins.components.collections.redis."
        "redis_rollback_exercise.RedisDataStructureFlow.redis_data_structure_flow"
    ), patch(
        "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.Report.objects.filter"
    ) as mock_filter, patch(
        "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.cache.set"
    ) as mock_cache_set:
        mock_filter.return_value.update = MagicMock()
        result = service._execute_inner_captured(data, parent_data=None)

    assert result is True
    mock_filter.return_value.update.assert_called_once_with(rollback_flow_obj_id="child_root_id")
    mock_cache_set.assert_called_once_with(
        f"{CHILD2RUNNER_CACHE_PREFIX}:child_root_id",
        {"runner_node_id": "runner_node_id", "parent_root_id": "parent_root_id"},
        3600,
    )


def test_execute_unknown_flow_identifier_sets_code_1():
    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = FakeData()
    data.outputs = SimpleNamespace()
    data.get_one_of_inputs = MagicMock(return_value=_build_execute_kwargs(flow_identifier="nonexistent_flow"))
    service._runtime_attrs = {"id": "n", "root_pipeline_id": "p"}

    result = service._execute_inner_captured(data, parent_data=None)

    assert result is True
    assert data.outputs.rollback_code == 1
    service.finish_schedule.assert_called_once()


def test_execute_flow_launch_exception_sets_code_1():
    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    data = FakeData()
    data.outputs = SimpleNamespace()
    data.get_one_of_inputs = MagicMock(return_value=_build_execute_kwargs())
    service._runtime_attrs = {"id": "n", "root_pipeline_id": "p"}

    with patch(
        "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.generate_root_id",
        return_value="child_root_id",
    ), patch(
        "backend.flow.plugins.components.collections.redis." "redis_rollback_exercise.RedisDataStructureFlow",
        side_effect=RuntimeError("flow init failed"),
    ):
        result = service._execute_inner_captured(data, parent_data=None)

    assert result is True
    assert data.outputs.rollback_code == 1
    service.finish_schedule.assert_called_once()


def test_execute_without_report_id_skips_report_update():
    """When report_id is absent, the report update step should be skipped."""
    service = RedisExerciseFlowRunnerService()
    data = FakeData()
    data.outputs = SimpleNamespace()
    data.get_one_of_inputs = MagicMock(return_value=_build_execute_kwargs(report_id=None, flow_id_field=None))
    service._runtime_attrs = {"id": "runner_node_id", "root_pipeline_id": "parent_root_id"}

    with patch(
        "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.generate_root_id",
        return_value="child_root_id",
    ), patch(
        "backend.flow.plugins.components.collections.redis."
        "redis_rollback_exercise.RedisDataStructureFlow.redis_data_structure_flow"
    ), patch(
        "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.Report.objects.filter"
    ) as mock_filter, patch(
        "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.cache.set"
    ):
        result = service._execute_inner_captured(data, parent_data=None)

    assert result is True
    mock_filter.return_value.update.assert_not_called()


# ==================== Best-effort cleanup guards ====================


def _cleanup_service():
    service = RedisExerciseBestEffortCleanupService()
    service.log_info = MagicMock()
    service.log_warning = MagicMock()
    return service


def _cleanup_global_data():
    return {
        "uid": 123,
        "bk_biz_id": 3,
        "infos": [
            {
                "cluster_id": 101,
                "instance_ip": "1.1.1.4",
                "instance_port": 30000,
                "redis": [{"ip": "1.1.1.3"}],
            }
        ],
    }


def _storage_instance(port, cluster_ids=None):
    cluster = SimpleNamespace(values_list=MagicMock(return_value=cluster_ids or []))
    return SimpleNamespace(port=port, cluster=cluster)


def _rollback_task(temp_range=None, prod_range=None, pairs=None):
    return SimpleNamespace(
        id=1,
        temp_instance_range=temp_range if temp_range is not None else ["1.1.1.3:30000"],
        prod_instance_range=prod_range if prod_range is not None else ["1.1.1.4:30000"],
        prod_temp_instance_pairs=pairs if pairs is not None else [["1.1.1.4:30000", "1.1.1.3:30000"]],
    )


@patch(
    "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.TbTendisRollbackTasks.objects.filter"
)
@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.StorageInstance.objects.filter")
@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.Cluster.objects.get")
def test_cleanup_targets_use_rollback_task_ports_not_all_storage_ports(
    mock_cluster_get, mock_storage_filter, mock_task_filter
):
    mock_cluster_get.return_value = SimpleNamespace(id=101, bk_cloud_id=0)
    mock_storage_filter.return_value = [_storage_instance(30000), _storage_instance(39999)]
    mock_task_filter.return_value = [
        _rollback_task(
            temp_range=["1.1.1.3:30001", "2.2.2.2:30000", "1.1.1.3:30000"],
            prod_range=["1.1.1.4:30000", "1.1.1.4:30001"],
            pairs=[
                ["1.1.1.4:30000", "1.1.1.3:30000"],
                ["1.1.1.4:30001", "1.1.1.3:30001"],
                ["1.1.1.4:30002", "2.2.2.2:30000"],
            ],
        )
    ]

    cleanup_hosts = _cleanup_service()._collect_cleanup_hosts(_cleanup_global_data())

    assert cleanup_hosts == [{"ip": "1.1.1.3", "bk_cloud_id": 0, "ports": [30000, 30001]}]
    mock_task_filter.assert_called_once_with(related_rollback_bill_id=123, bk_biz_id=3, prod_cluster_id=101)


@patch(
    "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.TbTendisRollbackTasks.objects.filter"
)
@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.StorageInstance.objects.filter")
@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.Cluster.objects.get")
def test_cleanup_targets_allow_expected_source_cluster_binding(
    mock_cluster_get, mock_storage_filter, mock_task_filter
):
    mock_cluster_get.return_value = SimpleNamespace(id=101, bk_cloud_id=0)
    mock_storage_filter.return_value = [_storage_instance(30000, cluster_ids=[101])]
    mock_task_filter.return_value = [_rollback_task()]

    cleanup_hosts = _cleanup_service()._collect_cleanup_hosts(_cleanup_global_data())

    assert cleanup_hosts == [{"ip": "1.1.1.3", "bk_cloud_id": 0, "ports": [30000]}]


@patch(
    "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.TbTendisRollbackTasks.objects.filter"
)
@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.StorageInstance.objects.filter")
@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.Cluster.objects.get")
def test_cleanup_targets_skip_unexpected_cluster_bound_storage(
    mock_cluster_get, mock_storage_filter, mock_task_filter
):
    mock_cluster_get.return_value = SimpleNamespace(id=101, bk_cloud_id=0)
    mock_storage_filter.return_value = [_storage_instance(30000, cluster_ids=[202])]
    mock_task_filter.return_value = [_rollback_task()]

    cleanup_hosts = _cleanup_service()._collect_cleanup_hosts(_cleanup_global_data())

    assert cleanup_hosts == []
    mock_task_filter.assert_not_called()


@patch(
    "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.TbTendisRollbackTasks.objects.filter"
)
@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.StorageInstance.objects.filter")
@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.Cluster.objects.get")
def test_cleanup_targets_skip_when_no_matching_rollback_task(mock_cluster_get, mock_storage_filter, mock_task_filter):
    mock_cluster_get.return_value = SimpleNamespace(id=101, bk_cloud_id=0)
    mock_storage_filter.return_value = []
    mock_task_filter.return_value = [
        _rollback_task(temp_range=["2.2.2.2:30000"], pairs=[["1.1.1.4:30000", "2.2.2.2:30000"]])
    ]

    cleanup_hosts = _cleanup_service()._collect_cleanup_hosts(_cleanup_global_data())

    assert cleanup_hosts == []


@patch(
    "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.TbTendisRollbackTasks.objects.filter"
)
@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.StorageInstance.objects.filter")
@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.Cluster.objects.get")
def test_cleanup_targets_exclude_source_prod_addresses(mock_cluster_get, mock_storage_filter, mock_task_filter):
    mock_cluster_get.return_value = SimpleNamespace(id=101, bk_cloud_id=0)
    mock_storage_filter.return_value = []
    mock_task_filter.return_value = [
        _rollback_task(
            temp_range=["1.1.1.3:30000", "1.1.1.3:30001"],
            prod_range=["1.1.1.4:30000", "1.1.1.3:30001"],
            pairs=[
                ["1.1.1.4:30000", "1.1.1.3:30000"],
                ["1.1.1.3:30001", "1.1.1.3:30001"],
            ],
        )
    ]

    cleanup_hosts = _cleanup_service()._collect_cleanup_hosts(_cleanup_global_data())

    assert cleanup_hosts == [{"ip": "1.1.1.3", "bk_cloud_id": 0, "ports": [30000]}]


@patch(
    "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.TbTendisRollbackTasks.objects.filter"
)
@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.StorageInstance.objects.filter")
@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.Cluster.objects.get")
def test_cleanup_targets_require_prod_temp_pairs(mock_cluster_get, mock_storage_filter, mock_task_filter):
    mock_cluster_get.return_value = SimpleNamespace(id=101, bk_cloud_id=0)
    mock_storage_filter.return_value = []
    mock_task_filter.return_value = [_rollback_task(pairs=[])]

    cleanup_hosts = _cleanup_service()._collect_cleanup_hosts(_cleanup_global_data())

    assert cleanup_hosts == []


def test_cleanup_script_removes_only_allowlisted_work_dirs():
    script = RedisExerciseBestEffortCleanupService._build_cleanup_script(
        [{"ip": "1.1.1.3", "bk_cloud_id": 0, "ports": [30000, 30001]}]
    )

    assert "30000 30001" in script
    assert "39999" not in script
    assert "/data/redis/*" not in script
    assert "/data1/redis/*" not in script
    assert 'pkill -f "$inst_dir"' in script
    assert "pkill -f redis-server || true" not in script
    assert "pkill -f predixy || true" not in script
    assert "tendis[a-z_+-]*" in script
    assert "/data/predixy/[0-9]*" in script
    assert "/data1/predixy/[0-9]*" in script
    assert "twemproxy-0.2.4" in script
    assert 'grep -RqsE "$backend_pattern" "$proxy_dir"' in script
    assert "Unsafe proxy work dir $proxy_dir, skip" in script
    assert 'rm -rf -- "$proxy_dir"' in script
    assert "Unsafe redis work dir $inst_dir, skip" in script
    assert 'rm -rf -- "$inst_dir"' in script
    assert "lsof" not in script
    assert "Allowlisted redis process still exists" in script
    assert 'case "$current_ip" in' in script
