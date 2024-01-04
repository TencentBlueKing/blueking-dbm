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
from copy import deepcopy

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.consts import MongoDBDomainPrefix, MongoDBTotalCache


def calculate_cluster(payload: dict) -> dict:
    """ 计算cluster"""

    payload_clusters = {}
    payload_clusters["uid"] = payload["uid"]
    payload_clusters["created_by"] = payload["created_by"]
    payload_clusters["bk_biz_id"] = payload["bk_biz_id"]
    payload_clusters["ticket_type"] = payload["ticket_type"]
    payload_clusters["cluster_type"] = payload["cluster_type"]
    payload_clusters["city"] = payload["city_code"]
    payload_clusters["app"] = payload["bk_app_abbr"]
    app = payload["bk_app_abbr"]
    payload_clusters["db_version"] = payload["db_version"]
    # 目前只支持11个节点
    domain_prefix = [
        MongoDBDomainPrefix.M1,
        MongoDBDomainPrefix.M2,
        MongoDBDomainPrefix.M3,
        MongoDBDomainPrefix.M4,
        MongoDBDomainPrefix.M5,
        MongoDBDomainPrefix.M6,
        MongoDBDomainPrefix.M7,
        MongoDBDomainPrefix.M8,
        MongoDBDomainPrefix.M9,
        MongoDBDomainPrefix.M10,
        MongoDBDomainPrefix.BACKUP,
    ]

    if payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
        payload_clusters["spec_id"] = payload["spec_id"]
        payload_clusters["spec_config"] = payload["infos"][0]["resource_spec"]["spec_config"]
        # 获取全部主机
        hosts = []
        for info in payload["infos"]:
            for machine in info["mongo_machine_set"]:
                hosts.append({"ip": machine["ip"], "bk_cloud_id": machine["bk_cloud_id"]})
        payload_clusters["hosts"] = hosts
        # 获取复制集实例
        sets = []
        node_replica_count = payload["node_replica_count"]
        print("node_replica_count")
        print(node_replica_count)
        port = payload["start_port"]
        oplog_percent = payload["oplog_percent"] / 100
        data_disk = "/data1"
        # 计算cacheSizeGB和oplogSizeMB  bk_mem:MB  ["/data1"]["size"]:GB
        avg_mem_size_gb = int(
            payload["infos"][0]["mongo_machine_set"][0]["bk_mem"]
            * MongoDBTotalCache.Cache_Percent
            / node_replica_count
            / 1024
        )
        if payload["infos"][0]["mongo_machine_set"][0]["storage"].get("/data1"):
            data_disk = "/data1"
        elif payload["infos"][0]["mongo_machine_set"][0]["storage"].get("/data"):
            data_disk = "/data"
        oplog_size_mb = int(
            payload["infos"][0]["mongo_machine_set"][0]["storage"].get(data_disk)["size"] * 1024 * oplog_percent
        )
        # 分配机器
        for index, info in enumerate(payload["infos"]):
            machines = []
            # 主从节点分布在不同的机房
            if payload["disaster_tolerance_level"] == AffinityEnum.CROS_SUBZONE:
                mongo_machine_set = deepcopy(info["mongo_machine_set"])
                if machines:
                    machines.clear()
                machines.append(mongo_machine_set[0])
                mongo_machine_set.remove(mongo_machine_set[0])
                for machine in mongo_machine_set:
                    if machine["sub_zone_id"] != machines[0]["sub_zone_id"]:
                        machines.append(machine)
                        break
                mongo_machine_set.remove(machines[1])
                machines.extend(mongo_machine_set)
            elif payload["disaster_tolerance_level"] == AffinityEnum.SAME_SUBZONE:
                machines = info["mongo_machine_set"]
            replica_sets = payload["replica_sets"][index * node_replica_count : node_replica_count * (index + 1)]
            for replica_set_index, replica_set in enumerate(replica_sets):
                skip_machine = True
                if replica_set_index == 0:
                    skip_machine = False
                nodes = []
                for machine_index, machine in enumerate(machines):
                    if machine_index == len(machines) - 1:
                        domain = "{}.{}.{}.db".format(domain_prefix[-1], replica_set["set_id"], app)
                    else:
                        domain = "{}.{}.{}.db".format(domain_prefix[machine_index], replica_set["set_id"], app)
                    nodes.append({"ip": machine["ip"], "bk_cloud_id": machine["bk_cloud_id"], "domain": domain})
                sets.append(
                    {
                        "set_id": replica_set["set_id"],
                        "alias": replica_set["name"],
                        "port": port,
                        "cacheSizeGB": avg_mem_size_gb,
                        "oplogSizeMB": oplog_size_mb,
                        "skip_machine": skip_machine,
                        "nodes": nodes,
                    }
                )
                port += 1
        payload_clusters["sets"] = sets
        return payload_clusters
    elif "cluster_type" == ClusterType.MongoShardedCluster.value:
        pass
