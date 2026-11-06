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

from backend import env
from backend.iam_app.handlers.backends.base import DummyIAMBackend, IAMBackend
from backend.iam_app.handlers.backends.v3 import IAMV3Backend
from backend.iam_app.handlers.backends.v4 import IAMV4Backend

__all__ = ["IAMBackend", "DummyIAMBackend", "IAMV3Backend", "IAMV4Backend", "get_iam_backend"]


def get_iam_backend(iam_client=None) -> IAMBackend:
    """按开关选择鉴权后端。iam_client 仅V3需要，复用 Permission 已初始化的SDK客户端"""
    if env.BK_IAM_SKIP:
        return DummyIAMBackend()
    if env.ENABLE_IAM_V4:
        return IAMV4Backend()
    return IAMV3Backend(iam_client)
