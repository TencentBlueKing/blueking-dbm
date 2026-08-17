"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import Callable, Type

from django.utils.translation import gettext as _

from backend.flow.engine.revoke.exception import RevokeFlowBaseException

# 挂载到被装饰函数上的属性名；与 RevokeFlowBase.revoke_flow 同名，
# 供 ticket 层通过 hasattr(func, "revoke_flow") 反射判定是否具备回退能力
_REVOKE_FLOW_ATTR: str = "revoke_flow"

# 挂载到被装饰函数上的"类对象"属性名；用于保留 @revoke_with 传入的具体子类身份，
# 供 CalcRecycleApplyHostParamBuilder.build_controller_info 反射写入 class_name/module 时
# 直接读取类对象，避免依赖 revoke_flow.__qualname__ 推断（后者会在子类未自定义
# revoke_flow 方法时固化为"方法真实定义所在的父类名"，导致反射错构父类实例）
_REVOKE_FLOW_CLASS_ATTR: str = "revoke_flow_class"


def revoke_with(flow_func: Type["RevokeFlowBase"]) -> Callable:
    """装饰器：用于关联主流程与其对应的回退流程类。

    功能说明 / 怎么做：
        - 在被装饰函数对象上挂载 ``revoke_flow`` 属性，值为传入的回退流程类的 ``revoke_flow`` 方法；
        - **额外挂载 ``revoke_flow_class`` 属性**，值为传入的回退流程类对象本身；该属性是
          :class:`CalcRecycleApplyHostParamBuilder.build_controller_info` 反射写入
          ``controller_info.class_name`` / ``module`` 的权威真源，避免历史上依赖
          ``__qualname__.split(".")[0]`` 推断在"子类未自定义 revoke_flow"场景下返回父类名。
        - 单据在 TERMINATED 时，ticket 层通过 ``hasattr(func, "revoke_flow")`` 反射判定是否
          需要发起 RECYCLE_APPLY_HOST 子单据；recycle 层再通过 ``revoke_flow_class`` 拿到实际
          执行回退的类并构造实例。

    :param flow_func: 回退流程类，必须是 ``RevokeFlowBase`` 的子类（不是实例，不是普通函数）
    :return: 真正的装饰器函数，返回原函数本身（不 wrap，仅打标记）

    边界 / 异常：
        - ``flow_func`` 非 ``RevokeFlowBase`` 子类 -> 抛 ``RevokeFlowBaseException``，
          让误用在 import 期即暴露，而不是拖到单据终止时才失败；
        - 被装饰函数已存在 ``revoke_flow`` 或 ``revoke_flow_class`` 属性（重复装饰 / 命名冲突）
          -> 抛 ``RevokeFlowBaseException``，避免静默覆盖。
    """
    # 延迟到运行时判定，避免与 RevokeFlowBase 的循环引用
    if not (isinstance(flow_func, type) and issubclass(flow_func, RevokeFlowBase)):
        raise RevokeFlowBaseException(_("revoke_with 需传入 RevokeFlowBase 子类，实际得到: {}").format(repr(flow_func)))

    def decorator(main_func: Callable) -> Callable:
        # 防止重复装饰或与已有属性静默冲突
        if hasattr(main_func, _REVOKE_FLOW_ATTR):
            raise RevokeFlowBaseException(
                _("{} 已存在 {} 属性，禁止重复装饰或覆盖").format(getattr(main_func, "__qualname__", main_func), _REVOKE_FLOW_ATTR)
            )
        if hasattr(main_func, _REVOKE_FLOW_CLASS_ATTR):
            raise RevokeFlowBaseException(
                _("{} 已存在 {} 属性，禁止重复装饰或覆盖").format(
                    getattr(main_func, "__qualname__", main_func), _REVOKE_FLOW_CLASS_ATTR
                )
            )
        # 添加校验函数信息到主函数的元数据中
        main_func.revoke_flow = flow_func.revoke_flow
        # 显式保留"子类身份"：CalcRecycleApplyHostParamBuilder.build_controller_info
        # 据此写入 controller_info.class_name / module，避免 __qualname__ 推断失真
        main_func.revoke_flow_class = flow_func
        return main_func

    return decorator


class RevokeFlowBase:
    """
    flow 退回流程的基类
    改造一些魔方方法，可以让继承的类直接函数方法化
    """

    def __init__(self, root_id: str, ticket_data: dict):
        """
        @param root_id:
        @param ticket_data: 单据参数结构
        """
        # 基础判断，判断参数传入的合法性
        if not isinstance(ticket_data, dict):
            raise RevokeFlowBaseException("ticket_data is not dict, check")
        if not isinstance(root_id, str):
            raise RevokeFlowBaseException("root_id is not str, check")
        # 初始化
        self.data = ticket_data
        self.root_id = root_id

    def revoke_flow(self):
        """
        初始callable方法，不同revoke定义重写revoke逻辑
        """
        raise NotImplementedError
