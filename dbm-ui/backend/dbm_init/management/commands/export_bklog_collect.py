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
import json
import os
from collections import OrderedDict

from django.core.management.base import BaseCommand

from backend.components import BKLogApi
from backend.dbm_init.constants import BKLOG_JOSN_FIELD_LIST, BKLOG_JSON_FILES_PATH


class Command(BaseCommand):
    help = "Pass in an id to create a json file for the information collected by the log platform"

    def add_arguments(self, parser):
        parser.add_argument("collector_config_ids", nargs="+", type=str, help="采集项ID列表")

    def handle(self, *args, **options):
        collector_config_ids = options["collector_config_ids"]

        for collector_config_id in collector_config_ids:
            origin_dict = {}
            data = BKLogApi.retrieve_databus_collector({"collector_config_id": collector_config_id})
            if not data:
                raise "Please enter the correct id"
            file_name = f'{data["collector_config_name_en"]}.json'
            file_path = os.path.join(BKLOG_JSON_FILES_PATH, file_name)

            with open(file_path, "w") as file:
                for field in BKLOG_JOSN_FIELD_LIST:
                    if field == "es_shards":
                        origin_dict[field] = data[field] if data.get(field) else data.get("storage_shards_nums", 3)
                    else:
                        origin_dict[field] = data.get(field, "")

                file.write(
                    json.dumps(
                        OrderedDict(origin_dict),
                        indent=4,
                    )
                )
