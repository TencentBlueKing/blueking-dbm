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
from pipeline.core.flow.activity import Service

from backend.components import KubernetesApi
from backend.exceptions import ApiRequestError, ApiResultError
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class VmSyncClusterService(BaseService):
    """
    同步vm集群
    """

    def _execute(self, data, parent_data):
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        params = {
            "k8sClusterName": global_data["k8s_cluster_name"],
            "namespace": trans_data.namespace,
            "clusterName": global_data["cluster_name"],
            "dbmClusterId": trans_data.cluster_id,
        }
        try:
            KubernetesApi.write_back_cluster_id(params)
        except (ApiRequestError, ApiResultError) as err:
            self.log_error(_("回写VictoriaMetrics集群ID失败: {}").format(err))
            return False
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class VmSyncClusterComponent(Component):
    name = __name__
    code = "vm_sync_cluster"
    bound_service = VmSyncClusterService
