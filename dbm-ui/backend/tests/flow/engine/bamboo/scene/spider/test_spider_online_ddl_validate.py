# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import call, patch

import pytest

from backend.flow.engine.bamboo.scene.spider.validate.exception import GhostCollationFailedException
from backend.flow.engine.bamboo.scene.spider.validate.spider_online_ddl_validate import TenDBClusterOnlineDDLValidator
from backend.flow.engine.controller.spider import SpiderController
from backend.flow.utils.mysql.rocksdb_ghost_collation_check import GhostCollationFinding
from backend.ticket.builders.tendbcluster.tendb_import_sqlfile import TenDBClusterSqlImportFlowBuilder

MODULE_PATH = "backend.flow.engine.bamboo.scene.spider.validate.spider_online_ddl_validate"


def make_finding(cluster_id, domain, host):
    return GhostCollationFinding(
        cluster_id=cluster_id,
        cluster_domain=domain,
        shard_id="0",
        role="remote_master",
        host=host,
        port=3306,
        check_value="ON",
        exceptions_value="",
        reason="missing_exception",
    )


def test_findings_raise_with_node_and_set_global_suggestion():
    cluster = SimpleNamespace(id=1)
    finding = make_finding(1, "test-1.tendbcluster.db", "127.0.0.1")

    with (
        patch(f"{MODULE_PATH}.Cluster.objects.get", return_value=cluster),
        patch(f"{MODULE_PATH}.check_rocksdb_ghost_collation", return_value=[finding]),
        pytest.raises(GhostCollationFailedException) as exc_info,
    ):
        TenDBClusterOnlineDDLValidator({"cluster_ids": [1]})

    message = str(exc_info.value)
    assert "127.0.0.1:3306" in message
    assert "SET GLOBAL rocksdb_strict_collation_exceptions" in message


def test_empty_findings_pass():
    cluster = SimpleNamespace(id=1)

    with (
        patch(f"{MODULE_PATH}.Cluster.objects.get", return_value=cluster),
        patch(f"{MODULE_PATH}.check_rocksdb_ghost_collation", return_value=[]),
    ):
        assert TenDBClusterOnlineDDLValidator({"cluster_ids": [1]}) is None


def test_multiple_clusters_aggregate_errors_and_raise_once():
    clusters = {1: SimpleNamespace(id=1), 2: SimpleNamespace(id=2)}
    finding = make_finding(2, "test-2.tendbcluster.db", "127.0.0.2")

    with (
        patch(f"{MODULE_PATH}.Cluster.objects.get", side_effect=lambda id: clusters[id]) as get_cluster,
        patch(f"{MODULE_PATH}.check_rocksdb_ghost_collation", side_effect=[[], [finding]]) as check,
        pytest.raises(GhostCollationFailedException) as exc_info,
    ):
        TenDBClusterOnlineDDLValidator({"cluster_ids": [1, 2]})

    assert "test-2.tendbcluster.db" in str(exc_info.value)
    assert get_cluster.call_args_list == [call(id=1), call(id=2)]
    assert check.call_args_list == [call(clusters[1]), call(clusters[2])]


def test_sql_import_controller_validator_is_wired_to_ticket_builder():
    assert SpiderController.spider_sql_import_scene.validator is TenDBClusterOnlineDDLValidator
    assert TenDBClusterSqlImportFlowBuilder.validator is TenDBClusterOnlineDDLValidator
