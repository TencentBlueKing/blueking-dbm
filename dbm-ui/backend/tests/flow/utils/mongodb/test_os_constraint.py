# -*- coding: utf-8 -*-
import logging
from contextlib import contextmanager

import pytest
from rest_framework.exceptions import ValidationError

from backend.flow.utils.mongodb.os_constraint import (
    apply_mongodb_os_constraint,
    constrain_mongodb_resource_os,
    mongodb_os_names_for_version,
    mongodb_resource_os_names,
)


@contextmanager
def capture_flow_logs(caplog, level=logging.WARNING):
    """The flow logger does not propagate, so caplog's root handler never sees it."""
    flow_logger = logging.getLogger("flow")
    original_level = flow_logger.level
    original_handler_level = caplog.handler.level
    flow_logger.setLevel(level)
    caplog.handler.setLevel(level)
    flow_logger.addHandler(caplog.handler)
    try:
        yield
    finally:
        flow_logger.removeHandler(caplog.handler)
        flow_logger.setLevel(original_level)
        caplog.handler.setLevel(original_handler_level)


def test_mongodb_os_names_for_version():
    for version in ("mongodb-8.0", "8.0.32", "mongodb-8.0.32", "8.2", "mongodb-8.2.1", "9.0"):
        assert mongodb_os_names_for_version(version) == ("tlinux-4", "tlinux-4.4"), version
    for version in (
        "3.0",
        "3.2",
        "3.4",
        "3.6",
        "4.0",
        "4.2",
        "4.4",
        "5.0",
        "6.0",
        "7.0",
        "mongodb-3.0.15",
        "mongodb-3.4.24",
        "mongodb-4.0.28",
        "mongodb-7.0.28",
    ):
        assert mongodb_os_names_for_version(version) is None, version
    assert mongodb_os_names_for_version("") is None
    with pytest.raises(ValueError):
        mongodb_os_names_for_version("not-a-version")


def test_explicit_version_on_parent_applies_to_info():
    parent = {"db_version": "mongodb-8.0.32"}
    info = {
        "bk_cloud_id": 0,
        "resource_spec": {
            "mongo_machine_set": {"spec_id": 1, "count": 3},
            "picked": {"hosts": [{"ip": "127.0.0.1"}], "count": 1},
        },
    }
    assert constrain_mongodb_resource_os(parent, info) is True
    role = info["resource_spec"]["mongo_machine_set"]
    assert role["os_names"] == ["tlinux-4", "tlinux-4.4"]
    assert "os_names" not in info["resource_spec"]["picked"]


def test_version_at_most_7_excludes_tlinux4_by_default():
    info = {"db_version": "mongodb-7.0.28", "resource_spec": {"mongodb": {"spec_id": 1, "count": 3}}}
    assert constrain_mongodb_resource_os(None, info) is True
    role = info["resource_spec"]["mongodb"]
    assert role["os_names"] == ["tlinux-4", "tlinux-4.4"]
    assert role["exclude_os_name"] is True


def test_version_at_most_7_can_use_tlinux4_when_enabled():
    info = {"db_version": "mongodb-7.0.28", "resource_spec": {"mongodb": {"spec_id": 1, "count": 3}}}
    assert constrain_mongodb_resource_os(None, info, allow_legacy_tlinux4=True) is False
    assert "os_names" not in info["resource_spec"]["mongodb"]


def test_cluster_major_version_fallback():
    info = {"cluster_id": 9, "resource_spec": {"mongodb": {"spec_id": 2, "count": 1}}}

    def loader(cluster_ids):
        assert list(cluster_ids) == [9]
        return ["mongodb-8.0.4"]

    assert mongodb_resource_os_names(None, info, cluster_version_loader=loader) == ["tlinux-4", "tlinux-4.4"]
    assert constrain_mongodb_resource_os(None, info, cluster_version_loader=loader) is True
    assert info["resource_spec"]["mongodb"]["os_names"] == ["tlinux-4", "tlinux-4.4"]


