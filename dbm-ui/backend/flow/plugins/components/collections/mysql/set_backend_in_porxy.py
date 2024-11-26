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

from backend.components import DRSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.mysql_commom_query import check_backend_in_proxy

logger = logging.getLogger("flow")


class SetBackendInProxyService(BaseService):
    """
    在新proxy设置backend后端信息，设置之前需要保证proxy的backend是1.1.1.1:3306
    如果不是则证明不是最新的，则作为异常退出
    """

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        if not check_backend_in_proxy(proxys=kwargs["proxys"], bk_cloud_id=int(kwargs["bk_cloud_id"])):
            # 检测不通过，异常
            return False

        # 刷新backend
        res = DRSApi.proxyrpc(
            {
                "addresses": kwargs["proxys"],
                "cmds": [f"refresh_backends('{kwargs['backend_host']}:{kwargs['backend_port']}',1)"],
                "force": False,
                "bk_cloud_id": int(kwargs["bk_cloud_id"]),
            }
        )
        is_error = False
        for i in res:
            if i["error_msg"]:
                self.log_error(f"the proxy [{kwargs['proxys']}] set backend failed:{i['error_msg']}")
                is_error = True

        if is_error:
            return False

        self.log_info(f"the proxy [{kwargs['proxys']}] set backend successfully")
        return True


class SetBackendInProxyComponent(Component):
    name = __name__
    code = "set_backend_in_proxy"
    bound_service = SetBackendInProxyService
