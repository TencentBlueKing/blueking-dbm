# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest

from backend.exceptions import ApiResultError
from backend.flow.utils.mongodb.mongodb_cluster_conf_tool import (
    MIGRATE_STATUS_DONE,
    MIGRATE_STATUS_PENDING,
    MongoClusterConfToolError,
    get_mongodb_cluster_by_domain,
    inspect_mongodb_cluster_conf,
    is_mongodb_cluster_conf_migrate_done,
    is_mongodb_cluster_conf_migrate_pending,
    list_mongodb_cluster_conf_migrate_domains,
    migrate_mongodb_cluster_conf_by_domain,
    migrate_mongodb_cluster_conf_pending_batch,
)


def _make_cluster(**overrides):
    cluster = MagicMock()
    cluster.id = overrides.get("id", 1)
    cluster.name = overrides.get("name", "cyc30")
    cluster.immute_domain = overrides.get("immute_domain", "cyc30.test.db")
    cluster.bk_biz_id = overrides.get("bk_biz_id", 3)
    cluster.cluster_type = overrides.get("cluster_type", "MongoReplicaSet")
    cluster.major_version = overrides.get("major_version", "mongodb-7.0")
    return cluster


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.Cluster.objects.get")
def test_get_mongodb_cluster_by_domain_rejects_non_mongodb(mock_get):
    mock_get.return_value = _make_cluster(cluster_type="RedisInstance")

    with pytest.raises(MongoClusterConfToolError, match="not MongoDB"):
        get_mongodb_cluster_by_domain("cyc30.test.db")


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.probe_mongodb_conf_files")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.resolve_cluster_dbconf_level_value")
def test_inspect_legacy_hit(mock_level_value, mock_probe):
    mock_level_value.return_value = "cyc30"
    mock_probe.side_effect = [
        [
            {"conf_file": "mongodb-7.0", "found": False, "owned": False, "status": "NOT_FOUND"},
            {
                "conf_file": "Mongodb-7",
                "found": True,
                "owned": True,
                "inherited": False,
                "status": "OWNED",
                "content": {
                    "key_file": {"conf_value": "dba-rs1", "level_name": "cluster", "level_value": "cyc30"},
                },
            },
        ],
        [{"conf_file": "mongodb-7.0", "found": False}, {"conf_file": "Mongodb-7", "found": True, "content": {}}],
    ]

    report = inspect_mongodb_cluster_conf(_make_cluster())

    assert report["effective"]["key_file"]["conf_value"] == "dba-rs1"
    assert report["effective"]["key_file"]["level_name"] == "cluster"
    assert report["effective_via"] == "Mongodb-7"
    assert report["effective_owned_via"] == "Mongodb-7"
    assert report["plat_used"] is False


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.probe_mongodb_conf_files")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.resolve_cluster_dbconf_level_value")
def test_inspect_inherited_legacy_not_owned(mock_level_value, mock_probe):
    mock_level_value.return_value = "dba-cycdevrs1"
    mock_probe.side_effect = [
        [
            {
                "conf_file": "mongodb-7.0",
                "found": True,
                "owned": True,
                "inherited": False,
                "status": "OWNED",
                "content": {
                    "key_file": {"conf_value": "", "level_name": "plat", "level_value": "0"},
                },
            },
            {
                "conf_file": "Mongodb-7",
                "found": True,
                "owned": False,
                "inherited": True,
                "status": "INHERITED",
                "content": {
                    "key_file": {"conf_value": "", "level_name": "plat", "level_value": "0"},
                    "cacheSizeGB": {"conf_value": "10", "level_name": "app", "level_value": "3"},
                },
            },
        ],
        [],
    ]

    report = inspect_mongodb_cluster_conf(_make_cluster())

    assert report["effective_owned_via"] == "mongodb-7.0"
    assert report["probes"][1]["status"] == "INHERITED"
    assert report["probes"][1]["content"]["cacheSizeGB"]["level_name"] == "app"


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.probe_mongodb_conf_files")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.resolve_cluster_dbconf_level_value")
def test_inspect_cluster_miss_uses_plat(mock_level_value, mock_probe):
    mock_level_value.return_value = "cyc30"
    mock_probe.side_effect = [
        [
            {"conf_file": "mongodb-7.0", "found": False},
            {"conf_file": "Mongodb-7", "found": False},
        ],
        [
            {"conf_file": "mongodb-7.0", "found": False},
            {
                "conf_file": "Mongodb-7",
                "found": True,
                "content": {
                    "key_file": {"conf_value": "plat-rs", "level_name": "plat", "level_value": "0"},
                },
            },
        ],
    ]

    report = inspect_mongodb_cluster_conf(_make_cluster())

    assert report["plat_used"] is True
    assert report["effective_via"] == "plat"
    assert report["effective"]["key_file"]["conf_value"] == "plat-rs"
    assert report["effective"]["key_file"]["level_name"] == "plat"


