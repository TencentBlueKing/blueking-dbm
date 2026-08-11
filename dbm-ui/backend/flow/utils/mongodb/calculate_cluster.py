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

from django.utils.translation import gettext as _

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster, Machine
from backend.flow.consts import (
    MongoDBClusterDefaultPort,
    MongoDBDomainPrefix,
    MongoDBTotalCache,
    MongoOplogSizePercent,
)
from backend.flow.utils.mongodb.mongodb_repo import MongoRepository
from backend.flow.utils.mongodb.version_utils import resolve_mongodb_flow_db_version


def get_cache_percent(memory_size: int) -> float:
    """按机器总内存(MB)分档计算 mongod cache 占比"""

    memory_gb = memory_size / 1024
    if memory_gb <= 4:
        return MongoDBTotalCache.Cache_Percent_Small.value
    if memory_gb <= 16:
        return MongoDBTotalCache.Cache_Percent_Medium.value
    return MongoDBTotalCache.Cache_Percent_Large.value


def get_cache_size(memory_size: int, num: int) -> int:
    """计算 cacheSizeGB。memory_size 单位为 MB。"""

    cache_percent = get_cache_percent(memory_size)
    cache_size = int(memory_size * cache_percent / num / 1024)
    return cache_size if cache_size > 0 else 1


def get_oplog_size(disk_size: int, oplog_percent: float, num: int) -> int:
    """计算oplog大小 mb"""

    return int(disk_size * 1024 * oplog_percent / num)


def machine_order_by_tolerance(disaster_tolerance_level: str, machine_set: list) -> list:
    """通过容灾级别获取机器顺序"""

    machines = []
    # 主从节点分布在不同的机房
    if disaster_tolerance_level in [
        AffinityEnum.CROSS_SUBZONE_STRONG,
        AffinityEnum.CROSS_SUBZONE_WEAK,
    ]:
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
    elif disaster_tolerance_level in [
        AffinityEnum.SAME_SUBZONE,
        AffinityEnum.NONE,
        AffinityEnum.SAME_SUBZONE_CROSS_SWTICH,
        AffinityEnum.CROSS_RACK,
    ]:
        machines = machine_set
    else:
        machines = machine_set
    return machines


