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
from contextlib import contextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from bamboo_engine.api import EngineAPIResult

from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.db_report.models import RedisRollbackExerciseReport
from backend.flow.consts import StateType
from backend.flow.models import FlowTree
from backend.flow.plugins.components.collections.redis.redis_rollback_exercise import (
    CHILD2RUNNER_CACHE_PREFIX,
    RedisExerciseBestEffortCleanupService,
    RedisExerciseFlowRunnerService,
)

RUNNER_MOD = "backend.flow.plugins.components.collections.redis.redis_rollback_exercise"
EMBED_PATCH = "backend.db_services.redis.rollback.failure_analysis.embed_failed_node_logs"
CHILD_ROOT_ID = "child_root_id"
PROD_INSTANCE_IP = "1.1.1.4"
TEMP_INSTANCE_IP = "1.1.1.3"
_OK_REVOKE = EngineAPIResult(result=True, data={}, message="")
_EMBEDDED_LOGS = "prior logs\nchild failed logs"


class FakeData:
    def __init__(self, outputs=None, inputs=None):
        self.outputs = SimpleNamespace(**(outputs or {}))
        self.inputs = SimpleNamespace(**(inputs or {}))

    def get_one_of_outputs(self, key):
        return getattr(self.outputs, key, None)

    def get_one_of_inputs(self, key):
        return getattr(self.inputs, key, None)


def _build_schedule_data(start_delta_seconds=10, polling_timeout=3600, child_root_id=CHILD_ROOT_ID, preserve=False):
    data = FakeData(
        outputs={
            "child_root_id": child_root_id,
            "start_time": (datetime.now() - timedelta(seconds=start_delta_seconds)).isoformat(),
            "polling_timeout": polling_timeout,
            "output_var": "rollback_code",
            "preserve_scene_on_failure": preserve,
        }
    )
    if preserve:
        data.inputs = SimpleNamespace(kwargs={"report_id": 1, "flow_id_field": "rollback_flow_obj_id"})
    return data


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


def _make_runner():
    service = RedisExerciseFlowRunnerService()
    service.finish_schedule = MagicMock()
    return service


def _schedule(service, data, child_state=None, callback_data=None):
    if child_state is not None:
        callback_data = {"child_root_id": CHILD_ROOT_ID, "child_state": child_state}
    return service._schedule_inner_captured(data, parent_data=None, callback_data=callback_data)


def _execute(kwargs=None):
    service = _make_runner()
    service._runtime_attrs = {"id": "runner_node_id", "root_pipeline_id": "parent_root_id"}
    data = FakeData()
    data.outputs = SimpleNamespace()
    data.get_one_of_inputs = MagicMock(return_value=_build_execute_kwargs(**(kwargs or {})))
    return service, data


@contextmanager
def _patch_child_flow(child_root_id=CHILD_ROOT_ID):
    with patch(f"{RUNNER_MOD}.generate_root_id", return_value=child_root_id), patch(
        f"{RUNNER_MOD}.RedisDataStructureFlow.redis_data_structure_flow"
    ), patch(f"{RUNNER_MOD}.Report.objects.filter") as mock_filter, patch(f"{RUNNER_MOD}.cache.set") as mock_cache_set:
        mock_filter.return_value.update = MagicMock()
        yield mock_filter, mock_cache_set


def _mock_preserved_report():
    report = MagicMock()
    report.task_message = "prior logs"
    return report


def _assert_scene_preserved(result, data, service, mock_revoke, report):
    assert result is False
    assert data.outputs.rollback_code == 1
    service.finish_schedule.assert_not_called()
    mock_revoke.assert_not_called()
    report.mark.assert_called_once()
    assert report.mark.call_args.args[0] == TaskStage.SCENE_PRESERVED


# ==================== Schedule ====================


