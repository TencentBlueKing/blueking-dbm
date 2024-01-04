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


# BackupSubTask 处理某个Cluster的备份任务.
class SendMediaSubTask:
    """
    payload: 整体的ticket_data
    sub_payload: 这个子任务的ticket_data
    rs:
    backup_dir:
    """

    def __init__(self):
        pass

    @classmethod
    def make_act_kwargs(cls, file_list, bk_host_list, file_target_path: str) -> dict:
        return {
            "file_list": file_list,
            "ip_list": bk_host_list,
            "exec_ips": [item["ip"] for item in bk_host_list],
            "file_target_path": file_target_path,
        }
