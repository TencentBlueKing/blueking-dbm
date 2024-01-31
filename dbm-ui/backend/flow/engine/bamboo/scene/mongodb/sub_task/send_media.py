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

from backend.flow.plugins.components.collections.mongodb.send_media import ExecSendMediaOperationComponent


# BackupSubTask 处理某个Cluster的备份任务.
class SendMedia:
    """
    SendMedia 将文件下发到指定机器的指定目录
    文件： file_list
    机器： bk_host_list
    目录： file_target_path
    exec_ips : 也是bk_host_list，但是只包含ip
    """

    def __init__(self):
        pass

    @classmethod
    def make_kwargs(cls, file_list, bk_host_list, file_target_path: str) -> dict:
        return {
            "file_list": file_list,
            "ip_list": bk_host_list,
            "file_target_path": file_target_path,
            "exec_ips": [item["ip"] for item in bk_host_list],
        }

    @classmethod
    def act(cls, act_name, file_list, bk_host_list, file_target_path: str) -> dict:
        """ return act args dict """
        kwargs = cls.make_kwargs(file_list, bk_host_list, file_target_path)
        return {
            "act_name": act_name,
            "act_component_code": ExecSendMediaOperationComponent.code,
            "kwargs": kwargs,
        }