def _empty_level_value_meta(**overrides):
    meta = {
        "target_level_value": "cyc30.test.db",
        "dry_run": True,
        "force": False,
        "migrations": [],
        "migrated_count": 0,
        "skipped_count": 0,
    }
    meta.update(overrides)
    return meta


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool._role_overwrite_blocked", return_value=None)
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_level_value")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_to_role")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.query_mongodb_dbconf_content")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.get_mongodb_cluster_by_domain")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.resolve_cluster_dbconf_level_value")
def test_migrate_dry_run_does_not_write(
    mock_level_value, mock_get_cluster, mock_query, mock_migrate, mock_lv_migrate, _mock_role_blocked
):
    cluster = _make_cluster(major_version="mongodb-3.0")
    mock_get_cluster.return_value = cluster
    mock_level_value.return_value = "cyc30"
    mock_query.return_value = {"key_file": "dba-rs1", "cacheSizeGB": "1", "oplogSizeMB": "5120"}
    mock_lv_migrate.return_value = _empty_level_value_meta(dry_run=True)

    report = migrate_mongodb_cluster_conf_by_domain(
        "cyc30.test.db",
        target_version="mongodb-7.0",
        dry_run=True,
    )

    assert report["preview_content"]["key_file"] == "dba-rs1"
    assert report["migrated"] is False
    assert report["skipped"] is False
    assert report["level_value_meta"]["migrated_count"] == 0
    mock_migrate.assert_not_called()
    mock_lv_migrate.assert_called_once_with(cluster=cluster, dry_run=True, force=False)


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool._role_overwrite_blocked", return_value=None)
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_level_value")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_to_role")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.query_mongodb_dbconf_content")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.get_mongodb_cluster_by_domain")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.resolve_cluster_dbconf_level_value")
def test_migrate_apply_writes(
    mock_level_value, mock_get_cluster, mock_query, mock_migrate, mock_lv_migrate, _mock_role_blocked
):
    cluster = _make_cluster(major_version="mongodb-3.0")
    mock_get_cluster.return_value = cluster
    mock_level_value.return_value = "cyc30"
    mock_query.return_value = {"key_file": "dba-rs1", "cacheSizeGB": "1", "oplogSizeMB": "5120"}
    mock_migrate.return_value = {
        "migrated": True,
        "deleted_conf_file": "Mongodb-3",
        "deleted_conf_files": ["Mongodb-3"],
        "target_conf_files": ["mongod.conf"],
    }
    mock_lv_migrate.return_value = _empty_level_value_meta(dry_run=False, migrated_count=1)

    report = migrate_mongodb_cluster_conf_by_domain(
        "cyc30.test.db",
        target_version="mongodb-7.0",
        dry_run=False,
    )

    assert report["migrated"] is True
    assert report["deleted_conf_file"] == "Mongodb-3"
    assert report["level_value_meta"]["migrated_count"] == 1
    mock_migrate.assert_called_once()
    mock_lv_migrate.assert_called_once_with(cluster=cluster, dry_run=False, force=False)


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool._role_overwrite_blocked", return_value=None)
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_level_value")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_to_role")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.query_mongodb_dbconf_content")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.get_mongodb_cluster_by_domain")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.resolve_cluster_dbconf_level_value")
def test_migrate_same_major_minor_still_migrates_to_role(
    mock_level_value, mock_get_cluster, mock_query, mock_migrate, mock_lv_migrate, _mock_role_blocked
):
    cluster = _make_cluster(major_version="mongodb-7.0")
    mock_get_cluster.return_value = cluster
    mock_level_value.return_value = "cyc30"
    mock_query.return_value = {"key_file": "dba-rs1", "cacheSizeGB": "1", "oplogSizeMB": "5120"}
    mock_migrate.return_value = {
        "migrated": True,
        "deleted_conf_files": ["mongodb-7.0"],
        "target_conf_files": ["mongod.conf"],
    }
    mock_lv_migrate.return_value = _empty_level_value_meta(dry_run=False)

    report = migrate_mongodb_cluster_conf_by_domain(
        "cyc30.test.db",
        target_version="mongodb-7.0.14",
        dry_run=False,
    )

    assert report["migrated"] is True
    mock_migrate.assert_called_once()
    mock_lv_migrate.assert_called_once()


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_level_value")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.query_mongodb_dbconf_content")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.get_mongodb_cluster_by_domain")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.resolve_cluster_dbconf_level_value")
def test_migrate_skips_when_source_missing(mock_level_value, mock_get_cluster, mock_query, mock_lv_migrate):
    cluster = _make_cluster(major_version="mongodb-3.0")
    mock_get_cluster.return_value = cluster
    mock_level_value.return_value = "cyc30"
    mock_query.side_effect = ApiResultError("cannot find parent level")
    mock_lv_migrate.return_value = _empty_level_value_meta(dry_run=False)

    report = migrate_mongodb_cluster_conf_by_domain(
        "cyc30.test.db",
        target_version="mongodb-7.0",
        dry_run=False,
    )

    assert report["skipped"] is True
    assert "not found" in report["reason"]
    mock_lv_migrate.assert_called_once()


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool._role_overwrite_blocked", return_value=None)
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_level_value")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_metadata_versions")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_to_role")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.query_mongodb_owned_content_at_level_values")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.get_mongodb_cluster_by_domain")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.resolve_cluster_dbconf_level_value")
def test_migrate_from_M_dry_run(
    mock_level_value,
    mock_get_cluster,
    mock_query,
    mock_migrate,
    mock_version_meta,
    mock_lv_migrate,
    _mock_role_blocked,
):
    cluster = _make_cluster(major_version="mongodb-7.0")
    mock_get_cluster.return_value = cluster
    mock_level_value.return_value = "cyc30.test.db"
    mock_query.return_value = (
        {"key_file": "dba-rs1", "cacheSizeGB": "1", "oplogSizeMB": "5120"},
        "cyc30",
    )
    mock_version_meta.return_value = {"skipped": True, "reason": "not x.y.z"}
    mock_lv_migrate.return_value = _empty_level_value_meta(
        dry_run=True,
        migrated_count=1,
        migrations=[
            {
                "conf_file": "Mongodb-7",
                "source_level_value": "cyc30",
                "target_level_value": "cyc30.test.db",
                "status": "would_migrate",
                "reason": "",
            }
        ],
    )

    report = migrate_mongodb_cluster_conf_by_domain(
        "cyc30.test.db",
        to_role=True,
        from_kind="M",
        dry_run=True,
    )

    assert report["to_role"] is True
    assert report["from_kind"] == "M"
    assert report["source_conf_file"] == "Mongodb-7"
    assert report["source_level_value"] == "cyc30"
    assert report["target_conf_file"] == "mongod.conf"
    assert report["preview_content"]["key_file"] == "dba-rs1"
    assert report["version_meta"]["skipped"] is True
    assert report["level_value_meta"]["migrated_count"] == 1
    mock_migrate.assert_not_called()
    mock_query.assert_called_once()
    assert mock_query.call_args.kwargs["conf_file"] == "Mongodb-7"
    mock_version_meta.assert_called_once_with(cluster, dry_run=True)
    mock_lv_migrate.assert_called_once_with(cluster=cluster, dry_run=True, force=False)


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool._role_overwrite_blocked", return_value=None)
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_level_value")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_metadata_versions")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_to_role")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.query_mongodb_owned_content_at_level_values")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.get_mongodb_cluster_by_domain")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.resolve_cluster_dbconf_level_value")
def test_migrate_from_mm_apply(
    mock_level_value,
    mock_get_cluster,
    mock_query,
    mock_migrate,
    mock_version_meta,
    mock_lv_migrate,
    _mock_role_blocked,
):
    cluster = _make_cluster(major_version="mongodb-7.0.14")
    mock_get_cluster.return_value = cluster
    mock_level_value.return_value = "cyc30.test.db"
    mock_query.return_value = (
        {"key_file": "dba-rs1", "cacheSizeGB": "1", "oplogSizeMB": "5120"},
        "cyc30.test.db",
    )
    mock_migrate.return_value = {
        "migrated": True,
        "deleted_conf_file": "mongodb-7.0",
        "deleted_conf_files": ["mongodb-7.0"],
    }
    mock_version_meta.return_value = {
        "migrated": True,
        "target_cluster_version": "mongodb-7.0.14",
        "target_instance_version": "mongodb-7.0.14",
    }
    mock_lv_migrate.return_value = _empty_level_value_meta(dry_run=False, migrated_count=1)

    report = migrate_mongodb_cluster_conf_by_domain(
        "cyc30.test.db",
        to_role=True,
        from_kind="mm",
        dry_run=False,
        force=True,
    )

    assert report["migrated"] is True
    assert report["from_kind"] == "mm"
    assert report["source_conf_file"] == "mongodb-7.0"
    assert report["deleted_conf_file"] == "mongodb-7.0"
    assert report["version_meta"]["migrated"] is True
    assert report["level_value_meta"]["migrated_count"] == 1
    mock_migrate.assert_called_once_with(
        bk_biz_id=cluster.bk_biz_id,
        namespace=cluster.cluster_type,
        level_value="cyc30.test.db",
        version="mongodb-7.0.14",
        from_kind="mm",
        force=True,
    )
    mock_version_meta.assert_called_once_with(cluster, dry_run=False)
    mock_lv_migrate.assert_called_once_with(cluster=cluster, dry_run=False, force=True)


