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

from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import CopyAppSettingKwargs
from backend.flow.utils.sqlserver.sqlserver_db_function import copy_app_setting_data
from backend.flow.utils.sqlserver.sqlserver_host import Host

logger = logging.getLogger("flow")


class CopyAppSettingService(BaseService):
    """
    克隆实例app_setting配置数据
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        # 理论上一个集群对应一个主域名
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])

        source_instance = cluster.storageinstance_set.get(machine__ip=kwargs["source_host"]["ip"])

        # 配置数据
        if copy_app_setting_data(
            source_instance=source_instance,
            target_host=Host(**kwargs["target_host"]),
            target_port=kwargs["target_port"],
            target_role=kwargs["target_role"],
        ):
            self.log_info("exec copy-app-setting successfully")
            return True

        return False


class CopyAppSettingComponent(Component):
    name = __name__
    code = "sqlserver_copy_app_setting"
    bound_service = CopyAppSettingService
    kwargs = CopyAppSettingKwargs
