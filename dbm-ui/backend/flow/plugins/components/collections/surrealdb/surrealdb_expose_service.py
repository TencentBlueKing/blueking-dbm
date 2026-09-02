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

import logging.config
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

import backend.flow.utils.k8s_db.surrealdb.surrealdb_context_dataclass as flow_context
from backend.components import KubernetesApi
from backend.exceptions import ApiResultError
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.k8s_db.consts import SCHEDULE_INTERVAL_SECONDS, SCHEDULE_MAX_RETRIES
from backend.flow.utils.k8s_db.surrealdb.consts import (
    COMPONENT_SURREAL,
    SERVICE_NAME,
    SURREALDB_PORT,
)

logger = logging.getLogger("flow")


class ExposeSurrealDBService(BaseService):
    """
    调用 dbs 接口暴露服务
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(SCHEDULE_INTERVAL_SECONDS)

    def _execute(self, data, parent_data) -> bool:
        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")
        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
        data.outputs["attempt"] = 0
        data.outputs["max_retries"] = SCHEDULE_MAX_RETRIES
        data.outputs["trans_data"] = trans_data
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        """异步轮询"""
        trans_data = data.outputs["trans_data"]
        global_data = data.get_one_of_inputs("global_data")
        attempt = data.outputs["attempt"] + 1
        data.outputs["attempt"] = attempt
        max_retries = data.outputs["max_retries"]
        clb_id = trans_data.clb_id

        params = {
            "k8sClusterName": global_data["k8s_cluster_name"],
            "namespace": trans_data.namespace,
            "clusterName": global_data["cluster_name"],
            "componentName": COMPONENT_SURREAL,
            "enable": True,
            "service": {
                "name": SERVICE_NAME,
                "serviceType": "LoadBalancer",
                "annotations": {"service.kubernetes.io/tke-existed-lbid": clb_id},
                "ports": [SURREALDB_PORT],
            },
            "async_to_dbm": False,
            "bk_username": global_data["created_by"],
        }

        try:
            resp = KubernetesApi.expose_ports(params)
        except ApiResultError as e:
            resp = None
            data.outputs["last_error"] = str(e)

        if resp:
            self.finish_schedule()
            return True

        if attempt >= max_retries:
            error_msg = data.outputs.get("last_error", "")
            self.log_error(f"surreal expose {clb_id} failed after {max_retries} attempts. {error_msg}")
            self.finish_schedule()
            return False

        self.log_info(
            f"surreal expose {clb_id} not ready yet, attempt {attempt}/{max_retries}. "
            f"Next check in {SCHEDULE_INTERVAL_SECONDS}s..."
        )
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class ExposeSurrealDBServiceComponent(Component):
    name = __name__
    code = "expose_surrealdb_service"
    bound_service = ExposeSurrealDBService
