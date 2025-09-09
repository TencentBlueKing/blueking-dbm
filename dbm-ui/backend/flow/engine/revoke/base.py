"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.flow.engine.revoke.exception import RevokeFlowBaseException


def revoke_with(flow_func):
    """装饰器：用于关联流程与回退流程函数"""

    def decorator(main_func):
        # 添加校验函数信息到主函数的元数据中
        main_func.revoke_flow = flow_func
        return main_func

    return decorator


class RevokeFlowBase:
    """
    flow 退回流程的基类
    改造一些魔方方法，可以让继承的类直接函数方法化
    """

    def __new__(cls, root_id: str, ticket_data: dict):
        """
        @param root_id:
        @param ticket_data: 单据参数结构
        """
        # 基础判断，判断参数传入的合法性
        if not isinstance(ticket_data, dict):
            raise RevokeFlowBaseException("ticket_data is not dict, check")
        if not isinstance(root_id, str):
            raise RevokeFlowBaseException("root_id is not str, check")
        # 执行callable方法
        instance = super().__new__(cls)
        instance.data = ticket_data
        instance.root_id = root_id
        return instance()  # 返回 __call__ 的结果

    def __call__(self):
        """
        初始callable方法，不同validator定义重写__call__逻辑
        """
        return None
