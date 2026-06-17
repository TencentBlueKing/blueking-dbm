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
import logging
from abc import ABC, abstractmethod
from typing import List, Type

logger = logging.getLogger("root")


class AlarmCallback(ABC):
    """
    告警回调基类，所有组件的告警回调套餐必须继承此基类并注册。

    使用方式：
        1. 继承 AlarmCallback
        2. 实现 callback() 方法，内部根据策略名等字段自行判断是否处理
        3. 子类会自动注册到 _registry 中

    分发逻辑：
        AlarmCallback.dispatch(callback_data)
        会遍历所有注册的子类，依次调用 callback
    """

    # 注册表：存储所有已注册的回调子类
    _registry: List[Type["AlarmCallback"]] = []

    def __init_subclass__(cls, **kwargs):
        """子类定义时自动注册到 registry"""
        super().__init_subclass__(**kwargs)
        # 只注册非抽象的具体实现类
        if not getattr(cls, "__abstractmethods__", None):
            AlarmCallback._registry.append(cls)

    @classmethod
    @abstractmethod
    def callback(cls, callback_data: dict) -> None:
        """
        执行告警回调处理逻辑。
        子类必须实现此方法，内部根据策略名等字段自行判断是否需要处理。

        :param callback_data: 告警回调数据
        """
        raise NotImplementedError

    @classmethod
    def dispatch(cls, callback_data: dict) -> None:
        """
        将告警回调数据分发给所有注册的处理器。
        每个处理器的 callback 内部自行判断是否需要处理。

        :param callback_data: 告警回调数据
        """
        for handler_cls in cls._registry:
            try:
                handler_cls.callback(callback_data)
            except Exception as e:
                logger.exception(f"[alarm_callback] processor {handler_cls.__name__} callback error: {e}")
