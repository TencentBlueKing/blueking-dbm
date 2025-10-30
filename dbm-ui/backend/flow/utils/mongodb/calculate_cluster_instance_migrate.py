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
from backend.db_meta.enums.cluster_type import ClusterType


def calculate_instance_migrate(migrate_info: dict) -> dict:
    """分片集群同一个集群实例迁移聚合"""

    if migrate_info["cluster_type"] == ClusterType.MongoReplicaSet.value:
        return migrate_info
    elif migrate_info["cluster_type"] == ClusterType.MongoShardedCluster.value:
        # instance_migrate_info = { "cluster_id": {"shard_name":[],"mongodb": [], "resource_spec": {}}}
        instance_migrate_info = {}
        for shard_set in migrate_info["infos"]:
            str_cluster_id = str(shard_set["cluster_id"])
            if not instance_migrate_info.get(str_cluster_id):
                instance_migrate_info[str_cluster_id] = {
                    "shard_name": [],
                    "mongodb": [],
                    "resource_spec": {},
                    "db_version": "",
                    "current_shard_nodes_num": 0,
                    "disaster_tolerance_level": "",
                    "city_code": "",
                }
            instance_migrate_info[str_cluster_id]["shard_name"].append(shard_set.get("shard_name"))
            instance_migrate_info[str_cluster_id]["mongodb"].append(shard_set.get("mongodb"))
            instance_migrate_info[str_cluster_id]["resource_spec"] = shard_set.get("resource_spec")
            instance_migrate_info[str_cluster_id]["db_version"] = shard_set.get("db_version")
            instance_migrate_info[str_cluster_id]["current_shard_nodes_num"] = shard_set.get("current_shard_nodes_num")
            instance_migrate_info[str_cluster_id]["disaster_tolerance_level"] = shard_set.get(
                "disaster_tolerance_level"
            )
            instance_migrate_info[str_cluster_id]["city_code"] = shard_set.get("city_code")

        infos = []
        for cluster_id, info in instance_migrate_info.items():
            infos.append(
                {
                    "cluster_id": int(cluster_id),
                    "shard_name": info["shard_name"],
                    "db_version": info["db_version"],
                    "current_shard_nodes_num": info["current_shard_nodes_num"],
                    "disaster_tolerance_level": info["disaster_tolerance_level"],
                    "city_code": info["city_code"],
                    "resource_spec": info["resource_spec"],
                    "mongodb": info["mongodb"],
                }
            )

        return {
            "uid": migrate_info["uid"],
            "ticket_type": migrate_info["ticket_type"],
            "bk_biz_id": migrate_info["bk_biz_id"],
            "bk_app_abbr": migrate_info["bk_app_abbr"],
            "created_by": migrate_info["created_by"],
            "cluster_type": migrate_info["cluster_type"],
            "infos": infos,
        }
