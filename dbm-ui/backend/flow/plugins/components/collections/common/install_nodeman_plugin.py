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

from pipeline.component_framework.component import Component
from pipeline.core.flow import StaticIntervalGenerator

from backend.components.bknodeman.client import BKNodeManApi
from backend.flow.plugins.components.collections.common.base_service import BaseService


class InstallNodemanPluginService(BaseService):
    """安装节点管理插件"""

    __need_schedule__ = True
    interval = StaticIntervalGenerator(5)

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        bk_host_ids = kwargs["bk_host_ids"]
        plugin_name = kwargs["plugin_name"]
        self.log_info(f"start installing {plugin_name} plugin")
        job = BKNodeManApi.operate_plugin(
            {"job_type": "MAIN_START_PLUGIN", "plugin_params": {"name": plugin_name}, "bk_host_id": bk_host_ids}
        )
        data.outputs.job_id = job["job_id"]

    def _schedule(self, data, parent_data, callback_data=None):
        job_id = data.get_one_of_outputs("job_id")
        job_details = BKNodeManApi.job_details({"job_id": job_id})
        status = job_details["status"]
        if status in BKNodeManApi.JobStatusType.PROCESSING_STATUS:
            self.log_info("installing plugin")
            return True
        if status == BKNodeManApi.JobStatusType.SUCCESS:
            self.log_info("install plugin successfully")
            self.finish_schedule()
            return True
        else:
            self.log_error("install plugin failed")
            return False


class InstallNodemanPluginServiceComponent(Component):
    name = __name__
    code = "install_nodeman_plugin_service"
    bound_service = InstallNodemanPluginService
