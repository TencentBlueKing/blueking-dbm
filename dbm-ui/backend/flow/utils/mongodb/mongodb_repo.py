from abc import abstractmethod
from typing import List, Union

from rest_framework import serializers

from backend.db_meta import request_validator
from backend.db_meta.enums import machine_type
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_meta.models import AppCache, Cluster, Machine, ProxyInstance, StorageInstance
from backend.flow.consts import MongoDBClusterRole
from backend.flow.utils.mongodb import mongodb_password
from backend.ticket.constants import InstanceType

# entities
# Node -> ReplicaSet -> Cluster[Rs,ShardedCluster]
# MongoNodeWithLabel
# MongoDBNsFilter


class MongoNode:
    def __init__(self, ip, port, role, bk_cloud_id, mtype, domain=None):
        self.ip: str = ip
        self.port: str = port
        self.role: str = role
        self.bk_cloud_id: int = bk_cloud_id
        self.machine_type = mtype
        self.domain: str = domain  # 这是关联bind_entry.first().entry

    # s is StorageInstance | ProxyInstance
    @classmethod
    def from_instance(cls, s: Union[ProxyInstance, StorageInstance], with_domain: bool = False):
        # withDomain: 默认为False. 取域名需要多查一次db.
        # meta_role: ProxyInstance的instance_role属性值为"proxy". 这里改为 mongos
        meta_role = MongoDBClusterRole.Mongos.value if s.instance_role == InstanceType.PROXY.value else s.instance_role
        domain = None
        if with_domain:
            domain = s.bind_entry.first().entry
        node = MongoNode(
            s.ip_port.split(":")[0], str(s.port), meta_role, s.machine.bk_cloud_id, s.machine_type, domain
        )
        return node


class ReplicaSet:
    set_name: str
    set_type: str  # replicaset or shardsvr or configsvr
    members: List[MongoNode]

    def __init__(self, set_type: str, set_name: str = None, members: List[MongoNode] = None):
        self.set_type = set_type
        self.set_name = set_name
        self.members = members

    # get_backup_node 返回MONGO_BACKUP member
    def get_backup_node(self):
        i = len(self.members) - 1
        while i >= 0:
            if self.members[i].role == InstanceRole.MONGO_BACKUP:
                return self.members[i]
            i = i - 1

        return None

    # get_not_backup_nodes 返回非MONGO_BACKUP的member
    def get_not_backup_nodes(self):
        members = []
        for m in self.members:
            if m.role != InstanceRole.MONGO_BACKUP:
                members.append(m)

        return members

    def get_bk_cloud_id(self):
        for i in self.members:
            return i.bk_cloud_id
        return None


# MongoDBCluster [interface] 有cluster_id cluster_name cluster_type
class MongoDBCluster:
    bk_cloud_id: int
    bk_biz_id: int
    creator: str
    name: str
    app: str
    immute_domain: str
    alias: str
    major_version: str
    region: str
    cluster_type: str
    cluster_id: str

    def __init__(
        self,
        bk_cloud_id: int = None,
        cluster_id: str = None,
        name: str = None,
        cluster_type: str = None,
        major_version: str = None,
        bk_biz_id: int = None,
        immute_domain: str = None,
        app: str = None,
        region: str = None,
    ):
        self.cluster_id = cluster_id
        self.name = name
        self.cluster_type = cluster_type
        self.major_version = major_version
        self.bk_biz_id = bk_biz_id
        self.immute_domain = immute_domain
        self.bk_cloud_id = bk_cloud_id
        self.app = app
        self.region = region

    @abstractmethod
    def get_shards(self) -> List[ReplicaSet]:
        raise NotImplementedError

    @abstractmethod
    def get_mongos(self) -> List[MongoNode]:
        raise NotImplementedError

    @abstractmethod
    def get_config(self) -> ReplicaSet:
        raise NotImplementedError

    def get_bk_cloud_id(self) -> int:
        return self.bk_cloud_id

    def is_sharded_cluster(self) -> bool:
        return self.cluster_type == str(ClusterType.MongoShardedCluster.value)

    def get_iplist(self) -> List:
        iplist = []
        for shard in self.get_shards():
            for member in shard.members:
                iplist.append(member.ip)
        config_rs = self.get_config()
        if config_rs is not None:
            for member in config_rs.members:
                iplist.append(member.ip)
        for mongos in self.get_mongos():
            iplist.append(mongos.ip)
        return iplist


