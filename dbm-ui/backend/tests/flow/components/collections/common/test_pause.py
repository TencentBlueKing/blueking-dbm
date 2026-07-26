# -*- coding: utf-8 -*-
"""PauseService: scene uid without ticket must pass through without creating todo."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.flow.plugins.components.collections.common.pause import PauseService, resolve_pause_ticket


class FakeData:
    def __init__(self, inputs):
        self.inputs = inputs
        self.outputs = SimpleNamespace()

    def get_one_of_inputs(self, key):
        return self.inputs.get(key)


def test_resolve_pause_ticket_rejects_non_numeric_uid():
    assert resolve_pause_ticket(None) is None
    assert resolve_pause_ticket("") is None
    assert resolve_pause_ticket("mongo-reduce-shard-3-20260725") is None
    assert resolve_pause_ticket("  ") is None


@patch("backend.flow.plugins.components.collections.common.pause.Ticket.objects.filter")
def test_resolve_pause_ticket_numeric_missing(mock_filter):
    mock_filter.return_value.first.return_value = None
    assert resolve_pause_ticket("12345") is None
    mock_filter.assert_called_once_with(id=12345)


@patch("backend.flow.plugins.components.collections.common.pause.Ticket.objects.filter")
def test_resolve_pause_ticket_numeric_exists(mock_filter):
    ticket = object()
    mock_filter.return_value.first.return_value = ticket
    assert resolve_pause_ticket(267) is ticket
    mock_filter.assert_called_once_with(id=267)


@patch("backend.flow.plugins.components.collections.common.pause.PipelineTodo.create")
@patch("backend.flow.plugins.components.collections.common.pause.resolve_pause_ticket", return_value=None)
def test_pause_execute_passes_without_ticket(mock_resolve, mock_todo_create):
    svc = PauseService()
    svc.log_info = MagicMock()
    data = FakeData({"kwargs": {}, "global_data": {"uid": "mongo-reduce-shard-scene-uid"}})

    assert svc._execute(data, None) is True
    assert svc.need_schedule() is False
    mock_todo_create.assert_not_called()


@patch("backend.flow.plugins.components.collections.common.pause.PipelineTodo.create")
@patch("backend.flow.plugins.components.collections.common.pause.resolve_pause_ticket")
def test_pause_execute_creates_todo_with_ticket(mock_resolve, mock_todo_create):
    ticket = MagicMock()
    flow = object()
    ticket.current_flow.return_value = flow
    mock_resolve.return_value = ticket

    svc = PauseService()
    svc.log_info = MagicMock()
    svc.setup_runtime_attrs(root_pipeline_id="root", id="node")
    data = FakeData({"kwargs": {"x": 1}, "global_data": {"uid": "266"}})

    assert svc._execute(data, None) is True
    assert svc.need_schedule() is True
    mock_todo_create.assert_called_once_with(ticket, flow, "root", "node")
