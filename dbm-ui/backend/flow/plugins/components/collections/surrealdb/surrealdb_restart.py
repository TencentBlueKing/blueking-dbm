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
from backend.flow.plugins.components.collections.surrealdb.utils import fetch_cluster_detail

logger = logging.getLogger("flow")


class RestartSurrealDBService(BaseService):
    """
    调用dbs接口重启 surrealdb 集群
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")
        cluster_detail = fetch_cluster_detail(self, global_data["cluster_id"])
        if cluster_detail is None:
            return False

        params = {
            "k8sClusterName": cluster_detail["k8sClusterConfig"]["clusterName"],
            "namespace": cluster_detail["namespace"],
            "clusterName": cluster_detail["clusterName"],
            "async_to_dbm": False,
            "bk_username": global_data["created_by"],
        }
        # 调用 dbs 接口重启集群
        try:
            KubernetesApi.restart_cluster(params, use_admin=True)
        except (ApiRequestError, ApiResultError) as e:
            self.log_error(_("重启 surrealdb 集群[{}]失败: {}").format(cluster_detail["clusterName"], e))
            return False
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class RestartSurrealDBComponent(Component):
    name = __name__
    code = "restart_surrealdb"
    bound_service = RestartSurrealDBService
