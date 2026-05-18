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
import os.path
import uuid
from typing import Dict, List, Set

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import Q
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.core.storages.storage import get_storage
from backend.db_meta.enums import ClusterType, MachineType, MachineTypeInstanceRoleMap
from backend.db_meta.models import Cluster, NosqlStorageSetDtl
from backend.db_package.models import Package
from backend.db_services.dbbase.cluster.handlers import ClusterServiceHandler
from backend.db_services.mongodb.resources.query import MongoDBListRetrieveResource
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.mongodb.mongodb_upgrade_version import MONGODB_MAJOR_MINOR_UPGRADE_CHAIN
from backend.flow.utils.mongodb.version_utils import normalize_mongodb_full_version

_CHAIN_INDEX = {v: i for i, v in enumerate(MONGODB_MAJOR_MINOR_UPGRADE_CHAIN)}


class ToolboxHandler(ClusterServiceHandler):
    """mongodb工具箱查询接口封装"""

    def __init__(self, bk_biz_id: int):
        super().__init__(bk_biz_id)

    @staticmethod
    def upload_script_file(
        bkrepo_path: str, script_content: List[str] = None, script_file_list: List[InMemoryUploadedFile] = None
    ) -> List[Dict[str, any]]:
        """
        - 将脚本文本或者脚本文件上传到制品库
        @param bkrepo_path: 脚本文件路径前缀
        @param script_content: 脚本语句内容列表
        @param script_file_list: 脚本语句文件
        """
        storage = get_storage(file_overwrite=False)

        # 初始化script_file_list
        if script_file_list is None:
            script_file_list = []

        # 如果上传的是脚本内容列表, 则为每个内容创建内存文件
        if script_content:
            from io import BytesIO

            for i, content in enumerate(script_content):
                if not content:
                    continue

                content_bytes = content.encode("utf-8")
                # 使用with语句确保BytesIO资源正确管理
                with BytesIO(content_bytes) as script_file:
                    # 生成唯一文件名
                    file_name = f"script_{uuid.uuid4().hex[:8]}_{i}.js"

                    # 创建InMemoryUploadedFile对象
                    memory_file = InMemoryUploadedFile(
                        file=script_file,
                        field_name="script_file",
                        name=file_name,
                        content_type="application/javascript",
                        size=len(content_bytes),
                        charset="utf-8",
                    )
                    script_file_list.append(memory_file)

        script_file_info_list: List[Dict[str, any]] = []
        for script_file in script_file_list:
            script_file_info: Dict[str, any] = {}
            with script_file as file:
                # 构建完整的文件路径
                script_path = storage.save(name=os.path.join(bkrepo_path, file.name.split("/")[-1]), content=file)

                # 恢复文件指针为文件头
                file.seek(0)
                # 读取文件内容
                content_bytes = file.read()
                script_content = content_bytes.decode("utf-8", errors="replace")

                script_file_info.update(
                    script_path=script_path, script_content=script_content, raw_file_name=file.name
                )

            script_file_info_list.append(script_file_info)

        return script_file_info_list

    def check_mongo_script_syntax(
        self,
        script_content: List[str] = None,
        script_filenames: List[str] = None,
        script_files: List[InMemoryUploadedFile] = None,
    ) -> Dict[str, any]:
        """
        MongoDB脚本语法检查
        @param script_content: 脚本内容列表
        @param script_filenames: 脚本文件名(在制品库的路径，说明已经在制品库上传好了)
        @param script_files: 脚本文件
        """
        from backend.db_services.mongodb.toolbox.constants import MONGODB_SCRIPT_PATH

        # 构建完整的脚本文件路径
        script_path = MONGODB_SCRIPT_PATH.format(biz=self.bk_biz_id)

        if script_filenames:
            script_file_info_list = []
            for filename in script_filenames:
                # 安全验证：防止路径遍历攻击
                # 1. 禁止路径遍历（禁止所有包含'..'的情况）
                if ".." in filename:
                    raise serializers.ValidationError(_("文件名[{}]包含非法路径遍历符'..'，可能存在安全风险").format(filename))
                # 2. 检查是否是绝对路径或Windows绝对路径
                if filename.startswith("/") or (
                    len(filename) >= 2
                    and filename[1] == ":"
                    and (filename[0].isalpha() and filename[0].upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                ):
                    raise serializers.ValidationError(_("文件名[{}]不能是绝对路径").format(filename))
                # 3. 确保是纯文件名，移除路径前缀
                if "/" in filename or "\\" in filename:
                    filename = os.path.basename(filename)

                script_file_info_list.append({"script_path": script_path + "/" + filename})
        else:
            script_file_info_list = self.upload_script_file(script_path, script_content, script_files)

        # 统一返回格式：如果是单个文件，也包装在scripts字段中
        return {"scripts": script_file_info_list}

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
    def _extract_full_version_tuple(cls, version: str):
        normalized = normalize_mongodb_full_version(version)
        numeric = normalized.removeprefix("mongodb-").split("-", 1)[0]
        major, minor, patch = numeric.split(".")[:3]
        return int(major), int(minor), int(patch)

    @staticmethod
    def _major_line_key(mm: str) -> str:
        return "mongodb-{}".format(mm)

    @classmethod
    def _collect_available_versions_by_major_line(cls, cluster, packages) -> Dict[str, Set[str]]:
        current_mm = cls._extract_major_minor(cluster.major_version)
        if current_mm not in _CHAIN_INDEX:
            raise serializers.ValidationError(_("不支持的当前版本：{}").format(current_mm))

        current_full = normalize_mongodb_full_version(cluster.major_version)
        current_tuple = cls._extract_full_version_tuple(current_full)

        by_line: Dict[str, Set[str]] = {}
        for package in packages:
            try:
                normalized_version = normalize_mongodb_full_version(package.version)
                package_mm = cls._extract_major_minor_from_package(package.version)
                package_tuple = cls._extract_full_version_tuple(package.version)
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
        packages = Package.objects.filter(
            pkg_type=MediumEnum.MongoDB,
            db_type=DBType.MongoDB,
            enable=True,
        ).order_by("-update_at")

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
