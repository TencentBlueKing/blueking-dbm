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

from backend.components import DBPrivManagerApi
from backend.exceptions import ApiResultError
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class RandomizeAdminPasswordService(BaseService):
    """
    触发随机化密码的活动节点
    """

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        clusters = [
            {
                "bk_cloud_id": kwargs["bk_cloud_id"],
                "cluster_type": kwargs["cluster_type"],
                "instances": kwargs["instances"],
            }
        ]
        try:
            DBPrivManagerApi.modify_mysql_admin_password(
                params={
                    "username": "ADMIN",  # 管理用户
                    "operator": "init",
                    "clusters": clusters,
                    "security_rule_name": "password",  # 用于生成随机化密码的安全规则
                    "async": False,  # 异步执行，避免占用资源
                },
                raw=True,
            )
        except ApiResultError as e:
            # 捕获接口返回结果异常
            logger.error(_("「接口modify_mysql_admin_password返回结果异常」{}").format(e.message))
            return False

        return True


class RandomizeAdminPasswordComponent(Component):
    name = __name__
    code = "randomize_admin_password"
    bound_service = RandomizeAdminPasswordService