class ReplicaSetCluster(MongoDBCluster):
    shard: ReplicaSet  # storages

    def __init__(
        self,
        bk_cloud_id=None,
        cluster_id=None,
        name=None,
        major_version=None,
        bk_biz_id=None,
        immute_domain=None,
        app: str = None,
        region: str = None,
        shard: ReplicaSet = None,
    ):
        super().__init__(
            bk_cloud_id,
            cluster_id,
            name,
            ClusterType.MongoReplicaSet.value,
            major_version,
            bk_biz_id,
            immute_domain,
            app,
            region,
        )
        self.shard = shard

    def get_shards(self, with_config: bool = False) -> List[ReplicaSet]:
        # no config
        return [self.shard]

    def get_mongos(self) -> List[MongoNode]:
        """Not Implemented"""
        return []

    def get_config(self) -> ReplicaSet:
        """Not Implemented"""
        return None


class ShardedCluster(MongoDBCluster):
    shards: List[ReplicaSet]  # storages
    mongos: List[MongoNode]  # proxies
    configsvr: ReplicaSet  # configs

    def __init__(
        self,
        bk_cloud_id=None,
        cluster_id=None,
        name=None,
        major_version=None,
        bk_biz_id=None,
        immute_domain=None,
        app: str = None,
        region: str = None,
        shards: List[ReplicaSet] = None,
        mongos: List[MongoNode] = None,
        configsvr: ReplicaSet = None,
    ):
        super().__init__(
            bk_cloud_id,
            cluster_id,
            name,
            ClusterType.MongoShardedCluster.value,
            major_version,
            bk_biz_id,
            immute_domain,
            app,
            region,
        )
        self.shards = shards
        self.mongos = mongos
        self.config = configsvr

    def get_shards(self, with_config: bool = False) -> List[ReplicaSet]:
        if not with_config:
            return self.shards

        shards = [self.config]
        shards.extend(self.shards)
        return shards

    def get_config(self) -> ReplicaSet:
        return self.config

    def get_mongos(self) -> List[MongoNode]:
        return self.mongos


