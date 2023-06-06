from backend.configuration.constants import DBType
from backend.db_package.models import Package
from backend.flow.consts import DBActuatorTypeEnum, RiakActuatorActionEnum, MediumEnum


class RiakActPayload(object):
    """
    定义Riak不同的执行类型，拼接不同的payload参数，对应不同的dict结构体
    """

    def __init__(self, ticket_data: dict):
        self.riak_pkg = None
        self.bk_biz_id = str(ticket_data["bk_biz_id"])
        self.ticket_data = ticket_data

    def get_deploy_payload(self, **kwargs) -> dict:
        """
        部署节点
        """
        self.riak_pkg = Package.get_latest_package(version=MediumEnum.Riak, pkg_type=DBType.Riak)
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.Deploy.value,
            "payload": {
                "module": self.ticket_data["db_module_id"],
                "pkg": {
                    "name": self.riak_pkg.name,
                    "md5": self.riak_pkg.md5,
                },
            },
        }

    def get_add_node_payload(self, **kwargs) -> dict:
        """
        部署节点
        """
        self.riak_pkg = Package.get_latest_package(version=MediumEnum.Riak, pkg_type=DBType.Riak)
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.AddNode.value,
            "payload": {
                "ips": kwargs["trans_data"]["operate_nodes"],
                "db_module_id": self.ticket_data["db_module_id"],
                "pkg": {
                    "name": self.riak_pkg.name,
                    "md5": self.riak_pkg.md5,
                },
            },
        }