from abc import abstractmethod
from typing import List, Union

from rest_framework import serializers

from backend.db_meta.enums import machine_type
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance

# entities
# Node -> ReplicaSet -> Cluster[Rs,ShardedCluster]
# MongoNodeWithLabel
# MongoDBNsFilter


class MongoNode:
    def __init__(self, ip, port, role, bk_cloud_id, mtype):
        self.ip: str = ip
        self.port: str = port
        self.role: str = role
        self.bk_cloud_id: int = bk_cloud_id
        self.machine_type = mtype
        self.domain: str = None  # 这是关联bind_entry.first().entry

    # s is StorageInstance | ProxyInstance
    @classmethod
    def from_instance(cls, s: Union[ProxyInstance, StorageInstance]):
        return MongoNode(s.ip_port.split(":")[0], str(s.port), s.instance_role, s.machine.bk_cloud_id, s.machine_type)

    @classmethod
    def from_proxy_instance(cls, s: ProxyInstance):
        m = cls.from_instance(s)
        m.domain = s.bind_entry.first().entry
        return m


class ReplicaSet:
    set_name: str
    set_type: str
    members: List[MongoNode]

    def __init__(self, set_name: str = None, members: List[MongoNode] = None):
        self.set_name = set_name
        self.members = members
        if len(self.members) > 0:
            self.set_type = self.members[0].role

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
            if m.role == InstanceRole.MONGO_BACKUP:
                members.append(m)

        return members

    def get_bk_cloud_id(self):
        for i in self.members:
            return i.bk_cloud_id
        return None


# MongoDBCluster 有cluster_id cluster_name cluster_type
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
    ):
        self.cluster_id = cluster_id
        self.name = name
        self.cluster_type = cluster_type
        self.major_version = major_version
        self.bk_biz_id = bk_biz_id
        self.immute_domain = immute_domain
        self.bk_cloud_id = bk_cloud_id
        self.app = app

    @abstractmethod
    def get_shards(self):
        pass

    @abstractmethod
    def get_mongos(self) -> List[MongoNode]:
        pass

    @abstractmethod
    def get_config(self) -> ReplicaSet:
        pass

    def get_bk_cloud_id(self) -> int:
        return self.bk_cloud_id


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
        )
        self.shard = shard

    def get_shards(self):
        return [self.shard]

    def get_mongos(self) -> List[MongoNode]:
        """ Not Implemented"""
        return []

    def get_config(self) -> ReplicaSet:
        """ Not Implemented"""
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
        )
        self.shards = shards
        self.mongos = mongos
        self.config = configsvr

    def get_shards(self) -> List[ReplicaSet]:
        return self.shards

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
    def fetch_many_cluster(cls, **kwargs):
        rows: List[MongoDBCluster] = []
        v = Cluster.objects.filter(**kwargs)
        for i in v:
            if i.cluster_type == ClusterType.MongoReplicaSet.value:
                # MongoReplicaSet 只有一个Set
                shard = ReplicaSet(i.name, [MongoNode.from_instance(m) for m in i.storageinstance_set.all()])

                row = ReplicaSetCluster(
                    bk_cloud_id=i.bk_cloud_id,
                    cluster_id=i.id,
                    name=i.name,
                    major_version=i.major_version,
                    bk_biz_id=i.bk_biz_id,
                    immute_domain=i.immute_domain,
                    app=None,  # app和bk_biz_id是1-1的关系，有一个就够了
                    shard=shard,
                )

                rows.append(row)
            elif i.cluster_type == ClusterType.MongoShardedCluster.value:
                shards = []
                configsvr = None
                mongos = [MongoNode.from_proxy_instance(m) for m in i.proxyinstance_set.all()]

                for m in i.nosqlstoragesetdtl_set.all():
                    # seg_range
                    members = [MongoNode.from_instance(m.instance)]
                    for e in m.instance.as_ejector.all():
                        members.append(MongoNode.from_instance(e.receiver))

                    shard = ReplicaSet(set_name=m.seg_range, members=members)
                    if m.instance.machine_type == machine_type.MachineType.MONOG_CONFIG.value:
                        configsvr = shard
                    else:
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
                )

                rows.append(row)

        return rows

    @classmethod
    def fetch_one_cluster(cls, **kwargs):
        rows = cls.fetch_many_cluster(**kwargs)
        if len(rows) > 0:
            return rows[0]
        return None

    @classmethod
    def fetch_many_cluster_dict(cls, **kwargs):
        clusters = cls.fetch_many_cluster(**kwargs)
        clusters_map = {}
        for cluster in clusters:
            clusters_map[cluster.cluster_id] = cluster
        return clusters_map


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
    ServerIP      string `json:"server_ip" mapstructure:"server_ip" yaml:"server_ip"`
    ServerPort    int    `json:"server_port" mapstructure:"server_port" yaml:"server_port" yaml:"server_port"`
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
    server_ip: str = None
    server_port: int = None
    set_name: str = None

    def __init__(self):
        pass

    def __json__(self):
        return {
            "bk_cloud_id": int(self.bk_cloud_id),
            "bk_biz_id": int(self.bk_biz_id),
            "app": self.app,
            "app_name": self.app_name,
            "cluster_domain": self.cluster_domain,
            "cluster_id": int(self.cluster_id),
            "cluster_name": self.cluster_name,
            "cluster_type": self.cluster_type,
            "role_type": self.role_type,
            "meta_role": self.meta_role,
            "server_ip": self.server_ip,
            "server_port": int(self.server_port),
            "set_name": self.set_name,
        }

    def append_set_info(self, rs: ReplicaSet):
        self.set_name = rs.set_name
        self.role_type = rs.set_type

    def append_cluster_info(self, clu: MongoDBCluster):
        self.cluster_id = clu.cluster_id
        self.cluster_name = clu.name
        self.cluster_type = clu.cluster_type
        self.cluster_domain = clu.immute_domain
        self.app = clu.app
        self.app_name = clu.app
        self.bk_cloud_id = clu.bk_cloud_id
        self.bk_biz_id = clu.bk_biz_id

    @classmethod
    def from_node(cls, node: MongoNode, rs: ReplicaSet = None, clu: MongoDBCluster = None):
        m = MongoNodeWithLabel()
        m.bk_cloud_id = node.bk_cloud_id
        m.server_ip = node.ip
        m.server_port = node.port
        m.meta_role = node.role
        # if mongos, set set_name && role_type to 'mongos' for compatibility
        if m.meta_role == machine_type.MachineType.MONGOS.value:
            m.set_name = machine_type.MachineType.MONGOS.value
            m.role_type = machine_type.MachineType.MONGOS.value
        elif rs is not None:
            m.append_set_info(rs)

        if clu is not None:
            m.append_cluster_info(clu)

        return m
