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
from pipeline.component_framework.component import Component
from pipeline.core.flow import StaticIntervalGenerator

from backend.flow.plugins.components.collections.common.sidecar_service_abc import SidecarServiceABC


class SidecarMySQLMasterSlaveHeartbeatService(SidecarServiceABC):
    interval = StaticIntervalGenerator(30)

    def sidecar_func(self, *args, **kwargs) -> bool:
        cluster_ids = kwargs["cluster_ids"]
        self.log_info("try to write heartbeat in {}".format(cluster_ids))
        return True


class SidecarMySQLMasterSlaveHeartbeatComponent(Component):
    name = __name__
    code = "sidecar-mysql-master-slave-heartbeat"
    bound_service = SidecarMySQLMasterSlaveHeartbeatService
