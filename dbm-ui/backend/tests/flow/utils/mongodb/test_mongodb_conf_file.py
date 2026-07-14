# -*- coding: utf-8 -*-
from unittest.mock import patch

import pytest

from backend.exceptions import ApiResultError
from backend.flow.utils.mongodb.mongodb_conf_file import (
    MongoDbconfLevelValueNotMigratedError,
    _cluster_owned_content_from_list_resp,
    assert_cluster_dbconf_level_migrated,
    cluster_has_legacy_dbconf_level_value,
    legacy_cluster_dbconf_level_values,
    migrate_mongodb_cluster_conf_file,
    migrate_mongodb_cluster_level_value,
    mongodb_conf_file_candidates,
    mongodb_conf_file_legacy,
    mongodb_conf_file_mm,
    mongodb_role_conf_files,
    mongodb_versioned_conf_file_candidates,
    query_mongodb_dbconf_content,
    resolve_cluster_dbconf_level_value,
    resolve_flow_dbconf_level_value,
)


def test_mongodb_conf_file_naming():
    assert mongodb_conf_file_mm("mongodb-3.0.24") == "mongodb-3.0"
    assert mongodb_conf_file_legacy("mongodb-3.0.24") == "Mongodb-3"
    assert mongodb_versioned_conf_file_candidates("mongodb-3.0.24") == ["mongodb-3.0", "Mongodb-3"]
    assert mongodb_conf_file_candidates("mongodb-3.0.24") == ["mongodb-3.0", "Mongodb-3"]
    assert mongodb_conf_file_candidates("mongodb-3.0.24", namespace="MongoReplicaSet") == [
        "mongod.conf",
        "mongodb-3.0",
        "Mongodb-3",
    ]
    assert mongodb_role_conf_files("MongoShardedCluster") == [
        "shardsvr.conf",
        "configsvr.conf",
        "mongos.conf",
    ]
    assert mongodb_conf_file_mm("mongodb-8.0.0") == "mongodb-8.0"
    assert mongodb_conf_file_legacy("mongodb-8.0.0") == "Mongodb-8"


def test_cluster_owned_content_excludes_plat_inherited():
    content = {
        "key_file": {
            "conf_name": "key_file",
            "conf_value": "dba-rs1",
            "level_name": "cluster",
            "level_value": "rs1.db",
        },
        "cacheSizeGB": {"conf_name": "cacheSizeGB", "conf_value": "0", "level_name": "plat", "level_value": "0"},
        "oplogSizeMB": {
            "conf_name": "oplogSizeMB",
            "conf_value": "10240",
            "level_name": "cluster",
            "level_value": "rs1.db",
        },
        "slowOpThresholdMs": {
            "conf_name": "slowOpThresholdMs",
            "conf_value": "200",
            "level_name": "plat",
            "level_value": "0",
        },
    }
    owned = _cluster_owned_content_from_list_resp(content)
    assert owned == {"key_file": "dba-rs1", "oplogSizeMB": "10240"}


def test_resolve_cluster_dbconf_level_value_uses_immute_domain():
    from unittest.mock import MagicMock

    cluster = MagicMock()
    cluster.immute_domain = "m1.cyc31rs2.dba.db"
    assert resolve_cluster_dbconf_level_value(cluster) == "m1.cyc31rs2.dba.db"

    cluster.immute_domain = "M1.Cyc31RS2.DBA.DB"
    assert resolve_cluster_dbconf_level_value(cluster) == "m1.cyc31rs2.dba.db"

    cluster.immute_domain = None
    assert resolve_cluster_dbconf_level_value(cluster) == ""


@patch("backend.flow.utils.mongodb.mongodb_conf_file.AppCache.objects.get")
def test_legacy_cluster_dbconf_level_values_replica_set(mock_app_get):
    from unittest.mock import MagicMock

    cluster = MagicMock()
    cluster.name = "dba-cyc31rs2"
    cluster.immute_domain = "m1.cyc31rs2.dba.db"
    cluster.cluster_type = "MongoReplicaSet"
    assert legacy_cluster_dbconf_level_values(cluster) == ["dba-cyc31rs2"]


