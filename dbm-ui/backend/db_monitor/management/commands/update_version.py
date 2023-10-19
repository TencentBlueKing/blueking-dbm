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
    help = "策略模板文件修复"

    def add_arguments(self, parser):
        parser.add_argument("-t", "--type", choices=["collect", "alarm", "all"], default="all", help="模板类型")
        parser.add_argument("version", type=int, help="版本号")

    def update_json_file(self, f, template_dict):
        # print(f"update json file: {f.name}")
        f.seek(0)
        f.write(json.dumps(template_dict, indent=2))
        f.truncate()

    def update_version(self, template_dir, version):
        for json_file in glob.glob(os.path.join(template_dir, "*.json")):
            with open(json_file, "r+") as f:
                template_dict = json.loads(f.read())
                template_dict["version"] = version
                self.update_json_file(f, template_dict)

    def handle(self, *args, **options):
        template_type = options["type"]
        version = options["version"]

        print(f"update {template_type} -> version = {version}...")

        if template_type in ["all", "alarm"]:
            self.update_version(TPLS_ALARM_DIR, version)

        if template_type in ["all", "collect"]:
            self.update_version(TPLS_COLLECT_DIR, version)