@patch(
    "backend.flow.utils.mongodb.mongodb_cluster_conf_tool._cluster_has_versioned_dbconf_anywhere", return_value=True
)
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_level_value")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_metadata_versions")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_to_role")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.query_mongodb_owned_content_at_level_values")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.get_mongodb_cluster_by_domain")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.resolve_cluster_dbconf_level_value")
def test_migrate_to_role_skips_version_meta_when_source_missing(
    mock_level_value,
    mock_get_cluster,
    mock_query,
    mock_migrate,
    mock_version_meta,
    mock_lv_migrate,
    _mock_has_versioned,
):
    cluster = _make_cluster(major_version="mongodb-7.0")
    mock_get_cluster.return_value = cluster
    mock_level_value.return_value = "cyc30.test.db"
    mock_query.side_effect = ApiResultError("cannot find parent level")
    mock_lv_migrate.return_value = _empty_level_value_meta(dry_run=True)

    report = migrate_mongodb_cluster_conf_by_domain(
        "cyc30.test.db",
        to_role=True,
        from_kind="M",
        dry_run=True,
    )

    assert report["skipped"] is True
    assert report["version_meta"] is None
    mock_version_meta.assert_not_called()
    mock_migrate.assert_not_called()


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool._owned_conf_files_across_levels")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_level_value")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_metadata_versions")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_to_role")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.query_mongodb_owned_content_at_level_values")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.get_mongodb_cluster_by_domain")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.resolve_cluster_dbconf_level_value")
def test_migrate_to_role_dry_run_blocks_role_overwrite_without_force(
    mock_level_value,
    mock_get_cluster,
    mock_query,
    mock_migrate,
    mock_version_meta,
    mock_lv_migrate,
    mock_owned_across,
):
    cluster = _make_cluster(major_version="mongodb-7.0")
    mock_get_cluster.return_value = cluster
    mock_level_value.return_value = "cyc30.test.db"
    mock_query.return_value = (
        {"key_file": "dba-rs1", "cacheSizeGB": "1", "oplogSizeMB": "5120"},
        "cyc30",
    )
    mock_owned_across.return_value = {"Mongodb-7", "mongod.conf"}
    mock_lv_migrate.return_value = _empty_level_value_meta(dry_run=True)

    report = migrate_mongodb_cluster_conf_by_domain(
        "cyc30.test.db",
        to_role=True,
        from_kind="M",
        dry_run=True,
        force=False,
    )

    assert report["skipped"] is True
    assert "force" in report["reason"]
    assert report["version_meta"] is None
    mock_version_meta.assert_not_called()
    mock_migrate.assert_not_called()


