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

from django.conf import settings
from django.core.management.base import BaseCommand

from backend.core.storages.storage import get_storage

logger = logging.getLogger("root")

BKREPO_TMP_DIR = os.path.join(settings.BASE_DIR, "backend/dbm_init/tmp")


class Command(BaseCommand):
    help = "导入本地文件到制品库"

    def add_arguments(self, parser):
        parser.add_argument("-p", "--path", help="目录名")

    def handle(self, *args, **options):
        path = options["path"]
        storage = get_storage()

        # 以`dbm_init/tmp`为根目录进行操作
        if not os.path.exists(BKREPO_TMP_DIR):
            os.makedirs(BKREPO_TMP_DIR)
        os.chdir(BKREPO_TMP_DIR)

        for root, dirs, files in os.walk(BKREPO_TMP_DIR):
            for file in files:
                if "?" in file:
                    continue

                for suffix in [
                    "txt",
                    "py",
                    "sql",
                    "xlsx",
                    "secret",
                    "crt",
                    "key",
                    "png",
                    "ppx",
                    "doc",
                    "md",
                    "DS_Store",
                ]:
                    if f".{suffix}" in file:
                        break
                else:
                    if path and f"/{path}" not in root:
                        continue

                    file_path = os.path.join(root, file)
                    file_path_bkrep = file_path.split("/tmp")[1]

                    logger.info("upload file: %s -> %s", file_path, file_path_bkrep)
                    with open(file_path, "rb") as f:
                        storage.save(file_path_bkrep, f)
