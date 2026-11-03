import time

import pytest
from django.core.exceptions import ValidationError

from backend.db_periodic_task.dispatch.nameservice_queue import (
    NAMESERVICE_CALL_GATE,
    NAMESERVICE_CALL_QPS,
    NAMESERVICE_NAMESPACE,
    CallIntervalGate,
    NameserviceQueue,
    NameserviceQueueConfig,
)
from backend.db_periodic_task.dispatch.queue import DispatchQueue


def test_from_raw_pins_max_reserved():
    config = NameserviceQueueConfig.from_raw({"max_reserved": 10, "max_admitted_jobs": 300})
    assert config.max_reserved == 1
    assert config.max_admitted_jobs == 300


def test_default_config_has_single_slot():
    assert NameserviceQueueConfig.from_raw({}).max_reserved == 1


def test_validate_raw_rejects_raised_concurrency():
    with pytest.raises(ValidationError):
        NameserviceQueueConfig.validate_raw({"max_reserved": 2})


def test_validate_raw_accepts_single_slot_and_admission_tuning():
    NameserviceQueueConfig.validate_raw({"max_reserved": 1, "max_admitted_jobs": 500})
    NameserviceQueueConfig.validate_raw({"max_admitted_jobs": 500})


def test_queue_is_registered_under_nameservice_namespace():
    assert NameserviceQueue.namespace == NAMESERVICE_NAMESPACE
    assert DispatchQueue.queue_for_namespace(NAMESERVICE_NAMESPACE) is NameserviceQueue


def test_call_gate_spaces_consecutive_calls():
    gate = CallIntervalGate(NAMESERVICE_CALL_QPS)
    gate.acquire()
    start = time.monotonic()
    gate.acquire()
    assert time.monotonic() - start >= 1.0 / NAMESERVICE_CALL_QPS - 0.005


def test_shared_gate_runs_at_fifteen_qps():
    assert NAMESERVICE_CALL_QPS == 15
    assert NAMESERVICE_CALL_GATE.min_interval == pytest.approx(1.0 / 15)