def _make_versioned_cluster(major_version, storage_versions=None, proxy_versions=None):
    cluster = _make_cluster(major_version=major_version)
    storage_versions = storage_versions if storage_versions is not None else [""]
    proxy_versions = proxy_versions if proxy_versions is not None else []

    storages = []
    for idx, ver in enumerate(storage_versions, start=1):
        inst = MagicMock()
        inst.id = idx
        inst.version = ver
        storages.append(inst)
    proxies = []
    for idx, ver in enumerate(proxy_versions, start=100):
        inst = MagicMock()
        inst.id = idx
        inst.version = ver
        proxies.append(inst)

    cluster.storageinstance_set.all.return_value = storages
    cluster.proxyinstance_set.all.return_value = proxies
    return cluster, storages, proxies


def test_migrate_metadata_versions_skips_without_package_for_mm():
    from backend.flow.utils.mongodb.mongodb_cluster_conf_tool import migrate_mongodb_cluster_metadata_versions

    cluster, _, _ = _make_versioned_cluster("mongodb-7.0", storage_versions=[""], proxy_versions=[])
    with patch(
        "backend.flow.utils.mongodb.mongodb_cluster_conf_tool.lookup_mongodb_package",
        return_value=None,
    ):
        report = migrate_mongodb_cluster_metadata_versions(cluster, dry_run=True)
    assert report["skipped"] is True
    assert "cannot resolve" in report["reason"]


