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
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow import StaticIntervalGenerator
from pipeline.exceptions import PipelineError

from backend.components import CCApi
from backend.components.bknodeman.client import BKNodeManApi, BKNodeManJobStatusError
from backend.flow.plugins.components.collections.common.base_service import BaseService


class InstallNodemanPluginService(BaseService):
    """安装节点管理插件"""

    RETRY_ERROR_CODES = [502, 504]  # 重试的错误码

    __need_schedule__ = True
    interval = StaticIntervalGenerator(10)
    MAX_POLL_COUNT = 50  # 最多轮询次数，超过后任务失败

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        # bk_cloud_id + ips 组合，在这里获取bk_host_id
        if kwargs.get("ips"):
            ips = kwargs["ips"]
            bk_cloud_id = kwargs["bk_cloud_id"]
            # 获取对应的bk_host_id
            res = CCApi.list_hosts_without_biz(
                {
                    "fields": ["bk_host_id"],
                    "host_property_filter": {
                        "condition": "AND",
                        "rules": [
                            {"field": "bk_host_innerip", "operator": "in", "value": ips},
                            {"field": "bk_cloud_id", "operator": "equal", "value": bk_cloud_id},
                        ],
                    },
                },
                use_admin=True,
            )
            bk_host_ids = [host["bk_host_id"] for host in res["info"]]
        else:
            bk_host_ids = kwargs.get("bk_host_ids", [])

        # 上下文有hosts
        if isinstance(trans_data, dict) and trans_data.get("hosts"):
            host_ids = [host["bk_host_id"] for host in trans_data["hosts"] if host.get("bk_host_id")]
            bk_host_ids.extend(host_ids)

        if not bk_host_ids:
            raise PipelineError(_("不存在主机，无法安装节点管理插件"))

        plugin_name = kwargs["plugin_name"]
        self.log_info(f"start installing {plugin_name} plugin")
        job = BKNodeManApi.operate_plugin(
            {"job_type": "MAIN_INSTALL_PLUGIN", "plugin_params": {"name": plugin_name}, "bk_host_id": bk_host_ids}
        )
        data.outputs.job_id = job["job_id"]
        data.outputs.poll_count = 0  # 每次execute重置轮询计数器
        self.log_info(_("安装插件任务: {}").format(BKNodeManApi.get_job_url(data.outputs.job_id)))

    def _schedule(self, data, parent_data, callback_data=None):
        job_id = data.get_one_of_outputs("job_id")
        max_retries = 3  # 最大重试次数
        retry_count = data.get_one_of_outputs("retry_count", 0)

        # 轮询次数超限检查
        poll_count = data.get_one_of_outputs("poll_count", 0)
        poll_count += 1
        data.outputs.poll_count = poll_count
        if poll_count > self.MAX_POLL_COUNT:
            self.log_error(
                _("安装节点管理插件任务超时: 轮询次数已达上限 {} 次（间隔 {}s），job_id={}").format(
                    self.MAX_POLL_COUNT, self.interval.interval, job_id
                )
            )
            return False
        try:
            status = BKNodeManApi.get_job_status(job_id)
        except BKNodeManJobStatusError as err:
            # 遇到网关类错误码时重试
            if err.status_code not in self.RETRY_ERROR_CODES:
                self.log_error(_("获取任务详情失败: {}").format(err.message))
                return False
            retry_count += 1
            if retry_count <= max_retries:
                data.outputs.retry_count = retry_count
                self.log_info(f"retrying job {job_id}, retry count: {retry_count}")
                return True
            self.log_error(_("已经达到最大重试次数{}次").format(max_retries))
            return False

        if status in BKNodeManApi.JobStatusType.PROCESSING_STATUS:
            self.log_info(f"installing plugin, job id is {job_id}")
            return True
        if status == BKNodeManApi.JobStatusType.SUCCESS:
            self.log_info("install plugin successfully")
            self.finish_schedule()
            return True
        self.log_error(f"install plugin failed, job status is {status}")
        return False


class InstallNodemanPluginServiceComponent(Component):
    name = __name__
    code = "install_nodeman_plugin_service"
    bound_service = InstallNodemanPluginService
