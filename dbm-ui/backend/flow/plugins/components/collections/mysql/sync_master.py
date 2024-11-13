"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import DBConfigApi, DBPrivManagerApi, DRSApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.constants import IP_PORT_DIVIDER
from backend.flow.consts import ConfigTypeEnum, NameSpaceEnum, PrivRole
from backend.flow.engine.bamboo.scene.mysql.common.exceptions import NormalTenDBFlowException
from backend.flow.plugins.components.collections.common.base_service import BaseService


class SyncMasterService(BaseService):
    def _get_repl_user(self):
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": "0",
                "level_name": LevelName.PLAT,
                "level_value": "0",
                "conf_file": "mysql#user",
                "conf_type": ConfigTypeEnum.InitUser,
                "namespace": NameSpaceEnum.TenDB.value,
                "format": FormatType.MAP,
            }
        )["content"]
        self.log_info("get repl_user successfully")
        return data["repl_user"], data["repl_pwd"]

    def _add_repl_user(
        self,
        address_list: list,
        bk_cloud_id: int,
        bk_biz_id: int,
        priv_role: PrivRole,
        priv_hosts: list,
        repl_user: str,
        repl_pwd: str,
    ):
        """
        @param address_list: 授权实例列表
        @param bk_cloud_id: 云区域ID
        @param bk_biz_id: 业务ID
        @param priv_role: 授权角色
        @param priv_hosts: 授权host
        @param repl_user: 同步账号
        @param repl_pwd: 账号pwd
        """
        # 远程授权
        for address in address_list:
            DBPrivManagerApi.add_priv_without_account_rule(
                {
                    "bk_cloud_id": bk_cloud_id,
                    "bk_biz_id": bk_biz_id,
                    "operator": "",
                    "user": repl_user,
                    "psw": repl_pwd,
                    "hosts": priv_hosts,
                    "dbname": "%",
                    "dml_ddl_priv": "",
                    "global_priv": "REPLICATION SLAVE, REPLICATION CLIENT",
                    "address": address,
                    "role": priv_role,
                }
            )
            self.log_info(_("在[{}]创建添加同步账号成功, priv_hosts:{}").format(address, priv_hosts))
        return True

    def get_bin_position(self, address: str, bk_cloud_id: int) -> (str, str):
        """
        获取位点信息
        """
        res = DRSApi.rpc(
            {
                "addresses": [address],
                "cmds": ["show master status;"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            raise NormalTenDBFlowException(message=_(f"exec show master status failed: {res[0]['error_msg']}"))
        self.log_info("get bin position successfully")
        return res[0]["cmd_results"][1]["table_data"][0]["File"], res[0]["cmd_results"][1]["table_data"][0]["Position"]

    def _execute(self, data, parent_data) -> bool:
        """
        用rds来处理主从同步的建立过程，处理步骤如下：
        1：先在master创建同步账号，保证待同步的slave有权限同步，并返回当前master位点信息
        2：根据不同场景，拼接建立同步sql，通过drs执行
        """
        kwargs = data.get_one_of_inputs("kwargs")
        repl_user, repl_pwd = self._get_repl_user()
        master_address = f"{kwargs['master']['host']}{IP_PORT_DIVIDER}{kwargs['master']['port']}"
        if kwargs["is_add_any"]:
            # 是否用%全匹配.全实例处理开权限，一步到位
            priv_hosts = ["%"]
            priv_instance_list = [f"{s['host']}{IP_PORT_DIVIDER}{s['port']}" for s in kwargs["slaves"]]
            if kwargs["is_master_add_priv"]:
                priv_instance_list += [master_address]

        else:
            # 不是全匹配，则每次只对master实例开权限
            priv_instance_list = [master_address]
            priv_hosts = [s["host"] for s in kwargs["slaves"]]

        self._add_repl_user(
            address_list=priv_instance_list,
            bk_biz_id=kwargs["bk_biz_id"],
            bk_cloud_id=kwargs["bk_cloud_id"],
            priv_role=kwargs["priv_role"],
            priv_hosts=priv_hosts,
            repl_user=repl_user,
            repl_pwd=repl_pwd,
        )
        if not kwargs["is_gtid"]:
            # 普通位点模式
            file, position = self.get_bin_position(address=master_address, bk_cloud_id=kwargs["bk_cloud_id"])
            repl_sql = (
                f"CHANGE MASTER TO "
                f"MASTER_HOST ='{kwargs['master']['host']}',"
                f"MASTER_PORT={kwargs['master']['port']},"
                f"MASTER_USER ='{repl_user}',"
                f"MASTER_PASSWORD='{repl_pwd}',"
                f"MASTER_LOG_FILE = '{file}',"
                f"MASTER_LOG_POS = {position};"
            )
        else:
            # GTID模式
            repl_sql = (
                f"CHANGE MASTER TO "
                f"MASTER_HOST ='{kwargs['master']['host']}',"
                f"MASTER_PORT={kwargs['master']['port']},"
                f"MASTER_USER ='{repl_user}',"
                f"MASTER_PASSWORD='{repl_pwd}',"
                "MASTER_AUTO_POSITION = 1;"
            )

        #  建立同步
        for secondary in kwargs["slaves"]:
            res = DRSApi.rpc(
                {
                    "addresses": [f"{secondary['host']}{IP_PORT_DIVIDER}{secondary['port']}"],
                    "cmds": [repl_sql, "start slave;"],
                    "force": False,
                    "bk_cloud_id": kwargs["bk_cloud_id"],
                }
            )
            if res[0]["error_msg"]:
                raise NormalTenDBFlowException(message=_(f"exec change master failed: {res[0]['error_msg']}"))
        return True


class SyncMasterComponent(Component):
    name = __name__
    code = "mysql_sync_master"
    bound_service = SyncMasterService
