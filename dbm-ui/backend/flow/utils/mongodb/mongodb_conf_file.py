# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import Any, Dict, List, Optional, Tuple

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import ConfFile, FormatType, LevelName, OpType, ReqType
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import AppCache, Cluster
from backend.exceptions import ApiResultError
from backend.flow.consts import DEFAULT_CONFIG_CONFIRM, DEFAULT_DB_MODULE_ID, ConfigTypeEnum
from backend.flow.utils.mongodb.version_utils import extract_mongodb_major_minor

# Role-based conf_file (version-independent).
MONGODB_CONF_FILE_MONGOD = ConfFile.MONGOD.value
MONGODB_CONF_FILE_SHARDSVR = ConfFile.SHARDSVR.value
MONGODB_CONF_FILE_CONFIGSVR = ConfFile.CONFIGSVR.value
MONGODB_CONF_FILE_MONGOS = ConfFile.MONGOS.value

_MONGODB_ROLE_CONF_FILES = {
    ClusterType.MongoReplicaSet.value: [MONGODB_CONF_FILE_MONGOD],
    ClusterType.MongoShardedCluster.value: [
        MONGODB_CONF_FILE_SHARDSVR,
        MONGODB_CONF_FILE_CONFIGSVR,
        MONGODB_CONF_FILE_MONGOS,
    ],
}

# Cluster-owned item names per role conf_file (for migrate / level_value copy).
_MONGODB_ROLE_OWNED_NAMES = {
    MONGODB_CONF_FILE_MONGOD: ["key_file", "cacheSizeGB", "oplogSizeMB", "slowOpThresholdMs"],
    MONGODB_CONF_FILE_SHARDSVR: ["cacheSizeGB", "oplogSizeMB", "slowOpThresholdMs"],
    MONGODB_CONF_FILE_CONFIGSVR: ["key_file", "cacheSizeGB", "oplogSizeMB", "slowOpThresholdMs"],
    MONGODB_CONF_FILE_MONGOS: [
        "destination",
        "slowOpThresholdMs",
        "net.compression.compressors",
        "taskExecutorPoolSize",
        "ShardingTaskExecutorPoolMinSize",
        "ShardingTaskExecutorPoolMaxSize",
    ],
}

# Flat legacy names used by flow payload / old single conf_file.
_LEGACY_FLAT_NAMES = {
    ClusterType.MongoReplicaSet.value: ["key_file", "cacheSizeGB", "oplogSizeMB", "slowOpThresholdMs"],
    ClusterType.MongoShardedCluster.value: [
        "key_file",
        "cacheSizeGB",
        "oplogSizeMB",
        "slowOpThresholdMs",
        "config_cacheSizeGB",
        "config_oplogSizeMB",
        "destination",
        "net.compression.compressors",
        "taskExecutorPoolSize",
        "ShardingTaskExecutorPoolMinSize",
        "ShardingTaskExecutorPoolMaxSize",
    ],
}


def mongodb_role_conf_files(namespace: str) -> List[str]:
    """Return role conf_file names for a MongoDB namespace."""
    return list(_MONGODB_ROLE_CONF_FILES.get(namespace) or [])


def mongodb_conf_file_mm(version: str) -> str:
    """Return legacy dbconfig conf_file in major.minor form, e.g. mongodb-3.0."""
    return "mongodb-{}".format(extract_mongodb_major_minor(version))


def mongodb_conf_file_legacy(version: str) -> str:
    """Return legacy dbconfig conf_file, e.g. Mongodb-3."""
    major, _, _ = extract_mongodb_major_minor(version).partition(".")
    return "Mongodb-{}".format(major)


# Source versioned conf_file kinds for --to-role --from=
FROM_MM = "mm"  # mongodb-x.y
FROM_M = "M"  # Mongodb-x
_FROM_KINDS = {FROM_MM, FROM_M}


def resolve_mongodb_versioned_conf_file(version: str, from_kind: str) -> str:
    """Resolve versioned conf_file name for a --from kind (mm|M)."""
    if from_kind == FROM_MM:
        return mongodb_conf_file_mm(version)
    if from_kind == FROM_M:
        return mongodb_conf_file_legacy(version)
    raise ValueError("invalid from_kind: {!r} (use mm|M)".format(from_kind))


