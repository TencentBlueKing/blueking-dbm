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

import pytest
from bamboo_engine.api import EngineAPIResult

from backend.db_report.models import RedisRollbackExerciseReport as Report
from backend.flow.consts import StateType
from backend.flow.plugins.components.collections.redis.redis_rollback_exercise import CHILD2RUNNER_CACHE_PREFIX
from backend.flow.signal.callback_map import TICKET_TYPE_HANDLERS
from backend.flow.signal.redis_rollback_exercise_handler import (
    TERMINAL_STATES,
    _resolve_runner_node_id,
    redis_data_structure_callback_handler,
    redis_data_structure_task_delete_callback_handler,
    wakeup_redis_rollback_runner_by_child,
)
from backend.ticket.constants import TicketType

pytestmark = pytest.mark.django_db

CHILD_ROOT_ID = "child_root_id"
PARENT_ROOT_ID = "parent_root_id"
RUNNER_NODE_ID = "runner_node_id"
CACHE_KEY = f"{CHILD2RUNNER_CACHE_PREFIX}:{CHILD_ROOT_ID}"
CACHE_MAPPING = {"parent_root_id": PARENT_ROOT_ID, "runner_node_id": RUNNER_NODE_ID}
HANDLER_MOD = "backend.flow.signal.redis_rollback_exercise_handler"


def _make_report(**overrides):
    kwargs = {
        "cluster_id": 1,
        "cluster_domain": "d",
        "cluster_type": "Redis",
        "instance_ip": "1.1.1.1",
        "instance_port": 6379,
        "redis_version": "7.0",
        "ticket_id": 1,
        "rollback_flow_obj_id": CHILD_ROOT_ID,
    }
    kwargs.update(overrides)
    return Report.objects.create(**kwargs)


def _configure_cache_hit(mock_cache_get, mock_flownode_filter, mock_schedule_filter=None, alive=True):
    mock_cache_get.return_value = CACHE_MAPPING
    mock_flownode_filter.return_value.exists.return_value = alive
    if mock_schedule_filter is not None:
        mock_schedule_filter.return_value.update = MagicMock(return_value=1)


def _mock_candidate_nodes(mock_node_filter, node_ids):
    mock_node_filter.return_value.order_by.return_value.values_list.return_value = node_ids


def _wakeup(child_state=StateType.FINISHED):
    return wakeup_redis_rollback_runner_by_child(CHILD_ROOT_ID, child_state, "unit_test")


# ==================== wakeup: cache hit path ====================


@patch(f"{HANDLER_MOD}.cache.get")
@patch(f"{HANDLER_MOD}.Schedule.objects.filter")
@patch(f"{HANDLER_MOD}.FlowNode.objects.filter")
@patch(
    f"{HANDLER_MOD}.BambooEngine.callback",
    return_value=EngineAPIResult(result=True, data={}, message=""),
)
def test_wakeup_cache_hit_skips_report_query(
    mock_callback, mock_flownode_filter, mock_schedule_filter, mock_cache_get
):
    _configure_cache_hit(mock_cache_get, mock_flownode_filter, mock_schedule_filter)

    assert _wakeup() == 1
    mock_cache_get.assert_called_once_with(CACHE_KEY)
    mock_schedule_filter.assert_called_once_with(node_id=RUNNER_NODE_ID, scheduling=True, finished=False)
    mock_schedule_filter.return_value.update.assert_called_once_with(scheduling=False)
    mock_callback.assert_called_once_with(
        node_id=RUNNER_NODE_ID,
        desc={"child_root_id": CHILD_ROOT_ID, "child_state": StateType.FINISHED, "trigger": "unit_test"},
    )


@pytest.mark.parametrize(
    "callback_result, callback_error",
    [
        (EngineAPIResult(result=False, data={}, message="callback rejected"), None),
        (None, Exception("callback boom")),
    ],
    ids=["rejected", "exception"],
)
@patch(f"{HANDLER_MOD}.cache.get")
@patch(f"{HANDLER_MOD}.Schedule.objects.filter")
@patch(f"{HANDLER_MOD}.FlowNode.objects.filter")
@patch(f"{HANDLER_MOD}.BambooEngine.callback")
def test_wakeup_cache_hit_callback_failure_returns_0(
    mock_callback, mock_flownode_filter, mock_schedule_filter, mock_cache_get, callback_result, callback_error
):
    _configure_cache_hit(mock_cache_get, mock_flownode_filter, mock_schedule_filter)
    if callback_error is not None:
        mock_callback.side_effect = callback_error
    else:
        mock_callback.return_value = callback_result

    assert _wakeup() == 0


# ==================== wakeup: cache miss fallback path ====================


