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
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class RemoteDbPrivRecoverService(BaseService):
    """
    定点回档结束后对remotedb节点进行权限恢复
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_debug(_("传入参数:{}").format(kwargs))
        spider_instance_list = kwargs["spider_instance_list"]
        bk_cloud_id = kwargs["bk_cloud_id"]
        instance_version = str(kwargs["instance_version"])
        instance = kwargs["instance"]
        remote_node_user = kwargs["remote_node_user"]
        grant_sqls = []
        create_user_sqls = []
        for one_ip in spider_instance_list:
            #  区分8.0 和其他版本. 8.0 先删除账号，再执行create，再执行grant
            if instance_version.startswith("8."):
                grant_sql = [
                    ("ALTER USER '{}'@'{}' IDENTIFIED WITH mysql_native_password BY '{}'").format(
                        remote_node_user["Username"], one_ip, remote_node_user["Password"]
                    ),
                    ("GRANT ALL PRIVILEGES ON *.* TO '{}'@'{}' WITH GRANT OPTION").format(
                        remote_node_user["Username"], one_ip
                    ),
                ]
                create_user_sqls.append(
                    "create user '{}'@'{}' IDENTIFIED BY '{}'".format(
                        remote_node_user["Username"], one_ip, remote_node_user["Password"]
                    )
                )
            else:
                grant_sql = [
                    ("GRANT ALL PRIVILEGES ON *.* TO '{}'@'{}' " "IDENTIFIED BY '{}' WITH GRANT OPTION").format(
                        remote_node_user["Username"], one_ip, remote_node_user["Password"]
                    )
                ]
            grant_sqls.extend(grant_sql)

        #  在每个remotedb 执行上授权
        self.log_info(_("{}remotedb执行授权".format(instance)))
        if instance_version.startswith("8."):
            self.log_debug(create_user_sqls)
            DRSApi.rpc(
                {
                    "addresses": [instance],
                    "cmds": create_user_sqls,
                    "force": False,
                    "bk_cloud_id": bk_cloud_id,
                }
            )
        self.log_debug(grant_sqls)
        grants_results = DRSApi.rpc(
            {
                "addresses": [instance],
                "cmds": grant_sqls,
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        if grants_results[0]["error_msg"]:
            self.log_info("execute sql error {}".format(grants_results[0]["error_msg"]))
            return False
        return True


class RemoteDbPrivRecoverComponent(Component):
    name = __name__
    code = "remotedb_privilege_recover"
    bound_service = RemoteDbPrivRecoverService
