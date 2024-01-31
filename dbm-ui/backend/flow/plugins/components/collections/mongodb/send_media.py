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
from typing import List

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend import env
from backend.components import JobApi
from backend.core import consts
from backend.flow.consts import MediumFileTypeEnum
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService

logger = logging.getLogger("json")


class ExecSendMediaOperation(BkJobService):
    """
    执行下发介质包
    """

    def _execute(self, data, parent_data) -> bool:
        """
        kwargs 私有变量
        """

        # 从流程节点中获取变量
        kwargs = data.get_inputs()["kwargs"]
        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]

        # 介质下发
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
        payload["file_target_path"] = kwargs["file_target_path"]
        payload["target_server"]["ip_list"] = kwargs["ip_list"]
        self.log_info(_("[{}] 下发介质包参数：{}").format(node_name, payload))
        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=kwargs["exec_ips"])

        # 请求传输
        resp = JobApi.fast_transfer_file(payload, raw=True)
        if resp["code"] != 0:
            self.log_error(_("下发介质包失败，resp:{}").format(resp))
            return False

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        return True

    # 流程节点输入参数
    def inputs_format(self) -> List:
        print("inputs_format", self.__class__.__name__, self.code)
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="exec_ips", key="exec_ips", type="list")]


class ExecSendMediaOperationComponent(Component):
    """
    ExecSendMediaOperation组件
    """

    name = __name__
    code = "send_media"
    bound_service = ExecSendMediaOperation