@pytest.mark.parametrize("via", ["callback", "poll"])
@pytest.mark.parametrize(
    "status, expected_code",
    [
        (StateType.FINISHED, 0),
        (StateType.FAILED, 1),
        (StateType.REVOKED, 1),
    ],
)
@patch(f"{RUNNER_MOD}.FlowTree.objects.get")
def test_schedule_terminal_finishes(mock_flowtree_get, status, expected_code, via):
    mock_flowtree_get.return_value = SimpleNamespace(status=status)
    service = _make_runner()
    data = _build_schedule_data()

    _schedule(service, data, child_state=status if via == "callback" else None)

    assert data.outputs.rollback_code == expected_code
    service.finish_schedule.assert_called_once()
    if via == "callback":
        mock_flowtree_get.assert_not_called()
    else:
        mock_flowtree_get.assert_called_once_with(root_id=CHILD_ROOT_ID)


@pytest.mark.parametrize(
    "callback_data",
    [
        pytest.param({"child_state": StateType.FINISHED}, id="missing_child_root_id"),
        pytest.param({"child_root_id": "wrong_id", "child_state": StateType.FINISHED}, id="mismatched_child_root_id"),
    ],
)
@patch(f"{RUNNER_MOD}.FlowTree.objects.get")
def test_callback_falls_through_to_poll(mock_flowtree_get, callback_data):
    mock_flowtree_get.return_value = SimpleNamespace(status=StateType.FINISHED)
    service = _make_runner()
    data = _build_schedule_data()

    _schedule(service, data, callback_data=callback_data)

    assert data.outputs.rollback_code == 0
    mock_flowtree_get.assert_called_once_with(root_id=CHILD_ROOT_ID)


@pytest.mark.parametrize("preserve", [False, True])
@patch(f"{RUNNER_MOD}.FlowTree.objects.get")
def test_flowtree_running_keeps_polling(mock_flowtree_get, preserve):
    mock_flowtree_get.return_value = SimpleNamespace(status=StateType.RUNNING)
    service = _make_runner()

    result = _schedule(service, _build_schedule_data(preserve=preserve))

    assert result is True
    service.finish_schedule.assert_not_called()


@patch(f"{RUNNER_MOD}.FlowTree.objects.get", side_effect=FlowTree.DoesNotExist)
def test_flowtree_does_not_exist_keeps_polling(_mock):
    service = _make_runner()

    result = _schedule(service, _build_schedule_data())

    assert result is True
    service.finish_schedule.assert_not_called()


def test_schedule_no_child_root_id_finishes_immediately():
    service = _make_runner()
    data = FakeData(outputs={"output_var": "rollback_code"})

    result = _schedule(service, data)

    assert result is True
    service.finish_schedule.assert_called_once()


def test_schedule_missing_start_time_sets_code_1():
    service = _make_runner()
    data = FakeData(outputs={"child_root_id": CHILD_ROOT_ID, "output_var": "rollback_code"})

    _schedule(service, data)

    assert data.outputs.rollback_code == 1
    service.finish_schedule.assert_called_once()


@pytest.mark.parametrize(
    "revoke",
    [
        pytest.param(_OK_REVOKE, id="ok"),
        pytest.param(EngineAPIResult(result=False, data={}, message="revoke failed"), id="failed"),
        pytest.param(Exception("network error"), id="exception"),
    ],
)
def test_timeout_still_sets_code_1(revoke):
    service = _make_runner()
    data = _build_schedule_data(start_delta_seconds=20, polling_timeout=10)
    patch_kwargs = {"side_effect": revoke} if isinstance(revoke, Exception) else {"return_value": revoke}

    with patch(f"{RUNNER_MOD}.BambooEngine.revoke_pipeline", **patch_kwargs) as mock_revoke:
        _schedule(service, data)

    assert data.outputs.rollback_code == 1
    service.finish_schedule.assert_called_once()
    mock_revoke.assert_called_once()


# ==================== Execute ====================


