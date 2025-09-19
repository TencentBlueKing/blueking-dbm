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

from functools import wraps

from rest_framework import status

from backend.db_services.risk_memo.constants import RISK_REQUIRE_MAP
from backend.db_services.risk_memo.models.risk_memo import RiskMemo, RiskOperateRecord


def log_operation(oper_type):
    def decorator(func):
        @wraps(func)
        def wrapper(view, request, *args, **kwargs):
            risk = None

            # 如果是删除操作  提前拿到risk对象
            if "delete" in oper_type:
                risk = view.get_queryset().get(pk=kwargs.get("pk", None))

            response = func(view, request, *args, **kwargs)

            # 确认操作类型，更新为特殊操作类型（如适用）
            if response.data is not None and "is_special" in response.data and response.data["is_special"]:
                operate_type = RISK_REQUIRE_MAP.get(oper_type, oper_type)
            else:
                operate_type = oper_type

            # 检查响应成功状态并获取对象实例
            if response.status_code in {status.HTTP_200_OK, status.HTTP_201_CREATED}:
                try:
                    risk = risk or view.get_queryset().get(pk=response.data["id"])
                    if "follow_up" in oper_type:
                        risk = risk.risk

                    # 创建操作记录
                    RiskOperateRecord.objects.create(creator=request.user.username, oper_type=operate_type, risk=risk)
                except (KeyError, RiskMemo.DoesNotExist) as e:
                    view.logger.error(f"Error in log_operation: {e}")

            return response

        return wrapper

    return decorator


class RiskHandler:
    pass