@patch("backend.flow.utils.mongodb.mongodb_conf_file.AppCache.objects.get")
def test_legacy_cluster_dbconf_level_values_includes_mixed_case_domain(mock_app_get):
    from unittest.mock import MagicMock

    cluster = MagicMock()
    cluster.name = "dba-cyc31rs2"
    cluster.immute_domain = "M1.Cyc31RS2.DBA.DB"
    cluster.cluster_type = "MongoReplicaSet"
    assert legacy_cluster_dbconf_level_values(cluster) == [
        "M1.Cyc31RS2.DBA.DB",
        "dba-cyc31rs2",
    ]


@patch("backend.flow.utils.mongodb.mongodb_conf_file.AppCache.objects.get")
def test_legacy_cluster_dbconf_level_values_sharded(mock_app_get):
    from unittest.mock import MagicMock

    mock_app_get.return_value.db_app_abbr = "dba"
    cluster = MagicMock()
    cluster.name = "mycluster"
    cluster.immute_domain = "mongos.mycluster.dba.db"
    cluster.cluster_type = "MongoShardedCluster"
    cluster.bk_biz_id = 3
    assert legacy_cluster_dbconf_level_values(cluster) == ["mycluster", "dba-mycluster"]


@patch("backend.flow.utils.mongodb.mongodb_conf_file.Cluster.objects.filter")
def test_resolve_flow_dbconf_level_value_maps_cluster_name(mock_filter):
    cluster = mock_filter.return_value.first.return_value
    cluster.immute_domain = "M1.Cyc31RS2.DBA.DB"
    assert (
        resolve_flow_dbconf_level_value(
            bk_biz_id=3,
            cluster_type="MongoReplicaSet",
            cluster_name="dba-cyc31rs2",
        )
        == "m1.cyc31rs2.dba.db"
    )


@patch("backend.flow.utils.mongodb.mongodb_conf_file.Cluster.objects.filter")
def test_resolve_flow_dbconf_level_value_keeps_shard_set_id(mock_filter):
    mock_filter.return_value.first.return_value = None
    assert (
        resolve_flow_dbconf_level_value(
            bk_biz_id=3,
            cluster_type="MongoShardedCluster",
            cluster_name="mycluster-s1",
        )
        == "mycluster-s1"
    )


@patch("backend.flow.utils.mongodb.mongodb_conf_file.delete_mongodb_cluster_dbconf")
@patch("backend.flow.utils.mongodb.mongodb_conf_file.upsert_mongodb_cluster_dbconf_file")
@patch("backend.flow.utils.mongodb.mongodb_conf_file.query_mongodb_cluster_level_owned_content")
@patch("backend.flow.utils.mongodb.mongodb_conf_file.list_cluster_owned_conf_files")
@patch("backend.flow.utils.mongodb.mongodb_conf_file.legacy_cluster_dbconf_level_values")
def test_migrate_mongodb_cluster_level_value_apply(
    mock_legacy_values,
    mock_list_owned,
    mock_query_owned,
    mock_upsert_file,
    mock_delete,
):
    from unittest.mock import MagicMock

    cluster = MagicMock()
    cluster.id = 64
    cluster.name = "dba-cyc31rs2"
    cluster.immute_domain = "m1.cyc31rs2.dba.db"
    cluster.bk_biz_id = 3
    cluster.cluster_type = "MongoReplicaSet"

    mock_legacy_values.return_value = ["dba-cyc31rs2"]
    mock_list_owned.side_effect = [
        set(),
        {"mongodb-3.2"},
    ]
    mock_query_owned.return_value = {
        "key_file": "dba-cyc31rs2",
        "cacheSizeGB": "1",
        "oplogSizeMB": "5120",
    }

    result = migrate_mongodb_cluster_level_value(cluster=cluster, dry_run=False)

    assert result["migrated_count"] == 1
    assert result["migrations"][0]["status"] == "migrated"
    mock_upsert_file.assert_called_once()
    assert mock_upsert_file.call_args.kwargs["level_value"] == "m1.cyc31rs2.dba.db"
    # Same conf_file name only; no versioned -> role conversion during level_value migrate.
    assert mock_upsert_file.call_args.kwargs["conf_file"] == "mongodb-3.2"
    mock_delete.assert_called_once_with(
        bk_biz_id=3,
        namespace="MongoReplicaSet",
        level_value="dba-cyc31rs2",
        conf_file="mongodb-3.2",
    )


