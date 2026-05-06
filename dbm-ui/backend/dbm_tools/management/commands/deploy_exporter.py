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

logger = logging.getLogger("root")


class Command(BaseCommand):
    help = _("部署指定ip,port,bk_cloud_id的exporter")

    def add_arguments(self, parser):
        parser.add_argument("-p", "--port", type=int, help=_("目标端口"), default=0)
        parser.add_argument("-b", "--bk_cloud_id", type=int, help=_("目标云区域id"), default=0)
        parser.add_argument("-i", "--ip", type=str, help=_("目标ip"))

    def handle(self, *args, **options):
        ip = options.get("ip")
        port = options.get("port", 0)
        bk_cloud_id = options.get("bk_cloud_id", 0)  # 0 表示公有云

        Command.deploy_exporter(ip, port, bk_cloud_id)

    def deploy_exporter(ip: str, port: int = 0, bk_cloud_id: int = 0):
        from backend.db_meta.enums import ClusterType
        from backend.db_meta.models import Machine, ProxyInstance, StorageInstance
        from backend.flow.utils.cc_manage import trigger_operate_collector

        # set log level to info, and print to console
        logger.setLevel(logging.INFO)

        print(f"deploy_exporter: ip: {ip}, port: {port}, bk_cloud_id: {bk_cloud_id}")
        if ip is None:
            print("error: ip or bk_cloud_id is None")
            return
        try:
            machine = Machine.objects.get(ip=ip, bk_cloud_id=bk_cloud_id)
            machine_type = machine.machine_type
        except Machine.DoesNotExist:
            print(f"error: Machine.DoesNotExist: {bk_cloud_id}:{ip}")
            return
        except Exception as e:
            print(f"error: Exception: {e}")
            return
        # get bk_instance_ids
        bk_instance_ids = {}
        for inst in StorageInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id):
            if port > 0 and inst.port != port:
                continue
            bk_instance_ids[inst.bk_instance_id] = f"{inst.machine.ip}:{inst.port}"
        for inst in ProxyInstance.objects.filter(machine__ip=ip, machine__bk_cloud_id=bk_cloud_id):
            if port > 0 and inst.port != port:
                continue
            bk_instance_ids[inst.bk_instance_id] = f"{inst.machine.ip}:{inst.port}"

        if len(bk_instance_ids.keys()) == 0:
            print("error: no instance found, ip: {ip}, bk_cloud_id: {bk_cloud_id}, port: {port}")
            return
        print(f"info: bk_instance_ids: {bk_instance_ids}")
        db_type = ClusterType.cluster_type_to_db_type(machine.cluster_type)
        trigger_operate_collector(db_type, machine_type, list(bk_instance_ids.keys()), "INSTALL")
        print(f"success: trigger_operate_collector: {db_type} {machine_type}, {list(bk_instance_ids.keys())}, INSTALL")
