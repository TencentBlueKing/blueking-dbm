# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from backend.flow.plugins.components.collections.mysql.check_open_area_database import CheckOpenAreaDatabaseService

MODULE_PATH = "backend.flow.plugins.components.collections.mysql.check_open_area_database"


def _make_data(targets):
    data = MagicMock()
    data.get_one_of_inputs.return_value = {
        "source_cluster_domain": "source.example.db",
        "targets": targets,
    }
    return data


def _target(domain, address, databases, bk_cloud_id=1):
    return {
        "target_cluster_domain": domain,
        "bk_cloud_id": bk_cloud_id,
        "address": address,
        "databases": databases,
    }


def _rpc_result(address, databases):
    return {
        "address": address,
        "error_msg": "",
        "cmd_results": [{"error_msg": "", "table_data": [{"Database": database} for database in databases]}],
    }


def _make_service():
    service = CheckOpenAreaDatabaseService()
    service.log_info = MagicMock()
    service.log_error = MagicMock()
    return service


def test_existing_database_blocks_after_all_targets_are_classified():
    targets = [
        _target("target-a.example.db", "1.1.1.1:3306", ["new_db", "existing_db"]),
        _target("target-b.example.db", "2.2.2.2:3306", ["another_db"]),
    ]
    service = _make_service()

    with patch(f"{MODULE_PATH}.DRSApi.rpc") as rpc:
        rpc.return_value = [
            _rpc_result("1.1.1.1:3306", ["existing_db"]),
            _rpc_result("2.2.2.2:3306", []),
        ]
        result = service._execute(_make_data(targets), None)

    assert result is False
    rpc.assert_called_once_with(
        {
            "bk_cloud_id": 1,
            "addresses": ["1.1.1.1:3306", "2.2.2.2:3306"],
            "cmds": ["show databases"],
            "force": False,
        }
    )
    available_log = service.log_info.call_args_list[0].args[0]
    unavailable_log = service.log_error.call_args_list[0].args[0]
    assert "new_db" in available_log
    assert "another_db" in available_log
    assert "existing_db" in unavailable_log


def test_all_absent_databases_allow_flow_to_continue():
    targets = [_target("target.example.db", "1.1.1.1:3306", ["new_db"])]
    service = _make_service()

    with patch(f"{MODULE_PATH}.DRSApi.rpc", return_value=[_rpc_result("1.1.1.1:3306", [])]):
        result = service._execute(_make_data(targets), None)

    assert result is True
    service.log_error.assert_not_called()
    assert "new_db" in service.log_info.call_args_list[0].args[0]


def test_drs_failure_does_not_skip_checks_in_other_clouds():
    targets = [
        _target("failed.example.db", "1.1.1.1:3306", ["failed_db"], bk_cloud_id=1),
        _target("checked.example.db", "1.1.1.1:3306", ["checked_db"], bk_cloud_id=2),
    ]
    service = _make_service()

    def rpc_side_effect(params):
        if params["bk_cloud_id"] == 1:
            raise RuntimeError("connection failed")
        return [_rpc_result("1.1.1.1:3306", [])]

    with patch(f"{MODULE_PATH}.DRSApi.rpc", side_effect=rpc_side_effect) as rpc:
        result = service._execute(_make_data(targets), None)

    assert result is False
    assert rpc.call_count == 2
    assert "checked_db" in service.log_info.call_args_list[0].args[0]
    unavailable_log = service.log_error.call_args_list[0].args[0]
    assert "failed_db" in unavailable_log
    assert "connection failed" in unavailable_log
