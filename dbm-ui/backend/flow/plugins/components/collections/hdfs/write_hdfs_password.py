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
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.components.mysql_priv_manager.client import DBPrivManagerApi
from backend.flow.consts import NameSpaceEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.utils.string import base64_encode

logger = logging.getLogger("flow")


class WriteHdfsPasswordService(BaseService):
    """
    部署集群后 回写集群配置到dbconfig，回写密码到密码服务
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")

        # Writing to password service
        self.log_info("Writing password to service")
        query_params = {
            "instances": [
                {
                    "ip": global_data["domain"],
                    "port": 0,
                    "bk_cloud_id": global_data["bk_cloud_id"],
                }
            ],
            "password": base64_encode(global_data["password"]),
            # 默认用户名
            "username": "root",
            "component": NameSpaceEnum.Hdfs,
            "operator": "admin",
        }
        DBPrivManagerApi.modify_password(params=query_params)

        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="command result", key="result", type="str")]


class WriteHdfsPasswordComponent(Component):
    name = __name__
    code = "write_hdfs_password"
    bound_service = WriteHdfsPasswordService
