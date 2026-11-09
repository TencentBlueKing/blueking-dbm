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

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.db_meta.models import Machine
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class MongoDeferredDeinstallCheckMeta(BaseService):
    """确认 Machine 是否仍在 meta；输出 machine_exists=1/0 供条件分支。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        ip = kwargs["ip"]
        bk_cloud_id = kwargs["bk_cloud_id"]
        force_physical = bool(kwargs.get("force_physical"))
        recycle = kwargs.get("recycle_host") or {}
        machine = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
        # 建单时已经删过 Machine。force_physical 且 meta 里又出现 Machine，说明这台 IP 被重新导入了，拒绝卸载。
        if machine is not None and force_physical:
            self.log_error(
                "machine re-registered after detach ip={} bk_host_id={} snapshot={}".format(
                    ip, machine.bk_host_id, recycle.get("bk_host_id")
                )
            )
            return False
        if machine is None:
            data.outputs.machine_exists = 1 if force_physical else 0
        else:
            data.outputs.machine_exists = 1
        if machine is not None:
            self.log_info("machine still in meta ip={} bk_cloud_id={}".format(ip, bk_cloud_id))
        elif force_physical:
            self.log_info(
                "machine meta already detached ip={} bk_cloud_id={}, continue physical uninstall".format(
                    ip, bk_cloud_id
                )
            )
        else:
            self.log_info(
                "machine already gone from meta ip={} bk_cloud_id={}, skip deferred deinstall".format(ip, bk_cloud_id)
            )
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MongoDeferredDeinstallCheckMetaComponent(Component):
    name = __name__
    code = "mongo_deferred_deinstall_check_meta"
    bound_service = MongoDeferredDeinstallCheckMeta
