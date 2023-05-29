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
import copy
import logging
import time
from typing import List

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.redis.redis_context_dataclass as flow_context
from backend import env
from backend.components import JobApi
from backend.core import consts
from backend.flow.consts import MediumFileTypeEnum
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService

logger = logging.getLogger("flow")


class TransFileService(BkJobService):
    """
    下载介质文件包到目标机器
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行传输文件的原子任务
        """
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]

        # 拼接节点执行ip所需要的信息，ip信息统一用list处理拼接
        if kwargs["get_trans_data_ip_var"]:
            exec_ips = self.splice_exec_ips_list(
                ticket_ips=kwargs["exec_ip"], pool_ips=getattr(trans_data, kwargs["get_trans_data_ip_var"])
            )
        else:
            exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"])

        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员{}").format(exec_ips))
            return False

        self.log_info(f"job will exec in {exec_ips}")
        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]

        # 拼接fast_trans_file 接口请求参数
        payload = copy.deepcopy(consts.BK_TRANSFER_REPO_PAYLOAD)
        payload["bk_biz_id"] = env.JOB_BLUEKING_BIZ_ID
        payload["file_source_list"].append(
            {
                "file_list": kwargs["file_list"],
                "file_type": MediumFileTypeEnum.Repo.value,
                "file_source_code": env.APP_CODE,
            }
        )
        payload["target_server"]["ip_list"] = target_ip_info

        self.log_info(_("[{}] 下发介质包参数：{}").format(node_name, payload))
        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=exec_ips)

        # 请求传输
        retry_times = kwargs["cluster"].get("retry_times", 0) + 1
        for retry in range(0, retry_times):
            resp = JobApi.fast_transfer_file(payload, raw=True)
            if resp["code"] != 0:
                self.log_error(_("下发介质包失败: [{}/{}] resp:{}").format(retry + 1, retry_times, resp))
                if retry + 1 >= retry_times:
                    return False
                time.sleep(kwargs["cluster"].get("retry_sleep", 1))  # 休息下，再重试

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="exec_ips", key="exec_ips", type="list")]


class TransFileComponent(Component):
    name = __name__
    code = "redis_exec_trans_file"
    bound_service = TransFileService