def mongodb_versioned_conf_file_candidates(version: str, from_kind: Optional[str] = None) -> List[str]:
    """Preferred versioned conf_file names (deduplicated) for fallback read/migrate."""
    if from_kind:
        return [resolve_mongodb_versioned_conf_file(version, from_kind)]
    candidates = [mongodb_conf_file_mm(version), mongodb_conf_file_legacy(version)]
    seen = set()
    ordered = []
    for name in candidates:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def mongodb_conf_file_candidates(version: str, namespace: Optional[str] = None) -> List[str]:
    """
    Preferred conf_file probe order: role files first (when namespace known), then versioned fallbacks.
    """
    candidates: List[str] = []
    if namespace:
        candidates.extend(mongodb_role_conf_files(namespace))
    candidates.extend(mongodb_versioned_conf_file_candidates(version))
    seen = set()
    ordered = []
    for name in candidates:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def _is_conf_not_found(err: Exception) -> bool:
    if not isinstance(err, ApiResultError):
        return False
    message = str(err).lower()
    return "cannot find parent level" in message or "not found" in message


def _query_single_conf_item(
    *,
    bk_biz_id: str,
    level_name: str,
    level_value: str,
    namespace: str,
    conf_type: str,
    conf_file: str,
    level_info: Optional[Dict] = None,
    format: str = FormatType.MAP.value,
) -> dict:
    params = {
        "bk_biz_id": bk_biz_id,
        "level_name": level_name,
        "level_value": level_value,
        "conf_file": conf_file,
        "conf_type": conf_type,
        "namespace": namespace,
        "format": format,
    }
    if level_info is not None:
        params["level_info"] = level_info
    return DBConfigApi.query_conf_item(params=params)


def _cluster_owned_content_from_list_resp(content: dict) -> dict:
    """
    Keep only conf items whose winning level_name is cluster.
    list-format query_conf_item still merges parents, but each item retains its source level_name.
    """
    owned = {}
    for conf_name, item in (content or {}).items():
        if not isinstance(item, dict):
            continue
        if item.get("level_name") != LevelName.CLUSTER.value:
            continue
        if "conf_value" not in item:
            continue
        owned[conf_name] = item["conf_value"]
    return owned


def query_mongodb_cluster_level_owned_content(
    *,
    bk_biz_id: str,
    level_value: str,
    namespace: str,
    conf_file: str,
    conf_type: str = ConfigTypeEnum.DBConf.value,
    level_info: Optional[Dict] = None,
) -> dict:
    """
    Read CLUSTER dbconf for migrate: only conf_name->value stored at level_name=cluster.
    Inherited plat/app values are excluded (query/probe still use merged MAP).
    """
    result = _query_single_conf_item(
        bk_biz_id=str(bk_biz_id),
        level_name=LevelName.CLUSTER.value,
        level_value=str(level_value),
        namespace=namespace,
        conf_type=conf_type,
        conf_file=conf_file,
        level_info=level_info,
        format=FormatType.LIST.value,
    )
    return _cluster_owned_content_from_list_resp(result.get("content") or {})


def list_cluster_owned_conf_files(
    *,
    bk_biz_id: str,
    namespace: str,
    level_value: str,
    conf_type: str = ConfigTypeEnum.DBConf.value,
) -> set:
    """Return conf_file names that have CLUSTER-level rows for level_value."""
    levels = DBConfigApi.list_level_values(
        params={
            "bk_biz_id": str(bk_biz_id),
            "namespace": namespace,
            "conf_type": conf_type,
            "level_name": LevelName.CLUSTER.value,
        }
    )
    return {item["conf_file"] for item in levels if str(item.get("level_value")) == str(level_value)}


def normalize_conf_content_with_levels(content: dict) -> dict:
    """
    Normalize dbconfig content to {conf_name: {conf_value, level_name, level_value}}.
    LIST format items already carry level_*; MAP values get empty level fields.
    """
    normalized = {}
    for conf_name, item in (content or {}).items():
        if isinstance(item, dict) and "conf_value" in item:
            normalized[conf_name] = {
                "conf_value": item.get("conf_value"),
                "level_name": item.get("level_name") or "",
                "level_value": item.get("level_value") or "",
            }
        else:
            normalized[conf_name] = {
                "conf_value": item,
                "level_name": "",
                "level_value": "",
            }
    return normalized