@pytest.mark.parametrize(
    "exec_kwargs, expect_update, expect_revoke_previous",
    [
        pytest.param({}, True, False, id="stores_report_and_cache"),
        pytest.param({"report_id": None, "flow_id_field": None}, False, False, id="no_report_id"),
        pytest.param({"preserve_scene_on_failure": True}, True, True, id="preserve_revokes_previous"),
    ],
)
def test_execute_submits_child_flow(exec_kwargs, expect_update, expect_revoke_previous):
    service, data = _execute(exec_kwargs)
    revoke_previous = f"{RUNNER_MOD}.RedisExerciseFlowRunnerService._revoke_previous_child_pipeline"

    with _patch_child_flow() as (mock_filter, mock_cache_set), patch(revoke_previous) as mock_revoke_previous:
        result = service._execute_inner_captured(data, parent_data=None)

    assert result is True
    if expect_update:
        mock_filter.return_value.update.assert_called_once_with(rollback_flow_obj_id=CHILD_ROOT_ID)
        mock_cache_set.assert_called_once_with(
            f"{CHILD2RUNNER_CACHE_PREFIX}:{CHILD_ROOT_ID}",
            {"runner_node_id": "runner_node_id", "parent_root_id": "parent_root_id"},
            3600,
        )
    else:
        mock_filter.return_value.update.assert_not_called()
    if expect_revoke_previous:
        mock_revoke_previous.assert_called_once_with(1, "rollback_flow_obj_id")
        assert data.outputs.preserve_scene_on_failure is True
    else:
        mock_revoke_previous.assert_not_called()


def test_execute_unknown_flow_identifier_sets_code_1():
    service, data = _execute({"flow_identifier": "nonexistent_flow"})

    result = service._execute_inner_captured(data, parent_data=None)

    assert result is True
    assert data.outputs.rollback_code == 1
    service.finish_schedule.assert_called_once()


def test_execute_flow_launch_exception_sets_code_1():
    service, data = _execute()

    with patch(f"{RUNNER_MOD}.generate_root_id", return_value=CHILD_ROOT_ID), patch(
        f"{RUNNER_MOD}.RedisDataStructureFlow", side_effect=RuntimeError("flow init failed")
    ):
        result = service._execute_inner_captured(data, parent_data=None)

    assert result is True
    assert data.outputs.rollback_code == 1
    service.finish_schedule.assert_called_once()


# ==================== Best-effort cleanup guards ====================


def _assert_cleanup_never_touches_prod(cleanup_hosts):
    prod_hosts = [host for host in cleanup_hosts if host["ip"] == PROD_INSTANCE_IP]
    assert not prod_hosts, f"cleanup must not target prod host {PROD_INSTANCE_IP!r}, got {cleanup_hosts}"


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
                "instance_ip": PROD_INSTANCE_IP,
                "instance_port": 30000,
                "redis": [{"ip": TEMP_INSTANCE_IP}],
            }
        ],
    }


def _storage_instance(port, cluster_ids=None):
    cluster = SimpleNamespace(values_list=MagicMock(return_value=cluster_ids or []))
    return SimpleNamespace(port=port, cluster=cluster)


def _rollback_task(temp_range=None, prod_range=None, pairs=None):
    return SimpleNamespace(
        id=1,
        temp_instance_range=temp_range if temp_range is not None else [f"{TEMP_INSTANCE_IP}:30000"],
        prod_instance_range=prod_range if prod_range is not None else [f"{PROD_INSTANCE_IP}:30000"],
        prod_temp_instance_pairs=pairs
        if pairs is not None
        else [[f"{PROD_INSTANCE_IP}:30000", f"{TEMP_INSTANCE_IP}:30000"]],
    )


def _run_cleanup(*, storage=None, tasks=None, global_data=None):
    service = _cleanup_service()
    gd = global_data if global_data is not None else _cleanup_global_data()
    with patch(f"{RUNNER_MOD}.Cluster.objects.get", return_value=SimpleNamespace(id=101, bk_cloud_id=0)), patch(
        f"{RUNNER_MOD}.StorageInstance.objects.filter", return_value=storage or []
    ), patch(f"{RUNNER_MOD}.TbTendisRollbackTasks.objects.filter") as mock_task_filter:
        mock_task_filter.return_value = tasks if tasks is not None else []
        hosts = service._collect_cleanup_hosts(gd)
        _assert_cleanup_never_touches_prod(hosts)
    return hosts, service, mock_task_filter