def test_migrate_metadata_versions_dry_run_preview():
    from backend.flow.utils.mongodb.mongodb_cluster_conf_tool import migrate_mongodb_cluster_metadata_versions

    cluster, storages, proxies = _make_versioned_cluster(
        "mongodb-4.4.24",
        storage_versions=["", "Mongodb-4"],
        proxy_versions=["mongos"],
    )
    report = migrate_mongodb_cluster_metadata_versions(cluster, dry_run=True)
    assert report["skipped"] is False
    assert report["migrated"] is False
    assert report["target_instance_version"] == "mongodb-4.4.24"
    assert report["target_cluster_version"] == "mongodb-4.4.24"
    assert report["storage_count"] == 2
    assert report["proxy_count"] == 1
    assert storages[0].version == ""
    assert cluster.major_version == "mongodb-4.4.24"


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.apply_mongodb_metadata_versions_to_cluster")
def test_migrate_metadata_versions_apply(mock_apply):
    from backend.flow.utils.mongodb.mongodb_cluster_conf_tool import migrate_mongodb_cluster_metadata_versions

    cluster, _, _ = _make_versioned_cluster("4.4.24", storage_versions=["old"], proxy_versions=["old"])
    report = migrate_mongodb_cluster_metadata_versions(cluster, dry_run=False)
    assert report["migrated"] is True
    assert report["target_instance_version"] == "mongodb-4.4.24"
    assert report["target_cluster_version"] == "mongodb-4.4.24"
    assert cluster.major_version == "mongodb-4.4.24"
    mock_apply.assert_called_once_with(cluster, "mongodb-4.4.24")


