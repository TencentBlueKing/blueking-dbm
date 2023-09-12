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


class RedisBackupFileTransService(BkJobService):
    """
    从Redis机器下载介质文件包到目标机器
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]

        backup_infos = trans_data.tendis_backup_info
        exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"])
        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]

        # 构造数据
        trans_data.backupinfo = backup_infos
        source_ip_list = {}
        file_list = []
        for backup_inst in backup_infos:
            file_list.extend(backup_inst["backup_files"])
            if not source_ip_list.get(backup_inst["server_ip"]):
                source_ip_list[backup_inst["server_ip"]] = True
        self.log_info("get backup files {}:{}".format(source_ip_list.keys(), file_list))

        # 服务器之间文件传输模式
        file_source = {
            "file_list": file_list,
            "account": {"alias": "root"},
            "file_type": MediumFileTypeEnum.Server.value,
            "server": {"ip_list": [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in source_ip_list.keys()]},
        }

        # 拼接fast_trans_file 接口请求参数
        payload = copy.deepcopy(consts.BK_TRANSFER_REPO_PAYLOAD)
        payload["bk_biz_id"] = env.JOB_BLUEKING_BIZ_ID
        payload["file_source_list"].append(file_source)
        payload["target_server"]["ip_list"] = target_ip_info
        payload["file_target_path"] = "/data/dbbak"

        self.log_info(_("[{}] 下发介质包参数：{}").format(node_name, payload))
        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=exec_ips)

        # 请求传输
        resp = JobApi.fast_transfer_file(payload, raw=True)

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs["trans_data"] = trans_data
        data.outputs["backup_tasks"] = backup_infos
        return True


class RedisBackupFileTransComponent(Component):
    name = __name__
    code = "redis_backup_file_trans"
    bound_service = RedisBackupFileTransService