def test_cleanup_targets_use_rollback_task_ports_not_all_storage_ports():
    hosts, _, mock_task = _run_cleanup(
        storage=[_storage_instance(30000), _storage_instance(39999)],
        tasks=[
            _rollback_task(
                temp_range=[f"{TEMP_INSTANCE_IP}:30001", "2.2.2.2:30000", f"{TEMP_INSTANCE_IP}:30000"],
                prod_range=[f"{PROD_INSTANCE_IP}:30000", f"{PROD_INSTANCE_IP}:30001"],
                pairs=[
                    [f"{PROD_INSTANCE_IP}:30000", f"{TEMP_INSTANCE_IP}:30000"],
                    [f"{PROD_INSTANCE_IP}:30001", f"{TEMP_INSTANCE_IP}:30001"],
                    [f"{PROD_INSTANCE_IP}:30002", "2.2.2.2:30000"],
                ],
            )
        ],
    )

    assert hosts == [{"ip": TEMP_INSTANCE_IP, "bk_cloud_id": 0, "ports": [30000, 30001]}]
    mock_task.assert_called_once_with(related_rollback_bill_id=123, bk_biz_id=3, prod_cluster_id=101)


@pytest.mark.parametrize(
    "cluster_ids, expected_hosts, task_called",
    [
        pytest.param([101], [{"ip": TEMP_INSTANCE_IP, "bk_cloud_id": 0, "ports": [30000]}], True, id="expected"),
        pytest.param([202], [], False, id="unexpected"),
    ],
)
def test_cleanup_targets_cluster_binding(cluster_ids, expected_hosts, task_called):
    hosts, _, mock_task = _run_cleanup(
        storage=[_storage_instance(30000, cluster_ids=cluster_ids)],
        tasks=[_rollback_task()],
    )

    assert hosts == expected_hosts
    if task_called:
        mock_task.assert_called_once()
    else:
        mock_task.assert_not_called()


def test_cleanup_targets_exclude_source_prod_addresses():
    hosts, _, _ = _run_cleanup(
        tasks=[
            _rollback_task(
                temp_range=[f"{TEMP_INSTANCE_IP}:30000", f"{TEMP_INSTANCE_IP}:30001"],
                prod_range=[f"{PROD_INSTANCE_IP}:30000", f"{TEMP_INSTANCE_IP}:30001"],
                pairs=[
                    [f"{PROD_INSTANCE_IP}:30000", f"{TEMP_INSTANCE_IP}:30000"],
                    [f"{TEMP_INSTANCE_IP}:30001", f"{TEMP_INSTANCE_IP}:30001"],
                ],
            )
        ],
    )

    assert hosts == [{"ip": TEMP_INSTANCE_IP, "bk_cloud_id": 0, "ports": [30000]}]


@pytest.mark.parametrize(
    "tasks, extra_info",
    [
        pytest.param(
            [
                _rollback_task(
                    temp_range=["2.2.2.2:30000"],
                    pairs=[[f"{PROD_INSTANCE_IP}:30000", "2.2.2.2:30000"]],
                )
            ],
            {},
            id="task_for_other_ip",
        ),
        pytest.param([_rollback_task(pairs=[])], {}, id="empty_task_pairs"),
        pytest.param(
            [],
            {"drill_prod_temp_instance_pairs": [[f"{PROD_INSTANCE_IP}:30000", f"{TEMP_INSTANCE_IP}:30000"]]},
            id="explicit_drill_pairs",
        ),
        pytest.param([], {}, id="ticket_instance_fields"),
    ],
)
def test_cleanup_targets_drill_fallback(tasks, extra_info):
    global_data = _cleanup_global_data()
    global_data["infos"][0].update(extra_info)

    hosts, service, _ = _run_cleanup(tasks=tasks, global_data=global_data)

    assert hosts == [{"ip": TEMP_INSTANCE_IP, "bk_cloud_id": 0, "ports": [30000]}]
    service.log_info.assert_any_call(
        f"Using drill ticket pairs fallback for {TEMP_INSTANCE_IP} (no TbTendisRollbackTasks)"
    )


