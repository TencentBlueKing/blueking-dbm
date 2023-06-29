from backend.configuration.constants import DBType
from backend.db_package.models import Package
from backend.flow.consts import DBActuatorTypeEnum, MediumEnum, RiakActuatorActionEnum
from backend.ticket.constants import TicketType


class RiakActPayload(object):
    """
    定义Riak不同的执行类型，拼接不同的payload参数，对应不同的dict结构体
    """

    def __init__(self, ticket_data: dict, cluster: dict):
        self.riak_pkg = None
        self.bk_biz_id = str(ticket_data["bk_biz_id"])
        self.ticket_data = ticket_data
        self.cluster = cluster

    def get_sysinit_payload(self, **kwargs) -> dict:
        """
        系统配置初始化
        """
        return {
            "db_type": DBActuatorTypeEnum.Default.value,
            "action": RiakActuatorActionEnum.SysinitRiak.value,
            "payload": {"general": {}, "extend": {}},
        }

    def get_deploy_payload(self, **kwargs) -> dict:
        """
        部署节点
        """
        self.riak_pkg = Package.get_latest_package(
            version=self.ticket_data["db_version"], pkg_type=MediumEnum.Riak, db_type=DBType.Riak
        )
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.Deploy.value,
            "payload": {
                "general": {},
                "extend": {
                    "distributed_cookie": self.cluster["distributed_cookie"],
                    "ring_size": self.cluster["ring_size"],
                    "leveldb.expiration": self.cluster["leveldb.expiration"],
                    "leveldb.expiration.mode": self.cluster["leveldb.expiration.mode"],
                    "leveldb.expiration.retention_time": self.cluster["leveldb.expiration.retention_time"],
                    "pkg": {
                        "name": self.riak_pkg.name,
                        "md5": self.riak_pkg.md5,
                    },
                },
            },
        }

    def get_deploy_trans_payload(self, **kwargs) -> dict:
        """
        部署节点
        """
        self.riak_pkg = Package.get_latest_package(
            version=self.ticket_data["db_version"], pkg_type=MediumEnum.Riak, db_type=DBType.Riak
        )
        configs = kwargs["trans_data"]["configs"]
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.Deploy.value,
            "payload": {
                "general": {},
                "extend": {
                    "distributed_cookie": configs["distributed_cookie"],
                    "ring_size": configs["ring_size"],
                    "leveldb.expiration": configs["leveldb.expiration"],
                    "leveldb.expiration.mode": configs["leveldb.expiration.mode"],
                    "leveldb.expiration.retention_time": configs["leveldb.expiration.retention_time"],
                    "pkg": {
                        "name": self.riak_pkg.name,
                        "md5": self.riak_pkg.md5,
                    },
                },
            },
        }

    def get_join_cluster_payload(self, **kwargs) -> dict:
        """
        添加节点
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.JoinCluster.value,
            "payload": {
                "general": {},
                "extend": {
                    "distributed_cookie": self.cluster["distributed_cookie"],
                    "ring_size": self.cluster["ring_size"],
                    "base_node": kwargs["trans_data"]["base_node"],
                },
            },
        }

    def get_join_cluster_trans_payload(self, **kwargs) -> dict:
        """
        添加节点
        """
        configs = kwargs["trans_data"]["configs"]
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.JoinCluster.value,
            "payload": {
                "general": {},
                "extend": {
                    "distributed_cookie": configs["distributed_cookie"],
                    "ring_size": configs["ring_size"],
                    "base_node": kwargs["trans_data"]["base_node"],
                },
            },
        }

    def get_remove_node_payload(self, **kwargs) -> dict:
        """
        剔除节点
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.RemoveNode.value,
            "payload": {
                "general": {},
                "extend": {
                    "operate_nodes": kwargs["trans_data"]["operate_nodes"],
                },
            },
        }

    def get_commit_cluster_change_payload(self, **kwargs) -> dict:
        """
        集群变更生效
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.CommitClusterChange.value,
            "payload": {
                "general": {},
                "extend": {
                    "nodes": kwargs["trans_data"]["nodes"],
                },
            },
        }

    def get_transfer_payload(self, **kwargs) -> dict:
        """
        集群数据搬迁进度
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.Transfer.value,
            "payload": {
                "general": {},
                "extend": {"auto_stop": self.ticket_data["ticket_type"] == TicketType.RIAK_CLUSTER_SCALE_IN},
            },
        }

    def get_check_connections_payload(self, **kwargs) -> dict:
        """
        检查连接
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.CheckConnections.value,
            "payload": {
                "general": {},
                "extend": {},
            },
        }

    def get_init_bucket_type_payload(self, **kwargs) -> dict:
        """
        初始化bucket_type
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.InitBucketType.value,
            "payload": {
                "general": {},
                "extend": {
                    "bucket_types": self.cluster["bucket_types"],
                },
            },
        }

    def get_config_payload(self, **kwargs) -> dict:
        """
        系统配置初始化
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.GetConfig.value,
            "payload": {"general": {}, "extend": {}},
        }

    def get_uninstall_payload(self, **kwargs) -> dict:
        """
        下架
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.UnInstall.value,
            "payload": {
                "general": {},
                "extend": {"auto_stop": self.ticket_data["ticket_type"] == TicketType.RIAK_CLUSTER_SCALE_IN},
            },
        }
