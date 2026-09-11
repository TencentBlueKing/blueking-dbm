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
from typing import List

from django.db import transaction
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.db_meta.models import Machine, ProxyInstance, StorageInstance
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.cc_manage import CcManage

logger = logging.getLogger("flow")


class MongoDeferredDeinstallCleanupMeta(BaseService):
    """
    延迟下架物理卸载成功后清理残留 Machine。
    CMR 在 defer_deinstall 时 keep_machine，此处删 meta 后 create_recycle_ticket 才能出回收单。
    """

    @transaction.atomic
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        ip = kwargs["ip"]
        bk_cloud_id = kwargs["bk_cloud_id"]
        machine = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
        if not machine:
            self.log_info("machine already gone ip={} bk_cloud_id={}, cleanup noop".format(ip, bk_cloud_id))
            return True

        if (
            StorageInstance.objects.filter(machine=machine).exists()
            or ProxyInstance.objects.filter(machine=machine).exists()
        ):
            self.log_error("refuse cleanup: machine {} still has instances, skip delete".format(machine.bk_host_id))
            return False

        cc_manage = CcManage(machine.bk_biz_id, machine.cluster_type)
        self.log_info(
            "deferred deinstall cleanup machine ip={} bk_host_id={} cluster_type={}".format(
                ip, machine.bk_host_id, machine.cluster_type
            )
        )
        cc_manage.recycle_host([machine.bk_host_id])
        machine.delete()
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MongoDeferredDeinstallCleanupMetaComponent(Component):
    name = __name__
    code = "mongo_deferred_deinstall_cleanup_meta"
    bound_service = MongoDeferredDeinstallCleanupMeta