def test_cleanup_targets_task_record_wins_over_drill_fallback():
    global_data = _cleanup_global_data()
    global_data["infos"][0]["drill_prod_temp_instance_pairs"] = [
        [f"{PROD_INSTANCE_IP}:30000", f"{TEMP_INSTANCE_IP}:30000"]
    ]

    hosts, service, _ = _run_cleanup(
        tasks=[
            _rollback_task(
                temp_range=[f"{TEMP_INSTANCE_IP}:30001"],
                prod_range=[f"{PROD_INSTANCE_IP}:30001"],
                pairs=[[f"{PROD_INSTANCE_IP}:30001", f"{TEMP_INSTANCE_IP}:30001"]],
            )
        ],
        global_data=global_data,
    )

    assert hosts == [{"ip": TEMP_INSTANCE_IP, "bk_cloud_id": 0, "ports": [30001]}]
    fallback_calls = [
        str(call) for call in service.log_info.call_args_list if "drill ticket pairs fallback" in str(call)
    ]
    assert fallback_calls == []


def test_cleanup_targets_skip_when_no_task_and_no_drill_pairs():
    hosts, _, _ = _run_cleanup(
        global_data={"uid": 123, "bk_biz_id": 3, "infos": [{"cluster_id": 101, "redis": [{"ip": TEMP_INSTANCE_IP}]}]},
    )

    assert hosts == []


def test_cleanup_script_removes_only_allowlisted_work_dirs():
    cleanup_hosts = [{"ip": TEMP_INSTANCE_IP, "bk_cloud_id": 0, "ports": [30000, 30001]}]
    _assert_cleanup_never_touches_prod(cleanup_hosts)
    script = RedisExerciseBestEffortCleanupService._build_cleanup_script(cleanup_hosts)

    assert TEMP_INSTANCE_IP in script
    assert PROD_INSTANCE_IP not in script
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


# ==================== Preserve scene (error_ignorable=False) ====================


@pytest.mark.parametrize("via", ["callback", "poll"])
@pytest.mark.parametrize("child_state", [StateType.FAILED, StateType.REVOKED])
@patch(EMBED_PATCH, return_value=_EMBEDDED_LOGS)
@patch(f"{RUNNER_MOD}.Report.objects.get")
@patch(f"{RUNNER_MOD}.BambooEngine.revoke_pipeline")
@patch(f"{RUNNER_MOD}.FlowTree.objects.get")
def test_failed_preserve_marks_scene_and_returns_false(
    mock_flowtree_get, mock_revoke, mock_report_get, _mock_embed, child_state, via
):
    mock_flowtree_get.return_value = SimpleNamespace(status=child_state)
    report = _mock_preserved_report()
    mock_report_get.return_value = report
    service = _make_runner()
    data = _build_schedule_data(preserve=True)

    result = _schedule(service, data, child_state=child_state if via == "callback" else None)

    _assert_scene_preserved(result, data, service, mock_revoke, report)
    if via == "callback":
        mock_flowtree_get.assert_not_called()
        assert _EMBEDDED_LOGS in report.mark.call_args.kwargs["task_message"]


@patch(EMBED_PATCH, return_value=_EMBEDDED_LOGS)
@patch(f"{RUNNER_MOD}.Report.objects.get")
@patch(f"{RUNNER_MOD}.BambooEngine.revoke_pipeline", return_value=_OK_REVOKE)
def test_timeout_preserve_does_not_revoke_and_returns_false(mock_revoke, mock_report_get, _mock_embed):
    report = _mock_preserved_report()
    mock_report_get.return_value = report
    service = _make_runner()
    data = _build_schedule_data(start_delta_seconds=20, polling_timeout=10, preserve=True)

    result = _schedule(service, data)
    _assert_scene_preserved(result, data, service, mock_revoke, report)