@patch("backend.flow.utils.mongodb.mongodb_conf_file.list_cluster_owned_conf_files")
@patch("backend.flow.utils.mongodb.mongodb_conf_file.legacy_cluster_dbconf_level_values")
def test_migrate_mongodb_cluster_level_value_skips_target_conflict(mock_legacy_values, mock_list_owned):
    from unittest.mock import MagicMock

    cluster = MagicMock()
    cluster.id = 64
    cluster.name = "dba-cyc31rs2"
    cluster.immute_domain = "m1.cyc31rs2.dba.db"
    cluster.bk_biz_id = 3
    cluster.cluster_type = "MongoReplicaSet"

    mock_legacy_values.return_value = ["dba-cyc31rs2"]
    mock_list_owned.side_effect = [
        {"mongodb-3.2"},
        {"mongodb-3.2"},
    ]

    result = migrate_mongodb_cluster_level_value(cluster=cluster, dry_run=False, force=False)

    assert result["migrated_count"] == 0
    assert result["skipped_count"] == 1
    assert result["migrations"][0]["status"] == "skipped"


def test_act_kwargs_dbconf_version_full_patch_without_init_info():
    """Replace flow sets payload db_version to mongodb-M.m.p but skips get_init_info."""
    from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

    kwargs = ActKwargs()
    kwargs.payload = {"db_version": "mongodb-3.0.15"}
    assert kwargs._mongodb_dbconf_version() == "mongodb-3.0"

    kwargs.db_release_version = "mongodb-3.0.15"
    assert kwargs._mongodb_dbconf_version() == "mongodb-3.0"

    kwargs.db_release_version = ""
    kwargs.payload["db_version"] = "3.0.15"
    assert kwargs._mongodb_dbconf_version() == "mongodb-3.0"


def test_ensure_flow_version_context_full_and_short():
    from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

    kwargs = ActKwargs()
    kwargs.payload = {"db_version": "mongodb-3.0.15"}
    kwargs.ensure_flow_version_context()
    assert kwargs.db_release_version == "mongodb-3.0.15"
    assert kwargs.db_release == "mongodb"
    assert kwargs.db_main_version == "3"
    assert kwargs.payload["db_version"] == "3.0.15"

    kwargs.ensure_flow_version_context()
    assert kwargs.payload["db_version"] == "3.0.15"

    kwargs2 = ActKwargs()
    kwargs2.payload = {"db_version": "3.0.15"}
    kwargs2.ensure_flow_version_context()
    assert kwargs2.db_release_version == "mongodb-3.0.15"
    assert kwargs2.payload["db_version"] == "3.0.15"


@patch("backend.flow.utils.mongodb.mongodb_conf_file.list_cluster_owned_conf_files")
@patch("backend.flow.utils.mongodb.mongodb_conf_file.legacy_cluster_dbconf_level_values")
def test_cluster_has_legacy_dbconf_level_value(mock_legacy_values, mock_list_owned):
    from unittest.mock import MagicMock

    cluster = MagicMock()
    mock_legacy_values.return_value = ["dba-cyc31rs2"]
    mock_list_owned.side_effect = [{"mongodb-3.2"}, set()]

    assert cluster_has_legacy_dbconf_level_value(cluster) is True

    mock_list_owned.side_effect = [set(), set()]
    assert cluster_has_legacy_dbconf_level_value(cluster) is False


