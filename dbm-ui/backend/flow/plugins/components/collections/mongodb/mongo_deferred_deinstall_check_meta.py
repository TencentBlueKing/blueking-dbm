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
        exists = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).exists()
        data.outputs.machine_exists = 1 if exists else 0
        if exists:
            self.log_info("machine still in meta ip={} bk_cloud_id={}".format(ip, bk_cloud_id))
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
