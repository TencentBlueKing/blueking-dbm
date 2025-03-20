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

from pipeline.component_framework.component import Component

from backend.db_meta.enums import ClusterEntryType, MachineType
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.exceptions import ApiResultError
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.dns_manage import DnsManage

logger = logging.getLogger("celery")


class FixDnsService(BaseService):
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")

        for port in kwargs["port_list"]:
            if kwargs["machine_type"] in [MachineType.PROXY, MachineType.SPIDER]:
                instance_obj = ProxyInstance.objects.get(
                    machine__bk_cloud_id=kwargs["bk_cloud_id"],
                    machine__ip=kwargs["ip"],
                    port=port,
                )
            else:
                instance_obj = StorageInstance.objects.get(
                    machine__bk_cloud_id=kwargs["bk_cloud_id"],
                    machine__ip=kwargs["ip"],
                    port=port,
                )

            for be in instance_obj.bind_entry.filter(cluster_entry_type=ClusterEntryType.DNS.value):
                try:
                    res = DnsManage(bk_cloud_id=kwargs["bk_cloud_id"], bk_biz_id=kwargs["bk_biz_id"]).create_domain(
                        instance_list=["{}#{}".format(kwargs["ip"], port)], add_domain_name=be.entry
                    )
                    if not res:
                        self.log_error("add {}#{} to {} failed".format(kwargs["ip"], port, be.entry))
                        return False
                except ApiResultError as e:
                    if "duplicate entry" not in e.message.lower():
                        raise e

        return True


class FixDnsComponent(Component):
    name = __name__
    code = "fix_dns"
    bound_service = FixDnsService