@patch("backend.flow.utils.mongodb.mongodb_conf_file.cluster_has_legacy_dbconf_level_value", return_value=True)
@patch("backend.flow.utils.mongodb.mongodb_conf_file.Cluster.objects.filter")
def test_assert_cluster_dbconf_level_migrated_raises(mock_filter, _mock_has_legacy):
    from unittest.mock import MagicMock

    cluster = MagicMock()
    cluster.name = "dba-cyc31rs2"
    cluster.immute_domain = "m1.cyc31rs2.dba.db"
    mock_filter.return_value.first.return_value = cluster

    with pytest.raises(MongoDbconfLevelValueNotMigratedError) as exc_info:
        assert_cluster_dbconf_level_migrated(
            bk_biz_id=3,
            cluster_type="MongoReplicaSet",
            cluster_name="dba-cyc31rs2",
        )

    assert "mongodb_cluster_conf migrate" in str(exc_info.value)
    assert "m1.cyc31rs2.dba.db" in str(exc_info.value)


@patch("backend.flow.utils.mongodb.mongodb_conf_file.cluster_has_legacy_dbconf_level_value", return_value=False)
@patch("backend.flow.utils.mongodb.mongodb_conf_file.Cluster.objects.filter")
def test_assert_cluster_dbconf_level_migrated_passes(mock_filter, _mock_has_legacy):
    from unittest.mock import MagicMock

    mock_filter.return_value.first.return_value = MagicMock()
    assert_cluster_dbconf_level_migrated(
        bk_biz_id=3,
        cluster_type="MongoReplicaSet",
        cluster_name="dba-cyc31rs2",
    )


@patch("backend.flow.utils.mongodb.mongodb_conf_file.cluster_has_legacy_dbconf_level_value")
@patch("backend.flow.utils.mongodb.mongodb_conf_file.Cluster.objects.filter")
def test_assert_cluster_dbconf_level_migrated_skips_shard_set_id(mock_filter, mock_has_legacy):
    mock_filter.return_value.first.return_value = None
    assert_cluster_dbconf_level_migrated(
        bk_biz_id=3,
        cluster_type="MongoShardedCluster",
        cluster_name="mycluster-s1",
    )
    mock_has_legacy.assert_not_called()


@patch("backend.flow.utils.mongodb.mongodb_dataclass.assert_cluster_dbconf_level_migrated")
@patch("backend.flow.utils.mongodb.mongodb_dataclass.resolve_flow_dbconf_level_value")
@patch("backend.flow.utils.mongodb.mongodb_dataclass.query_mongodb_dbconf_content")
def test_get_cluster_key_file_fallback(mock_query, mock_resolve_level, _mock_assert_migrated):
    from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

    mock_resolve_level.return_value = "m1.cyc31rs1.dba.db"
    mock_query.return_value = {}
    kwargs = ActKwargs()
    kwargs.payload = {"bk_biz_id": "3", "db_version": "mongodb-3.0.15"}
    kwargs.cluster_type = "MongoReplicaSet"
    assert kwargs.get_cluster_key_file(cluster_name="cyc31rs1") == "cyc31rs1"

    mock_query.return_value = {"key_file": "dba-rs1"}
    assert kwargs.get_cluster_key_file(cluster_name="cyc31rs1") == "dba-rs1"
    mock_resolve_level.assert_called_with(bk_biz_id="3", cluster_type="MongoReplicaSet", cluster_name="cyc31rs1")


@patch("backend.flow.utils.mongodb.mongodb_conf_file.list_cluster_owned_conf_files", return_value={"mongodb-3.0"})
@patch("backend.flow.utils.mongodb.mongodb_conf_file.DBConfigApi.query_conf_item")
def test_query_mongodb_dbconf_content_falls_back_to_versioned(mock_query, _mock_owned):
    mock_query.side_effect = [
        ApiResultError("cannot find parent level"),
        {"content": {"key_file": "dba-rs1", "cacheSizeGB": "1"}},
    ]

    content = query_mongodb_dbconf_content(
        bk_biz_id="3",
        level_name="cluster",
        level_value="dba-rs1",
        namespace="MongoReplicaSet",
        version="mongodb-3.0.24",
        level_info={"module": "0"},
        plat_fallback=False,
    )

    assert content["key_file"] == "dba-rs1"
    assert mock_query.call_count == 2
    assert mock_query.call_args_list[0].kwargs["params"]["conf_file"] == "mongodb-3.0"
    assert mock_query.call_args_list[1].kwargs["params"]["conf_file"] == "Mongodb-3"


