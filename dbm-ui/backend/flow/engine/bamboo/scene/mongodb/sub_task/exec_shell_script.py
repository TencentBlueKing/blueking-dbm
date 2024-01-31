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
from backend.flow.plugins.components.collections.mongodb.fast_exec_script import MongoFastExecScriptComponent
from backend.flow.utils.mongodb.mongodb_dataclass import CommonContext


# ExecShellScript 执行shell脚本
class ExecShellScript:
    """
    ExecShellScript 执行脚本内容. 没有Template
    """

    def __init__(self):
        pass

    @classmethod
    def make_kwargs(cls, bk_host_list, exec_account, script_content: str) -> dict:
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": 0,
            "script_content": script_content,
            "bk_host_list": bk_host_list,
            "exec_account": exec_account,
            "db_act_template": {
                "payload": {
                    # nothing to render
                }
            },
        }

    @classmethod
    def act(cls, act_name, file_list, bk_host_list, exec_account, script_content: str) -> dict:
        """ return act args dict """
        kwargs = cls.make_kwargs(bk_host_list, exec_account, script_content)
        return {
            "act_name": act_name,
            "act_component_code": MongoFastExecScriptComponent.code,
            "kwargs": kwargs,
        }