# MongoRepository
#
class MongoRepository:
    def __init__(self):
        pass

    @classmethod
    def fetch_many_cluster(cls, with_domain: bool, **kwargs):
        # with_domain 是否: 获取复制集和mongos的域名，赋值在MongoNode的domain属性上
        rows: List[MongoDBCluster] = []
        v = Cluster.objects.filter(**kwargs)
        for i in v:
            if i.cluster_type == ClusterType.MongoReplicaSet.value:
                # MongoReplicaSet 只有一个Set
                shard = ReplicaSet(
                    MongoDBClusterRole.Replicaset.value,
                    i.name,
                    [MongoNode.from_instance(m, with_domain) for m in i.storageinstance_set.all()],
                )

                row = ReplicaSetCluster(
                    bk_cloud_id=i.bk_cloud_id,
                    cluster_id=i.id,
                    name=i.name,
                    major_version=i.major_version,
                    bk_biz_id=i.bk_biz_id,
                    immute_domain=i.immute_domain,
                    app=None,  # app和bk_biz_id是1-1的关系，有一个就够了
                    shard=shard,
                    region=i.region,
                )

                rows.append(row)
            elif i.cluster_type == ClusterType.MongoShardedCluster.value:
                shards = []
                configsvr = None
                mongos = [MongoNode.from_instance(m, with_domain=with_domain) for m in i.proxyinstance_set.all()]

                for m in i.nosqlstoragesetdtl_set.all():
                    # find first member
                    members = [MongoNode.from_instance(m.instance)]
                    # find all receiver member
                    for e in m.instance.as_ejector.all():
                        members.append(MongoNode.from_instance(e.receiver))

                    # configsvr
                    if m.instance.machine_type == machine_type.MachineType.MONOG_CONFIG.value:
                        shard = ReplicaSet(MongoDBClusterRole.ConfigSvr.value, set_name=m.seg_range, members=members)
                        configsvr = shard

                    # shardsvr
                    else:
                        shard = ReplicaSet(MongoDBClusterRole.ShardSvr.value, set_name=m.seg_range, members=members)
                        shards.append(shard)

                row = ShardedCluster(
                    bk_cloud_id=i.bk_cloud_id,
                    cluster_id=i.id,
                    name=i.name,
                    major_version=i.major_version,
                    bk_biz_id=i.bk_biz_id,
                    immute_domain=i.immute_domain,
                    app=None,  # app和bk_biz_id是1-1的关系，有一个就够了
                    mongos=mongos,
                    shards=shards,
                    configsvr=configsvr,
                    region=i.region,
                )

                rows.append(row)

        return rows

    @classmethod
    def fetch_one_cluster(cls, withDomain: bool, **kwargs):
        rows = cls.fetch_many_cluster(withDomain, **kwargs)
        if len(rows) > 0:
            return rows[0]
        return None

    @classmethod
    def fetch_many_cluster_dict(cls, withDomain: bool = False, **kwargs):
        clusters = cls.fetch_many_cluster(withDomain, **kwargs)
        clusters_map = {}
        for cluster in clusters:
            clusters_map[cluster.cluster_id] = cluster
        return clusters_map

    @staticmethod
    def get_cluster_id_by_host(hosts: List, bk_cloud_id: int) -> List[int]:
        """根据提供的IP 查询集群信息"""
        hosts = request_validator.validated_str_list(hosts)
        cluster_list = []
        rows = Machine.objects.prefetch_related("storageinstance_set").filter(ip__in=hosts, bk_cloud_id=bk_cloud_id)
        if rows is not None:
            for machine_row in rows:
                for storage in machine_row.storageinstance_set.prefetch_related("cluster"):  # 这里存在多个实例
                    for cluster in storage.cluster.all():
                        # todo 检查 只能是MongoDb的Cluster
                        cluster_list.append(cluster.id)

        rows = Machine.objects.prefetch_related("proxyinstance_set").filter(ip__in=hosts, bk_cloud_id=bk_cloud_id)
        if rows is not None:
            for machine_row in rows:
                for storage in machine_row.proxyinstance_set.prefetch_related("cluster"):  # 这里存在多个实例
                    for cluster in storage.cluster.all():
                        # todo 检查 只能是MongoDb的Cluster
                        cluster_list.append(cluster.id)

        return list(set(cluster_list))

    @classmethod
    def get_cluster_id_by_domain(cls, cluster_domain: [str]) -> List[int]:
        cluster_domain = request_validator.validated_str_list(cluster_domain)
        cluster_list = []
        rows = Cluster.objects.filter(immute_domain__in=cluster_domain)
        for row in rows:
            cluster_list.append(row.id)
        return cluster_list

    @classmethod
    def get_host_from_nodes(cls, nodes: List[MongoNode]) -> List:
        """
        get_host_from_nodes 提取bk_host，且去重
        @param nodes: MongoNode列表
        """
        bk_host_list = []
        cloud_id = nodes[0].bk_cloud_id
        ips = []
        for v in nodes:
            ips.append(v.ip)
            if v.bk_cloud_id != cloud_id:
                raise Exception("cannot exist two cloud_id")

        ips = list(set(ips))
        for ip in ips:
            bk_host_list.append({"ip": ip, "bk_cloud_id": cloud_id})

        return bk_host_list


