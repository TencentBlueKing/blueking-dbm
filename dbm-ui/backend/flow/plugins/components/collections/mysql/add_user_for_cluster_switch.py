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

from pipeline.component_framework.component import Component

from backend.components.mysql_priv_manager.client import DBPrivManagerApi
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class AddSwitchUserService(BaseService):
    """
    为mysql集群进行切换的流程定义添加mysql 临时用户的活动节点
    """

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        DBPrivManagerApi.add_priv_without_account_rule(
            params={
                "bk_cloud_id": kwargs["bk_cloud_id"],
                "bk_biz_id": global_data["bk_biz_id"],
                "operator": global_data["created_by"],
                "user": kwargs["user"],
                "psw": kwargs["psw"],
                "hosts": kwargs["hosts"],
                "dbname": "%",
                "dml_ddl_priv": "",
                "global_priv": "all privileges",
                "address": kwargs["address"],
            }
        )
        return True


class AddSwitchUserComponent(Component):
    name = __name__
    code = "add_switch_user"
    bound_service = AddSwitchUserService
