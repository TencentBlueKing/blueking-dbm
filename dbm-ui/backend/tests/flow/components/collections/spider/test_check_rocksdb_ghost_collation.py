# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.flow.plugins.components.collections.spider.check_rocksdb_ghost_collation import (
    CheckRocksDBGhostCollationService,
)
from backend.flow.utils.mysql.rocksdb_ghost_collation_check import GhostCollationFinding

MODULE_PATH = "backend.flow.plugins.components.collections.spider.check_rocksdb_ghost_collation"


def _make_data(cluster_id):
    data = MagicMock()
    data.get_one_of_inputs.return_value = {"cluster_id": cluster_id}
    return data


def test_findings_block_flow_and_log_formatted_message():
    cluster = SimpleNamespace(id=1)
    finding = GhostCollationFinding(
        cluster_id=1,
        cluster_domain="test.tendbcluster.db",
        shard_id="0",
        role="remote_master",
        host="127.0.0.1",
        port=3306,
        check_value="ON",
        exceptions_value="",
        reason="missing_exception",
    )
    service = CheckRocksDBGhostCollationService()
    service.log_error = MagicMock()

    with (
        patch(f"{MODULE_PATH}.Cluster.objects.get", return_value=cluster) as get_cluster,
        patch(f"{MODULE_PATH}.check_rocksdb_ghost_collation", return_value=[finding]) as check,
        patch(f"{MODULE_PATH}.format_ghost_collation_findings", return_value="formatted findings") as formatter,
    ):
        result = service._execute(_make_data(cluster.id), None)

    assert result is False
    get_cluster.assert_called_once_with(id=cluster.id)
    check.assert_called_once_with(cluster)
    formatter.assert_called_once_with([finding])
    service.log_error.assert_called_once_with("formatted findings")


def test_empty_findings_allow_flow_to_continue():
    cluster = SimpleNamespace(id=2)
    service = CheckRocksDBGhostCollationService()
    service.log_error = MagicMock()

    with (
        patch(f"{MODULE_PATH}.Cluster.objects.get", return_value=cluster),
        patch(f"{MODULE_PATH}.check_rocksdb_ghost_collation", return_value=[]) as check,
        patch(f"{MODULE_PATH}.format_ghost_collation_findings") as formatter,
    ):
        result = service._execute(_make_data(cluster.id), None)

    assert result is True
    check.assert_called_once_with(cluster)
    formatter.assert_not_called()
    service.log_error.assert_not_called()
