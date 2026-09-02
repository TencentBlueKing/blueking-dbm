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

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

import backend.flow.utils.k8s_db.vm.k8s_vm_context_dataclass as flow_context
from backend.components import KubernetesApi
from backend.exceptions import ApiRequestError, ApiResultError
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.k8s_db.consts import SCHEDULE_INTERVAL_SECONDS, SCHEDULE_MAX_RETRIES

logger = logging.getLogger("flow")


class K8sVmDeleteService(BaseService):
    """
    删除 k8s vm 集群
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(SCHEDULE_INTERVAL_SECONDS)

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")

        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        cluster_id = global_data["cluster_id"]
        try:
            cluster_detail = KubernetesApi.cluster_detail({"cluster_id": cluster_id}, use_admin=True)
        except (ApiRequestError, ApiResultError) as err:
            self.log_error(_("获取VictoriaMetrics集群[{}]详情失败: {}").format(cluster_id, err))
            return False

        k8s_cluster_name = cluster_detail["k8sClusterConfig"]["clusterName"]
        namespace = cluster_detail["namespace"]
        cluster_name = cluster_detail["clusterName"]

        trans_data.cluster_name = cluster_name
        trans_data.namespace = namespace
        trans_data.k8s_cluster_name = k8s_cluster_name

        base_params = {
            "k8sClusterName": k8s_cluster_name,
            "namespace": namespace,
            "clusterName": cluster_name,
            "async_to_dbm": False,
            "bk_username": global_data["created_by"],
        }

        try:
            KubernetesApi.partial_update_cluster({**base_params, "terminationPolicy": "Delete"}, use_admin=True)
        except (ApiRequestError, ApiResultError) as err:
            self.log_error(_("关闭VictoriaMetrics集群[{}]删除保护失败: {}").format(cluster_name, err))
            return False

        data.outputs["cluster_id"] = cluster_id
        data.outputs["base_params"] = base_params
        data.outputs["attempt"] = 0
        data.outputs["max_retries"] = SCHEDULE_MAX_RETRIES
        data.outputs["trans_data"] = trans_data
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        cluster_id = data.outputs["cluster_id"]
        base_params = data.outputs["base_params"]
        attempt = data.outputs["attempt"] + 1
        data.outputs["attempt"] = attempt
        max_retries = data.outputs["max_retries"]

        try:
            cluster_detail = KubernetesApi.cluster_detail({"cluster_id": cluster_id}, use_admin=True)
        except (ApiRequestError, ApiResultError) as err:
            if attempt >= max_retries:
                self.log_error(_("确认VictoriaMetrics集群[{}]删除保护状态失败: {}").format(cluster_id, err))
                self.finish_schedule()
                return False
            self.log_info(
                _("获取VictoriaMetrics集群[{}]删除保护状态失败，将在{}秒后重试: {}").format(cluster_id, SCHEDULE_INTERVAL_SECONDS, err)
            )
            return True

        if cluster_detail.get("terminationPolicy") != "Delete":
            if attempt >= max_retries:
                self.log_error(_("等待VictoriaMetrics集群[{}]删除保护关闭超时").format(cluster_id))
                self.finish_schedule()
                return False
            self.log_info(_("VictoriaMetrics集群[{}]删除保护尚未关闭，将在{}秒后重试").format(cluster_id, SCHEDULE_INTERVAL_SECONDS))
            return True

        try:
            KubernetesApi.delete_cluster(base_params, use_admin=True)
        except (ApiRequestError, ApiResultError) as err:
            self.log_error(_("删除VictoriaMetrics集群[{}]失败: {}").format(base_params["clusterName"], err))
            self.finish_schedule()
            return False

        self.finish_schedule()
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class K8sVmDeleteComponent(Component):
    name = __name__
    code = "k8s_vm_delete"
    bound_service = K8sVmDeleteService
