# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.flow.consts import SUCCESS_LIST
from backend.flow.plugins.components.collections.mysql.check_sqlfile_md5 import CheckSqlFileMd5Service
from backend.flow.utils.mysql.sqlfile_md5_check import (
    ParseFailure,
    build_md5sum_script,
    compare_sqlfile_md5,
    parse_md5_lines,
)


class _Data:
    def __init__(self, kwargs, outputs=None):
        self.inputs = {"kwargs": kwargs}
        self.outputs = SimpleNamespace(**(outputs or {}))

    def get_one_of_inputs(self, key):
        return self.inputs.get(key)

    def get_one_of_outputs(self, key):
        return getattr(self.outputs, key, None)


def test_matching_md5_has_no_failure():
    digest = "d41d8cd98f00b204e9800998ecf8427e"
    actual = parse_md5_lines("banner\nDBM_SQLFILE_MD5_V1\tchange.sql\t{}\n".format(digest.upper()))

    assert actual == {"change.sql": digest}
    assert compare_sqlfile_md5({"change.sql": digest.upper()}, actual) == []


def test_mismatch_contains_filename_and_both_digests():
    expected = "d41d8cd98f00b204e9800998ecf8427e"
    actual = "0cc175b9c0f1b6a831c399e269772661"

    failures = compare_sqlfile_md5({"change.sql": expected}, {"change.sql": actual})

    assert len(failures) == 1
    assert failures[0].filename == "change.sql"
    assert failures[0].expected == expected
    assert failures[0].actual == actual


def test_missing_file_contains_filename():
    failures = compare_sqlfile_md5(
        {"change.sql": "d41d8cd98f00b204e9800998ecf8427e"},
        {"change.sql": "MISSING"},
    )

    assert len(failures) == 1
    assert failures[0].filename == "change.sql"
    assert failures[0].kind == "missing_file"


def test_banner_only_log_is_unparsable():
    parsed = parse_md5_lines("job banner only")

    assert isinstance(parsed, ParseFailure)
    assert parsed.raw_lines == ("job banner only",)


def test_unparsable_version_line_returns_raw_line():
    raw_line = "DBM_SQLFILE_MD5_V1\tchange.sql\tnot-md5"

    parsed = parse_md5_lines("job banner\n{}\n".format(raw_line))

    assert isinstance(parsed, ParseFailure)
    assert parsed.raw_lines == (raw_line,)


def test_illegal_filename_does_not_build_or_execute_script():
    service = CheckSqlFileMd5Service()
    service.log_error = MagicMock()
    data = _Data(
        {
            "root_id": "root-1",
            "node_id": "node-1",
            "node_name": "md5",
            "bk_cloud_id": 0,
            "sql_path": "/data/install/sqlfile_root-1/",
            "exec_targets": [{"ip": "127.0.0.1", "bk_cloud_id": 0}],
            "sql_files_md5": {"change.sql; touch bad": "d41d8cd98f00b204e9800998ecf8427e"},
        }
    )

    with patch(
        "backend.flow.plugins.components.collections.mysql.check_sqlfile_md5.build_md5sum_script"
    ) as build_script:
        with patch(
            "backend.flow.plugins.components.collections.mysql.check_sqlfile_md5.JobApi.fast_execute_script"
        ) as execute_script:
            assert service._execute(data, {}) is False

    build_script.assert_not_called()
    execute_script.assert_not_called()
    assert "change.sql; touch bad" not in build_md5sum_script("/data/install/sqlfile_root-1/", ["change.sql"])
    assert "change.sql; touch bad" in str(service.log_error.call_args)


def _md5_execute_data(sql_files_md5):
    return _Data(
        {
            "root_id": "root-1",
            "node_id": "node-1",
            "node_name": "md5",
            "bk_cloud_id": 0,
            "sql_path": "/data/install/sqlfile_root-1/",
            "repo_path": "mysql/sqlfile/1",
            "exec_targets": [{"ip": "127.0.0.1", "bk_cloud_id": 0}],
            "sql_files_md5": sql_files_md5,
        }
    )