@patch("backend.flow.utils.mongodb.mongodb_conf_file.list_cluster_owned_conf_files", return_value={"mongodb-3.0"})
@patch("backend.flow.utils.mongodb.mongodb_conf_file.delete_mongodb_cluster_dbconf")
@patch("backend.flow.utils.mongodb.mongodb_conf_file.upsert_mongodb_cluster_dbconf_file")
@patch("backend.flow.utils.mongodb.mongodb_conf_file._query_cluster_dbconf_content_with_conf_file")
def test_migrate_mongodb_cluster_conf_file(mock_query, mock_upsert_file, mock_delete, _mock_owned):
    mock_query.return_value = (
        {
            "key_file": "dba-rs1",
            "cacheSizeGB": "1",
            "oplogSizeMB": "5120",
        },
        "Mongodb-3",
    )

    result = migrate_mongodb_cluster_conf_file(
        bk_biz_id=3,
        namespace="MongoReplicaSet",
        level_value="dba-rs1",
        source_version="mongodb-3.0",
        target_version="mongodb-3.6",
    )

    assert result["migrated"] is True
    assert "Mongodb-3" in (result.get("deleted_conf_files") or [result.get("deleted_conf_file")])
    mock_upsert_file.assert_called()
    assert mock_upsert_file.call_args.kwargs["conf_file"] == "mongod.conf"
    mock_delete.assert_called()


@patch("backend.flow.utils.mongodb.mongodb_conf_file.list_cluster_owned_conf_files", return_value={"mongod.conf"})
@patch("backend.flow.utils.mongodb.mongodb_conf_file.delete_mongodb_cluster_dbconf")
@patch("backend.flow.utils.mongodb.mongodb_conf_file.upsert_mongodb_cluster_dbconf_file")
@patch("backend.flow.utils.mongodb.mongodb_conf_file._query_cluster_dbconf_content_with_conf_file")
def test_migrate_skips_when_already_on_role_and_no_versioned(mock_query, mock_upsert, mock_delete, _mock_owned):
    mock_query.side_effect = ApiResultError("cannot find parent level")
    result = migrate_mongodb_cluster_conf_file(
        bk_biz_id=3,
        namespace="MongoReplicaSet",
        level_value="dba-rs1",
        source_version="mongodb-6.0",
        target_version="mongodb-6.0.27",
    )

    assert result["migrated"] is False
    mock_upsert.assert_not_called()
    mock_delete.assert_not_called()


@patch("backend.flow.utils.mongodb.mongodb_conf_file.list_cluster_owned_conf_files", return_value=set())
@patch("backend.flow.utils.mongodb.mongodb_conf_file.delete_mongodb_cluster_dbconf")
@patch("backend.flow.utils.mongodb.mongodb_conf_file.upsert_mongodb_cluster_dbconf_file")
@patch("backend.flow.utils.mongodb.mongodb_conf_file._query_cluster_dbconf_content_with_conf_file")
def test_migrate_returns_false_when_cluster_conf_missing(mock_query, mock_upsert, mock_delete, _mock_owned):
    mock_query.side_effect = ApiResultError("cannot find parent level")

    result = migrate_mongodb_cluster_conf_file(
        bk_biz_id=3,
        namespace="MongoReplicaSet",
        level_value="dba-rs1",
        source_version="mongodb-3.0",
        target_version="mongodb-3.6",
    )

    assert result["migrated"] is False
    mock_upsert.assert_not_called()
    mock_delete.assert_not_called()


