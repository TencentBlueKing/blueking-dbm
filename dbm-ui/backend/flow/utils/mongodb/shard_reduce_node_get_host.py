from backend.db_meta.enums import MachineType
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_meta.enums.type_maps import MachineTypeInstanceRoleMap
from backend.db_meta.models import Machine
from backend.flow.utils.mongodb.mongodb_repo import MongoRepository


def get_cluster_instance_info(cluster_id: int) -> dict:
    """获取集群实例信息"""

    cluster_instance_info = {}
    cluster_info = MongoRepository().fetch_one_cluster(withDomain=True, id=cluster_id)
    cluster_instance_info["bk_cloud_id"] = cluster_info.bk_cloud_id
    nodes = []
    if cluster_info.cluster_type == ClusterType.MongoReplicaSet.value:
        backup_node = {}
        for member in cluster_info.get_shards()[0].members:
            if member.role == InstanceRole.MONGO_BACKUP.value:
                backup_node = {
                    "ip": member.ip,
                    "port": int(member.port),
                    "bk_cloud_id": member.bk_cloud_id,
                    "domain": member.domain,
                    "instance_role": member.role,
                }
                continue
            nodes.append(
                {
                    "ip": member.ip,
                    "port": int(member.port),
                    "bk_cloud_id": member.bk_cloud_id,
                    "domain": member.domain,
                    "instance_role": member.role,
                }
            )
        nodes.append(backup_node)
        cluster_instance_info["nodes"] = nodes
    elif cluster_info.cluster_type == ClusterType.MongoShardedCluster.value:
        mongos = cluster_info.get_mongos()
        shards = cluster_info.get_shards()
        config = cluster_info.get_config()
        mongos_nodes = []
        shards_nodes = []
        config_nodes = []
        for mongo in mongos:
            mongos_nodes.append(
                {"ip": mongo.ip, "port": int(mongo.port), "bk_cloud_id": mongo.bk_cloud_id, "domain": mongo.domain}
            )
        for shard in shards:
            shard_info = {"shard": shard.set_name}
            nodes = []
            backup_node = {}
            for member in shard.members:
                if member.role == InstanceRole.MONGO_BACKUP.value:
                    backup_node = {
                        "ip": member.ip,
                        "port": int(member.port),
                        "bk_cloud_id": member.bk_cloud_id,
                        "instance_role": member.role,
                    }
                    continue
                nodes.append(
                    {
                        "ip": member.ip,
                        "port": int(member.port),
                        "bk_cloud_id": member.bk_cloud_id,
                        "instance_role": member.role,
                    }
                )
            nodes.append(backup_node)
            shard_info["nodes"] = nodes
            shards_nodes.append(shard_info)
        backup_node = {}
        for member in config.members:
            if member.role == InstanceRole.MONGO_BACKUP.value:
                backup_node = {
                    "ip": member.ip,
                    "port": int(member.port),
                    "bk_cloud_id": member.bk_cloud_id,
                    "instance_role": member.role,
                }
                continue
            config_nodes.append(
                {
                    "ip": member.ip,
                    "port": int(member.port),
                    "bk_cloud_id": member.bk_cloud_id,
                    "instance_role": member.role,
                }
            )
        config_nodes.append(backup_node)
        cluster_instance_info["mongos_nodes"] = mongos_nodes
        cluster_instance_info["shards_nodes"] = shards_nodes
        cluster_instance_info["config_nodes"] = config_nodes
    return cluster_instance_info


def get_hosts_reduce_node(ticket_data: dict) -> list:
    """缩容shard节点数获取下架机器"""

    # 实例角色信息
    instance_role = MachineTypeInstanceRoleMap[MachineType.MONGODB]
    # 获取下架机器
    replicaset_hosts = []
    cluster_hosts = []
    hosts = []
    for replicaset_info in ticket_data["infos"][ClusterType.MongoReplicaSet.value]:
        reduce_shard_nodes = replicaset_info["reduce_shard_nodes"]
        replicaset_hosts_set = set()
        bk_cloud_id = ""
        for cluster_id in replicaset_info["cluster_ids"]:
            cluster_instance_info = get_cluster_instance_info(cluster_id=cluster_id)
            current_node_num = len(cluster_instance_info["nodes"])
            for index in range(reduce_shard_nodes):
                role = instance_role[current_node_num - 2 - index]
                for node in cluster_instance_info["nodes"]:
                    if node["instance_role"] == role:
                        replicaset_hosts_set.add(node["ip"])
                        bk_cloud_id = node["bk_cloud_id"]
                        break
        for ip in replicaset_hosts_set:
            replicaset_hosts.append({"ip": ip, "bk_cloud_id": bk_cloud_id})
    for cluster_info in ticket_data["infos"][ClusterType.MongoShardedCluster.value]:
        cluster_hosts_set = set()
        bk_cloud_id = ""
        reduce_shard_nodes = cluster_info["reduce_shard_nodes"]
        cluster_instance_info = get_cluster_instance_info(cluster_id=cluster_info["cluster_id"])
        # 所有shard的实例对应关系
        shards_instance_relationships = {}
        for shard in cluster_instance_info["shards_nodes"]:
            shards_instance_relationships[shard["shard"]] = []
        for shard in cluster_instance_info["shards_nodes"]:
            current_node_num = len(shard["nodes"])
            for index in range(reduce_shard_nodes):
                role = instance_role[current_node_num - 2 - index]
                for node in shard["nodes"]:
                    if node["instance_role"] == role:
                        bk_cloud_id = node["bk_cloud_id"]
                        cluster_hosts_set.add(node["ip"])
        for ip in cluster_hosts_set:
            cluster_hosts.append({"ip": ip, "bk_cloud_id": bk_cloud_id})
    for host in replicaset_hosts + cluster_hosts:
        machine = Machine.objects.get(ip=host["ip"], bk_cloud_id=host["bk_cloud_id"])
        hosts.append(
            {
                "ip": host["ip"],
                "bk_host_id": machine.bk_host_id,
                "bk_cloud_id": host["bk_cloud_id"],
            }
        )
    return hosts
