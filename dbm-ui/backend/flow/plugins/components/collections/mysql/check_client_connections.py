"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend import env
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.check_client_connections import check_client_connection


class CheckClientConnService(BaseService):
    """
    定义检测实例是否存储用户连接的活动节点（系统账号和内置账号会过滤）
    本节点只支持mysql/spider实例，不支持中控实例的检测
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        results = check_client_connection(
            bk_cloud_id=kwargs["bk_cloud_id"],
            instances=kwargs["check_instances"],
            is_filter_sleep=kwargs.get("is_filter_sleep", False),
            is_proxy=kwargs.get("is_proxy", False),
        )
        process_infos = []
        for res in results:
            # 检查返回的每个实例的结果
            if res["error_msg"]:
                self.log_error(f"select processlist failed: {res['error_msg']}")
                return False

            if res["cmd_results"][0]["table_data"]:
                self.log_error(
                    f"[{res['address']}] There are also {len(res['cmd_results'][0]['table_data'])} not-system threads"
                )
                temp = {"check_address": res["address"]}
                for i in res["cmd_results"][0]["table_data"]:
                    process_infos.append({**temp, **i})
            else:
                self.log_info(f"This node [{res['address']}]  passed the checkpoint [check-client-conn]!")

        if len(process_infos) > 0:
            # 结果录入缓存，目的打印到注册表
            self.set_flow_output(
                global_data["job_root_id"],
                key="check_result",
                value=process_infos,
                is_sensitive=False,
            )
            # 输出下载打印
            self.log_error(
                _("检测结果详情请下载excel:<a href='{}/apis/taskflow/excel_download/?root_id={}&key={}'>excel 下载</a>").format(
                    env.BK_SAAS_HOST, global_data["job_root_id"], "check_result"
                )
            )
            return False

        return True


class CheckClientConnComponent(Component):
    name = __name__
    code = "check_client_connections"
    bound_service = CheckClientConnService
