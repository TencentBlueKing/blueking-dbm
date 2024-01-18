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
from backend.flow.consts import MongoDBClusterDefaultPort, MongoDBDomainPrefix, MongoDBTotalCache


def machine_order_by_tolerance(disaster_tolerance_level: str, machine_set: list) -> list:
    """通过容灾级别获取机器顺序"""

    machines = []
    # 主从节点分布在不同的机房
    if disaster_tolerance_level == AffinityEnum.CROS_SUBZONE:
        mongo_machine_set = deepcopy(machine_set)
        machines.append(mongo_machine_set[0])
        mongo_machine_set.remove(mongo_machine_set[0])
        for machine in mongo_machine_set:
            if machine["sub_zone_id"] != machines[0]["sub_zone_id"]:
                machines.append(machine)
                break
        mongo_machine_set.remove(machines[1])
        machines.extend(mongo_machine_set)
    # 主从节点分布在相同的机房
    elif disaster_tolerance_level == AffinityEnum.SAME_SUBZONE:
        machines = machine_set
    return machines


def replicase_calc(payload: dict, payload_clusters: dict, app: str, domain_prefix: list) -> dict:
    """replicase进行计算"""

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
    if payload["infos"][0]["mongo_machine_set"][0]["storage_device"].get("/data1"):
        data_disk = "/data1"
    elif payload["infos"][0]["mongo_machine_set"][0]["storage_device"].get("/data"):
        data_disk = "/data"
    oplog_size_mb = int(
        payload["infos"][0]["mongo_machine_set"][0]["storage_device"].get(data_disk)["size"]
        * 1024
        * oplog_percent
        / node_replica_count
    )
    # 分配机器
    for index, info in enumerate(payload["infos"]):
        # 通过容灾获取机器顺序
        machines = machine_order_by_tolerance(payload["disaster_tolerance_level"], info["mongo_machine_set"])
        # 获取机器对应的多个复制集
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
                    "key_file": "{}-{}".format(app, replica_set["set_id"]),
                    "cacheSizeGB": avg_mem_size_gb,
                    "oplogSizeMB": oplog_size_mb,
                    "skip_machine": skip_machine,
                    "nodes": nodes,
                }
            )
            port += 1
    payload_clusters["sets"] = sets
    return payload_clusters