def test_repo_mismatch_does_not_run_host_script():
    expected = "d41d8cd98f00b204e9800998ecf8427e"
    repo_digest = "0cc175b9c0f1b6a831c399e269772661"
    service = CheckSqlFileMd5Service()
    service.log_error = MagicMock()
    storage = MagicMock()
    storage.get_file_md5.return_value = repo_digest

    with patch(
        "backend.flow.plugins.components.collections.mysql.check_sqlfile_md5.get_storage",
        return_value=storage,
    ):
        with patch(
            "backend.flow.plugins.components.collections.mysql.check_sqlfile_md5.JobApi.fast_execute_script"
        ) as execute_script:
            assert service._execute(_md5_execute_data({"change.sql": expected}), {}) is False

    execute_script.assert_not_called()
    storage.get_file_md5.assert_called_once_with("mysql/sqlfile/1/change.sql")
    error_text = str(service.log_error.call_args)
    assert "repo_mismatch" in error_text
    assert expected in error_text
    assert repo_digest in error_text
    assert "确认没有问题后再跳过本节点" in error_text


def test_repo_missing_file_does_not_run_host_script():
    service = CheckSqlFileMd5Service()
    service.log_error = MagicMock()
    storage = MagicMock()
    storage.get_file_md5.side_effect = FileExistsError("missing")

    with patch(
        "backend.flow.plugins.components.collections.mysql.check_sqlfile_md5.get_storage",
        return_value=storage,
    ):
        with patch(
            "backend.flow.plugins.components.collections.mysql.check_sqlfile_md5.JobApi.fast_execute_script"
        ) as execute_script:
            assert (
                service._execute(
                    _md5_execute_data({"change.sql": "d41d8cd98f00b204e9800998ecf8427e"}),
                    {},
                )
                is False
            )

    execute_script.assert_not_called()
    assert "repo_missing" in str(service.log_error.call_args)


def test_repo_match_still_runs_host_script():
    expected = "d41d8cd98f00b204e9800998ecf8427e"
    service = CheckSqlFileMd5Service()
    service.log_error = MagicMock()
    service.log_info = MagicMock()
    storage = MagicMock()
    storage.get_file_md5.return_value = expected.upper()

    with patch(
        "backend.flow.plugins.components.collections.mysql.check_sqlfile_md5.get_storage",
        return_value=storage,
    ):
        with patch(
            "backend.flow.plugins.components.collections.mysql.check_sqlfile_md5.FlowNode.objects.filter"
        ) as flow_node:
            flow_node.return_value.update.return_value = 1
            with patch(
                "backend.flow.plugins.components.collections.mysql.check_sqlfile_md5.JobApi.fast_execute_script",
                return_value={"result": True, "data": {"job_instance_id": 1}},
            ) as execute_script:
                assert service._execute(_md5_execute_data({"change.sql": expected}), {}) is True

    execute_script.assert_called_once()


def test_schedule_mismatch_fails_after_fetching_each_ip_log():
    expected = "d41d8cd98f00b204e9800998ecf8427e"
    actual = "0cc175b9c0f1b6a831c399e269772661"
    targets = [
        {"ip": "127.0.0.1", "bk_cloud_id": 0},
        {"ip": "127.0.0.2", "bk_cloud_id": 0},
    ]
    data = _Data(
        {
            "node_name": "md5",
            "sql_path": "/data/install/sqlfile_root-1/",
            "sql_files_md5": {"change.sql": expected},
        },
        {
            "ext_result": {"result": True, "data": {"job_instance_id": 10}},
            "exec_ips": targets,
        },
    )
    service = CheckSqlFileMd5Service()
    service.log_error = MagicMock()
    service.log_info = MagicMock()
    service.__status__ = MagicMock(
        return_value={
            "result": True,
            "data": {
                "finished": True,
                "job_instance": {"status": SUCCESS_LIST[0]},
                "step_instance_list": [{"step_instance_id": 20}],
            },
        }
    )
    service.__log__ = MagicMock(
        side_effect=[
            {
                "result": True,
                "data": {"log_content": "DBM_SQLFILE_MD5_V1\tchange.sql\t{}".format(actual)},
            },
            {
                "result": True,
                "data": {"log_content": "DBM_SQLFILE_MD5_V1\tchange.sql\t{}".format(expected)},
            },
        ]
    )

    assert service._schedule(data, {}) is False
    assert service.__log__.call_count == 2
    error_text = str(service.log_error.call_args_list)
    assert "change.sql" in error_text
    assert expected in error_text
    assert actual in error_text
    assert "确认没有问题后再跳过本节点" in error_text
