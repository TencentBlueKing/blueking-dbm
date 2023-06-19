from backend.configuration.constants import DBType
from backend.db_package.models import Package
from backend.flow.consts import DBActuatorTypeEnum, RiakActuatorActionEnum, MediumEnum


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
        self.riak_pkg = Package.get_latest_package(version="2.2.1", pkg_type=MediumEnum.Riak, db_type=DBType.Riak)
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.Deploy.value,
            "payload": {
                "general": {},
                "extend": {
                    "distributed_cookie": self.cluster["distributed_cookie"],
                    "ring_size": self.cluster["ring_size"],
                    "db_module_id": self.ticket_data["db_module_id"],
                    "pkg": {
                        "name": self.riak_pkg.name,
                        "md5": self.riak_pkg.md5,
                    }
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

    def get_init_bucket_type_payload(self, **kwargs) -> dict:
        """
        添加节点
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

