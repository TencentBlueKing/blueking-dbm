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
import json
import logging

from pipeline.component_framework.component import Component

from backend import env
from backend.components.bkmonitorv3.client import BKMonitorV3Api
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class AddAlarmShieldService(BaseService):
    """
    输出上下文 alarm_shield_id : int
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        bk_biz_id = global_data["bk_biz_id"]

        shield_param = {
            "category": "dimension",
            "begin_time": kwargs["begin_time"],
            "end_time": kwargs["end_time"],
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "cycle_config": {"begin_time": "", "end_time": "", "day_list": [], "week_list": [], "type": 1},
            "shield_notice": False,
            "notice_config": {},
            "description": kwargs["description"],
            "dimension_config": {
                "dimension_conditions": [
                    {"condition": "and", "key": "appid", "method": "eq", "value": [f"{bk_biz_id}"], "name": "appid"},
                ]
            },
        }

        dimensions = kwargs["dimensions"]
        for dim in dimensions:
            shield_param["dimension_config"]["dimension_conditions"].append(
                {
                    "condition": "and",
                    "key": dim["name"],
                    "method": "eq",
                    "value": dim["values"],
                    "name": dim["name"],
                }
            )

        shield_param.update(
            {"description": self.format_shield_description(bk_biz_id, description=shield_param["description"])}
        )
        logger.info("alarm shield param: {}".format(json.dumps(shield_param)))

        res = BKMonitorV3Api.add_shield(shield_param)
        logger.info("alarm shield {} created".format(res))

        trans_data.alarm_shield_id = res["id"]
        data.outputs["trans_data"] = trans_data
        return True

    @staticmethod
    def format_shield_description(bk_biz_id, description=""):
        prefix = f"[dbm:appid={bk_biz_id}]"
        # 先删后补，避免出现多个前缀
        description = description.replace(prefix, "").strip()
        return f"{prefix}{description}"


class AddAlarmShieldComponent(Component):
    name = __name__
    code = "add_alarm_shield"
    bound_service = AddAlarmShieldService
