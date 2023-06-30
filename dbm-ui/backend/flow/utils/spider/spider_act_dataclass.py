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


@dataclass
class CtlSwitchToSlaveKwargs:
    """
    定义ctl集群切换的私有变量结构体
    """

    cluster_id: int
    reduce_ctl_primary: str  # 待回收的ctl，格式是ip:port
    new_ctl_primary: str  # 待提升主的ctl，格式是ip:port


@dataclass
class CtlDropRoutingKwargs:
    """
    定义ctl节点路由删除的私有变量结构体
    """

    cluster_id: int
    reduce_ctl: str  # 待回收的ctl，格式是ip:port


@dataclass
class DropSpiderRoutingKwargs:
    """
    定义spider节点路由删除的私有变量结构体
    """

    cluster_id: int
    reduce_spiders: list  # 待下架的spider列表，每个元素的格式是字典
    is_safe: bool  # 是否做安全检测
