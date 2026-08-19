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

import abc
import logging
import time
from typing import Any, Callable, List, Union

from iam import Resource
from requests.exceptions import ConnectionError as RequestsConnectionError

from backend.iam_app.dataclass.actions import ActionMeta

logger = logging.getLogger("root")


class IAMBackend(metaclass=abc.ABCMeta):
    """
    鉴权后端。

    Permission 作为门面只保留与IAM版本无关的逻辑（超管豁免、无权限申请数据、异常抛出），
    协议相关的部分（payload组装、请求发送、返回解析）由各版本的后端实现。
    """

    # IAM 网关偶发 RemoteDisconnected，做快速重试
    MAX_RETRIES = 3
    RETRY_INTERVAL_SECONDS = 0.2

    def call_with_retry(self, func: Callable, *args, default: Any = None, **kwargs) -> Any:
        """
        统一处理IAM请求的重试与异常。
        鉴权异常时不抛出而是返回default由调用方兜底，与V3的既有行为保持一致
        """
        for retry in range(self.MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except RequestsConnectionError as e:
                if "RemoteDisconnected" in str(e) and retry < self.MAX_RETRIES - 1:
                    logger.warning("[iam_backend] RemoteDisconnected, retry %s/%s: %s", retry + 1, self.MAX_RETRIES, e)
                    time.sleep(self.RETRY_INTERVAL_SECONDS)
                    continue
                logger.exception("[iam_backend] connection error: %s", e)
                return default
            except Exception as e:  # pylint: disable=broad-except
                logger.exception("[iam_backend] request failed: %s", e)
                return default
        return default

    @abc.abstractmethod
    def is_allowed(self, username: str, action: ActionMeta, resources: List[Resource]) -> bool:
        """单个动作对单个资源鉴权"""
        raise NotImplementedError

    @abc.abstractmethod
    def policy_query(self, username: str, action: ActionMeta, obj_list: List[Union[int, str]]) -> List:
        """从待判定的对象中筛出有权限的部分，返回原始对象"""
        raise NotImplementedError

    @abc.abstractmethod
    def grant_creator_actions(self, resource: Resource, creator: str) -> Any:
        """资源新建后给创建者授权"""
        raise NotImplementedError


class DummyIAMBackend(IAMBackend):
    """BK_IAM_SKIP 开启时使用，所有鉴权直接放行"""

    def is_allowed(self, username: str, action: ActionMeta, resources: List[Resource]) -> bool:
        return True

    def policy_query(self, username: str, action: ActionMeta, obj_list: List[Union[int, str]]) -> List:
        return list(obj_list)

    def grant_creator_actions(self, resource: Resource, creator: str) -> Any:
        return None
