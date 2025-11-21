from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Machine
from backend.flow.utils.mongodb.mongodb_repo import MongoRepository


def get_shards_info(cluster_id: int) -> list:
    """获取cluster的shard信息"""

    cluster_info = MongoRepository().fetch_one_cluster(with_domain=True, id=cluster_id)
    if cluster_info.cluster_type == ClusterType.MongoReplicaSet.value:
        nodes = []
        for member in cluster_info.get_shards()[0].members:
            nodes.append(
                {
                    "ip": member.ip,
                    "port": int(member.port),
                    "bk_cloud_id": member.bk_cloud_id,
                    "domain": member.domain,
                    "instance_role": member.role,
                }
            )
        return nodes
    elif cluster_info.cluster_type == ClusterType.MongoShardedCluster.value:
        shards = cluster_info.get_shards()
        shards_nodes = []
        for shard in shards:
            shard_info = {"shard": shard.set_name}
            shard_nodes = []
            for member in shard.members:
                shard_nodes.append(
                    {
                        "ip": member.ip,
                        "port": int(member.port),
                        "bk_cloud_id": member.bk_cloud_id,
                        "instance_role": member.role,
                    }
                )
            shard_info["nodes"] = shard_nodes
            shards_nodes.append(shard_info)
        return shards_nodes


def get_instance_by_ip(ip: str, bk_cloud_id: int) -> list:
    """根据IP获取实例信息"""

    instances = []
    machine = Machine.objects.get(ip=ip, bk_cloud_id=bk_cloud_id)
    for instance in machine.storageinstance_set.all():
        instances.append(
            {
                "ip": ip,
                "port": instance.port,
                "bk_cloud_id": bk_cloud_id,
            }
        )
    return instances


def instance_migrate_remove_hosts(flow_data: dict) -> list:
    """实例迁移下架主机"""

    remove_hosts = []
    cluster_type = flow_data.get("cluster_type")
    clusters_node_set = set()
    all_instances_set = set()
    # 获取所有主机的集合
    hosts_set = set()
    # 没有被回收的主机的集合
    no_remove_hosts_set = set()
    if cluster_type == ClusterType.MongoReplicaSet.value:
        for migrate_info in flow_data.get("infos"):
            for cluster_id in migrate_info.get("cluster_ids"):
                # 获取cluster的shard信息
                nodes = get_shards_info(cluster_id)
                for node in nodes:
                    # 集群实例的集合和机器的集合
                    clusters_node_set.add((node["ip"], node["port"], node["bk_cloud_id"]))
                    hosts_set.add((node["ip"], node["bk_cloud_id"]))

    elif cluster_type == ClusterType.MongoShardedCluster.value:
        for migrate_info in flow_data.get("infos"):
            cluster_id = migrate_info.get("cluster_id")
            shard_name = migrate_info.get("shard_name")
            shards_info = get_shards_info(cluster_id)
            for one_shard_name in shard_name:
                for shard in shards_info:
                    if shard["shard"] == one_shard_name:
                        for node in shard["nodes"]:
                            clusters_node_set.add((node["ip"], node["port"], node["bk_cloud_id"]))
                            hosts_set.add((node["ip"], node["bk_cloud_id"]))
                        break
    # 获取所有主机的实例信息
    for host in hosts_set:
        instances = get_instance_by_ip(host[0], host[1])
        for instance in instances:
            all_instances_set.add((instance["ip"], instance["port"], instance["bk_cloud_id"]))
    # 没有被回收的实例的集合
    no_remove_instances_set = all_instances_set - clusters_node_set
    # 没有被回收的主机的集合
    for no_remove_instance in no_remove_instances_set:
        no_remove_hosts_set.add((no_remove_instance[0], no_remove_instance[2]))
    # 被回收的主机的集合
    remove_hosts_set = hosts_set - no_remove_hosts_set
    if remove_hosts_set:
        for remove_host in remove_hosts_set:
            remove_hosts.append(
                {
                    "ip": remove_host[0],
                    "bk_cloud_id": remove_host[1],
                }
            )
        return remove_hosts
    else:
        return []
