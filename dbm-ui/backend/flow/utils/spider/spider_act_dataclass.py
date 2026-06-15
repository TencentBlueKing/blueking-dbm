from dataclasses import dataclass
from typing import Dict, List, Optional

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.consts import TDBCTL_USER
from backend.flow.utils.mysql.mysql_act_dataclass import MysqlSyncMasterKwargs


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
    reduce_ctl_primary: str  # 待回收的ctl primary，格式是ip:port
    reduce_ctl_secondary_list: list  # 待回收的ctl secondary, 格式是[{"ip":xxx...}...]


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
    is_reduce_tdbctl: bool = False  # 控制是否下架中控实例


@dataclass()
class InstancePairs:
    """
    定义需要替换的实例信息对
    """

    old_ip: str
    new_ip: str
    old_port: int
    new_port: int
    server_name: str
    tdbctl_pass: str


@dataclass
class SwitchRemoteSlaveRoutingKwargs:
    """
    定义spider节点remote slave替换操作的私有变量结构体
    """

    cluster_id: int
    switch_remote_instance_pairs: Optional[List[InstancePairs]]


@dataclass()
class InstanceServerName:
    """
    定义需要替换的实例信息对
    """

    server_name: str
    new_ip: str
    new_port: int
    tdbctl_pass: str


@dataclass
class SwitchRemoteShardRoutingKwargs:
    """
    定义spider节点remote slave替换操作的私有变量结构体
    """

    cluster_id: int
    switch_remote_shard: Optional[List[InstanceServerName]]


@dataclass
class AddSpiderRoutingSubFlowParam:
    """
    add_spider_routing_sub_flow 的入参数据结构。

    @param cluster: 待操作的集群对象, 用于推导 bk_cloud_id / ctl_primary 等。
    @param add_spiders: 待添加的 spider 节点列表, 元素形如 {"ip": "x.x.x.x", "bk_host_id": 123, ...}。
    @param add_spider_role: 待添加节点的角色, 取值范围 TenDBClusterSpiderRole 中的:
                            spider_master / spider_slave / spider_mnt。
                            支持传入枚举或字符串两种形式, 子流程内部会自动归一化。
    @param spider_pass: spider 端口内置账号 (TDBCTL_USER) 的密码; 通常是上层流程为本批节点
                        新生成的随机串, 必填。
    @param spider_user: spider 端口内置账号名, 默认即 TDBCTL_USER, 一般不需要覆盖。
    @param tdbctl_pass: 中控之间互相连接的共享密码; 仅 spider_master 角色需要,
                        留空时 dbactuator 会从中控本机 mysql.servers 兜底读取
                        (等价于 Python 旧版 _read_ctl_pass)。
    """

    cluster: Cluster
    add_spiders: List[Dict]
    add_spider_role: str
    spider_pass: str
    spider_user: str = TDBCTL_USER


@dataclass
class SpiderSyncCtlMasterKwargs(MysqlSyncMasterKwargs):
    """
    定义 spider 中控集群同步 (SyncCtlMasterService) 活动节点的私有变量结构体。

    在 MysqlSyncMasterKwargs 基础上新增 cluster_id, 用于在活动节点 _execute 入口处
    通过 Cluster.tendbcluster_ctl_primary_address() 实时探测当前 ctl primary, 避免
    上层编排时缓存的 master 与运行时真实 primary 不一致 (中控切换场景)。

    @attributes cluster_id: 待操作的 TenDB Cluster 集群 id, 必填。
    其余字段含义与 MysqlSyncMasterKwargs 完全一致。
    """

    # 由于父类已经有非默认值字段, 这里给一个默认值占位, 实例化时调用方必须显式传入。
    cluster_id: int = 0