class MongoDBNsFilter(object):
    class Serializer(serializers.Serializer):
        db_patterns = serializers.ListField(child=serializers.CharField(), allow_null=True)
        table_patterns = serializers.ListField(child=serializers.CharField(), allow_null=True)
        ignore_dbs = serializers.ListField(child=serializers.CharField(), allow_null=True)
        ignore_tables = serializers.ListField(child=serializers.CharField(), allow_null=True)

    """
    MongoDBNsFilter
    """
    db_patterns: [str] = None
    ignore_dbs: [str] = None
    table_patterns: [str] = None
    ignore_tables: [str] = None

    def __init__(self):
        pass

    @classmethod
    def is_partial(cls, payload: dict) -> bool:
        if payload is None:
            return False
        else:
            if (
                payload["db_patterns"] is None
                and payload["ignore_dbs"] is None
                and payload["table_patterns"] is None
                and payload["ignore_tables"] is None
            ):
                return False

            if (
                payload["db_patterns"] is None
                or payload["ignore_dbs"] is None
                or payload["table_patterns"] is None
                or payload["ignore_tables"] is None
            ):
                raise Exception("bad nsFilter {}".format(payload))
            return True

    @classmethod
    def from_payload(cls, payload: dict):
        m = MongoDBNsFilter()
        m.db_patterns = payload["db_patterns"]
        m.ignore_dbs = payload["ignore_dbs"]
        m.table_patterns = payload["table_patterns"]
        m.ignore_tables = payload["ignore_tables"]
        return m


