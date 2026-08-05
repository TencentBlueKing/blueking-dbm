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

import re
from typing import Any, Dict, List, Set

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import Prefetch, Q
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, MachineType, MachineTypeInstanceRoleMap
from backend.db_meta.models import Cluster, NosqlStorageSetDtl
from backend.db_package.models import Package
from backend.db_services.dbbase.cluster.handlers import ClusterServiceHandler
from backend.db_services.mongodb.resources.query import MongoDBListRetrieveResource
from backend.db_services.mongodb.toolbox.constants import MONGODB_SCRIPT_PATH
from backend.db_services.mysql.sql_import.handlers import SQLHandler as MySQLSQLHandler
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version import MONGODB_MAJOR_MINOR_UPGRADE_CHAIN
from backend.flow.utils.mongodb.version_utils import (
    _resolve_package_full_version,
    extract_mongodb_version_tuple,
    get_cluster_live_instance_version,
    normalize_mongodb_full_version,
)

_CHAIN_INDEX = {v: i for i, v in enumerate(MONGODB_MAJOR_MINOR_UPGRADE_CHAIN)}


class ToolboxHandler(ClusterServiceHandler):
    """mongodb工具箱查询接口封装"""

    def __init__(self, bk_biz_id: int):
        super().__init__(bk_biz_id)

    @classmethod
    def upload_script_file(
        cls, bk_biz_id: int, script_content: str = None, script_files: List[InMemoryUploadedFile] = None
    ) -> List[Dict[str, Any]]:
        """
        将sql文本或者sql文件上传到制品库
        @param bk_biz_id: 业务ID
        @param sql_content: sql 语句内容
        @param sql_files: sql 语句文件
        """
        # 逻辑同mysql的sql文件上传，直接复用即可
        upload_sql_path = MONGODB_SCRIPT_PATH.format(biz=bk_biz_id)
        sql_file_info_list = MySQLSQLHandler.upload_sql_file(
            upload_sql_path, script_content, script_files, suffix=".js"
        )
        for sql_file_info in sql_file_info_list:
            sql_file_info["raw_file_name"] = sql_file_info["sql_path"].split("/")[-1]
            sql_file_info["script_path"] = sql_file_info.pop("sql_path")
            sql_file_info["script_content"] = sql_file_info.pop("sql_content")
        return sql_file_info_list

    @staticmethod
    def _extract_major_minor(version: str) -> str:
        if not version:
            raise serializers.ValidationError(_("当前集群版本为空"))
        raw_version = version.strip()
        if raw_version.lower().startswith("mongodb-"):
            raw_version = raw_version.split("-", 1)[1]
        parts = raw_version.split(".")
        if len(parts) < 2:
            raise serializers.ValidationError(_("不支持的当前版本：{}").format(version))
        return "{}.{}".format(parts[0], parts[1])

    @staticmethod
    def _extract_major_minor_from_package(package_version: str) -> str:
        normalized = normalize_mongodb_full_version(package_version)
        return ".".join(normalized.removeprefix("mongodb-").split(".")[:2])

    @classmethod
    def _resolve_package_listed_version(cls, package) -> str:
        """
        Resolve full mongodb-x.y.z for toolbox listing.
        V2 packages may store Package.version as series (mongodb-x.y); prefer db_version patch.
        """
        try:
            return _resolve_package_full_version(package)
        except ValueError:
            # Do not synthesize M.m.0 from series-only Package.version without db_version
            from backend.flow.utils.mongodb.version_utils import is_mongodb_major_minor_only

            if is_mongodb_major_minor_only(getattr(package, "version", "") or ""):
                raise
            return normalize_mongodb_full_version(package.version)

    @classmethod
    def _extract_full_version_tuple(cls, version: str):
        major, minor, patch = extract_mongodb_version_tuple(version)
        if patch is None:
            normalized = normalize_mongodb_full_version(version)
            numeric = normalized.removeprefix("mongodb-").split("-", 1)[0]
            major, minor, patch = numeric.split(".")[:3]
            return int(major), int(minor), int(patch)
        return major, minor, patch

    @staticmethod
    def _major_line_key(mm: str) -> str:
        return "mongodb-{}".format(mm)

    @classmethod
    def _collect_available_versions_by_major_line(cls, cluster, packages) -> Dict[str, Set[str]]:
        live_version = get_cluster_live_instance_version(cluster) or cluster.major_version
        current_mm = cls._extract_major_minor(live_version)
        if current_mm not in _CHAIN_INDEX:
            raise serializers.ValidationError(_("不支持的当前版本：{}").format(current_mm))

        current_full = normalize_mongodb_full_version(live_version)
        current_tuple = cls._extract_full_version_tuple(current_full)

        by_line: Dict[str, Set[str]] = {}
        for package in packages:
            try:
                normalized_version = cls._resolve_package_listed_version(package)
                package_mm = cls._extract_major_minor(normalized_version)
                package_tuple = cls._extract_full_version_tuple(normalized_version)
            except ValueError:
                continue

            if package_mm not in _CHAIN_INDEX:
                continue

            line_key = cls._major_line_key(package_mm)
            if package_mm == current_mm:
                if package_tuple <= current_tuple:
                    continue
            elif _CHAIN_INDEX[package_mm] <= _CHAIN_INDEX[current_mm]:
                continue

            if line_key not in by_line:
                by_line[line_key] = set()
            by_line[line_key].add(normalized_version)

        return by_line

    @staticmethod
    def _intersect_major_line_maps(maps: List[Dict[str, Set[str]]]) -> Dict[str, Set[str]]:
        if not maps:
            return {}
        all_keys: Set[str] = set()
        for m in maps:
            all_keys |= set(m.keys())
        result: Dict[str, Set[str]] = {}
        for key in all_keys:
            sets = [m.get(key, set()) for m in maps]
            inter = set.intersection(*sets) if sets else set()
            if inter:
                result[key] = inter
        return result

    @classmethod
    def list_available_versions(cls, cluster_ids: List[int]) -> List[dict]:
        clusters = Cluster.objects.filter(id__in=cluster_ids)
        cluster_map = {cluster.id: cluster for cluster in clusters}
        missing_cluster_ids = sorted(set(cluster_ids) - set(cluster_map.keys()))
        if missing_cluster_ids:
            raise serializers.ValidationError(_("集群不存在：{}").format(",".join(map(str, missing_cluster_ids))))
        packages = (
            Package.objects.filter(
                pkg_type=MediumEnum.MongoDB,
                db_type=DBType.MongoDB,
                enable=True,
            )
            .select_related("db_version")
            .order_by("-update_at")
        )

        maps: List[Dict[str, Set[str]]] = []
        for cluster_id in cluster_ids:
            maps.append(cls._collect_available_versions_by_major_line(cluster_map[cluster_id], packages))

        merged = cls._intersect_major_line_maps(maps)
        if not merged:
            return []

        ordered: List[dict] = []
        for mm in MONGODB_MAJOR_MINOR_UPGRADE_CHAIN:
            key = cls._major_line_key(mm)
            if key not in merged:
                continue
            full_list = sorted(merged[key], key=cls._extract_full_version_tuple)
            ordered.append({"major": key, "full_list": full_list})
        return ordered

    @staticmethod
    def _shard_name_sort_key(set_name: str) -> int:
        matches = re.findall("[0-9]+$", set_name)
        return int(matches[-1]) if matches else 0

    @classmethod
    def list_cluster_shards(cls, bk_biz_id: int, cluster_ids: List[int]) -> List[dict]:
        """按 cluster_ids 顺序返回当前业务下分片集群的分片名列表（按编号升序，不含 configsvr）"""

        clusters = Cluster.objects.filter(bk_biz_id=bk_biz_id, id__in=cluster_ids).prefetch_related(
            Prefetch(
                "nosqlstoragesetdtl_set",
                queryset=NosqlStorageSetDtl.objects.filter(instance__machine__machine_type=MachineType.MONGODB).only(
                    "id", "seg_range", "cluster_id"
                ),
                to_attr="mongodb_shard_dtls",
            )
        )
        cluster_map = {cluster.id: cluster for cluster in clusters}
        missing_cluster_ids = sorted(set(cluster_ids) - set(cluster_map.keys()))
        if missing_cluster_ids:
            raise serializers.ValidationError(_("集群不存在：{}").format(",".join(map(str, missing_cluster_ids))))

        result: List[dict] = []
        for cluster_id in cluster_ids:
            cluster = cluster_map[cluster_id]
            if cluster.cluster_type != ClusterType.MongoShardedCluster.value:
                raise serializers.ValidationError(_("集群{}不是分片集群").format(cluster_id))
            shard_list = sorted(
                {dtl.seg_range for dtl in cluster.mongodb_shard_dtls},
                key=cls._shard_name_sort_key,
            )
            result.append(
                {
                    "cluster_id": cluster_id,
                    "immute_domain": cluster.immute_domain,
                    "shard_list": shard_list,
                }
            )
        return result

    @classmethod
    def get_execute_net_tcp_cluster_hosts(cls, cluster):
        cluster_type = cluster.cluster_type
        host_ids = []
        # 有可能连后端Master/slave, 也有可能连接Proxy的
        if cluster_type in [ClusterType.MongoReplicaSet]:
            host_ids = list(cluster.storageinstance_set.values_list("machine__bk_host_id", flat=True))
            host_ids.extend(list(cluster.proxyinstance_set.values_list("machine__bk_host_id", flat=True)))
        # 只连接Proxy的
        elif cluster_type in [ClusterType.MongoShardedCluster]:
            host_ids = list(cluster.proxyinstance_set.values_list("machine__bk_host_id", flat=True))

        return host_ids

    @classmethod
    def get_mongo_shard(cls, bk_biz_id, data):
        cluster_ids = []
        if data.get("cluster_id"):
            cluster_ids.append(data["cluster_id"])
        if data.get("shard_names"):
            cluster_ids.append(
                NosqlStorageSetDtl.objects.filter(seg_range__in=data["shard_names"]).values_list(
                    "cluster__id", flat=True
                )
            )

        cluster_ids = list(set(cluster_ids))
        if cluster_ids:
            clusters = Cluster.objects.filter(id__in=cluster_ids).all()
        else:
            clusters = Cluster.objects.filter(
                bk_biz_id=bk_biz_id, cluster_type=ClusterType.MongoShardedCluster.value
            ).all()
        shard_data = []
        for cluster in clusters:
            mongodb_insts = [
                m for m in cluster.storageinstance_set.all() if m.machine.machine_type == MachineType.MONGODB
            ]
            mongodb = [m.simple_desc for m in mongodb_insts]
            shard_num = cluster.nosqlstoragesetdtl_set.filter(
                instance__machine__machine_type=MachineType.MONGODB
            ).count()
            shard_node_count = len(mongodb) / shard_num
            # 获取各个分片的节点组
            inst_filter = Q(
                instance_role__in=[role for role in MachineTypeInstanceRoleMap[MachineType.MONGODB]],
                cluster=cluster,
                machine_type=MachineType.MONGODB,
            )
            insts, inst_id__shard = MongoDBListRetrieveResource.query_storage_shard(inst_filter)
            shard_name_instance_map = {}
            for inst in insts:
                shard_name = inst_id__shard[inst.id]
                if data.get("shard_names"):
                    if shard_name not in data["shard_names"]:
                        continue
                if shard_name in shard_name_instance_map:
                    shard_name_instance_map[shard_name].append(inst)
                else:
                    shard_name_instance_map[shard_name] = [inst]
            shard_data.extend(
                [
                    {
                        "shard_name": shard_name,
                        "related_instance": [inst.simple_desc for inst in shard_name_instance_map[shard_name]],
                        "cluster_id": cluster.id,
                        "master_domain": cluster.immute_domain,
                        "region": cluster.region,
                        "major_version": cluster.major_version,
                        "disaster_tolerance_level": cluster.disaster_tolerance_level,
                        "shard_node_count": shard_node_count,
                    }
                    for shard_name in shard_name_instance_map
                ]
            )
        return shard_data

    @classmethod
    def get_shard_others_instance(cls, storage, cluster):
        inst_filter = Q(
            instance_role__in=[role for role in MachineTypeInstanceRoleMap[MachineType.MONGODB]],
            cluster=cluster,
            machine_type=MachineType.MONGODB,
        )
        insts, inst_id__shard = MongoDBListRetrieveResource.query_storage_shard(inst_filter)
        others_instance = []
        current_shard_name = inst_id__shard[storage.id]
        for inst in insts:
            shard_name = inst_id__shard[inst.id]
            if shard_name == current_shard_name and inst.id != storage.id:
                others_instance.append(inst)
        return others_instance