def test_cluster_version_at_most_7_excludes_tlinux4():
    info = {"cluster_ids": [3], "resource_spec": {"mongodb": {"spec_id": 2, "count": 1}}}

    def loader(cluster_ids):
        assert list(cluster_ids) == [3]
        return ["4.2"]

    assert constrain_mongodb_resource_os(None, info, cluster_version_loader=loader) is True
    role = info["resource_spec"]["mongodb"]
    assert role["os_names"] == ["tlinux-4", "tlinux-4.4"]
    assert role["exclude_os_name"] is True


def test_explicit_older_version_skips_cluster_lookup():
    info = {
        "db_version": "mongodb-6.0.27",
        "cluster_id": 9,
        "resource_spec": {"mongodb": {"spec_id": 2, "count": 1}},
    }

    def loader(_cluster_ids):
        raise AssertionError("explicit version should skip cluster lookup")

    assert constrain_mongodb_resource_os(None, info, cluster_version_loader=loader) is True
    assert info["resource_spec"]["mongodb"]["exclude_os_name"] is True


def test_apply_writes_infos_and_top_level_spec():
    ticket = {
        "db_version": "mongodb-8.0.32",
        "resource_spec": {"mongodb": {"spec_id": 1, "count": 3}},
        "infos": [
            {"resource_spec": {"mongo_machine_set": {"spec_id": 2, "count": 3}}},
            {
                "db_version": "4.0",
                "resource_spec": {"mongodb": {"spec_id": 3, "count": 1, "hosts": [{"ip": "127.0.0.1"}]}},
            },
        ],
    }
    apply_mongodb_os_constraint(ticket, allow_legacy_tlinux4=False)
    assert ticket["resource_spec"]["mongodb"]["os_names"] == ["tlinux-4", "tlinux-4.4"]
    assert ticket["infos"][0]["resource_spec"]["mongo_machine_set"]["os_names"] == ["tlinux-4", "tlinux-4.4"]
    assert "os_names" not in ticket["infos"][1]["resource_spec"]["mongodb"]


def test_unknown_explicit_version_is_a_validation_error():
    info = {"db_version": "not-a-version", "resource_spec": {"mongodb": {"spec_id": 1, "count": 1}}}
    with pytest.raises(ValidationError) as exc:
        constrain_mongodb_resource_os(None, info)
    assert "not-a-version" in str(exc.value.detail)
    assert "os_names" not in info["resource_spec"]["mongodb"]


def test_invalid_cluster_version_is_treated_as_legacy(caplog):
    info = {"cluster_ids": [3], "resource_spec": {"mongodb": {"spec_id": 1, "count": 1}}}

    def loader(_cluster_ids):
        return ["MongoDB-bad"]

    with capture_flow_logs(caplog):
        assert constrain_mongodb_resource_os(None, info, cluster_version_loader=loader) is True
    role = info["resource_spec"]["mongodb"]
    assert role["os_names"] == ["tlinux-4", "tlinux-4.4"]
    assert role["exclude_os_name"] is True
    assert any("MongoDB-bad" in record.message for record in caplog.records)


def test_invalid_cluster_version_can_use_tlinux4_when_enabled(caplog):
    info = {"cluster_ids": [3], "resource_spec": {"mongodb": {"spec_id": 1, "count": 1}}}

    def loader(_cluster_ids):
        return ["not-a-version"]

    with capture_flow_logs(caplog):
        applied = constrain_mongodb_resource_os(None, info, cluster_version_loader=loader, allow_legacy_tlinux4=True)
    assert applied is False
    assert "os_names" not in info["resource_spec"]["mongodb"]
    assert any("not-a-version" in record.message for record in caplog.records)


def test_current_explicit_version_wins_over_parent():
    parent = {"db_version": "mongodb-8.0.32"}
    info = {"db_version": "7.0", "resource_spec": {"mongodb": {"spec_id": 1, "count": 1}}}
    assert constrain_mongodb_resource_os(parent, info) is True
    role = info["resource_spec"]["mongodb"]
    assert role["os_names"] == ["tlinux-4", "tlinux-4.4"]
    assert role["exclude_os_name"] is True


def test_existing_os_names_are_not_overwritten():
    info = {
        "db_version": "8.0",
        "resource_spec": {"mongodb": {"spec_id": 1, "count": 1, "os_names": ["custom-os"]}},
    }
    assert constrain_mongodb_resource_os(None, info) is True
    assert info["resource_spec"]["mongodb"]["os_names"] == ["custom-os"]