class MongoNodeWithLabel(object):
    """
    MongoNodeWithLabel 包含了MongoDB节点的所有信息，对应的go文件是: dbm-services/mongo/db-tools/dbmon/config/config.go
    包括：
    BkDbmLabel bk dbm label for Instance
    BkCloudID     int64  `json:"bk_cloud_id" mapstructure:"bk_cloud_id" yaml:"bk_cloud_id"`
    BkBizID       string `json:"bk_biz_id" mapstructure:"bk_biz_id" yaml:"bk_biz_id" yaml:"bk_biz_id"`
    App           string `json:"app" mapstructure:"app" yaml:"app"`
    AppName       string `json:"app_name" mapstructure:"-" yaml:"app_name"`
    ClusterDomain string `json:"cluster_domain" mapstructure:"cluster_domain" yaml:"cluster_domain"`
    ClusterId     string `json:"cluster_id" mapstructure:"cluster_id" yaml:"cluster_id"`
    ClusterName   string `json:"cluster_name" mapstructure:"cluster_name" yaml:"cluster_name"`
    ClusterType   string `json:"cluster_type" mapstructure:"cluster_type" yaml:"cluster_type"`
    RoleType      string `json:"role_type" mapstructure:"role_type" yaml:"role_type"` // shardsvr,mongos,configsvr
    MetaRole      string `json:"meta_role" mapstructure:"meta_role" yaml:"meta_role"` // m0,m1,backup...|mongos
    ServerIP      string `json:"ip" mapstructure:"ip" yaml:"ip"`
    ServerPort    int    `json:"port" mapstructure:"port" yaml:"port" yaml:"port"`
    SetName       string `json:"setname" mapstructure:"setname" yaml:"setname" yaml:"set_name"`
    """

    bk_cloud_id: int = None
    bk_biz_id: int = None
    app: str = None
    app_name: str = None
    cluster_domain: str = None
    cluster_id: str = None
    cluster_name: str = None
    cluster_type: str = None
    role_type: str = None
    meta_role: str = None
    ip: str = None
    port: int = None
    set_name: str = None
    username: str = None
    password: str = None

    def __init__(self):
        pass

    def __json__(self):
        return {
            "bk_cloud_id": int(self.bk_cloud_id),
            "bk_biz_id": int(self.bk_biz_id),
            "app": str(self.app),
            "app_name": str(self.app_name),
            "cluster_domain": str(self.cluster_domain),
            "cluster_id": int(self.cluster_id),
            "cluster_name": self.cluster_name,
            "cluster_type": self.cluster_type,
            "role_type": self.role_type,
            "meta_role": self.meta_role,
            "ip": self.ip,
            "port": int(self.port),
            "set_name": self.set_name,
            "username": self.username,
            "password": self.password,
        }

    def __json__without_password__(self):
        return {
            "bk_cloud_id": int(self.bk_cloud_id),
            "bk_biz_id": int(self.bk_biz_id),
            "app": str(self.app),
            "app_name": str(self.app_name),
            "cluster_domain": str(self.cluster_domain),
            "cluster_id": int(self.cluster_id),
            "cluster_name": self.cluster_name,
            "cluster_type": self.cluster_type,
            "role_type": self.role_type,
            "meta_role": self.meta_role,
            "ip": self.ip,
            "port": int(self.port),
            "set_name": self.set_name,
        }

    def append_cluster_info(self, clu: MongoDBCluster):
        self.cluster_id = clu.cluster_id
        self.cluster_name = clu.name
        self.cluster_type = clu.cluster_type
        self.cluster_domain = clu.immute_domain
        self.app = AppCache.get_app_attr(clu.bk_biz_id, "db_app_abbr")
        self.app_name = AppCache.get_biz_name(clu.bk_biz_id)
        self.bk_cloud_id = clu.bk_cloud_id
        self.bk_biz_id = clu.bk_biz_id

    @classmethod
    def from_node(cls, node: MongoNode, rs: ReplicaSet = None, clu: MongoDBCluster = None):
        m = MongoNodeWithLabel()
        m.bk_cloud_id = node.bk_cloud_id
        m.ip = node.ip
        m.port = int(node.port)
        m.meta_role = node.role
        if m.meta_role == machine_type.MachineType.MONGOS.value:
            # if mongos, set set_name && role_type to 'mongos' for compatibility
            m.set_name = m.meta_role
            m.role_type = m.meta_role
        else:
            # not mongos
            if rs is not None:
                m.set_name = rs.set_name
                m.role_type = rs.set_type
            else:
                m.set_name = ""
                m.role_type = ""

        if clu is not None:
            m.append_cluster_info(clu)

        return m

    @staticmethod
    def from_hosts(iplist: List, bk_cloud_id: int) -> List:
        """根据提供的IP 查询集群信息
        Args:
            iplist (List): ip 列表
            bk_cloud_id (int): 云区域ID
        Return:
            List of storageinstance_set | proxyinstance_set
        """
        # todo 如果输入IP是其它类型DB的IP. 报错. or 跳过.
        instance_list = []
        cluster_id_list = MongoRepository.get_cluster_id_by_host(iplist, bk_cloud_id)
        if not cluster_id_list:
            return instance_list

        clusters = MongoRepository.fetch_many_cluster_dict(withDomain=False, id__in=cluster_id_list)
        for cluster in clusters.values():
            for member in cluster.get_mongos():
                if member.ip in iplist:
                    instance_list.append(MongoNodeWithLabel.from_node(member, None, cluster))

            for rs in cluster.get_shards():
                if not rs:
                    continue
                for member in rs.members:
                    if member.ip in iplist:
                        instance_list.append(MongoNodeWithLabel.from_node(member, rs, cluster))

            rs = cluster.get_config()
            if not rs:
                continue
            for member in rs.members:
                if member.ip in iplist:
                    instance_list.append(MongoNodeWithLabel.from_node(member, rs, cluster))

        return instance_list

    @staticmethod
    def append_password(nodes: List, username: str):
        """
        为每个节点添加密码
        """
        bk_nodes = []
        for node in nodes:
            bk_nodes.append({"ip": node.ip, "port": node.port, "bk_cloud_id": node.bk_cloud_id})
        result = mongodb_password.MongoDBPassword().get_nodes_password_from_db(bk_nodes, username)
        if result["password"] is None:
            raise Exception("get_nodes_password_from_db fail {}".format(result["info"]))

        pwd_dict = {}
        for row in result["password"]:
            k = "{}:{}:{}:{}".format(row.get("ip"), row.get("port"), row.get("bk_cloud_id"), row.get("username"))
            pwd_dict[k] = row

        for node in nodes:
            node.username = username
            k = "{}:{}:{}:{}".format(node.ip, node.port, node.bk_cloud_id, username)
            node.password = pwd_dict.get(k).get("password")

        return result
