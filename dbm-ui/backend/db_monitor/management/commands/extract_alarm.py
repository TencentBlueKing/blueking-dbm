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
import logging
from typing import List

from django.core.management.base import BaseCommand

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import DBType
from backend.db_meta.models import AppMonitorTopo
from backend.db_monitor.models import NoticeGroup, RuleTemplate

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = "监控告警模板提取到本地数据库"

    def add_arguments(self, parser):
        parser.add_argument("db_type", choices=DBType.get_values(), type=str, help="db类型")
        parser.add_argument("bkmonitor_strategy_list", nargs="+", type=int, help="监控策略ID列表")

    def to_template(self, db_type: str, instance: dict):
        """告警策略模板化处理"""

        def clear_id(objs: List[dict], id_name="id"):
            for obj in objs:
                obj.pop(id_name, None)

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

        clear_id([template])
        clear_id(template["detects"])

        # 更新业务id
        template["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
        # 更新label，追加db_type
        template["labels"] = list(set(template["labels"] + [f"DBM_{db_type.upper()}", "DBM"]))

        # 更新通知组
        notice = template["notice"]
        clear_id([notice])
        notice["user_groups"] = []

        # 更新监控项和metric_id
        items = template["items"]
        clear_id(items)
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

                # result_table_id = query_config.get("result_table_id")
                # if result_table_id and custom_event_key in metric_id and bkmonitor_event_key in result_table_id:
                #     query_config["result_table_id"] = "bkmonitor_event_{event_data_id}"
                #     logger.info(query_config.get("result_table_id"))

        return instance["id"], template

    def handle(self, *args, **options):
        bkmonitor_strategy_list = options["bkmonitor_strategy_list"]
        db_type = options["db_type"]
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
            logger.info(f"[{db_type}-{strategy_id}]update rule template: {strategy_template['name']}")
            obj, _ = RuleTemplate.objects.update_or_create(
                defaults={
                    "name": strategy_template["name"],
                    "details": strategy_template,
                },
                monitor_strategy_id=strategy_id,
                db_type=db_type,
            )
