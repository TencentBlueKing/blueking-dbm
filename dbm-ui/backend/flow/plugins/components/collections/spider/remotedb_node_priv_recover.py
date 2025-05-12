# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class RemoteNodePrivRecoverService(BaseService):
    """
    定点回档结束后对remotedb节点进行权限恢复
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_info(_("传入参数:{}").format(kwargs))
        spider_instance_list = kwargs["spider_instance_list"]
        bk_cloud_id = kwargs["bk_cloud_id"]
        # 查询出所有spider的权限
        results = DRSApi.rpc(
            {
                "addresses": spider_instance_list,
                "cmds": ["select * from mysql.servers"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        remote_instances = {}
        # 在所有spider/spider_slave获取权限
        self.log_info(_("获取spider权限"))
        for res in results:
            if res["error_msg"]:
                self.log_info("execute sql error {}".format(res["error_msg"]))
                return False
            else:
                if len(res["cmd_results"][0]["table_data"]) == 0:
                    self.log_info("null privileges {}".format(res["address"]))
                else:
                    for one_priv in res["cmd_results"][0]["table_data"]:
                        instance_ip, instance_port = str(res["address"]).split(IP_PORT_DIVIDER)
                        grant_sql = (
                            "GRANT ALL PRIVILEGES ON *.* TO '{}'@'{}' " "IDENTIFIED BY '{}' WITH GRANT OPTION"
                        ).format(one_priv["Username"], instance_ip, one_priv["Password"])
                        remote_instance = "{}{}{}".format(one_priv["Host"], IP_PORT_DIVIDER, one_priv["Port"])
                        if remote_instance in remote_instances.keys():
                            remote_instances[remote_instance].append(grant_sql)
                        else:
                            remote_instances[remote_instance] = [grant_sql]
        #  在每个remotedb 执行上授权
        self.log_info(_("remotedb执行授权"))
        for instances, grant_sqls in remote_instances.items():
            grants_results = DRSApi.rpc(
                {
                    "addresses": [instances],
                    "cmds": grant_sqls,
                    "force": False,
                    "bk_cloud_id": bk_cloud_id,
                }
            )
            for res in grants_results:
                if res["error_msg"]:
                    self.log_info("execute sql error {}".format(res["error_msg"]))
                    return False
        return True


class RemoteNodePrivRecoverComponent(Component):
    name = __name__
    code = "remote_node_privilege_recover"
    bound_service = RemoteNodePrivRecoverService
