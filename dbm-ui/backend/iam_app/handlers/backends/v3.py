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
from typing import List

from iam import Request, Resource, Subject

from backend import env
from backend.iam_app.dataclass.actions import ActionMeta
from backend.iam_app.handlers.backends.base import IAMBackend

logger = logging.getLogger("root")


class IAMV3Backend(IAMBackend):
    """基于 bk-iam SDK 的 V3 鉴权后端"""

    def __init__(self, iam_client):
        self.iam = iam_client

    def make_request(self, username: str, action: ActionMeta, resources: List[Resource]) -> Request:
        return Request(
            system=env.BK_IAM_SYSTEM_ID,
            subject=Subject("user", username),
            action=action,
            resources=resources,
            environment=None,
        )

    def is_allowed(self, username: str, action: ActionMeta, resources: List[Resource]) -> bool:
        request = self.make_request(username, action, resources)
        return bool(self.call_with_retry(self.iam.is_allowed, request, default=False))

    def abc(self, a, b, c):
        pass