def probe_mongodb_conf_files(
    *,
    bk_biz_id: str,
    level_name: str,
    level_value: str,
    namespace: str,
    version: str,
    conf_type: str = ConfigTypeEnum.DBConf.value,
    level_info: Optional[Dict] = None,
    conf_files: Optional[List[str]] = None,
    owned_conf_files: Optional[set] = None,
) -> List[Dict[str, Any]]:
    """
    Probe each conf_file individually and return per-file hit/miss details.
    When owned_conf_files is provided (CLUSTER probes), distinguish OWNED vs INHERITED.
    Content uses LIST format so each item retains source level_name (plat/app/cluster).
    """
    probe_conf_files = conf_files or mongodb_conf_file_candidates(version, namespace=namespace)
    if owned_conf_files is None and level_name == LevelName.CLUSTER.value:
        owned_conf_files = list_cluster_owned_conf_files(
            bk_biz_id=bk_biz_id,
            namespace=namespace,
            level_value=level_value,
            conf_type=conf_type,
        )

    probes = []
    for conf_file in probe_conf_files:
        probe = {
            "conf_file": conf_file,
            "found": False,
            "owned": False,
            "inherited": False,
            "status": "NOT_FOUND",
        }
        try:
            result = _query_single_conf_item(
                bk_biz_id=str(bk_biz_id),
                level_name=level_name,
                level_value=str(level_value),
                namespace=namespace,
                conf_type=conf_type,
                conf_file=conf_file,
                level_info=level_info,
                format=FormatType.LIST.value,
            )
            content = normalize_conf_content_with_levels(result.get("content") or {})
            probe["found"] = True
            probe["content"] = content
            if owned_conf_files is not None:
                probe["owned"] = conf_file in owned_conf_files
                probe["inherited"] = not probe["owned"]
                probe["status"] = "OWNED" if probe["owned"] else "INHERITED"
            else:
                probe["owned"] = True
                probe["status"] = "FOUND"
        except Exception as err:
            probe["error"] = str(err)
        probes.append(probe)
    return probes


def _merge_role_content_to_flat(namespace: str, role_contents: Dict[str, dict]) -> dict:
    """
    Merge role conf_file MAP contents into the legacy flat shape used by flows.
    Sharded: configsvr cache/oplog -> config_cacheSizeGB / config_oplogSizeMB; key_file from configsvr only.
    """
    flat: Dict[str, Any] = {}
    if namespace == ClusterType.MongoReplicaSet.value:
        flat.update(role_contents.get(MONGODB_CONF_FILE_MONGOD) or {})
        return flat

    shardsvr = role_contents.get(MONGODB_CONF_FILE_SHARDSVR) or {}
    configsvr = role_contents.get(MONGODB_CONF_FILE_CONFIGSVR) or {}
    mongos = role_contents.get(MONGODB_CONF_FILE_MONGOS) or {}

    for name in ("cacheSizeGB", "oplogSizeMB", "slowOpThresholdMs"):
        if name in shardsvr:
            flat[name] = shardsvr[name]
    if "cacheSizeGB" in configsvr:
        flat["config_cacheSizeGB"] = configsvr["cacheSizeGB"]
    if "oplogSizeMB" in configsvr:
        flat["config_oplogSizeMB"] = configsvr["oplogSizeMB"]
    if "key_file" in configsvr:
        flat["key_file"] = configsvr["key_file"]
    if "slowOpThresholdMs" in configsvr and "slowOpThresholdMs" not in flat:
        flat["slowOpThresholdMs"] = configsvr["slowOpThresholdMs"]
    for name in (
        "destination",
        "slowOpThresholdMs",
        "net.compression.compressors",
        "taskExecutorPoolSize",
        "ShardingTaskExecutorPoolMinSize",
        "ShardingTaskExecutorPoolMaxSize",
    ):
        if name in mongos and (name == "destination" or name not in flat):
            flat[name] = mongos[name]
    return flat


def _query_role_conf_maps(
    *,
    bk_biz_id: str,
    level_name: str,
    level_value: str,
    namespace: str,
    conf_type: str,
    level_info: Optional[Dict] = None,
) -> Tuple[Dict[str, dict], bool]:
    """Return ({conf_file: map_content}, any_found)."""
    role_contents: Dict[str, dict] = {}
    any_found = False
    for conf_file in mongodb_role_conf_files(namespace):
        try:
            result = _query_single_conf_item(
                bk_biz_id=str(bk_biz_id),
                level_name=level_name,
                level_value=str(level_value),
                namespace=namespace,
                conf_type=conf_type,
                conf_file=conf_file,
                level_info=level_info,
                format=FormatType.MAP.value,
            )
            role_contents[conf_file] = result.get("content") or {}
            any_found = True
        except Exception as err:
            if _is_conf_not_found(err):
                continue
            raise
    return role_contents, any_found


