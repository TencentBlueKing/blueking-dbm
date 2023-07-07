"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import ugettext_lazy as _
from pipeline.component_framework.component import Component

from backend.flow.engine.bamboo.scene.spider.common.exceptions import NormalSpiderFlowException
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.check_client_connections import check_client_connection


class CheckClientConnService(BaseService):
    """
    定义检测实例是否存储用户连接的活动节点（系统账号和内置账号会过滤）
    本节点只支持mysql/spider实例，不支持中控实例的检测
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")

        results = check_client_connection(kwargs["bk_cloud_id"], kwargs["check_instances"])

        for res in results:
            # 检查返回的每个实例的结果

            if res["error_msg"]:
                self.log_error(f"select processlist failed: {res[0]['error_msg']}")
                return False

            if res["cmd_results"][0]["table_data"]:
                self.log_error(f"There are also {len(res['cmd_results'][0]['table_data'])} not-system threads")
                return False

            else:
                self.log_info(f"This node [{res['address']}]  passed the checkpoint [check-client-conn]!")

        return True


class CheckClientConnComponent(Component):
    name = __name__
    code = "check_client_connections"
    bound_service = CheckClientConnService