@patch(f"{HANDLER_MOD}.cache.get", return_value=None)
@patch(f"{HANDLER_MOD}._resolve_parent_root_id", return_value=PARENT_ROOT_ID)
@patch(f"{HANDLER_MOD}._resolve_runner_node_id", return_value=RUNNER_NODE_ID)
@patch(f"{HANDLER_MOD}.Schedule.objects.filter")
@patch(f"{HANDLER_MOD}.FlowNode.objects.filter")
@patch(
    f"{HANDLER_MOD}.BambooEngine.callback",
    return_value=EngineAPIResult(result=True, data={}, message=""),
)
def test_wakeup_cache_miss_falls_back_to_report(
    mock_callback,
    mock_flownode_filter,
    mock_schedule_filter,
    _mock_resolve_runner,
    _mock_resolve_parent,
    _mock_cache_get,
):
    _make_report()
    mock_schedule_filter.return_value.update = MagicMock(return_value=1)
    mock_flownode_filter.return_value.exists.return_value = True

    assert _wakeup() == 1
    mock_callback.assert_called_once()


@pytest.mark.parametrize(
    "ticket_id, parent_id, runner_id, create_report",
    [
        pytest.param(1, PARENT_ROOT_ID, RUNNER_NODE_ID, False, id="no_report"),
        pytest.param(0, PARENT_ROOT_ID, RUNNER_NODE_ID, True, id="falsy_ticket_id"),
        pytest.param(1, None, RUNNER_NODE_ID, True, id="no_parent_root_id"),
        pytest.param(1, PARENT_ROOT_ID, None, True, id="no_runner_node_id"),
    ],
)
@patch(f"{HANDLER_MOD}.cache.get", return_value=None)
@patch(f"{HANDLER_MOD}._resolve_parent_root_id")
@patch(f"{HANDLER_MOD}._resolve_runner_node_id")
def test_wakeup_cache_miss_returns_0_when_mapping_incomplete(
    mock_resolve_runner, mock_resolve_parent, _mock_cache_get, ticket_id, parent_id, runner_id, create_report
):
    if create_report:
        _make_report(ticket_id=ticket_id)
        child_root_id = CHILD_ROOT_ID
    else:
        child_root_id = "orphan_child_root_id"
    mock_resolve_parent.return_value = parent_id
    mock_resolve_runner.return_value = runner_id

    assert wakeup_redis_rollback_runner_by_child(child_root_id, StateType.FINISHED, "unit_test") == 0


# ==================== handler registration ====================


def test_redis_sub_ticket_handlers_registered():
    assert TICKET_TYPE_HANDLERS.get(TicketType.REDIS_DATA_STRUCTURE.lower()) == redis_data_structure_callback_handler
    assert (
        TICKET_TYPE_HANDLERS.get(TicketType.REDIS_DATA_STRUCTURE_TASK_DELETE.lower())
        == redis_data_structure_task_delete_callback_handler
    )


# ==================== _handle_redis_sub_ticket_callback ====================


@pytest.mark.parametrize("terminal_state", sorted(TERMINAL_STATES))
@patch(f"{HANDLER_MOD}.FlowTree.objects.get")
@patch(f"{HANDLER_MOD}.Ticket.objects.filter")
@patch(f"{HANDLER_MOD}.wakeup_redis_rollback_runner_by_child")
def test_callback_handler_terminal_state_with_drill_ticket(
    mock_wakeup, mock_ticket_filter, mock_flowtree_get, terminal_state
):
    mock_ticket_filter.return_value.only.return_value.first.return_value = MagicMock(
        ticket_type=TicketType.REDIS_ROLLBACK_EXERCISE
    )
    mock_flowtree_get.return_value = MagicMock(status=terminal_state)
    redis_data_structure_callback_handler(
        node_id="node_id",
        root_id=CHILD_ROOT_ID,
        status=terminal_state,
        ticket_id=1,
    )
    mock_wakeup.assert_called_once_with(
        child_root_id=CHILD_ROOT_ID, child_state=terminal_state, trigger="post_set_state"
    )


@patch(f"{HANDLER_MOD}.Ticket.objects.filter")
@patch(f"{HANDLER_MOD}.wakeup_redis_rollback_runner_by_child")
def test_callback_handler_ignores_non_drill_or_non_terminal(mock_wakeup, mock_ticket_filter):
    mock_ticket_filter.return_value.only.return_value.first.return_value = MagicMock(
        ticket_type=TicketType.REDIS_DATA_STRUCTURE
    )
    redis_data_structure_task_delete_callback_handler(
        node_id="node_id",
        root_id=CHILD_ROOT_ID,
        status=StateType.FINISHED,
        ticket_id=2,
    )
    mock_wakeup.assert_not_called()

    mock_ticket_filter.return_value.only.return_value.first.return_value = MagicMock(
        ticket_type=TicketType.REDIS_ROLLBACK_EXERCISE
    )
    redis_data_structure_callback_handler(
        node_id="node_id",
        root_id=CHILD_ROOT_ID,
        status=StateType.RUNNING,
        ticket_id=1,
    )
    mock_wakeup.assert_not_called()