def _query_versioned_conf_item_with_candidates(
    *,
    bk_biz_id: str,
    level_name: str,
    level_value: str,
    namespace: str,
    conf_type: str,
    version: str,
    level_info: Optional[Dict] = None,
) -> dict:
    last_err = None
    for conf_file in mongodb_versioned_conf_file_candidates(version):
        try:
            return _query_single_conf_item(
                bk_biz_id=bk_biz_id,
                level_name=level_name,
                level_value=level_value,
                namespace=namespace,
                conf_type=conf_type,
                conf_file=conf_file,
                level_info=level_info,
                format=FormatType.MAP.value,
            )
        except Exception as err:
            if _is_conf_not_found(err):
                last_err = err
                continue
            raise
    if last_err is not None:
        raise last_err
    raise ValueError("no conf_file candidate for version {}".format(version))


def query_mongodb_dbconf_content(
    *,
    bk_biz_id: str,
    level_name: str,
    level_value: str,
    namespace: str,
    version: str,
    conf_type: str = ConfigTypeEnum.DBConf.value,
    level_info: Optional[Dict] = None,
    plat_fallback: bool = True,
) -> dict:
    """
    Query dbconfig map content in legacy flat shape.
    Prefer role conf_files; fall back to versioned mongodb-M.m / Mongodb-M.
    When level is cluster and all miss, optionally fall back to plat.
    """

    def _query_at_level(biz_id: str, lvl_name: str, lvl_value: str, lvl_info: Optional[Dict]) -> dict:
        prefer_versioned = False
        if lvl_name == LevelName.CLUSTER.value:
            owned = list_cluster_owned_conf_files(
                bk_biz_id=biz_id,
                namespace=namespace,
                level_value=lvl_value,
                conf_type=conf_type,
            )
            role_set = set(mongodb_role_conf_files(namespace))
            if owned and not (owned & role_set):
                prefer_versioned = True

        if not prefer_versioned:
            role_contents, any_role = _query_role_conf_maps(
                bk_biz_id=biz_id,
                level_name=lvl_name,
                level_value=lvl_value,
                namespace=namespace,
                conf_type=conf_type,
                level_info=lvl_info,
            )
            if any_role:
                return _merge_role_content_to_flat(namespace, role_contents)

        return _query_versioned_conf_item_with_candidates(
            bk_biz_id=biz_id,
            level_name=lvl_name,
            level_value=lvl_value,
            namespace=namespace,
            conf_type=conf_type,
            version=version,
            level_info=lvl_info,
        )["content"]

    try:
        return _query_at_level(str(bk_biz_id), level_name, str(level_value), level_info)
    except Exception as err:
        if not plat_fallback or level_name == LevelName.PLAT.value:
            raise
        if not _is_conf_not_found(err):
            raise
        return _query_at_level("0", LevelName.PLAT.value, "0", None)


def query_mongodb_legacy_dbconf_content(
    *,
    bk_biz_id: str,
    level_name: str,
    level_value: str,
    namespace: str,
    version: str,
    conf_type: str = ConfigTypeEnum.DBConf.value,
    level_info: Optional[Dict] = None,
) -> dict:
    """
    Read CLUSTER-owned items from legacy Mongodb-M for migrate.
    Only level_name=cluster values are returned (inherited plat/app excluded).
    """
    # level_name is accepted for call-site compatibility; migrate always reads CLUSTER owned rows.
    _ = level_name
    return query_mongodb_cluster_level_owned_content(
        bk_biz_id=str(bk_biz_id),
        level_value=str(level_value),
        namespace=namespace,
        conf_file=mongodb_conf_file_legacy(version),
        conf_type=conf_type,
        level_info=level_info,
    )


def _query_cluster_dbconf_content_with_conf_file(
    *,
    bk_biz_id: str,
    level_value: str,
    namespace: str,
    version: str,
    level_info: Optional[Dict] = None,
    from_kind: Optional[str] = None,
) -> Tuple[dict, str]:
    """Read CLUSTER-owned dbconf for migrate and return (content, matched conf_file)."""
    last_err = None
    for conf_file in mongodb_versioned_conf_file_candidates(version, from_kind=from_kind):
        try:
            content = query_mongodb_cluster_level_owned_content(
                bk_biz_id=str(bk_biz_id),
                level_value=str(level_value),
                namespace=namespace,
                conf_file=conf_file,
                level_info=level_info,
            )
            if content:
                return content, conf_file
            last_err = ValueError("no cluster-owned items in {}".format(conf_file))
        except Exception as err:
            if _is_conf_not_found(err):
                last_err = err
                continue
            raise
    if last_err is not None:
        raise last_err
    raise ValueError("no conf_file candidate for version {}".format(version))


