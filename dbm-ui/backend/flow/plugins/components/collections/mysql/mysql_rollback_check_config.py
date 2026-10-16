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
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.constants import IP_PORT_DIVIDER
from backend.flow.engine.bamboo.scene.mysql.common.get_master_config import get_instance_config
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.plugins.components.collections.mysql.check_client_connections import _format_process_infos


class MySQLRollbackCheckConfigService(BaseService):
    """
    检查2个实例的配置信息
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_info(_("传入参数:{}").format(kwargs))
        self.log_info(_("如果检查不通过,根据您实际需求来选择跳过此节点。"))
        src_instance = "{}{}{}".format(kwargs["instance_ip"], IP_PORT_DIVIDER, kwargs["instance_port"])
        dst_instance = "{}{}{}".format(kwargs["dst_instance_ip"], IP_PORT_DIVIDER, kwargs["dst_instance_port"])
        bk_cloud_id = kwargs["bk_cloud_id"]

        self.log_info("source instance: {}".format(src_instance))
        self.log_info("destination instance: {}".format(dst_instance))
        src_instance_config = get_instance_config(bk_cloud_id, kwargs["instance_ip"], [kwargs["instance_port"]])[
            str(kwargs["instance_port"])
        ]
        dst_instance_config = get_instance_config(
            bk_cloud_id, kwargs["dst_instance_ip"], [kwargs["dst_instance_port"]]
        )[str(kwargs["dst_instance_port"])]
        # 对比源实例与目标实例的配置参数
        compare_result = []
        check_result = True
        all_variable_names = set(src_instance_config.keys()) | set(dst_instance_config.keys())
        for variable_name in sorted(all_variable_names):
            src_value = src_instance_config.get(variable_name)
            dst_value = dst_instance_config.get(variable_name)
            is_equal = src_value == dst_value
            if not is_equal:
                check_result = False
            compare_result.append(
                {
                    "Variable_name": variable_name,
                    "src_instance_value": src_value,
                    "dst_instance_value": dst_value,
                    "result": "yes" if is_equal else "no",
                }
            )
        formatted = _format_process_infos(compare_result, info_max_len=120)
        self.log_info(formatted)
        # if formatted:
        #     self.log_error(formatted)
        if not check_result:
            self.log_warning(_("源实例与目标实例存在配置差异,请根据实际需求选择是否跳过此节点"))
            return False
        else:
            return True


class MySQLRollbackCheckConfigComponent(Component):
    name = __name__
    code = "mysql_rollback_check_config"
    bound_service = MySQLRollbackCheckConfigService
