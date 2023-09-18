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
import base64
import json
import logging
import os

from django.core.management.base import BaseCommand
from django.forms import model_to_dict

from backend.db_monitor.constants import TPLS_ALARM_DIR, TPLS_COLLECT_DIR
from backend.db_monitor.models import CollectTemplate, RuleTemplate

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = "策略模板导出到文件"

    COLLECT_FIELDS = [
        "bk_biz_id",
        "plugin_id",
        "db_type",
        "details",
    ]
    ALARM_FIELDS = [
        "bk_biz_id",
        "monitor_strategy_id",
        "name",
        "db_type",
        "details",
        "is_enabled",
    ]

    def add_arguments(self, parser):
        parser.add_argument("-t", "--type", choices=["collect", "alarm", "all"], default="all", help="模板类型")

    def handle(self, *args, **options):
        collect_templates = CollectTemplate.objects.filter(bk_biz_id=0)
        alarm_templates = RuleTemplate.objects.filter(bk_biz_id=0, is_enabled=True)
        template_type = options["type"]

        if template_type in ["all", "collect"]:
            for template in collect_templates:
                # 转base64并写文件
                template = model_to_dict(template, fields=self.COLLECT_FIELDS)
                template_json = json.dumps(template)
                template_file_name = "{bk_biz_id}.{db_type}.{plugin_id}.json".format(**template)
                with open(os.path.join(TPLS_COLLECT_DIR, template_file_name), "w") as template_file:
                    template_file.write(template_json)

        if template_type in ["all", "alarm"]:
            for template in alarm_templates:
                template = model_to_dict(template, fields=self.ALARM_FIELDS)
                template_json = json.dumps(template)
                template_file_name = "{db_type}#{name}.json".format(**template)
                with open(os.path.join(TPLS_ALARM_DIR, template_file_name), "w") as template_file:
                    template_file.write(template_json)
