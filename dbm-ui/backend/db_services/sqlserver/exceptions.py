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
from django.utils.translation import gettext_lazy as _

from backend.exceptions import AppBaseException, ErrorCode


class SQLServerBaseException(AppBaseException):
    """SQLServer 服务层通用业务异常基类。

    职责：
      - db_services/sqlserver 领域主动抛出的业务异常统一派生于此；
      - 挂接 DB_SERVICE_CODE 模块码，与项目通用错误码体系对齐；
      - 上层（flow / view / aiagent 等）可捕获本基类做统一处理。
    """

    MODULE_CODE = ErrorCode.DB_SERVICE_CODE
    MESSAGE = _("SQLServer 服务层异常")
    MESSAGE_TPL = "{msg}"


class UnsafeIdentifierException(SQLServerBaseException):
    """SQLServer 标识符未通过白名单校验（库名 / schema / 对象名含非法字符或超长）。"""

    ERROR_CODE = "801"
    MESSAGE = _("SQLServer 存在不安全的标识符")
    MESSAGE_TPL = "{msg}"


class UnsafeSQLException(SQLServerBaseException):
    """SQLServer 用户 SQL 文本未通过安全校验（仅允许只读查询场景）。"""

    ERROR_CODE = "802"
    MESSAGE = _("SQLServer 存在不安全的 SQL 语句")
    MESSAGE_TPL = "{msg}"