def cluster_shard_get_machine(
    all_machine: list, shard_info: list, node_count: int, node_replicaset_count: int, disaster_tolerance_level: str
):
    """分片集群分配机器"""

    shards = []
    add_shards = {}
    for index, machine_set in enumerate(all_machine):
        # 通过容灾获取机器顺序
        machines = machine_order_by_tolerance(disaster_tolerance_level, machine_set)
        # 获取机器对应的多个复制集
        replica_sets = shard_info[index * node_replicaset_count : node_replicaset_count * (index + 1)]
        for replica_set in replica_sets:
            nodes = [{"ip": machine["ip"], "bk_cloud_id": machine["bk_cloud_id"]} for machine in machines]
            replica_set["nodes"] = nodes
            shards.append(replica_set)
            if node_count > 1:
                add_shard_nodes = nodes[0:-1]
            else:
                add_shard_nodes = nodes
            add_shards[replica_set["set_id"]] = ",".join(
                ["{}:{}".format(node["ip"], str(replica_set["port"])) for node in add_shard_nodes]
            )
    return shards, add_shards


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
    node_count = payload["node_count"]
    # 一个副本集的副本数量
    payload_clusters["node_count"] = node_count
    port = payload["start_port"]
    oplog_percent = payload["oplog_percent"] / 100
    data_disk = "/data1"
    avg_mem_size_gb = get_cache_size(
        memory_size=payload["infos"][0]["mongo_machine_set"][0]["bk_mem"],
        num=node_replica_count,
    )
    if payload["infos"][0]["mongo_machine_set"][0]["storage_device"].get("/data1"):
        data_disk = "/data1"
    elif payload["infos"][0]["mongo_machine_set"][0]["storage_device"].get("/data"):
        data_disk = "/data"
    if payload["infos"][0]["mongo_machine_set"][0]["storage_device"].get(data_disk).get("size"):
        disk_size = payload["infos"][0]["mongo_machine_set"][0]["storage_device"].get(data_disk)["size"]
    else:
        disk_size = payload["infos"][0]["mongo_machine_set"][0]["storage_device"].get(data_disk).get("min")
    oplog_size_mb = get_oplog_size(
        disk_size=disk_size,
        oplog_percent=oplog_percent,
        num=node_replica_count,
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
                # 副本集node count等于1
                if node_count == 1:
                    domain = "{}.{}.{}.db".format(domain_prefix[machine_index], replica_set["set_id"], app)
                elif node_count > 1:
                    # 副本集node count大于1
                    if machine_index == len(machines) - 1:
                        domain = "{}.{}.{}.db".format(domain_prefix[-1], replica_set["set_id"], app)
                    else:
                        domain = "{}.{}.{}.db".format(domain_prefix[machine_index], replica_set["set_id"], app)
                nodes.append({"ip": machine["ip"], "bk_cloud_id": machine["bk_cloud_id"], "domain": domain})
            set_id_key_file = "{}-{}".format(app, replica_set["set_id"])
            sets.append(
                {
                    "set_id": set_id_key_file,
                    "alias": replica_set["name"],
                    "port": port,
                    "key_file": set_id_key_file,
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
    payload_clusters["cluster_id"] = "{}-{}".format(app, payload["cluster_name"])
    payload_clusters["machine_specs"] = payload["machine_specs"]
    oplog_percent = payload["oplog_percent"] / 100
    disaster_tolerance_level = payload["disaster_tolerance_level"]
    node_replica_count = int(payload["shard_num"] / payload["shard_machine_group"])
    payload_clusters["key_file"] = "{}-{}".format(app, payload["cluster_name"])
    config_port = MongoDBClusterDefaultPort.CONFIG_PORT.value  # 设置常量
    shard_port = MongoDBClusterDefaultPort.SHARD_START_PORT.value  # 以这个27001开始
    shard_port_not_use = [payload["proxy_port"], config_port]
    node_count = len(payload["nodes"]["mongodb"][0])
    # 一个副本集的副本数量
    payload_clusters["node_count"] = node_count

    # 计算configCacheSizeGB，shardCacheSizeGB，oplogSizeMB
    shard_avg_mem_size_gb = get_cache_size(
        memory_size=payload["nodes"]["mongodb"][0][0]["bk_mem"],
        num=node_replica_count,
    )
    config_mem_size_gb = get_cache_size(
        memory_size=payload["nodes"]["mongo_config"][0]["bk_mem"],
        num=1,
    )
    # shard oplogSizeMB
    data_disk = "/data1"
    if payload["nodes"]["mongodb"][0][0]["storage_device"].get("/data1"):
        data_disk = "/data1"
    elif payload["nodes"]["mongodb"][0][0]["storage_device"].get("/data"):
        data_disk = "/data"

    if payload["nodes"]["mongodb"][0][0]["storage_device"].get(data_disk).get("size"):
        disk_size = payload["nodes"]["mongodb"][0][0]["storage_device"].get(data_disk)["size"]
    else:
        disk_size = payload["nodes"]["mongodb"][0][0]["storage_device"].get(data_disk).get("min")
    shard_oplog_size_mb = get_oplog_size(
        disk_size=disk_size,
        oplog_percent=oplog_percent,
        num=node_replica_count,
    )
    # config oplogSizeMB
    if payload["nodes"]["mongo_config"][0]["storage_device"].get("/data1"):
        data_disk = "/data1"
    elif payload["nodes"]["mongo_config"][0]["storage_device"].get("/data"):
        data_disk = "/data"
    if payload["nodes"]["mongo_config"][0]["storage_device"].get(data_disk).get("size"):
        disk_size = payload["nodes"]["mongo_config"][0]["storage_device"].get(data_disk)["size"]
    else:
        disk_size = payload["nodes"]["mongo_config"][0]["storage_device"].get(data_disk).get("min")
    config_oplog_size_mb = int(disk_size * 1024 * oplog_percent)

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
    config["set_id"] = "{}-{}".format(payload_clusters["cluster_id"], "conf")  # 设置常量
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
    for i in range(payload["shard_num"]):
        if shard_port in shard_port_not_use:
            shard_port += 1
        shard_info.append(
            {
                "set_id": "{}-s{}".format(payload_clusters["cluster_id"], str(i + 1)),
                "port": shard_port,
                "cacheSizeGB": shard_avg_mem_size_gb,
                "oplogSizeMB": shard_oplog_size_mb,
            }
        )
        shard_port += 1

    payload_clusters["shards"], payload_clusters["add_shards"] = cluster_shard_get_machine(
        all_machine=payload["nodes"]["mongodb"],
        shard_info=shard_info,
        node_count=node_count,
        node_replicaset_count=node_replica_count,
        disaster_tolerance_level=disaster_tolerance_level,
    )

    # mongos
    mongos = {}
    mongos["port"] = payload["proxy_port"]  # 默认27021
    mongos["conf_set_id"] = config["set_id"]
    mongos["domain"] = "mongos.{}.{}.db".format(payload["cluster_name"], app)
    nodes = [{"ip": machine["ip"], "bk_cloud_id": machine["bk_cloud_id"]} for machine in payload["nodes"]["mongos"]]
    mongos["nodes"] = nodes
    payload_clusters["mongos"] = mongos

    return payload_clusters


def calculate_cluster(payload: dict) -> dict:
    """计算cluster"""

    payload_clusters = {}
    payload_clusters["uid"] = payload["uid"]
    payload_clusters["created_by"] = payload["created_by"]
    payload_clusters["bk_biz_id"] = payload["bk_biz_id"]
    payload_clusters["ticket_type"] = payload["ticket_type"]
    payload_clusters["cluster_type"] = payload["cluster_type"]
    payload_clusters["city"] = payload["city_code"]
    payload_clusters["bk_app_abbr"] = payload["bk_app_abbr"]
    payload_clusters["disaster_tolerance_level"] = payload["disaster_tolerance_level"]
    payload_clusters["zone_list"] = payload.get("zone_list", [])
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


def calculate_cluster_add_shard(payload: dict) -> dict:
    """分片集群增加 shard 计算"""

    add_shard_payload = {}
    add_shard_payload["uid"] = payload["uid"]
    add_shard_payload["created_by"] = payload["created_by"]
    add_shard_payload["bk_biz_id"] = payload["bk_biz_id"]
    add_shard_payload["ticket_type"] = payload["ticket_type"]
    add_shard_payload["bk_app_abbr"] = payload["bk_app_abbr"]
    add_shard_payload["cluster_type"] = ClusterType.MongoShardedCluster.value

    # 计算多个cluster
    cluster_add_shard_info = []
    for cluster in payload["infos"]:
        cluster_info = {}
        cluster_info["cluster_id"] = cluster["cluster_id"]
        cluster_info["db_version"] = cluster["db_version"]
        cluster_info["city"] = cluster["city_code"]
        cluster_info["resource_spec"] = cluster["resource_spec"]
        cluster_id = cluster["cluster_id"]
        # 亲和性
        disaster_tolerance_level = cluster["disaster_tolerance_level"]
        # 增加总的分片数
        add_shards_num = cluster["add_shards_num"]
        # 一个 shard 有多少个 node
        # current_shard_nodes_num = cluster["current_shard_nodes_num"]
        # 单机部署分片数
        node_replicaset_count = cluster["node_replicaset_count"]

        # 从dbconfig获取 key_file
        cluster_info["key_file"] = ""
        # 所有的机器
        hosts = []
        for host_set in cluster["mongo_add_shards"]:
            for host in host_set:
                hosts.append(
                    {
                        "ip": host["ip"],
                        "bk_cloud_id": host["bk_cloud_id"],
                    }
                )
        cluster_info["hosts"] = hosts

        # shard CacheSizeGB
        shard_avg_mem_size_gb = get_cache_size(
            memory_size=cluster["mongo_add_shards"][0][0]["bk_mem"],
            num=node_replicaset_count,
        )

        # shard oplogSizeMB
        data_disk = "/data1"
        if cluster["mongo_add_shards"][0][0]["storage_device"].get("/data1"):
            data_disk = "/data1"
        elif cluster["mongo_add_shards"][0][0]["storage_device"].get("/data"):
            data_disk = "/data"
        shard_oplog_size_mb = get_oplog_size(
            disk_size=cluster["mongo_add_shards"][0][0]["storage_device"].get(data_disk)["size"],
            oplog_percent=MongoOplogSizePercent.Oplog_Percent.value,
            num=node_replicaset_count,
        )

        # 查询集群信息
        cluster_info_from_db = MongoRepository().fetch_one_cluster(id=cluster_id)
        cluster_name = cluster_info_from_db.name
        cluster_info["cluster_name"] = cluster_name

        # 获取 mongos
        mongos = cluster_info_from_db.get_mongos()[0]
        cluster_info["mongos"] = {}
        cluster_info["mongos"]["port"] = mongos.port
        cluster_info["mongos"]["nodes"] = [
            {
                "ip": mongos.ip,
                "bk_cloud_id": mongos.bk_cloud_id,
                "port": mongos.port,
            }
        ]
        # 获取 shard 和 config 的端口
        shard_port_not_use = []
        for shard in cluster_info_from_db.get_shards():
            shard_port_not_use.append(shard.members[0].port)
        shard_port = max(shard_port_not_use) + 1
        shard_num = len(shard_port_not_use)
        shard_port_not_use.append(cluster_info_from_db.get_config().members[0].port)

        # 获取新增shard的set_id port
        shard_info = []
        for i in range(add_shards_num):
            if shard_port in shard_port_not_use:
                shard_port += 1
            shard_info.append(
                {
                    "set_id": "{}-s{}".format(cluster_name, str(shard_num + i + 1)),
                    "port": shard_port,
                    "cacheSizeGB": shard_avg_mem_size_gb,
                    "oplogSizeMB": shard_oplog_size_mb,
                }
            )
            shard_port += 1
        node_count = len(cluster["mongo_add_shards"][0])
        cluster_info["node_count"] = node_count

        # 新增的分片信息 新增的分片添加到集群信息
        cluster_info["shards"], cluster_info["add_shards"] = cluster_shard_get_machine(
            all_machine=cluster["mongo_add_shards"],
            shard_info=shard_info,
            node_count=node_count,
            node_replicaset_count=node_replicaset_count,
            disaster_tolerance_level=disaster_tolerance_level,
        )

        cluster_add_shard_info.append(cluster_info)

    add_shard_payload["cluster_add_shard_info"] = cluster_add_shard_info
    return add_shard_payload


def _validate_remaining_shard_deployment_balanced(all_shards: list, selected_names: set) -> None:
    """
    缩容后剩余部署均衡校验（指定分片 / 指定数量均适用）：
    - 主机上剩余实例数为 0：允许（回收机器）
    - 仍有实例的主机：各主机剩余分片实例数必须一致
      （例：3 组机器共 6 片、单机 2 片时，可缩 2/4/5，不可缩 1/3）
    """

    ip_remaining_count = {}
    for shard in all_shards:
        if shard.set_name in selected_names:
            continue
        for member in shard.members:
            ip_remaining_count[member.ip] = ip_remaining_count.get(member.ip, 0) + 1

    counts = set(ip_remaining_count.values())
    if len(counts) > 1:
        raise ValueError(_("剩余分片部署不均衡：仍有实例的主机剩余分片实例数必须一致，当前各主机计数={}").format(dict(sorted(ip_remaining_count.items()))))


def calculate_cluster_reduce_shard(payload: dict) -> dict:
    """分片集群减少 shard 计算与校验"""

    reduce_payload = {
        "uid": payload["uid"],
        "created_by": payload["created_by"],
        "bk_biz_id": payload["bk_biz_id"],
        "ticket_type": payload.get("ticket_type", "MongoDBReduceShardFlow"),
        "bk_cloud_id": payload.get("bk_cloud_id", 0),
        "cluster_type": ClusterType.MongoShardedCluster.value,
    }
    if "ticket_id" in payload:
        reduce_payload["ticket_id"] = payload["ticket_id"]
    if "bk_app_abbr" in payload:
        reduce_payload["bk_app_abbr"] = payload["bk_app_abbr"]

    cluster_reduce_shard_info = []
    for cluster in payload["infos"]:
        cluster_id = cluster["cluster_id"]
        reduce_mode = cluster.get("reduce_mode") or "by_shard_names"

        cluster_info_from_db = MongoRepository().fetch_one_cluster(id=cluster_id)
        if cluster_info_from_db is None:
            raise ValueError(_("集群不存在：{}").format(cluster_id))
        if cluster_info_from_db.cluster_type != ClusterType.MongoShardedCluster.value:
            raise ValueError(_("集群{}不是分片集群").format(cluster_id))

        all_shards = cluster_info_from_db.get_shards(sort_by_set_name=True)
        all_shard_names = {shard.set_name for shard in all_shards}

        if reduce_mode == "by_count":
            reduce_shards_num = int(cluster.get("reduce_shards_num") or 0)
            if reduce_shards_num < 1:
                raise ValueError(_("集群{}缩容分片数必须>=1").format(cluster_id))
            if reduce_shards_num >= len(all_shards):
                raise ValueError(_("集群{}缩容后至少保留1个分片").format(cluster_id))
            shard_names = [shard.set_name for shard in all_shards[-reduce_shards_num:]]
        else:
            shard_names = list(cluster.get("shard_names") or [])
            if not shard_names:
                raise ValueError(_("集群{}的shard_names不能为空").format(cluster_id))

        selected = set(shard_names)
        if len(selected) != len(shard_names):
            raise ValueError(_("集群{}的shard_names存在重复").format(cluster_id))

        unknown = selected - all_shard_names
        if unknown:
            raise ValueError(_("集群{}存在未知分片：{}").format(cluster_id, sorted(unknown)))

        config = cluster_info_from_db.get_config()
        if config and config.set_name in selected:
            raise ValueError(_("集群{}不能缩容 configsvr 分片 {}").format(cluster_id, config.set_name))

        remaining = len(all_shard_names) - len(selected)
        if remaining < 1:
            raise ValueError(_("集群{}缩容后至少保留1个分片").format(cluster_id))

        _validate_remaining_shard_deployment_balanced(all_shards, selected)

        bk_cloud_id = cluster.get("bk_cloud_id", cluster_info_from_db.bk_cloud_id)
        mongos = cluster_info_from_db.get_mongos()[0]
        mongos_nodes = [
            {
                "ip": mongos.ip,
                "bk_cloud_id": mongos.bk_cloud_id,
                "port": mongos.port,
            }
        ]

        reduce_shards = []
        storages = []
        old_instances = []
        shard_host_map = {}
        for shard in all_shards:
            if shard.set_name not in selected:
                continue
            nodes = []
            for member in shard.members:
                node = {
                    "ip": member.ip,
                    "port": int(member.port),
                    "bk_cloud_id": member.bk_cloud_id,
                    "set_id": shard.set_name,
                }
                nodes.append({"ip": member.ip, "port": int(member.port)})
                old_instances.append(node)
                shard_host_map[member.ip] = {"ip": member.ip, "bk_cloud_id": member.bk_cloud_id}
            reduce_shards.append(shard.set_name)
            storages.append({"shard": shard.set_name, "nodes": nodes})

        # mongos + 待删 shard 主机都需要下发介质（removeShard 在 mongos 执行）
        hosts = list(shard_host_map.values())
        if mongos.ip not in shard_host_map:
            hosts.append({"ip": mongos.ip, "bk_cloud_id": mongos.bk_cloud_id})

        db_version = resolve_mongodb_flow_db_version(Cluster.objects.get(pk=cluster_id))

        cluster_reduce_shard_info.append(
            {
                "cluster_id": cluster_id,
                "cluster_name": cluster_info_from_db.name,
                "bk_cloud_id": bk_cloud_id,
                "db_version": db_version,
                "mongos": {"port": mongos.port, "nodes": mongos_nodes},
                "reduce_shards": reduce_shards,
                "storages": storages,
                "hosts": hosts,
                "old_instances": old_instances,
                "old_hosts": list(shard_host_map.values()),
            }
        )

    reduce_payload["cluster_reduce_shard_info"] = cluster_reduce_shard_info
    return reduce_payload


def calc_cluster_standardization(payload: dict) -> dict:
    """计算集群标准化"""

    # 集群id
    cluster_ids = payload["cluster_ids"]
    bk_cloud_id = payload["bk_cloud_id"]
    bk_biz_id = payload["bk_biz_id"]
    payload["cluster_info"] = {}
    # {ClusterType.MongoShardedCluster.value: [], ClusterType.MongoReplicaSet.value: []}
    cluster_info, shard_clucster, rsp_cluster = {}, [], []
    # 获取集群信息，通过集群类型进行分类
    for cluster_id in cluster_ids:
        cluster = MongoRepository().fetch_one_cluster(id=cluster_id)
        if cluster.cluster_type == ClusterType.MongoShardedCluster.value:
            shard_clucster.append(cluster_id)  # 分片集群所有的集群id
        elif cluster.cluster_type == ClusterType.MongoReplicaSet.value:
            rsp_cluster.append(cluster)  # 副本集所有的集群信息
    # 副本集多实例部署要聚合 有可能多个副本集在单据中，则主机去重
    host_set, all_rsp_id_set = set(), set()
    for cluster in rsp_cluster:
        hosts = []
        members = cluster.get_shards()[0].members
        for member in members:
            hosts.append(member.ip)
        if hosts:
            sort_hosts_tuple = tuple(sorted(hosts))
            if sort_hosts_tuple not in host_set:
                host_set.add(sort_hosts_tuple)
        else:
            continue

    unique_host_set = []  # [[cluster1_id,cluster2_id], [cluster3_id]] 副本集多实例部署同组机器的集群信息
    for host in host_set:
        rsp_cluster_id_set = []
        all_storageinstance = Machine.objects.get(
            ip=host[0], bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id
        ).storageinstance_set.all()
        for storageinstance in all_storageinstance:
            for cluster in storageinstance.cluster.all():
                if cluster.id not in all_rsp_id_set:
                    all_rsp_id_set.add(cluster.id)
                    rsp_cluster_id_set.append(cluster.id)
        if rsp_cluster_id_set:
            unique_host_set.append(rsp_cluster_id_set)

    cluster_info[ClusterType.MongoShardedCluster.value] = shard_clucster
    cluster_info[ClusterType.MongoReplicaSet.value] = unique_host_set
    payload["cluster_info"] = cluster_info
    return payload