def delete_mongodb_cluster_dbconf(
    *,
    bk_biz_id: int,
    namespace: str,
    level_value: str,
    conf_file: str,
) -> None:
    """Delete CLUSTER-level MongoDB dbconf for a specific conf_file."""
    DBConfigApi.delete_level_value(
        {
            "bk_biz_id": str(bk_biz_id),
            "namespace": namespace,
            "conf_type": ConfigTypeEnum.DBConf.value,
            "conf_file": conf_file,
            "level_name": LevelName.CLUSTER.value,
            "level_value": level_value,
        }
    )


def resolve_cluster_dbconf_level_value(cluster: Cluster) -> str:
    """Return dbconfig CLUSTER level_value as lowercase immute_domain."""
    return (cluster.immute_domain or "").lower()


def legacy_cluster_dbconf_level_values(cluster: Cluster) -> List[str]:
    """Return legacy CLUSTER level_value keys that may exist before immute_domain migration."""
    target = resolve_cluster_dbconf_level_value(cluster)
    candidates = [cluster.immute_domain, cluster.name]
    if cluster.cluster_type == ClusterType.MongoShardedCluster.value:
        try:
            app = AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).db_app_abbr
            candidates.append("{}-{}".format(app, cluster.name))
            if cluster.name.startswith("{}-".format(app)):
                bare = cluster.name[len(app) + 1 :]
                if bare:
                    candidates.append(bare)
        except AppCache.DoesNotExist:
            pass
    seen = set()
    ordered = []
    for value in candidates:
        if value and value != target and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def resolve_flow_dbconf_level_value(*, bk_biz_id, cluster_type: str, cluster_name: str) -> str:
    """Map flow set_id/cluster_name to lowercase immute_domain; keep shard set_id when no Cluster match."""
    cluster = Cluster.objects.filter(
        bk_biz_id=bk_biz_id,
        cluster_type=cluster_type,
        name=cluster_name,
    ).first()
    if cluster:
        return resolve_cluster_dbconf_level_value(cluster)
    return cluster_name


class MongoDbconfLevelValueNotMigratedError(ValueError):
    """CLUSTER dbconf still under legacy level_value; run migrate first."""


_MIGRATE_CLUSTER_CONF_CMD = "python manage.py mongodb_cluster_conf migrate {domain} --to-role --from=mm|M --apply"


def cluster_has_legacy_dbconf_level_value(cluster: Cluster) -> bool:
    """Return True if CLUSTER dbconf rows still exist under legacy level_value keys."""
    namespace = cluster.cluster_type
    bk_biz_id = cluster.bk_biz_id
    conf_type = ConfigTypeEnum.DBConf.value
    for old_level_value in legacy_cluster_dbconf_level_values(cluster):
        if list_cluster_owned_conf_files(
            bk_biz_id=bk_biz_id,
            namespace=namespace,
            level_value=old_level_value,
            conf_type=conf_type,
        ):
            return True
    return False


def assert_cluster_dbconf_level_migrated(
    *,
    bk_biz_id,
    cluster_type: str,
    cluster_name: str,
) -> None:
    """
    Block flow/dbconf reads when CLUSTER rows still live under legacy level_value keys.
    Shard set_id (no matching Cluster row) is not checked.
    """
    cluster = Cluster.objects.filter(
        bk_biz_id=bk_biz_id,
        cluster_type=cluster_type,
        name=cluster_name,
    ).first()
    if cluster is None:
        return
    if cluster_has_legacy_dbconf_level_value(cluster):
        raise MongoDbconfLevelValueNotMigratedError(
            "MongoDB CLUSTER dbconf for cluster {name} (domain={domain}) still uses legacy "
            "level_value keys. Run migration before this operation: "
            "{cmd}".format(
                name=cluster.name,
                domain=cluster.immute_domain,
                cmd=_MIGRATE_CLUSTER_CONF_CMD.format(domain=cluster.immute_domain),
            )
        )


