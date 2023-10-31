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

from backend.configuration.constants import DBType
from backend.db_monitor.constants import TPLS_ALARM_DIR, TPLS_COLLECT_DIR
from backend.db_monitor.models import CollectTemplate, RuleTemplate

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = "策略模板导出到文件"

    COLLECT_FIELDS = [
        "name",
        "machine_types",
        "bk_biz_id",
        "plugin_id",
        "db_type",
        "details",
    ]
    ALARM_FIELDS = [
        "bk_biz_id",
        "name",
        "db_type",
        "details",
        "is_enabled",
    ]

    def add_arguments(self, parser):
        parser.add_argument("-t", "--type", choices=["collect", "alarm", "all"], default="all", help="模板类型")
        parser.add_argument(
            "-d",
            "--dbtype",
            choices=DBType.get_values() + ["all"],
            default="all",
            type=str,
            help="db类型",
        )

    def handle(self, *args, **options):
        template_type = options["type"]
        db_type = options["dbtype"]

        collect_templates = CollectTemplate.objects.filter(bk_biz_id=0)
        alarm_templates = RuleTemplate.objects.filter(bk_biz_id=0, is_enabled=True)
        if db_type != "all":
            collect_templates = collect_templates.filter(db_type=db_type)
            alarm_templates = alarm_templates.filter(db_type=db_type)

        print(f"start export db: {db_type} 's {template_type}...")
        if template_type in ["all", "collect"]:
            for template in collect_templates:
                # 转base64并写文件
                template = model_to_dict(template, fields=self.COLLECT_FIELDS)
                template["version"] = template.get("version", 1)
                template_json = json.dumps(template, indent=2)
                template_file_name = "{db_type}.{name}.json".format(**template)
                with open(os.path.join(TPLS_COLLECT_DIR, template_file_name), "w") as template_file:
                    template_file.write(template_json)
                    print(f"export db: {db_type}'s {template_type}: {template['name']}")

        if template_type in ["all", "alarm"]:
            for template in alarm_templates:
                template = model_to_dict(template, fields=self.ALARM_FIELDS)
                template_json = json.dumps(template)
                template_file_name = "{name}.json".format(**template)
                with open(os.path.join(TPLS_ALARM_DIR, template_file_name), "w") as template_file:
                    template_file.write(template_json)
                    print(f"export db: {db_type}'s {template_type}: {template['name']}")