@patch("backend.flow.utils.mongodb.mongodb_conf_file.DBConfigApi.list_level_values")
@patch("backend.flow.utils.mongodb.mongodb_conf_file.DBConfigApi.query_conf_item")
def test_probe_mongodb_conf_files_reports_owned_vs_inherited(mock_query, mock_list):
    from backend.flow.utils.mongodb.mongodb_conf_file import probe_mongodb_conf_files

    mock_list.return_value = [
        {
            "bk_biz_id": "3",
            "namespace": "MongoReplicaSet",
            "conf_type": "dbconf",
            "conf_file": "mongodb-7.0",
            "level_name": "cluster",
            "level_value": "dba-cycdevrs1",
        }
    ]
    mock_query.side_effect = [
        {
            "content": {
                "key_file": {"conf_value": "mm", "level_name": "cluster", "level_value": "dba-cycdevrs1"},
            }
        },
        {
            "content": {
                "key_file": {"conf_value": "legacy", "level_name": "plat", "level_value": "0"},
            }
        },
    ]

    probes = probe_mongodb_conf_files(
        bk_biz_id="3",
        level_name="cluster",
        level_value="dba-cycdevrs1",
        namespace="MongoReplicaSet",
        version="mongodb-7.0",
        conf_files=["mongodb-7.0", "Mongodb-7"],
    )

    assert probes[0]["status"] == "OWNED"
    assert probes[1]["status"] == "INHERITED"
    assert probes[1]["inherited"] is True
    assert probes[0]["content"]["key_file"]["level_name"] == "cluster"
    assert probes[1]["content"]["key_file"]["level_name"] == "plat"


@patch("backend.flow.utils.mongodb.mongodb_conf_file.DBConfigApi.list_level_values", return_value=[])
@patch("backend.flow.utils.mongodb.mongodb_conf_file.DBConfigApi.query_conf_item")
def test_probe_mongodb_conf_files_reports_each_file(mock_query, _mock_list):
    from backend.flow.utils.mongodb.mongodb_conf_file import probe_mongodb_conf_files

    mock_query.side_effect = [
        ApiResultError("cannot find parent level"),
        {
            "content": {
                "key_file": {"conf_value": "dba-rs1", "level_name": "cluster", "level_value": "cyc30"},
            }
        },
    ]

    probes = probe_mongodb_conf_files(
        bk_biz_id="3",
        level_name="cluster",
        level_value="cyc30",
        namespace="MongoReplicaSet",
        version="mongodb-7.0",
        conf_files=["mongodb-7.0", "Mongodb-7"],
    )

    assert len(probes) == 2
    assert probes[0]["found"] is False
    assert probes[1]["found"] is True
    assert probes[1]["content"]["key_file"]["conf_value"] == "dba-rs1"
    assert probes[1]["content"]["key_file"]["level_name"] == "cluster"


def test_format_probe_content_shows_level():
    from backend.flow.utils.mongodb.mongodb_cluster_conf_tool import _format_probe_content

    text = _format_probe_content(
        {
            "key_file": {"conf_value": "dba-rs1", "level_name": "cluster"},
            "cacheSizeGB": {"conf_value": "0", "level_name": "plat"},
            "oplogSizeMB": {"conf_value": "10240", "level_name": "cluster"},
        }
    )
    assert "key_file=dba-rs1@cluster" in text
    assert "cacheSizeGB=0@plat" in text
    assert "oplogSizeMB=10240@cluster" in text


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.cluster_owns_versioned_dbconf")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.cluster_has_legacy_dbconf_level_value")
def test_migrate_status_pending_and_done(mock_legacy, mock_owns_versioned):
    # pending: versioned conf owned
    mock_legacy.return_value = False
    mock_owns_versioned.return_value = True
    assert is_mongodb_cluster_conf_migrate_pending(_make_cluster()) is True
    assert is_mongodb_cluster_conf_migrate_done(_make_cluster()) is False

    # done: neither
    mock_owns_versioned.return_value = False
    assert is_mongodb_cluster_conf_migrate_done(_make_cluster()) is True
    assert is_mongodb_cluster_conf_migrate_pending(_make_cluster()) is False

    # pending: legacy level_value only
    mock_legacy.return_value = True
    mock_owns_versioned.return_value = False
    assert is_mongodb_cluster_conf_migrate_pending(_make_cluster()) is True
    assert is_mongodb_cluster_conf_migrate_done(_make_cluster()) is False


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.is_mongodb_cluster_conf_migrate_pending")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.is_mongodb_cluster_conf_migrate_done")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.iter_mongodb_clusters")
def test_list_migrate_domains_sorted_and_filtered(mock_iter, mock_done, mock_pending):
    clusters = [
        _make_cluster(id=3, immute_domain="c3.db", major_version="mongodb-3.2.11", bk_biz_id=3),
        _make_cluster(id=1, immute_domain="c1.db", major_version="mongodb-3.2", bk_biz_id=3),
        _make_cluster(id=2, immute_domain="c2.db", major_version="mongodb-4.0.28", bk_biz_id=9),
        _make_cluster(id=4, immute_domain="c4.db", major_version="", bk_biz_id=3),
    ]
    mock_iter.return_value = [clusters[1], clusters[0], clusters[3]]
    mock_pending.side_effect = lambda c: c.immute_domain == "c3.db"
    mock_done.side_effect = lambda c: c.immute_domain == "c1.db"

    pending = list_mongodb_cluster_conf_migrate_domains(status=MIGRATE_STATUS_PENDING, bk_biz_id=3)
    done = list_mongodb_cluster_conf_migrate_domains(status=MIGRATE_STATUS_DONE, bk_biz_id=3)

    assert [e["immute_domain"] for e in pending] == ["c3.db"]
    assert [e["immute_domain"] for e in done] == ["c1.db"]
    mock_iter.assert_called_with(bk_biz_id=3)


