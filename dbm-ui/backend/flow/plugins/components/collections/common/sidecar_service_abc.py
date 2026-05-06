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
from abc import ABC, abstractmethod

from bamboo_engine import api
from docutils import Component
from pipeline.core.flow import StaticIntervalGenerator
from pipeline.eri.runtime import BambooDjangoRuntime

from backend.flow.consts import StateType
from backend.flow.plugins.components.collections.common.base_service import BaseService


class SidecarServiceABC(BaseService, ABC):
    """
    示例
    class SidecarDemoService(SidecarServiceABC):
        interval = StaticIntervalGenerator(30)

        def sidecar_func(self, *args, **kwargs) -> bool:
            custom_param = kwargs["custom_param"]
            self.log_info("output {}".format(custom_param))
            return True


    class SidecarDemoComponent(Component):
        name = __name__
        code = "sidecar-demo"
        bound_service = SidecarDemoService

    1. 这样就定义了一个每 30s 打印一行日志的 component
    2. 如何使用这个 component 注入子流程可以参考 dbm-ui/backend/flow/engine/bamboo/scene/common/build_sidecar_wrapper.py
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(30)

    def _execute(self, data, parent_data):
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        global_data = data.get_one_of_inputs("global_data")
        root_id = global_data["job_root_id"]

        if self._worker_is_running(root_id=root_id):
            ret = self.sidecar_func(data, parent_data)
            if ret:
                return True
            else:
                self.finish_schedule()
                return False

        self.finish_schedule()
        return True

    def _worker_is_running(self, root_id: str) -> bool:
        ret = api.get_pipeline_states(BambooDjangoRuntime(), root_id, False)
        for child in ret.data[root_id]["children"].values():
            child_id = child["id"]
            if self.runtime_attrs["top_pipeline_id"] == child_id:
                continue

            if child["state"] == StateType.RUNNING:
                return True

        return False

    @abstractmethod
    def sidecar_func(self, data, parent_data) -> bool:
        pass


class SidecarComponent(Component, ABC):
    @abstractmethod
    def node_name(self) -> str:
        return ""