def upsert_mongodb_cluster_dbconf_file(
    *,
    bk_biz_id,
    namespace: str,
    level_value: str,
    conf_file: str,
    conf_items: List[Dict[str, Any]],
) -> None:
    """Write CLUSTER-level MongoDB dbconf for a specific conf_file."""
    if not conf_items:
        return
    DBConfigApi.upsert_conf_item(
        {
            "conf_file_info": {
                "conf_file": conf_file,
                "conf_type": ConfigTypeEnum.DBConf.value,
                "namespace": namespace,
            },
            "conf_items": conf_items,
            "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
            "confirm": DEFAULT_CONFIG_CONFIRM,
            "req_type": ReqType.SAVE_AND_PUBLISH,
            "bk_biz_id": str(bk_biz_id),
            "level_name": LevelName.CLUSTER,
            "level_value": level_value,
        }
    )


def _flat_content_to_role_items(namespace: str, content: dict) -> Dict[str, List[Dict[str, Any]]]:
    """
    Split legacy flat conf map (or flat conf_items values) into role file upserts.
    Accepts both role-native names and legacy config_* aliases.
    """
    by_role: Dict[str, List[Dict[str, Any]]] = {cf: [] for cf in mongodb_role_conf_files(namespace)}

    def _add(conf_file: str, conf_name: str, conf_value: Any) -> None:
        if conf_file not in by_role:
            return
        by_role[conf_file].append({"conf_name": conf_name, "conf_value": str(conf_value), "op_type": OpType.UPDATE})

    if namespace == ClusterType.MongoReplicaSet.value:
        for name in _MONGODB_ROLE_OWNED_NAMES[MONGODB_CONF_FILE_MONGOD]:
            if name in content:
                _add(MONGODB_CONF_FILE_MONGOD, name, content[name])
        return by_role

    # shardsvr
    for name in ("cacheSizeGB", "oplogSizeMB", "slowOpThresholdMs"):
        if name in content:
            _add(MONGODB_CONF_FILE_SHARDSVR, name, content[name])
    # configsvr (prefer config_* aliases when present)
    if "config_cacheSizeGB" in content:
        _add(MONGODB_CONF_FILE_CONFIGSVR, "cacheSizeGB", content["config_cacheSizeGB"])
    if "config_oplogSizeMB" in content:
        _add(MONGODB_CONF_FILE_CONFIGSVR, "oplogSizeMB", content["config_oplogSizeMB"])
    if "key_file" in content:
        _add(MONGODB_CONF_FILE_CONFIGSVR, "key_file", content["key_file"])
    # mongos
    for name in (
        "destination",
        "net.compression.compressors",
        "taskExecutorPoolSize",
        "ShardingTaskExecutorPoolMinSize",
        "ShardingTaskExecutorPoolMaxSize",
    ):
        if name in content:
            _add(MONGODB_CONF_FILE_MONGOS, name, content[name])
    return by_role