@patch("backend.flow.utils.mongodb.mongodb_conf_file.list_cluster_owned_conf_files", return_value={"Mongodb-7"})
@patch("backend.flow.utils.mongodb.mongodb_conf_file.delete_mongodb_cluster_dbconf")
@patch("backend.flow.utils.mongodb.mongodb_conf_file.upsert_mongodb_cluster_dbconf_file")
@patch("backend.flow.utils.mongodb.mongodb_conf_file._query_cluster_dbconf_content_with_conf_file")
def test_migrate_from_M_to_role_deletes_source(mock_query, mock_upsert_file, mock_delete, _mock_owned):
    from backend.flow.utils.mongodb.mongodb_conf_file import migrate_mongodb_cluster_to_role

    mock_query.return_value = (
        {"key_file": "dba-rs1", "cacheSizeGB": "1", "oplogSizeMB": "5120"},
        "Mongodb-7",
    )

    result = migrate_mongodb_cluster_to_role(
        bk_biz_id=3,
        namespace="MongoReplicaSet",
        level_value="dba-rs1",
        version="mongodb-7.0",
        from_kind="M",
    )

    assert result["migrated"] is True
    assert result["deleted_conf_file"] == "Mongodb-7"
    mock_upsert_file.assert_called()
    assert mock_upsert_file.call_args.kwargs["conf_file"] == "mongod.conf"
    mock_delete.assert_called_once()
    assert mock_delete.call_args.kwargs["conf_file"] == "Mongodb-7"
    assert mock_query.call_args.kwargs["from_kind"] == "M"


@patch(
    "backend.flow.utils.mongodb.mongodb_conf_file.list_cluster_owned_conf_files",
    return_value={"Mongodb-7", "mongod.conf"},
)
@patch("backend.flow.utils.mongodb.mongodb_conf_file.delete_mongodb_cluster_dbconf")
@patch("backend.flow.utils.mongodb.mongodb_conf_file.upsert_mongodb_cluster_dbconf_file")
@patch("backend.flow.utils.mongodb.mongodb_conf_file._query_cluster_dbconf_content_with_conf_file")
def test_migrate_to_role_requires_force_when_role_exists(mock_query, mock_upsert_file, mock_delete, _mock_owned):
    from backend.flow.utils.mongodb.mongodb_conf_file import migrate_mongodb_cluster_to_role

    result = migrate_mongodb_cluster_to_role(
        bk_biz_id=3,
        namespace="MongoReplicaSet",
        level_value="cyc30.test.db",
        version="mongodb-7.0",
        from_kind="M",
        force=False,
    )

    assert result["migrated"] is False
    assert result["skipped"] is True
    assert "force" in result["reason"]
    mock_query.assert_not_called()
    mock_upsert_file.assert_not_called()
    mock_delete.assert_not_called()


@patch(
    "backend.flow.utils.mongodb.mongodb_conf_file.list_cluster_owned_conf_files",
    return_value={"Mongodb-7", "mongod.conf"},
)
@patch("backend.flow.utils.mongodb.mongodb_conf_file.delete_mongodb_cluster_dbconf")
@patch("backend.flow.utils.mongodb.mongodb_conf_file.upsert_mongodb_cluster_dbconf_file")
@patch("backend.flow.utils.mongodb.mongodb_conf_file._query_cluster_dbconf_content_with_conf_file")
def test_migrate_to_role_force_overwrites_existing_role(mock_query, mock_upsert_file, mock_delete, _mock_owned):
    from backend.flow.utils.mongodb.mongodb_conf_file import migrate_mongodb_cluster_to_role

    mock_query.return_value = (
        {"key_file": "dba-rs1", "cacheSizeGB": "1", "oplogSizeMB": "5120"},
        "Mongodb-7",
    )

    result = migrate_mongodb_cluster_to_role(
        bk_biz_id=3,
        namespace="MongoReplicaSet",
        level_value="cyc30.test.db",
        version="mongodb-7.0",
        from_kind="M",
        force=True,
    )

    assert result["migrated"] is True
    mock_upsert_file.assert_called()
    mock_delete.assert_called_once()
