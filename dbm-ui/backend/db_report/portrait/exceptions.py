# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 SDK 业务异常定义。

设计要点：
    - 与仓内其它模块保持一致，全部派生自 ``AppBaseException``
    - 复用 ``ErrorCode.MCP_CODE`` 模块码，语义上"画像摘要"是给 MCP/Agent 消费的数据源
    - 每个子异常都定义独立 ``ERROR_CODE`` + ``MESSAGE_TPL``，前端 / 日志可精确定位
    - 调用方应捕获 ``PortraitSDKBaseException`` 一族，而非直接捕获 ``AppBaseException``

边界：
    - 所有 SDK 校验类失败都应转成本模块异常抛出，禁止直接抛 ``ValueError`` / ``Exception``
    - 维度契约错误（如 code 拼写）已由 :class:`PortraitDimensionCode` 枚举在编译期兜住，
      SDK 内部不再定义"未注册"异常——首次上报即自动懒注册
"""
from django.utils.translation import gettext_lazy as _

from backend.exceptions import AppBaseException, ErrorCode


class PortraitSDKBaseException(AppBaseException):
    """集群画像 SDK 异常基类。

    职责：作为 SDK 层所有业务异常的公共父类，供上层统一捕获。
    边界：本类不直接使用，请派生具体子类。
    """

    MODULE_CODE = ErrorCode.MCP_CODE
    MESSAGE = _("集群画像 SDK 异常")
    MESSAGE_TPL = "{msg}"


class PortraitInvalidPayloadException(PortraitSDKBaseException):
    """入参非法异常。

    触发条件：
        - 关键参数缺失 / 类型错误 / 越界（如 detail_url 超长、bk_biz_id <= 0 等）
    修复建议：
        - 检查调用点参数格式；SDK 校验规则参见 ``PortraitIngestSDK._validate_payload``
    """

    ERROR_CODE = "103"
    MESSAGE = _("集群画像上报入参非法")
    MESSAGE_TPL = _("{msg}")
