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

from backend.components import BKMonitorV3Api
from backend.db_meta.enums import MachineType
from backend.db_meta.models.cluster_monitor import SHORT_NAMES
from backend.db_monitor.models import CollectTemplate

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = "监控采集策略模板提取到本地数据库"

    def add_arguments(self, parser):
        parser.add_argument(
            "db_type", choices=["mysql", "redis", "es", "hdfs", "kafka", "pulsar", "influxdb"], type=str, help="db类型"
        )
        parser.add_argument("short_name", choices=SHORT_NAMES + ["redis"], help="集群名后缀，比如db.redis.proxy -> proxy")
        parser.add_argument("collect_list", nargs="+", type=str, help="监控采集策略ID列表")

    def to_template(self, instance: dict):
        """监控采集策略模板化处理"""

        def clear_id(objs: List[dict], id_name="id"):
            for obj in objs:
                obj.pop(id_name, None)

        def clear_keys(obj: dict, keeped_keys: List):
            for key in list(obj.keys()):
                if key not in keeped_keys:
                    obj.pop(key, None)

        template = copy.deepcopy(instance)
        clear_id([template])

        # 剔除无用参数
        clear_keys(
            template,
            [
                "name",
                "label",
                "collect_type",
                "plugin_id",
                "params",
                "remote_collecting_host" "subscription_id",
                "target_node_type",
                "target_nodes",
                "target_object_type",
                "plugin_info",
            ],
        )

        plugin_info = template["plugin_info"]
        clear_keys(
            plugin_info,
            [
                "plugin_id",
                "plugin_type",
                # "config_json",
                "metric_json",
                "os_type_list",
            ],
        )
        template["target_nodes"] = []

        return template

    def handle(self, *args, **options):
        collect_list = options["collect_list"]
        db_type = options["db_type"]
        short_name = options["short_name"]

        # 批量获取策略
        for collect_id in collect_list:
            instance = BKMonitorV3Api.query_collect_config_detail({"id": str(collect_id)})
            # 策略转模板

            plugin_id = instance["plugin_info"]["plugin_id"]
            collect_template = self.to_template(instance)
            print(collect_template)
            logger.info(f"[{db_type}-{collect_id}] update collect template: {collect_template['name']}")
            obj, _ = CollectTemplate.objects.update_or_create(
                defaults={
                    "name": collect_template["name"],
                    "details": collect_template,
                },
                db_type=db_type,
                short_name=short_name,
                plugin_id=plugin_id,
            )
