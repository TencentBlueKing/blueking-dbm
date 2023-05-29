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
import logging
import os
import subprocess
import zipfile

from django.conf import settings
from django.core.management.base import BaseCommand

from backend.core.storages.storage import get_storage

logger = logging.getLogger("root")

BKREPO_TMP_DIR = os.path.join(settings.BASE_DIR, "backend/dbm_init/tmp")


class Command(BaseCommand):
    help = "导出制品库文件到本地"

    def add_arguments(self, parser):
        parser.add_argument("-p", "--path", help="目录名")
        parser.add_argument("-o", "--option", help="解压", choices=["unzip", "download", "all"], default="all")

    def handle(self, *args, **options):
        path = options["path"]
        option = options["option"]
        storage = get_storage()

        # 以dbm_init为根目录进行操作
        if not os.path.exists(BKREPO_TMP_DIR):
            os.makedirs(BKREPO_TMP_DIR)
        os.chdir(BKREPO_TMP_DIR)

        if option in ["download", "all"]:
            if path:
                subprocess.call(["wget", storage.url(f"/{path}")])
            else:
                with open(os.path.join(BKREPO_TMP_DIR, "wget.txt"), "w") as f:
                    for d in storage.listdir("/")[0]:
                        f.write(storage.url(d["fullPath"]) + "\n")
                subprocess.call(["wget", "-i", "./wget.txt"])

        if option in ["unzip", "all"]:
            for root, dirs, files in os.walk(BKREPO_TMP_DIR):
                for file in files:
                    if "?" not in file:
                        continue

                    if path and path not in file:
                        continue

                    db_type = file.split("?")[0]
                    with zipfile.ZipFile(os.path.join(root, file)) as zfile:
                        logger.info("unzip dir: %s", file)
                        zfile.extractall(os.path.join(BKREPO_TMP_DIR, db_type))
