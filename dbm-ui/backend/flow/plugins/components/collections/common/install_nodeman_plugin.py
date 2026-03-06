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

from backend import env
from backend.components import CCApi
from backend.components.bknodeman.client import BKNodeManApi
from backend.flow.plugins.components.collections.common.base_service import BaseService


class InstallNodemanPluginService(BaseService):
    """安装节点管理插件"""

    RETRY_ERROR_CODES = [502, 504]  # 重试的错误码
    HTTP_STATUS_OK = 200  # HTTP请求成功的状态码
    MAX_SCHEDULE_COUNT = 50  # schedule 最大轮询次数，超过则判定为超时失败

    __need_schedule__ = True
    interval = StaticIntervalGenerator(10)

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
        # 每次 execute 重置 schedule 计数，确保重试时超时计数归零
        data.outputs.schedule_count = 0
        self.log_info(_("安装插件任务: {}/#/task-list/detail/{}").format(env.BK_NODEMAN_URL, data.outputs.job_id))

    def _schedule(self, data, parent_data, callback_data=None):
        job_id = data.get_one_of_outputs("job_id")
        max_retries = 3  # 最大重试次数（针对网络错误码）
        retry_count = data.get_one_of_outputs("retry_count", 0)

        # 超时保护：schedule 执行次数超过上限则判定失败
        schedule_count = data.get_one_of_outputs("schedule_count", 0)
        schedule_count += 1
        data.outputs.schedule_count = schedule_count
        if schedule_count > self.MAX_SCHEDULE_COUNT:
            self.log_error(
                _("安装节点管理插件超时：轮询次数已达 {} 次（每次间隔 10s），任务 job_id={}").format(
                    self.MAX_SCHEDULE_COUNT, job_id
                )
            )
            return False

        # 调用 API 并设置 raw=True, raise_exception=False，遇到特定错误码时重试
        raw_response = BKNodeManApi.job_details._send(params={"job_id": job_id}, headers={})
        # 检查网络状态
        if raw_response.status_code == self.HTTP_STATUS_OK:
            try:
                # 网络请求成功，解析响应内容
                response = raw_response.json()
                status = response.get("data", {}).get("status")
                if status in BKNodeManApi.JobStatusType.PROCESSING_STATUS:
                    self.log_info(
                        f"installing plugin, job id is {job_id}, schedule_count={schedule_count}/{self.MAX_SCHEDULE_COUNT}"
                    )
                    return True
                if status == BKNodeManApi.JobStatusType.SUCCESS:
                    self.log_info("install plugin successfully")
                    self.finish_schedule()
                    return True
                else:
                    self.log_error("install plugin failed")
                    return False
            except (KeyError, TypeError, ValueError) as e:
                self.log_error(_("解析响应出错: {}，响应内容: {}").format(str(e), raw_response.text))
                return False
        elif raw_response.status_code in self.RETRY_ERROR_CODES:
            retry_count += 1
            if retry_count <= max_retries:
                data.outputs.retry_count = retry_count
                self.log_info(f"retrying job {job_id}, retry count: {retry_count}")
                return True
            else:
                self.log_error(_("已经达到最大重试次数{}次").format(max_retries))
                return False
        else:
            self.log_error(
                _("获取任务详情失败: {}").format(
                    f"code: {raw_response.status_code}, message: {raw_response.text or raw_response.reason}"
                )
            )
            return False


class InstallNodemanPluginServiceComponent(Component):
    name = __name__
    code = "install_nodeman_plugin_service"
    bound_service = InstallNodemanPluginService
