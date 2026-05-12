"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DBPrivManagerApi, DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.consts import TDBCTL_USER, PrivRole
from backend.flow.plugins.components.collections.common.base_service import BaseService


class AddSpiderSystemUserService(BaseService):
    """
    Add internal accounts for to-be-joined spider nodes.

    This activity is split out from AddSpiderRoutingService so that
    user-granting is decoupled from the routing-creation step:
      1. drop the existing TDBCTL_USER@<ctl_primary_host> on each spider
         node (idempotent, prevents conflict when create-node implicitly
         re-creates accounts);
      2. add internal account on the spider business port (role=SPIDER);
      3. when add_spider_role == spider_master, also add internal account
         on the corresponding tdbctl admin port (role=TDBCTL).

    Required kwargs:
        cluster_id        (int)
        add_spiders       (list[dict]): [{"ip": "x.x.x.x"}, ...]
        add_spider_role   (str): spider_master / spider_slave / spider_mnt
        user              (str): internal account name on spider port
        passwd            (str): internal account password on spider port

    Optional kwargs:
        ctl_pass          (str): internal account password on tdbctl admin
                                 port. Required (effectively) when
                                 add_spider_role == spider_master. If
                                 not provided, will be read from current
                                 ctl-primary's mysql.servers as fallback.

    Required global_data:
        created_by        (str): the requester username, used as operator
                                 in DBPrivManagerApi.
    """

    def _drop_user(self, spider_ip: str, spider_port: int, ctl_primary_host: str, bk_cloud_id: int):
        """
        Drop TDBCTL_USER@<ctl_primary_host> on the target spider node, so
        that the implicit account creation inside `tdbctl create node`
        won't fail because of an existing-user/replication conflict.

        Errors here are warnings only and never block the flow, which is
        consistent with the original AddSpiderRoutingService behavior.
        """
        res = DRSApi.rpc(
            {
                "addresses": [f"{spider_ip}{IP_PORT_DIVIDER}{spider_port}"],
                "cmds": [f"DROP USER '{TDBCTL_USER}'@'{ctl_primary_host}'"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            self.log_warning(f"drop user failed:[{res[0]['error_msg']}]")
        return True

    def _read_ctl_pass(self, ctl_master: str, bk_cloud_id: int) -> str:
        """
        Fallback to read the internal tdbctl password from the current
        ctl-primary's mysql.servers, so all tdbctl nodes in the same
        cluster share an identical credential and avoid replication
        conflicts.
        """
        res = DRSApi.rpc(
            {
                "addresses": [f"{ctl_master}"],
                "cmds": ["select Password as result from mysql.servers where Server_name like 'TDBCTL%' limit 1"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            self.log_error(f"read ctl pass failed:[{res[0]['error_msg']}]")
            return ""

        table_data = res[0]["cmd_results"][0]["table_data"]
        if not table_data:
            self.log_error("read ctl pass failed: empty result from mysql.servers")
            return ""
        return table_data[0]["result"]

    def __add_priv(self, params: dict) -> bool:
        try:
            DBPrivManagerApi.add_priv_without_account_rule(params)
            self.log_info(_("在[{}]创建添加内置账号成功").format(params["address"]))
        except Exception as e:  # pylint: disable=broad-except
            self.log_error(_("[{}]添加用户接口异常，相关信息: {}").format(params["address"], e))
            return False
        return True

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        cluster = Cluster.objects.get(id=kwargs["cluster_id"])
        ctl_master = cluster.tendbcluster_ctl_primary_address()
        ctl_master_ip = ctl_master.split(":")[0]
        spider_port = cluster.proxyinstance_set.first().port
        admin_port = cluster.proxyinstance_set.first().admin_port

        add_spiders = kwargs["add_spiders"]
        add_spider_role = kwargs["add_spider_role"]
        user = kwargs["user"]
        passwd = kwargs["passwd"]
        ctl_pass = kwargs.get("ctl_pass") or ""

        self.log_info(
            f"[{cluster.immute_domain}] ctl_primary={ctl_master}, "
            f"spider_port={spider_port}, admin_port={admin_port}, "
            f"add_spider_role={add_spider_role}, add_spiders={add_spiders}"
        )

        # 1) When the role is spider_master, ctl_pass is required: prefer
        #    the value passed in by the upstream flow; if not provided,
        #    fall back to reading from current ctl-primary so behavior
        #    is identical to the legacy AddSpiderRoutingService.
        if add_spider_role == TenDBClusterSpiderRole.SPIDER_MASTER.value and not ctl_pass:
            ctl_pass = self._read_ctl_pass(ctl_master=ctl_master, bk_cloud_id=cluster.bk_cloud_id)
            if not ctl_pass:
                self.log_error(_("无法获取中控内置账号密码 ctl_pass"))
                return False

        # 2) For each to-be-joined spider node:
        #    - drop user (warning-only)
        #    - grant on spider business port (role=SPIDER)
        #    - grant on tdbctl admin port (role=TDBCTL) only when
        #      add_spider_role == spider_master
        for spider in add_spiders:
            spider_ip = spider["ip"]

            self._drop_user(
                spider_ip=spider_ip,
                spider_port=spider_port,
                ctl_primary_host=ctl_master_ip,
                bk_cloud_id=cluster.bk_cloud_id,
            )

            content = {
                "bk_cloud_id": cluster.bk_cloud_id,
                "bk_biz_id": cluster.bk_biz_id,
                "operator": global_data["created_by"],
                "user": user,
                "psw": passwd,
                "hosts": [ctl_master_ip],
                "dbname": "%",
                "dml_ddl_priv": "",
                "global_priv": "all privileges",
                "address": f"{spider_ip}{IP_PORT_DIVIDER}{spider_port}",
                "role": PrivRole.SPIDER.value,
            }
            if not self.__add_priv(params=content):
                return False

            if add_spider_role == TenDBClusterSpiderRole.SPIDER_MASTER.value:
                # The same-host tdbctl admin port also needs the internal
                # account, but with the tdbctl-shared password.
                content_ctl = dict(content)
                content_ctl["address"] = f"{spider_ip}{IP_PORT_DIVIDER}{admin_port}"
                content_ctl["role"] = PrivRole.TDBCTL.value
                content_ctl["psw"] = ctl_pass
                if not self.__add_priv(params=content_ctl):
                    return False

        return True


class AddSpiderSystemUserComponent(Component):
    name = __name__
    code = "add_spider_system_user"
    bound_service = AddSpiderSystemUserService
