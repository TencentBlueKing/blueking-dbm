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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend import env
from backend.components import JobApi
from backend.core import consts
from backend.flow.consts import DBA_ROOT_USER, MediumFileTypeEnum
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService

logger = logging.getLogger("flow")


class TransFileService(BkJobService):
    """
    下载介质文件包到目标机器
    """

    def __get_exec_ips(self, kwargs, trans_data) -> list:
        """
        获取需要执行的ip list
        """
        # 拼接节点执行ip所需要的信息，ip信息统一用list处理拼接
        if kwargs.get("get_trans_data_ip_var"):
            exec_ips = self.splice_exec_ips_list(pool_ips=getattr(trans_data, kwargs["get_trans_data_ip_var"]))
        else:
            exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"])

        return exec_ips

    def _execute(self, data, parent_data) -> bool:
        """
        执行传输文件的原子任务。目前文件传输支持两个模式：1：第三方cos原文件传输 2：服务器之间文件传输
        kwargs.get('file_type') 参数用来控传输模式，如果等于1，则采用服务之间的文件传输。否则都作为第三方cos原文件传输
        """
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]

        # 拼接节点执行ip所需要的信息，ip信息统一用list处理拼接
        exec_ips = self.__get_exec_ips(kwargs=kwargs, trans_data=trans_data)

        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员{}").format(exec_ips))
            return False

        if kwargs.get("file_type") == MediumFileTypeEnum.Server.value:
            # 服务器之间文件传输模式
            if not kwargs["source_ip_list"]:
                self.log_error(_("选择服务器之间文件传输模式，应当源文件的机器ip列表不能为空，请联系系统管理员{}").format(kwargs["source_ip_list"]))
                return False

            file_source = {
                "file_list": kwargs["file_list"],
                "account": {"alias": "root"},
                "file_type": MediumFileTypeEnum.Server.value,
                "server": {
                    "ip_list": [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in kwargs["source_ip_list"]]
                },
            }

        else:
            # 第三方cos原文件传输模式
            file_source = {
                "file_list": kwargs["file_list"],
                "file_type": MediumFileTypeEnum.Repo.value,
                "file_source_code": env.APP_CODE,
            }

        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]

        # 拼接fast_trans_file 接口请求参数
        payload = copy.deepcopy(consts.BK_TRANSFER_REPO_PAYLOAD)
        payload["bk_biz_id"] = env.JOB_BLUEKING_BIZ_ID
        payload["file_source_list"].append(file_source)
        payload["target_server"]["ip_list"] = target_ip_info

        # 选择什么用户来传输文件
        if kwargs.get("run_as_system_user"):
            payload["account_alias"] = kwargs["run_as_system_user"]
        else:
            # 现在默认使用root账号来执行
            payload["account_alias"] = DBA_ROOT_USER

        if kwargs.get("file_target_path"):
            kwargs["file_target_path"] = str(kwargs["file_target_path"]).strip()
            if kwargs["file_target_path"] is not None and kwargs["file_target_path"] != "":
                payload["file_target_path"] = kwargs["file_target_path"]

        self.log_info(_("[{}] 下发介质包参数：{}").format(node_name, payload))
        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=exec_ips)

        # 请求传输
        resp = JobApi.fast_transfer_file(payload, raw=True)

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        return True


class TransFileComponent(Component):
    name = __name__
    code = "mysql_exec_trans_file"
    bound_service = TransFileService
