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

import importlib
from typing import Any, Callable, Dict

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.exceptions import ApiRequestError, ApiResultError
from backend.flow.plugins.components.collections.common.base_service import BaseService


class ExternalService(BaseService):
    """调用第三方服务接口"""

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")

        import_path: str = kwargs.get("import_path")
        import_module: str = kwargs.get("import_module")
        call_func: str = kwargs.get("call_func")
        params: Dict[str, Any] = kwargs.get("params")

        external_service: Callable = getattr(getattr(importlib.import_module(import_path), import_module), call_func)
        try:
            resp = external_service(params)
            self.log_info(_("第三方接口: {} 请求成功! 返回参数为: {}").format(f"{import_module}.{call_func}", resp))
        except (ApiResultError, ApiRequestError) as e:
            self.log_info(_("第三方接口:{} 调用失败！错误信息为: {}").format(f"{import_module}.{call_func}", e))
            return False
        except Exception as e:  # pylint: disable=broad-except
            self.log_info(_("请求遇到未知错误！错误信息为: {}").format(e))
            return False

        # TODO: 考虑对第三方接口请求后对回调函数的支持
        return True


class ExternalServiceComponent(Component):
    name = __name__
    code = "external_service"
    bound_service = ExternalService