@patch(f"{RUNNER_MOD}.Report.objects.get")
@patch(f"{RUNNER_MOD}.BambooEngine.revoke_pipeline")
def test_callback_failed_preserve_report_missing_still_returns_false(mock_revoke, mock_report_get):
    mock_report_get.side_effect = RedisRollbackExerciseReport.DoesNotExist
    service = _make_runner()
    data = _build_schedule_data(preserve=True)

    result = _schedule(service, data, child_state=StateType.FAILED)

    assert result is False
    assert data.outputs.rollback_code == 1


@patch(EMBED_PATCH)
@patch(f"{RUNNER_MOD}.Report.objects.get")
def test_preserve_scene_is_idempotent_when_report_already_preserved(mock_report_get, mock_embed):
    report = _mock_preserved_report()
    report.task_stage = TaskStage.SCENE_PRESERVED
    mock_report_get.return_value = report

    RedisExerciseFlowRunnerService()._preserve_scene(_build_schedule_data(preserve=True), CHILD_ROOT_ID)

    report.mark.assert_not_called()
    mock_embed.assert_not_called()


@pytest.mark.parametrize(
    "status,should_revoke",
    [
        (StateType.FINISHED, False),
        (StateType.REVOKED, False),
        (StateType.CREATED, True),
        (StateType.READY, True),
        (StateType.RUNNING, True),
        (StateType.FAILED, True),
        (None, False),
    ],
)
@patch(f"{RUNNER_MOD}.BambooEngine.revoke_pipeline", return_value=_OK_REVOKE)
@patch(f"{RUNNER_MOD}.FlowTree.objects.filter")
@patch(f"{RUNNER_MOD}.Report.objects.filter")
def test_revoke_previous_child_pipeline(mock_report_filter, mock_flowtree_filter, mock_revoke, status, should_revoke):
    mock_report_filter.return_value.values_list.return_value.first.return_value = (
        None if status is None else "old_child"
    )
    mock_flowtree_filter.return_value.only.return_value.first.return_value = (
        None if status is None else SimpleNamespace(status=status)
    )

    RedisExerciseFlowRunnerService()._revoke_previous_child_pipeline(1, "rollback_flow_obj_id")

    if should_revoke:
        mock_revoke.assert_called_once()
    else:
        mock_revoke.assert_not_called()


# ==================== Cleanup: leftover child revoke ====================


@pytest.mark.parametrize(
    "leftover_ids, expected_revoke_count",
    [
        pytest.param(["child_1", "child_2"], 2, id="revokes_leftovers"),
        pytest.param([], 0, id="no_leftovers"),
    ],
)
def test_cleanup_revokes_leftover_child_flows(leftover_ids, expected_revoke_count):
    service = _cleanup_service()
    report = MagicMock(rollback_flow_obj_id="child_1", delete_flow_obj_id="child_2")

    with patch(f"{RUNNER_MOD}.FlowTree.objects.filter") as mock_flowtree_filter, patch(
        f"{RUNNER_MOD}.BambooEngine.revoke_pipeline", return_value=_OK_REVOKE
    ) as mock_revoke, patch(f"{RUNNER_MOD}.get_effective_drill_infos", return_value=[{"report_id": 1}]), patch(
        f"{RUNNER_MOD}.Report.objects.filter"
    ) as mock_report_filter:
        mock_flowtree_filter.return_value.exclude.return_value.values_list.return_value = leftover_ids
        mock_report_filter.return_value.only.return_value.first.return_value = report
        service._revoke_leftover_child_flows({})

    assert mock_revoke.call_count == expected_revoke_count
    exclude_kwargs = mock_flowtree_filter.return_value.exclude.call_args.kwargs
    assert set(exclude_kwargs["status__in"]) == {StateType.FINISHED, StateType.REVOKED}
