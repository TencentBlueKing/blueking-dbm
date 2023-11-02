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
import copy
import json
import logging
import os
from collections import OrderedDict

from django.core.management.base import BaseCommand

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import DBType
from backend.db_monitor.constants import TPLS_ALARM_DIR, TargetLevel, TargetPriority
from backend.db_monitor.models import RuleTemplate

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = "监控告警模板提取到本地数据库"

    def add_arguments(self, parser):
        parser.add_argument("db_type", choices=DBType.get_values(), type=str, help="db类型")
        parser.add_argument("bkmonitor_strategy_list", nargs="+", type=int, help="监控策略ID列表")
        parser.add_argument("-c", "--custom-conditions", nargs="*", help="自定义过滤条件的key列表", type=str)
        parser.add_argument("-d", "--disabled", dest="is_disabled", action="store_true", help="disable by default")

    def to_template(self, db_type: str, instance: dict):
        """告警策略模板化处理"""

        template = copy.deepcopy(instance)

        # 剔除无用参数
        for key in [
            "id",
            "version",
            "is_enabled",
            "is_invalid",
            "invalid_type",
            "config_source",
            "alert_count",
            "shield_alert_count",
            "shield_info",
            "update_time",
            "update_user",
            "create_time",
            "create_user",
            "add_allowed",
        ]:
            template.pop(key, None)

        self.clear_id([template])
        self.clear_id(template["detects"])

        # 更新业务id
        template["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
        # 更新label，追加db_type
        template["labels"] = list(set(template["labels"] + [f"DBM_{db_type.upper()}", "DBM"]))

        # 更新通知组
        notice = template["notice"]
        self.clear_id([notice])
        notice["user_groups"] = []

        # 更新监控项和metric_id
        items = template["items"]
        self.clear_id(items)
        for item in items:
            # 更新监控目标为db_type对应的cmdb拓扑
            item["target"] = []

            # 自定义事件和指标需要调整metric_id和result_table_id
            # custom.event.100465_bkmonitor_event_542898.redis_sync
            # custom_event_key = "custom.event"
            # bkmonitor_event_key = "bkmonitor_event"
            for query_config in item["query_configs"]:
                metric_id = query_config["metric_id"]
                # if custom_event_key in metric_id and bkmonitor_event_key in metric_id:
                if query_config["data_type_label"] == "event":
                    metric_ids = metric_id.split(".")
                    metric_ids[2] = "bkmonitor_event_{event_data_id}"
                    query_config["metric_id"] = ".".join(metric_ids)
                    query_config["result_table_id"] = "bkmonitor_event_{event_data_id}"
                    logger.info(query_config.get("metric_id"))

        return instance["id"], template

    def clear_id(self, objs, id_name="id"):
        for obj in objs:
            obj.pop(id_name, None)

    def handle(self, *args, **options):
        bkmonitor_strategy_list = options["bkmonitor_strategy_list"]
        custom_conditions = options["custom_conditions"] or []
        db_type = options["db_type"]
        is_disabled = options["is_disabled"]
        res = BKMonitorV3Api.search_alarm_strategy_v3(
            {
                "page": 1,
                "page_size": 1000,
                "conditions": [{"key": "strategy_id", "value": bkmonitor_strategy_list}],
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "with_notice_group": False,
                "with_notice_group_detail": False,
            }
        )

        # 批量获取策略
        # scenario_list = res["scenario_list"]
        strategy_config_list = res["strategy_config_list"]
        logger.info(f"[{db_type}]get {len(strategy_config_list)} alarm strategy")
        for strategy_config in strategy_config_list:

            # 策略转模板
            strategy_id, strategy_template = self.to_template(db_type, strategy_config)
            logger.info(f"[{db_type}-{strategy_id}]update policy template: {strategy_template['name']}")

            # obj, _ = RuleTemplate.objects.update_or_create(
            #     defaults={
            #         "name": strategy_template["name"],
            #         "details": strategy_template,
            #     },
            #     monitor_strategy_id=strategy_id,
            #     db_type=db_type,
            # )

            template_name = strategy_template["name"]
            strategy_template["labels"] = sorted(set(strategy_template["labels"]))
            strategy_template["source"] = "dbm"
            strategy_template["bk_biz_id"] = ""
            strategy_template["priority"] = TargetPriority.PLATFORM.value

            # 平台策略仅开启基于分派通知
            strategy_template["notice"]["options"]["assign_mode"] = ["by_rule"]
            strategy_template["labels"] = sorted(set(strategy_template["labels"]))

            data_type_label = ""
            custom_agg_conditions = []
            for item in strategy_template["items"]:
                # 清空监控目标
                item["target"] = []
                item["origin_sql"] = ""

                # 补充app_id作为维度
                self.clear_id(item["query_configs"])
                self.clear_id(item["algorithms"])

                for query_config in item["query_configs"]:
                    metric_id = query_config["metric_id"]

                    # 标记告警数据来源
                    data_type_label = query_config["data_type_label"]

                    if "promql" in query_config:
                        promql = query_config["promql"]
                        if metric_id != promql:
                            query_config["metric_id"] = promql
                    else:
                        # 奇怪，监控新版阉割了name
                        metric_field = query_config.get("metric_field")
                        if metric_field and not metric_id.endswith(metric_field):
                            query_config["metric_id"] = ".".join(metric_id.split(".")[:-1] + [metric_field])
                            logger.info(f"found bad metric_id rule: {template_name} -> {query_config['metric_id']}")

                    # 根据监控侧长度限制进行截断
                    if len(query_config["metric_id"]) > 128:
                        logger.info(f"found too long promql metric: {template_name} -> {query_config['metric_id']}")

                    query_config["metric_id"] = query_config["metric_id"][:128]

                    if "agg_dimension" in query_config and "appid" not in query_config["agg_dimension"]:
                        query_config["agg_dimension"].append("appid")

                    custom_agg_conditions = list(
                        filter(lambda x: x["key"] in custom_conditions, query_config.get("agg_condition", []))
                    )

                    if "agg_condition" in query_config:
                        query_config["agg_condition"] = list(
                            filter(
                                lambda x: x["key"] not in ["app"] + TargetLevel.get_values(),
                                query_config["agg_condition"],
                            )
                        )

            self.clear_id(strategy_template["items"])

            with open(os.path.join(TPLS_ALARM_DIR, f"{template_name}.json"), "w") as template_file:
                is_enabled = not is_disabled
                strategy_template["is_enabled"] = is_enabled
                template_dict = OrderedDict(
                    {
                        "bk_biz_id": 0,
                        "name": template_name,
                        "db_type": db_type,
                        "details": strategy_template,
                        "is_enabled": is_enabled,
                        "monitor_indicator": strategy_template["items"][0]["name"],
                        "version": 0,
                        "alert_source": data_type_label,
                        "custom_conditions": custom_agg_conditions,
                    }
                )

                template_file.write(json.dumps(template_dict, indent=2))