def cluster_calc(payload: dict, payload_clusters: dict, app: str) -> dict:
    """cluster进行计算"""

    payload_clusters["alias"] = payload["cluster_alias"]
    payload_clusters["cluster_id"] = payload["cluster_name"]
    payload_clusters["machine_specs"] = payload["machine_specs"]
    oplog_percent = payload["oplog_percent"] / 100
    disaster_tolerance_level = payload["disaster_tolerance_level"]
    node_replica_count = int(payload["shard_num"] / payload["shard_machine_group"])
    payload_clusters["key_file"] = "{}-{}".format(app, payload["cluster_name"])
    config_port = MongoDBClusterDefaultPort.CONFIG_PORT.value  # 设置常量
    shard_port = MongoDBClusterDefaultPort.SHARD_START_PORT.value  # 以这个27001开始
    shard_port_not_use = [payload["proxy_port"], config_port]

    # 计算configCacheSizeGB，shardCacheSizeGB，oplogSizeMB
    shard_avg_mem_size_gb = int(
        payload["nodes"]["mongodb"][0][0]["bk_mem"] * MongoDBTotalCache.Cache_Percent / node_replica_count / 1024
    )
    config_mem_size_gb = int(
        payload["nodes"]["mongo_config"][0]["bk_mem"] * MongoDBTotalCache.Cache_Percent / node_replica_count / 1024
    )
    # shard oplogSizeMB
    data_disk = "/data1"
    if payload["nodes"]["mongodb"][0][0]["storage_device"].get("/data1"):
        data_disk = "/data1"
    elif payload["nodes"]["mongodb"][0][0]["storage_device"].get("/data"):
        data_disk = "/data"
    shard_oplog_size_mb = int(
        payload["nodes"]["mongodb"][0][0]["storage_device"].get(data_disk)["size"]
        * 1024
        * oplog_percent
        / node_replica_count
    )
    # config oplogSizeMB
    if payload["nodes"]["mongo_config"][0]["storage_device"].get("/data1"):
        data_disk = "/data1"
    elif payload["nodes"]["mongo_config"][0]["storage_device"].get("/data"):
        data_disk = "/data"
    config_oplog_size_mb = int(
        payload["nodes"]["mongo_config"][0]["storage_device"].get(data_disk)["size"] * 1024 * oplog_percent
    )

    # 获取全部主机
    hosts = []
    # mongo_config
    for machine in payload["nodes"]["mongo_config"]:
        hosts.append({"ip": machine["ip"], "bk_cloud_id": machine["bk_cloud_id"]})
    # mongodb
    for machines in payload["nodes"]["mongodb"]:
        for machine in machines:
            hosts.append({"ip": machine["ip"], "bk_cloud_id": machine["bk_cloud_id"]})
    # mongos
    for machine in payload["nodes"]["mongos"]:
        hosts.append({"ip": machine["ip"], "bk_cloud_id": machine["bk_cloud_id"]})
    payload_clusters["hosts"] = hosts

    # 分配机器
    # mongo_config
    config = {}
    config["set_id"] = "{}-{}".format(payload["cluster_name"], "conf")  # 设置常量
    config["port"] = config_port  # 设置常量
    config["cacheSizeGB"] = config_mem_size_gb
    config["oplogSizeMB"] = config_oplog_size_mb
    machines = machine_order_by_tolerance(disaster_tolerance_level, payload["nodes"]["mongo_config"])
    config["nodes"] = []
    for machine in machines:
        config["nodes"].append({"ip": machine["ip"], "bk_cloud_id": machine["bk_cloud_id"]})
    payload_clusters["config"] = config
    # shards
    # 获取shard的id，port
    shard_info = []
    add_shards = {}
    for i in range(payload["shard_num"]):
        if shard_port in shard_port_not_use:
            shard_port += 1
        shard_info.append(
            {
                "set_id": "{}-s{}".format(payload["cluster_name"], str(i + 1)),
                "port": shard_port,
                "cacheSizeGB": shard_avg_mem_size_gb,
                "oplogSizeMB": shard_oplog_size_mb,
            }
        )
        shard_port += 1
    shards = []
    for index, machine_set in enumerate(payload["nodes"]["mongodb"]):
        # 通过容灾获取机器顺序
        machines = machine_order_by_tolerance(payload["disaster_tolerance_level"], machine_set)
        # 获取机器对应的多个复制集
        replica_sets = shard_info[index * node_replica_count : node_replica_count * (index + 1)]
        for replica_set in replica_sets:
            nodes = [{"ip": machine["ip"], "bk_cloud_id": machine["bk_cloud_id"]} for machine in machines]
            replica_set["nodes"] = nodes
            shards.append(replica_set)
            add_shards["{}-{}".format(app, replica_set["set_id"])] = ",".join(
                ["{}:{}".format(node["ip"], str(replica_set["port"])) for node in nodes[0:-1]]
            )

    payload_clusters["shards"] = shards
    payload_clusters["add_shards"] = add_shards

    # mongos
    mongos = {}
    mongos["port"] = payload["proxy_port"]  # 默认27021
    mongos["set_id"] = payload["cluster_name"]
    mongos["domain"] = "mongos.{}.{}.db".format(payload["cluster_name"], app)
    nodes = [{"ip": machine["ip"], "bk_cloud_id": machine["bk_cloud_id"]} for machine in payload["nodes"]["mongos"]]
    mongos["nodes"] = nodes
    payload_clusters["mongos"] = mongos

    return payload_clusters


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
    cluster_type = payload["cluster_type"]

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

    result = {}
    if cluster_type == ClusterType.MongoReplicaSet.value:
        result = replicase_calc(payload, payload_clusters, app, domain_prefix)
    elif cluster_type == ClusterType.MongoShardedCluster.value:
        result = cluster_calc(payload, payload_clusters, app)
    return result