@patch(f"{HANDLER_MOD}.Ticket.objects.filter")
@patch(f"{HANDLER_MOD}.wakeup_redis_rollback_runner_by_child")
def test_callback_handler_no_ticket_id_returns_early(mock_wakeup, mock_ticket_filter):
    redis_data_structure_callback_handler(
        node_id="node_id",
        root_id=CHILD_ROOT_ID,
        status=StateType.FINISHED,
        ticket_id=0,
    )
    mock_ticket_filter.assert_not_called()
    mock_wakeup.assert_not_called()


@patch(f"{HANDLER_MOD}.Ticket.objects.filter")
@patch(f"{HANDLER_MOD}.wakeup_redis_rollback_runner_by_child")
def test_callback_handler_ticket_not_found_returns_early(mock_wakeup, mock_ticket_filter):
    mock_ticket_filter.return_value.only.return_value.first.return_value = None
    redis_data_structure_callback_handler(
        node_id="node_id",
        root_id=CHILD_ROOT_ID,
        status=StateType.FINISHED,
        ticket_id=999,
    )
    mock_wakeup.assert_not_called()


# ==================== _resolve_runner_node_id ====================


@patch(f"{HANDLER_MOD}.BambooEngine.get_node_output_data")
@patch(f"{HANDLER_MOD}.FlowNode.objects.filter")
def test_resolve_runner_node_id_scan(mock_node_filter, mock_get_node_output):
    _mock_candidate_nodes(mock_node_filter, ["node_1", "node_2"])
    mock_get_node_output.return_value = MagicMock(data={"child_root_id": CHILD_ROOT_ID})

    node_id = _resolve_runner_node_id(parent_root_id=PARENT_ROOT_ID, child_root_id=CHILD_ROOT_ID)

    assert node_id == "node_1"
    mock_node_filter.assert_called_once_with(
        root_id=PARENT_ROOT_ID, status__in=[StateType.RUNNING, StateType.CREATED, StateType.READY]
    )


@patch(f"{HANDLER_MOD}.FlowNode.objects.filter")
def test_resolve_runner_node_id_no_candidates_returns_none(mock_node_filter):
    _mock_candidate_nodes(mock_node_filter, [])

    assert _resolve_runner_node_id(parent_root_id=PARENT_ROOT_ID, child_root_id=CHILD_ROOT_ID) is None


@patch(f"{HANDLER_MOD}.BambooEngine.get_node_output_data")
@patch(f"{HANDLER_MOD}.FlowNode.objects.filter")
def test_resolve_runner_node_id_no_matching_output_returns_none(mock_node_filter, mock_get_node_output):
    _mock_candidate_nodes(mock_node_filter, ["node_1", "node_2"])
    mock_get_node_output.return_value = MagicMock(data={"child_root_id": "other_child_id"})

    assert _resolve_runner_node_id(parent_root_id=PARENT_ROOT_ID, child_root_id=CHILD_ROOT_ID) is None
    assert mock_get_node_output.call_count == 2


@patch(f"{HANDLER_MOD}.BambooEngine.get_node_output_data")
@patch(f"{HANDLER_MOD}.FlowNode.objects.filter")
def test_resolve_runner_node_id_output_exception_continues(mock_node_filter, mock_get_node_output):
    _mock_candidate_nodes(mock_node_filter, ["node_1", "node_2"])
    mock_get_node_output.side_effect = [
        Exception("node_1 failed"),
        MagicMock(data={"child_root_id": CHILD_ROOT_ID}),
    ]

    assert _resolve_runner_node_id(parent_root_id=PARENT_ROOT_ID, child_root_id=CHILD_ROOT_ID) == "node_2"


# ==================== Wakeup guard: failed runner nodes are not woken ====================


@patch(f"{HANDLER_MOD}.cache.get")
@patch(f"{HANDLER_MOD}.cache.delete")
@patch(f"{HANDLER_MOD}.FlowNode.objects.filter")
@patch(f"{HANDLER_MOD}.BambooEngine.callback")
def test_wakeup_cache_hit_runner_failed_skips_callback(
    mock_callback, mock_flownode_filter, mock_cache_delete, mock_cache_get
):
    _configure_cache_hit(mock_cache_get, mock_flownode_filter, alive=False)

    assert _wakeup(StateType.FAILED) == 0
    mock_callback.assert_not_called()
    mock_cache_delete.assert_called_once_with(CACHE_KEY)


@patch(f"{HANDLER_MOD}.cache.get", return_value=None)
@patch(f"{HANDLER_MOD}._resolve_parent_root_id", return_value=PARENT_ROOT_ID)
@patch(f"{HANDLER_MOD}._resolve_runner_node_id", return_value=RUNNER_NODE_ID)
@patch(f"{HANDLER_MOD}.FlowNode.objects.filter")
@patch(f"{HANDLER_MOD}.BambooEngine.callback")
def test_wakeup_cache_miss_runner_failed_skips_callback(
    mock_callback, mock_flownode_filter, _mock_resolve_runner, _mock_resolve_parent, _mock_cache_get
):
    _make_report()
    mock_flownode_filter.return_value.exists.return_value = False

    assert _wakeup(StateType.FAILED) == 0
    mock_callback.assert_not_called()
