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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.components.mysql_priv_manager.client import MySQLPrivManagerApi
from backend.db_services.mysql.permission.clone.handlers import CloneHandler
from backend.db_services.mysql.permission.constants import CloneType
from backend.exceptions import ApiResultError
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class CloneUserService(BaseService):
    """
    slave 克隆账号
    """

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        clone_data_list = kwargs["clone_data"]

        address__machine_map = CloneHandler(
            bk_biz_id=global_data["bk_biz_id"], operator=global_data["created_by"], clone_type=CloneType.INSTANCE
        ).get_address__machine_map(clone_data_list)
        try:

            for clone_data in clone_data_list:
                params = {"bk_biz_id": global_data["bk_biz_id"], "operator": global_data["created_by"]}
                params.update(
                    {
                        "source": {
                            "address": clone_data["source"],
                            "machine_type": address__machine_map[clone_data["source"]].machine_type,
                        },
                        "target": {
                            "address": clone_data["target"],
                            "machine_type": address__machine_map[clone_data["target"]].machine_type,
                        },
                        "bk_cloud_id": clone_data["bk_cloud_id"],
                    }
                )
                MySQLPrivManagerApi.clone_instance(params=params)
            return True
        except Exception as e:  # pylint: disable=broad-except
            if isinstance(e, ApiResultError):
                error_message = _("「权限克隆返回结果异常」{}").format(e.message)
            else:
                error_message = _("「权限克隆调用异常」{}").format(e)
            self.log_info(_("执行克隆失败!"))
            self.log_error(f"[{kwargs['node_name']}] failed: {error_message}")
            return False

    def inputs_format(self) -> List:
        return [Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True)]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="clone result", key="ext_result", type="bool")]


class CloneUserComponent(Component):
    name = __name__
    # 这里code用clone_user_rules，避免与MySQL权限克隆的冲突
    # TODO: 这CloneRules与CloneUserService两部分代码比较相似，是否可以考虑合并？
    code = "clone_user_rules"
    bound_service = CloneUserService