@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.migrate_mongodb_cluster_conf_by_domain")
@patch("backend.flow.utils.mongodb.mongodb_cluster_conf_tool.list_mongodb_cluster_conf_migrate_domains")
def test_migrate_pending_batch_takes_limit(mock_list, mock_migrate):
    mock_list.return_value = [
        {
            "id": 1,
            "immute_domain": "a.db",
            "name": "a",
            "major_version": "mongodb-3.2.11",
            "bk_biz_id": 3,
            "cluster_type": "MongoReplicaSet",
        },
        {
            "id": 2,
            "immute_domain": "b.db",
            "name": "b",
            "major_version": "mongodb-4.0.28",
            "bk_biz_id": 3,
            "cluster_type": "MongoReplicaSet",
        },
        {
            "id": 3,
            "immute_domain": "c.db",
            "name": "c",
            "major_version": "mongodb-5.0.14",
            "bk_biz_id": 3,
            "cluster_type": "MongoReplicaSet",
        },
    ]
    mock_migrate.side_effect = lambda **kwargs: {
        "cluster": {"immute_domain": kwargs["cluster_domain"], "id": 0},
        "to_role": True,
        "from_kind": kwargs.get("from_kind"),
        "dry_run": kwargs["dry_run"],
        "migrated": False,
        "skipped": False,
        "reason": "dry-run",
        "level_value": "x",
        "source_version": "v",
        "target_version": "v",
        "source_conf_file": "mongodb-3.2",
        "target_conf_file": "mongod.conf",
        "preview_content": None,
        "preview_conf_items": None,
        "deleted_conf_file": None,
        "level_value_meta": None,
        "version_meta": None,
        "force": kwargs.get("force", False),
    }

    batch = migrate_mongodb_cluster_conf_pending_batch(limit=2, from_kind="mm", bk_biz_id=3, dry_run=True)

    assert batch["pending_total"] == 3
    assert batch["selected_count"] == 2
    assert batch["from_kind"] == "mm"
    assert [e["immute_domain"] for e in batch["selected"]] == ["a.db", "b.db"]
    assert mock_migrate.call_count == 2
    mock_migrate.assert_any_call(cluster_domain="a.db", dry_run=True, to_role=True, from_kind="mm", force=False)
    mock_migrate.assert_any_call(cluster_domain="b.db", dry_run=True, to_role=True, from_kind="mm", force=False)


def test_migrate_pending_batch_rejects_bad_limit():
    with pytest.raises(MongoClusterConfToolError, match="limit must be"):
        migrate_mongodb_cluster_conf_pending_batch(limit=0, from_kind="mm")
