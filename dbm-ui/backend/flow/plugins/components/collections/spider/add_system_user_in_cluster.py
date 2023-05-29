import copy

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import DBConfigApi, MySQLPrivManagerApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.constants import IP_PORT_DIVIDER
from backend.core.encrypt.handlers import RSAHandler
from backend.db_meta.models import Cluster
from backend.flow.consts import ConfigTypeEnum, NameSpaceEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService


class AddSystemUserInClusterService(BaseService):
    """
    定义spider(tenDB cluster)集群添加内置账号的活动节点
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        # 获取内置账号信息
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": "0",
                "level_name": LevelName.PLAT,
                "level_value": "0",
                "conf_file": "spider#user",
                "conf_type": ConfigTypeEnum.InitUser,
                "namespace": NameSpaceEnum.TenDB.value,
                "format": FormatType.MAP,
            }
        )
        user = data["content"]["tdbctl_user"]
        password = data["content"]["tdbctl_pwd"]

        # 密码加密
        encrypted = RSAHandler.encrypt_password(MySQLPrivManagerApi.fetch_public_key(), password, salt=None)

        # 远程授权
        params = {
            "bk_cloud_id": 0,
            "bk_biz_id": int(global_data["bk_biz_id"]),
            "operator": global_data["created_by"],
            "user": user,
            "psw": encrypted,
            "hosts": [kwargs["ctl_master_ip"]],
            "dbname": "%",
            "dml_ddl_priv": "",
            "global_priv": "all privileges",
            "address": "",
        }

        # 新集群部署的授权模式
        if global_data["ticket_type"] == "SPIDER_CLUSTER_APPLY":

            # 获取云区域id的方式
            params["bk_cloud_id"] = global_data["bk_cloud_id"]

            # 新集群部署，对所有的新spider节点授权
            for spider_ip in global_data["spider_ip_list"]:
                content = copy.deepcopy(params)
                content["spider_flag"] = True
                content["address"] = f'{spider_ip["ip"]}{IP_PORT_DIVIDER}{global_data["spider_port"]}'
                try:
                    MySQLPrivManagerApi.add_priv_without_account_rule(content)
                    self.log_info(_("在[{}]创建添加内置账号成功").format(content["address"]))
                except Exception as e:  # pylint: disable=broad-except
                    self.log_error(_("[{}]添加用户接口异常，相关信息: {}").format(content["address"], e))
                    return False

            #  新集群部署，对所有的新的ctl节点授权
            for ctl_ip in global_data["spider_ip_list"]:
                params["address"] = f'{ctl_ip["ip"]}{IP_PORT_DIVIDER}{global_data["ctl_port"]}'
                try:
                    MySQLPrivManagerApi.add_priv_without_account_rule(params)
                    self.log_info(_("在[{}]创建添加内置账号成功").format(params["address"]))
                except Exception as e:  # pylint: disable=broad-except
                    self.log_error(_("[{}]添加用户接口异常，相关信息: {}").format(params["address"], e))
                    return False

            # 新集群部署，对所有的新remote节点授权
            for mysql_ip in global_data["mysql_ip_list"]:
                for mysql_port in global_data["mysql_ports"]:
                    params["address"] = f'{mysql_ip["ip"]}{IP_PORT_DIVIDER}{mysql_port}'
                    try:
                        MySQLPrivManagerApi.add_priv_without_account_rule(params)
                        self.log_info(_("在[{}]创建添加内置账号成功").format(params["address"]))
                    except Exception as e:  # pylint: disable=broad-except
                        self.log_error(_("[{}]添加用户接口异常，相关信息: {}").format(params["address"], e))
                        return False

            return True

        # 从集群添加的授权模式
        elif global_data["ticket_type"] == "SPIDER_SLAVE_APPLY":

            # 获取云区域id的方式,已集群信息为准
            cluster = Cluster.objects.get(id=global_data["cluster_id"])
            params["bk_cloud_id"] = cluster.bk_cloud_id
            spider_port = cluster.proxyinstance_set.first().port

            for spider_ip in global_data["spider_slave_ip_list"]:
                content = copy.deepcopy(params)
                content["spider_flag"] = True
                content["address"] = f'{spider_ip["ip"]}{IP_PORT_DIVIDER}{spider_port}'
                try:
                    MySQLPrivManagerApi.add_priv_without_account_rule(content)
                    self.log_info(_("在[{}]创建添加内置账号成功").format(content["address"]))
                except Exception as e:  # pylint: disable=broad-except
                    self.log_error(_("[{}]添加用户接口异常，相关信息: {}").format(content["address"], e))
                    return False

        else:
            self.log_error(_("[{}]根据单据类型活动节点找不到对应的授权方式。").format(global_data["ticket_type"]))
            return False


class AddSystemUserInClusterComponent(Component):
    name = __name__
    code = "add_system_user_in_cluster"
    bound_service = AddSystemUserInClusterService