def split_flat_conf_items_to_roles(
    namespace: str, conf_items: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Split flat conf_items list into role conf_file buckets."""
    content = {item["conf_name"]: item["conf_value"] for item in conf_items if "conf_name" in item}
    return _flat_content_to_role_items(namespace, content)


def upsert_mongodb_cluster_dbconf(
    *,
    bk_biz_id: str,
    namespace: str,
    level_value: str,
    conf_items: List[Dict[str, Any]],
    version: Optional[str] = None,
) -> None:
    """Write CLUSTER-level MongoDB dbconf under role conf_files. ``version`` is ignored (compat)."""
    _ = version
    by_role = split_flat_conf_items_to_roles(namespace, conf_items)
    for conf_file, items in by_role.items():
        upsert_mongodb_cluster_dbconf_file(
            bk_biz_id=bk_biz_id,
            namespace=namespace,
            level_value=level_value,
            conf_file=conf_file,
            conf_items=items,
        )


def _conf_items_from_content(content: dict, namespace: str, conf_file: Optional[str] = None) -> List[Dict[str, Any]]:
    if conf_file and conf_file in _MONGODB_ROLE_OWNED_NAMES:
        names = _MONGODB_ROLE_OWNED_NAMES[conf_file]
    else:
        names = _LEGACY_FLAT_NAMES.get(namespace) or ["key_file", "cacheSizeGB", "oplogSizeMB"]
    conf_items = []
    for name in names:
        if name not in content:
            continue
        conf_items.append({"conf_name": name, "conf_value": str(content[name]), "op_type": OpType.UPDATE})
    return conf_items


def migrate_mongodb_cluster_to_role(
    *,
    bk_biz_id: int,
    namespace: str,
    level_value: str,
    version: str,
    from_kind: Optional[str] = None,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Copy CLUSTER-owned items from versioned conf_file(s) into role conf_files.
    When from_kind is mm|M, only that source conf_file is read and deleted.
    When from_kind is None, try mongodb-M.m then Mongodb-M (upgrade / auto path).
    When role conf_files already exist, require force=True to overwrite.
    """
    result: Dict[str, Any] = {
        "migrated": False,
        "already_role": False,
        "skipped": False,
        "reason": "",
        "deleted_conf_files": [],
        "target_conf_files": [],
        "conflict_roles": [],
    }
    owned = list_cluster_owned_conf_files(
        bk_biz_id=bk_biz_id,
        namespace=namespace,
        level_value=level_value,
        conf_type=ConfigTypeEnum.DBConf.value,
    )
    role_files = set(mongodb_role_conf_files(namespace))
    existing_roles = owned & role_files
    versioned_owned = owned - role_files
    if existing_roles and not versioned_owned:
        result["already_role"] = True
        result["reason"] = "already owns role conf_files only"
        return result
    if existing_roles and not force:
        result["skipped"] = True
        result["conflict_roles"] = sorted(existing_roles)
        result["reason"] = "target already owns role conf_files {}; pass --force to overwrite".format(
            ",".join(result["conflict_roles"])
        )
        return result

    level_info = {"module": str(DEFAULT_DB_MODULE_ID)}
    try:
        content, source_conf_file = _query_cluster_dbconf_content_with_conf_file(
            bk_biz_id=str(bk_biz_id),
            level_value=level_value,
            namespace=namespace,
            version=version,
            level_info=level_info,
            from_kind=from_kind,
        )
    except Exception as err:
        result["skipped"] = True
        result["reason"] = "source conf not found: {}".format(err)
        return result

    by_role = _flat_content_to_role_items(namespace, content)
    wrote_any = False
    for conf_file, items in by_role.items():
        if not items:
            continue
        upsert_mongodb_cluster_dbconf_file(
            bk_biz_id=bk_biz_id,
            namespace=namespace,
            level_value=level_value,
            conf_file=conf_file,
            conf_items=items,
        )
        result["target_conf_files"].append(conf_file)
        wrote_any = True
    if not wrote_any:
        result["skipped"] = True
        result["reason"] = "source conf has no migratable role items"
        return result

    # Delete only the source conf_file that was migrated (not other versioned leftovers).
    delete_mongodb_cluster_dbconf(
        bk_biz_id=bk_biz_id,
        namespace=namespace,
        level_value=level_value,
        conf_file=source_conf_file,
    )
    result["deleted_conf_files"] = [source_conf_file]
    result["deleted_conf_file"] = source_conf_file
    result["migrated"] = True
    return result


def migrate_mongodb_cluster_conf_file(
    *,
    bk_biz_id: int,
    namespace: str,
    level_value: str,
    source_version: str,
    target_version: str,
) -> Dict[str, Any]:
    """
    Version hops are obsolete: migrate CLUSTER-owned versioned dbconf into role conf_files.
    source_version/target_version are kept for call-site compatibility; target version is unused.
    """
    _ = target_version
    migration = migrate_mongodb_cluster_to_role(
        bk_biz_id=bk_biz_id,
        namespace=namespace,
        level_value=level_value,
        version=source_version,
    )
    # Adapt shape expected by callers of the old version-hop API.
    return {
        "migrated": migration.get("migrated", False),
        "deleted_conf_file": (migration.get("deleted_conf_files") or [None])[0],
        "deleted_conf_files": migration.get("deleted_conf_files") or [],
        "target_conf_files": migration.get("target_conf_files") or [],
    }


def query_mongodb_owned_content_at_level_values(
    *,
    bk_biz_id: str,
    namespace: str,
    conf_file: str,
    level_values: List[str],
    conf_type: str = ConfigTypeEnum.DBConf.value,
    level_info: Optional[Dict] = None,
) -> Tuple[dict, str]:
    """
    Read CLUSTER-owned content for conf_file, trying level_values in order.
    Returns (content, matched_level_value). Raises the last read error when none match.
    """
    last_err: Optional[Exception] = None
    for level_value in level_values:
        if not level_value:
            continue
        try:
            content = query_mongodb_cluster_level_owned_content(
                bk_biz_id=str(bk_biz_id),
                level_value=str(level_value),
                namespace=namespace,
                conf_file=conf_file,
                conf_type=conf_type,
                level_info=level_info,
            )
        except Exception as err:
            if _is_conf_not_found(err):
                last_err = err
                continue
            raise
        if content:
            return content, str(level_value)
        last_err = ValueError("no cluster-owned items in {} at level_value={}".format(conf_file, level_value))
    if last_err is not None:
        raise last_err
    raise ValueError("conf_file {} not found at any level_value".format(conf_file))


def cluster_dbconf_level_value_search_order(cluster: Cluster) -> List[str]:
    """immute_domain first, then legacy keys — shared by dry-run and apply source lookup."""
    target = resolve_cluster_dbconf_level_value(cluster)
    ordered = [target]
    for value in legacy_cluster_dbconf_level_values(cluster):
        if value and value not in ordered:
            ordered.append(value)
    return ordered


def migrate_mongodb_cluster_level_value(
    *,
    cluster: Cluster,
    dry_run: bool = True,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Copy OWNED CLUSTER dbconf rows from legacy level_value keys to immute_domain.
    Preserves the same conf_file name (no versioned -> role conversion).
    Only conf items with level_name=cluster are written (inherited plat/app excluded).
    Deletes legacy rows after a successful write when dry_run is False.
    """
    target_level_value = resolve_cluster_dbconf_level_value(cluster)
    namespace = cluster.cluster_type
    bk_biz_id = cluster.bk_biz_id
    level_info = {"module": str(DEFAULT_DB_MODULE_ID)}
    conf_type = ConfigTypeEnum.DBConf.value

    target_owned = list_cluster_owned_conf_files(
        bk_biz_id=bk_biz_id,
        namespace=namespace,
        level_value=target_level_value,
        conf_type=conf_type,
    )

    result = {
        "cluster": {
            "id": cluster.id,
            "name": cluster.name,
            "immute_domain": cluster.immute_domain,
            "bk_biz_id": bk_biz_id,
            "cluster_type": namespace,
        },
        "target_level_value": target_level_value,
        "dry_run": dry_run,
        "force": force,
        "migrations": [],
        "migrated_count": 0,
        "skipped_count": 0,
    }

    for old_level_value in legacy_cluster_dbconf_level_values(cluster):
        old_owned = list_cluster_owned_conf_files(
            bk_biz_id=bk_biz_id,
            namespace=namespace,
            level_value=old_level_value,
            conf_type=conf_type,
        )
        for conf_file in sorted(old_owned):
            entry = {
                "conf_file": conf_file,
                "source_level_value": old_level_value,
                "target_level_value": target_level_value,
                "status": "",
                "reason": "",
            }
            if conf_file in target_owned and not force:
                entry["status"] = "skipped"
                entry["reason"] = "target already owns conf_file"
                result["skipped_count"] += 1
                result["migrations"].append(entry)
                continue

            try:
                content = query_mongodb_cluster_level_owned_content(
                    bk_biz_id=str(bk_biz_id),
                    level_value=old_level_value,
                    namespace=namespace,
                    conf_file=conf_file,
                    conf_type=conf_type,
                    level_info=level_info,
                )
            except Exception as err:
                entry["status"] = "skipped"
                entry["reason"] = "read source failed: {}".format(err)
                result["skipped_count"] += 1
                result["migrations"].append(entry)
                continue

            conf_items = _conf_items_from_content(content, namespace, conf_file=conf_file)
            if not conf_items:
                entry["status"] = "skipped"
                entry["reason"] = "no cluster-owned migratable items"
                result["skipped_count"] += 1
                result["migrations"].append(entry)
                continue

            entry["content"] = content
            if dry_run:
                entry["status"] = "would_migrate"
                result["migrated_count"] += 1
                result["migrations"].append(entry)
                continue

            # Same conf_file name only; versioned -> role is handled by migrate_mongodb_cluster_to_role.
            upsert_mongodb_cluster_dbconf_file(
                bk_biz_id=bk_biz_id,
                namespace=namespace,
                level_value=target_level_value,
                conf_file=conf_file,
                conf_items=conf_items,
            )
            target_owned.add(conf_file)
            delete_mongodb_cluster_dbconf(
                bk_biz_id=bk_biz_id,
                namespace=namespace,
                level_value=old_level_value,
                conf_file=conf_file,
            )
            entry["status"] = "migrated"
            result["migrated_count"] += 1
            result["migrations"].append(entry)

    return result
