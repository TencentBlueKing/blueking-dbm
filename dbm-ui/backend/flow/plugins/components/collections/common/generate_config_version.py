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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class GenerateConfigVersionService(BaseService):
    """
    生成配置版本服务
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        # 获取参数
        bk_biz_id = kwargs.get("bk_biz_id")
        level_name = kwargs.get("level_name", LevelName.CLUSTER)
        level_value = kwargs.get("level_value")
        level_info = kwargs.get("level_info", {})
        conf_file = kwargs.get("conf_file", "MySQL-5.6")
        conf_type = kwargs.get("conf_type", "dbconf")
        namespace = kwargs.get("namespace", "tendbha")
        format_type = kwargs.get("format", FormatType.MAP_LEVEL)
        method = kwargs.get("method", ReqType.GENERATE_AND_PUBLISH)

        try:
            # 调用配置生成API
            result = DBConfigApi.get_or_generate_instance_config(
                {
                    "bk_biz_id": str(bk_biz_id),
                    "level_name": level_name,
                    "level_value": level_value,
                    "level_info": level_info,
                    "conf_file": conf_file,
                    "conf_type": conf_type,
                    "namespace": namespace,
                    "format": format_type,
                    "method": method,
                }
            )

            self.log_info(_("配置版本生成成功: {}").format(result))
            return True

        except Exception as e:
            self.log_error(_("配置版本生成失败: {}").format(str(e)))
            return False


class GenerateConfigVersionComponent(Component):
    name = _("生成配置版本")
    code = "generate_config_version"
    bound_service = GenerateConfigVersionService
