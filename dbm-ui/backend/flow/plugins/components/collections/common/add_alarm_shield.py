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
import datetime
import json
from dataclasses import dataclass, field
from typing import List, Optional

from pipeline.component_framework.component import Component

from backend import env
from backend.components.bkmonitorv3.client import BKMonitorV3Api
from backend.db_monitor.constants import MonitorShieldType
from backend.db_monitor.utils import format_shield_description
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.validate_handler import ValidateHandler, validate_list, validate_string

# logger = logging.getLogger("flow")


@dataclass()
class AddAlarmShieldKwargs(ValidateHandler):
    """
    定义添加告警屏蔽（AddAlarmShieldService）活动节点的私有变量结构体。

    时间参数说明（二选一，均不传则抛出异常）:
        - 方式一: 传入 duration_seconds，自动以当前时间为起点计算 begin_time / end_time
        - 方式二: 显式传入 begin_time 和 end_time

    屏蔽类型说明（category）:
        - "dimension"（默认）: 基于维度屏蔽，仅根据 appid + 自定义维度条件进行屏蔽
        - "strategy": 基于策略屏蔽，需额外指定 strategy_id 和 level

    使用示例:
        # 基于维度屏蔽
        kwargs = AddAlarmShieldKwargs(
            description="屏蔽1",
            dimensions=[{"name": "instance_host", "values": ["xxx"]}],
            duration_seconds=7200,
        )

        # 基于策略屏蔽
        kwargs = AddAlarmShieldKwargs(
            description="屏蔽2",
            dimensions=[{"name": "instance", "values": ["xxx"]}],
            duration_seconds=3600,
            category="strategy",
            strategy_id=12345,
            level=[1, 2],
        )
    """

    description: str = field(metadata={"validate": validate_string})
    dimensions: List[dict] = field(default_factory=list, metadata={"validate": validate_list})
    duration_seconds: Optional[int] = None
    begin_time: Optional[str] = None
    end_time: Optional[str] = None
    category: str = "dimension"
    strategy_id: Optional[List[int]] = None
    level: Optional[List[int]] = None


class AddAlarmShieldService(BaseService):
    """
    添加告警屏蔽服务节点。
    在流程编排中作为一个原子节点，用于在执行数据库变更操作前对监控告警进行屏蔽，
    避免变更过程中产生的预期告警干扰运维人员。

    输出上下文:
        alarm_shield_id (int): 蓝鲸监控返回的屏蔽规则 ID，后续可用于解除屏蔽（见 DisableAlarmShieldService）

    屏蔽类型（category）:
        - "dimension"（默认）: 基于维度屏蔽，仅根据 appid + 自定义维度条件进行屏蔽
        - "strategy": 基于策略屏蔽，需额外指定 strategy_id（策略ID）和 level（告警等级）

    kwargs 入参说明:
        - duration_seconds (int, 可选): 屏蔽持续时间（秒），传入后自动计算 begin_time / end_time
        - begin_time (str, 可选): 屏蔽开始时间，格式 "YYYY-MM-DD HH:MM:SS"
        - end_time (str, 可选): 屏蔽结束时间，格式 "YYYY-MM-DD HH:MM:SS"
        - description (str): 屏蔽描述信息
        - category (str, 可选): 屏蔽类型，默认为 "dimension"
        - dimensions (list[dict]): 屏蔽维度列表，每个元素包含 name 和 values
        - strategy_id (int, 仅 category="strategy" 时必传): 策略 ID
        - level (list, 仅 category="strategy" 时必传): 告警等级

    注意: duration_seconds 与 (begin_time + end_time) 二选一，均不传则抛出异常。
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        # ============ 第一步：确定屏蔽的起止时间 ============
        # 优先使用 duration_seconds（持续时长），自动计算起止时间
        if "duration_seconds" in kwargs:
            begin_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            end_time = (
                datetime.datetime.now() + datetime.timedelta(seconds=int(kwargs["duration_seconds"]))
            ).strftime("%Y-%m-%d %H:%M:%S")
        else:
            # 其次使用显式指定的 begin_time 和 end_time
            if "begin_time" in kwargs and "end_time" in kwargs:
                begin_time = kwargs["begin_time"]
                end_time = kwargs["end_time"]
            else:
                # 两种方式都未提供，抛出异常
                raise Exception("add alarm shield missing args")

        bk_biz_id = global_data["bk_biz_id"]
        # 屏蔽类型，默认为基于维度屏蔽
        category = kwargs.get("category", "dimension")

        # ============ 第二步：构造蓝鲸监控屏蔽 API 的请求参数 ============
        shield_param = {
            "category": category,
            "begin_time": begin_time,
            "end_time": end_time,
            # 注意：这里使用的是 DBA 平台的业务 ID（env.DBA_APP_BK_BIZ_ID），而非用户业务 ID
            # 因为告警策略是在 DBA 平台业务下统一管理的
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            # cycle_config.type=1 表示"一次性"屏蔽（不循环）
            "cycle_config": {"begin_time": "", "end_time": "", "day_list": [], "week_list": [], "type": 1},
            # 屏蔽期间不发送通知
            "shield_notice": False,
            "notice_config": {},
            "description": kwargs["description"],
            # 维度配置：默认以 appid（用户业务ID）作为基础维度条件
            "dimension_config": {
                "dimension_conditions": [
                    {"condition": "and", "key": "appid", "method": "eq", "value": [f"{bk_biz_id}"], "name": "appid"},
                ]
            },
        }

        # ============ 第三步：根据屏蔽类型补充策略相关参数 ============
        # 判断这次屏蔽操作基于什么类型操作
        if category == MonitorShieldType.STRATEGY.value:
            # 如果基于策略屏蔽，则需要传入策略id, 且必须传入屏蔽等级
            shield_param["dimension_config"]["id"] = kwargs["strategy_id"]
            shield_param["dimension_config"]["level"] = kwargs["level"]

        # ============ 第四步：追加用户自定义的维度条件 ============
        # dimensions 示例: [{"name": "instance", "values": ["127.0.0.1:3306"]}]
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

        # ============ 第五步：格式化描述信息并调用蓝鲸监控 API 创建屏蔽 ============
        # 在描述前添加 [dbm:appid=xxx] 前缀，便于在监控平台中追踪和识别
        shield_param.update(
            {"description": format_shield_description(bk_biz_id, description=shield_param["description"])}
        )
        self.log_info("alarm shield param: {}".format(json.dumps(shield_param)))
        # 调用蓝鲸监控 V3 API 创建告警屏蔽规则
        res = BKMonitorV3Api.add_shield(shield_param)
        self.log_info("alarm shield {} created".format(res))

        # ============ 第六步：将屏蔽 ID 写入上下文，供下游节点使用 ============
        # 典型用途：DisableAlarmShieldService 会读取此 ID 来解除屏蔽
        trans_data.alarm_shield_id = res["id"]
        data.outputs["trans_data"] = trans_data
        return True


class AddAlarmShieldComponent(Component):
    """
    Pipeline 组件注册类。
    将 AddAlarmShieldService 注册为流程引擎可调度的原子节点，
    在流程编排 YAML/JSON 中通过 code="add_alarm_shield" 引用此组件。
    """

    name = __name__
    code = "add_alarm_shield"
    bound_service = AddAlarmShieldService
    kwargs = AddAlarmShieldKwargs
