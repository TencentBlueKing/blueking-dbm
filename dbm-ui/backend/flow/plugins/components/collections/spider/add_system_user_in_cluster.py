from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import MySQLPrivManagerApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.consts import PrivRole
from backend.flow.plugins.components.collections.common.base_service import BaseService


class AddSystemUserInClusterService(BaseService):
    """
    定义spider(tenDB cluster)集群添加内置账号的活动节点
    """

    def __add_priv(self, params):
        """
        定义添加权限的内置方法
        """

        try:
            MySQLPrivManagerApi.add_priv_without_account_rule(params)
            self.log_info(_("在[{}]创建添加内置账号成功").format(params["address"]))
        except Exception as e:  # pylint: disable=broad-except
            self.log_error(_("[{}]添加用户接口异常，相关信息: {}").format(params["address"], e))
            return False

        return True

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        user = kwargs["user"]
        password = kwargs["passwd"]

        # 远程授权
        params = {
            "bk_cloud_id": global_data["bk_cloud_id"],
            "bk_biz_id": int(global_data["bk_biz_id"]),
            "operator": global_data["created_by"],
            "user": user,
            "psw": password,
            "hosts": [kwargs["ctl_master_ip"]],
            "dbname": "%",
            "dml_ddl_priv": "",
            "global_priv": "all privileges",
            "address": "",
            "role": "",
        }

        # 新集群部署，对所有的新spider节点授权
        for spider_ip in global_data["spider_ip_list"]:
            params["address"] = f'{spider_ip["ip"]}{IP_PORT_DIVIDER}{global_data["spider_port"]}'
            params["role"] = PrivRole.SPIDER.value
            if not self.__add_priv(params=params):
                return False

        #  新集群部署，对所有的新的ctl节点授权
        for ctl_ip in global_data["spider_ip_list"]:
            params["address"] = f'{ctl_ip["ip"]}{IP_PORT_DIVIDER}{global_data["ctl_port"]}'
            params["role"] = PrivRole.TDBCTL.value
            if not self.__add_priv(params=params):
                return False

        # 新集群部署，对所有的新remote节点授权
        for mysql_ip in global_data["mysql_ip_list"]:
            for mysql_port in global_data["mysql_ports"]:
                params["address"] = f'{mysql_ip["ip"]}{IP_PORT_DIVIDER}{mysql_port}'
                params["role"] = PrivRole.MYSQL.value
                if not self.__add_priv(params=params):
                    return False

        return True


class AddSystemUserInClusterComponent(Component):
    name = __name__
    code = "add_system_user_in_cluster"
    bound_service = AddSystemUserInClusterService
