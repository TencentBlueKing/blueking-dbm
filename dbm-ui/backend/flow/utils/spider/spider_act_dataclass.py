from dataclasses import dataclass

from backend.db_meta.enums import TenDBClusterSpiderRole


@dataclass()
class InstanceTuple:
    """
    定义有主从关系的实例信息对
    """

    master_ip: str
    slave_ip: str
    mysql_port: int


@dataclass()
class ShardInfo:
    """
    对应每个分片集所关联的实例信息对
    """

    shard_key: int
    instance_tuple: InstanceTuple


@dataclass
class AddSpiderRoutingKwargs:
    """
    定义添加spider节点路由的私有变量结构体
    """

    cluster_id: int
    add_spiders: list
    add_spider_role: TenDBClusterSpiderRole
    user: str
    passwd: str
