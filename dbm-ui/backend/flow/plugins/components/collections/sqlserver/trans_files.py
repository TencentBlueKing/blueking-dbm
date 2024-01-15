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

from backend import env
from backend.components import JobApi
from backend.flow.consts import DEFAULT_SQLSERVER_PATH, MediumFileTypeEnum
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService

logger = logging.getLogger("flow")


class TransFileInWindowsService(BkJobService):
    """
    下载介质文件包到目标机器(window系统)
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行传输文件的原子任务。目前文件传输支持两个模式：1：第三方cos原文件传输 2：服务器之间文件传输
        kwargs.get('file_type') 参数用来控传输模式，如果等于1，则采用服务之间的文件传输。否则都作为第三方cos原文件传输
        """
        kwargs = data.get_one_of_inputs("kwargs")
        root_id = kwargs["root_id"]
        node_id = kwargs["node_id"]
        node_name = kwargs["node_name"]
        target_hosts = kwargs["target_hosts"]

        if not target_hosts:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员{}").format(target_hosts))
            return False

        if kwargs.get("file_type") == MediumFileTypeEnum.Server.value:
            # 服务器之间文件传输模式
            if not kwargs["source_hosts"]:
                self.log_error(
                    _("选择服务器之间文件传输模式，应当源文件的机器ip列表不能为空，请联系系统管理员: source_hosts:{}").format(kwargs["source_hosts"])
                )
                return False
            if not kwargs["file_target_path"]:
                self.log_error(
                    _("选择服务器之间文件传输模式，目标路径不能为空，请联系系统管理员: file_target_path:{}").format(kwargs["file_target_path"])
                )
                return False

            file_source = {
                "file_list": kwargs["file_list"],
                "account": {"alias": "system"},
                "file_type": MediumFileTypeEnum.Server.value,
                "server": {"ip_list": kwargs["source_hosts"]},
            }
            file_target_path = kwargs["file_target_path"]

        else:
            # 第三方cos原文件传输模式
            file_source = {
                "file_list": kwargs["file_list"],
                "file_type": MediumFileTypeEnum.Repo.value,
                "file_source_code": env.APP_CODE,
            }
            file_target_path = DEFAULT_SQLSERVER_PATH

        payload = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "file_target_path": file_target_path,
            "transfer_mode": 2,
            "file_source_list": [file_source],
            "account_alias": "system",
            "target_server": {"ip_list": target_hosts},
        }

        self.log_debug(_("[{}] 下发介质包参数：{}").format(node_name, payload))
        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=target_hosts)

        # 请求传输
        resp = JobApi.fast_transfer_file(payload, raw=True)

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs.exec_ips = target_hosts
        return True


class TransFileInWindowsComponent(Component):
    name = __name__
    code = "trans_file_in_window"
    bound_service = TransFileInWindowsService
