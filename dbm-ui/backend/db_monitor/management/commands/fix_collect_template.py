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
import glob
import json
import logging
import os

from django.core.management.base import BaseCommand

from backend.db_monitor.constants import TPLS_ALARM_DIR, TPLS_COLLECT_DIR, TargetPriority

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = "采集模板文件修复"

    def add_arguments(self, parser):
        parser.add_argument(
            "-d",
            "--dbtype",
            choices=["mysql", "redis", "es", "hdfs", "kafka", "pulsar", "influxdb", "all"],
            default="all",
            type=str,
            help="db类型",
        )

    def update_json_file(self, f, template_dict):
        f.seek(0)
        f.write(json.dumps(template_dict, indent=2))
        f.truncate()

    def handle(self, *args, **options):
        db_type = options["dbtype"]
        json_files = glob.glob(os.path.join(TPLS_COLLECT_DIR, "*.json"))
        for json_file in json_files:
            with open(json_file, "r+") as f:
                template_dict = json.loads(f.read())
                # 补充 machine_types 参数
                if not template_dict.get("machine_types"):
                    template_dict["machine_types"] = []

                template_dict.pop("short_name", None)
                self.update_json_file(f, template_dict)
