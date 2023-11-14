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

from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

from backend import env
from backend.components import CCApi

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = _("修改指定模块的服务实例进程绑定的ip")

    def add_arguments(self, parser):
        parser.add_argument("bk_module_id", type=int, help=_("模块ID"))
        parser.add_argument("-p", "--port", type=str, help=_("目标端口"))
        parser.add_argument("-i", "--ip", type=str, help=_("目标ip"))
        parser.add_argument("-t", "--type", choices=["real", "zeros"], default="real", help=_("替换方式"))

    def handle(self, *args, **options):
        bk_module_id = options.get("bk_module_id")
        port = options.get("port")
        replace_type = options.get("type")
        ip = options.get("ip")

        bk_biz_id = env.DBA_APP_BK_BIZ_ID

        instances = CCApi.list_service_instance(
            {"bk_biz_id": bk_biz_id, "bk_module_id": bk_module_id, "page": {"start": 0, "limit": 500}}
        )["info"]

        for instance in instances:
            processes = CCApi.list_process_instance(
                {
                    "bk_biz_id": bk_biz_id,
                    "service_instance_id": instance["id"],
                }
            )

            target_ip = instance["name"].split("_")[0] if replace_type == "real" else "0.0.0.0"
            for p in processes:
                bind_info = p["property"]["bind_info"]
                if port and bind_info[0]["port"] != port:
                    continue
                if ip and bind_info[0]["ip"] != ip:
                    continue
                bind_info[0]["ip"] = target_ip

            updated_processes = [p["property"] for p in processes]
            CCApi.update_process_instance({"bk_biz_id": bk_biz_id, "processes": updated_processes})
