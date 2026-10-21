# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.flow.plugins.components.collections.spider.check_remote_master_var_consistency import (
    CheckRemoteMasterVarConsistencyService,
)
from backend.flow.utils.mysql.remote_master_var_consistency import (
    KIND_DIFFERENT,
    InstanceVarMap,
    Mismatch,
    diff_remote_masters,
)

MODULE_PATH = "backend.flow.plugins.components.collections.spider.check_remote_master_var_consistency"


def _make_data(cluster_id):
    data = MagicMock()
    data.get_one_of_inputs.return_value = {"cluster_id": cluster_id}
    return data


def _instance(ip, port, bk_cloud_id=0):
    return SimpleNamespace(port=port, machine=SimpleNamespace(ip=ip, bk_cloud_id=bk_cloud_id, port=port))


def _service():
    service = CheckRemoteMasterVarConsistencyService()
    service.log_error = MagicMock()
    return service


def test_mismatch_returns_false():
    cluster = SimpleNamespace(id=1)
    mismatch = Mismatch(
        name="innodb_large_prefix",
        kind=KIND_DIFFERENT,
        rows=(("127.0.0.2", 20000, "A"), ("127.0.0.3", 20000, "B")),
    )
    service = _service()
    with (
        patch(f"{MODULE_PATH}.Cluster.objects.get", return_value=cluster),
        patch(f"{MODULE_PATH}.running_remote_masters", return_value=[_instance("127.0.0.2", 20000)]),
        patch(
            f"{MODULE_PATH}.query_remote_master_variables",
            return_value=([InstanceVarMap("127.0.0.2", 20000, {})], []),
        ),
        patch(f"{MODULE_PATH}.diff_remote_masters", return_value=[mismatch]) as diff,
    ):
        result = service._execute(_make_data(cluster.id), None)

    assert result is False
    diff.assert_called_once()
    service.log_error.assert_called_once()
    assert "innodb_large_prefix" in service.log_error.call_args[0][0]


def test_no_mismatch_returns_true():
    cluster = SimpleNamespace(id=2)
    service = _service()
    with (
        patch(f"{MODULE_PATH}.Cluster.objects.get", return_value=cluster),
        patch(f"{MODULE_PATH}.running_remote_masters", return_value=[_instance("127.0.0.2", 20000)]),
        patch(
            f"{MODULE_PATH}.query_remote_master_variables",
            return_value=([InstanceVarMap("127.0.0.2", 20000, {})], []),
        ),
        patch(f"{MODULE_PATH}.diff_remote_masters", return_value=[]) as diff,
    ):
        result = service._execute(_make_data(cluster.id), None)

    assert result is True
    diff.assert_called_once()
    service.log_error.assert_not_called()


def test_zero_masters_returns_false():
    cluster = SimpleNamespace(id=3)
    service = _service()
    with (
        patch(f"{MODULE_PATH}.Cluster.objects.get", return_value=cluster),
        patch(f"{MODULE_PATH}.running_remote_masters", return_value=[]),
        patch(f"{MODULE_PATH}.query_remote_master_variables") as query,
        patch(f"{MODULE_PATH}.diff_remote_masters") as diff,
    ):
        result = service._execute(_make_data(cluster.id), None)

    assert result is False
    query.assert_not_called()
    diff.assert_not_called()
    service.log_error.assert_called_once()


def _rpc_ok(address, value):
    return {
        "address": address,
        "error_msg": "",
        "cmd_results": [{"table_data": [{"Variable_name": "innodb_large_prefix", "Value": value}], "error_msg": ""}],
    }


def test_two_masters_with_different_innodb_large_prefix_fail():
    cluster = SimpleNamespace(id=5)
    left = _instance("127.0.0.2", 20000)
    right = _instance("127.0.0.3", 20000)
    resp = [_rpc_ok("127.0.0.2:20000", "ON"), _rpc_ok("127.0.0.3:20000", "OFF")]
    service = _service()
    with (
        patch(f"{MODULE_PATH}.Cluster.objects.get", return_value=cluster),
        patch(f"{MODULE_PATH}.running_remote_masters", return_value=[left, right]),
        patch(f"{MODULE_PATH}.DRSApi.rpc", return_value=resp),
    ):
        result = service._execute(_make_data(cluster.id), None)

    assert result is False
    logged = service.log_error.call_args[0][0]
    assert "innodb_large_prefix" in logged
    assert "127.0.0.2" in logged
    assert "127.0.0.3" in logged


def test_cmd_error_is_logged_and_not_passed_to_diff():
    cluster = SimpleNamespace(id=6)
    good = _instance("127.0.0.2", 20000)
    bad = _instance("127.0.0.3", 20000)
    resp = [
        _rpc_ok("127.0.0.2:20000", "ONLY"),
        {
            "address": "127.0.0.3:20000",
            "error_msg": "",
            "cmd_results": [{"table_data": None, "error_msg": "permission denied"}],
        },
    ]
    service = _service()
    with (
        patch(f"{MODULE_PATH}.Cluster.objects.get", return_value=cluster),
        patch(f"{MODULE_PATH}.running_remote_masters", return_value=[good, bad]),
        patch(f"{MODULE_PATH}.DRSApi.rpc", return_value=resp),
        patch(f"{MODULE_PATH}.diff_remote_masters", wraps=diff_remote_masters) as diff,
    ):
        result = service._execute(_make_data(cluster.id), None)

    assert result is False
    passed = diff.call_args[0][0]
    assert [item.ip for item in passed] == ["127.0.0.2"]
    assert "permission denied" in service.log_error.call_args[0][0]


def test_drs_address_error_is_not_passed_to_diff():
    cluster = SimpleNamespace(id=4)
    good = _instance("127.0.0.2", 20000)
    bad = _instance("127.0.0.3", 20000)
    resp = [
        {
            "address": "127.0.0.2:20000",
            "error_msg": "",
            "cmd_results": [{"table_data": [{"Variable_name": "innodb_large_prefix", "Value": "ON"}]}],
        },
        {
            "address": "127.0.0.3:20000",
            "error_msg": "boom",
            "cmd_results": [],
        },
    ]
    service = _service()
    with (
        patch(f"{MODULE_PATH}.Cluster.objects.get", return_value=cluster),
        patch(f"{MODULE_PATH}.running_remote_masters", return_value=[good, bad]),
        patch(f"{MODULE_PATH}.DRSApi.rpc", return_value=resp),
        patch(f"{MODULE_PATH}.diff_remote_masters", wraps=diff_remote_masters) as diff,
    ):
        result = service._execute(_make_data(cluster.id), None)

    assert result is False
    diff.assert_called_once()
    passed = diff.call_args[0][0]
    assert [item.ip for item in passed] == ["127.0.0.2"]
    assert "127.0.0.3" in service.log_error.call_args[0][0]
