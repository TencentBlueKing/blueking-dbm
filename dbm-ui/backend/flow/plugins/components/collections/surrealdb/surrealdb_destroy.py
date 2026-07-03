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
from time import sleep
from typing import List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.surrealdb.surrealdb_context_dataclass as flow_context
from backend.components import KubernetesApi
from backend.exceptions import ApiRequestError, ApiResultError
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.plugins.components.collections.surrealdb.utils import fetch_cluster_detail

logger = logging.getLogger("flow")

# 关闭删除保护后, dbs 侧需要一定时间来生效, 这里等待其生效后再发起删除
DISABLE_DELETION_PROTECTION_WAIT_SECONDS = 5


class DestroySurrealDBService(BaseService):
    """
    删除 surrealdb 集群
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")

        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        cluster_detail = fetch_cluster_detail(self, global_data["cluster_id"])
        if cluster_detail is None:
            return False

        k8s_cluster_config = cluster_detail["k8sClusterConfig"]
        cluster_name = cluster_detail["clusterName"]
        namespace = cluster_detail["namespace"]
        k8s_cluster_name = k8s_cluster_config["clusterName"]

        trans_data.cluster_name = cluster_name
        trans_data.namespace = namespace
        trans_data.k8s_cluster_name = k8s_cluster_name

        # 通用参数: 关闭删除保护与删除集群共用
        base_params = {
            "k8sClusterName": k8s_cluster_name,
            "namespace": namespace,
            "clusterName": cluster_name,
            "async_to_dbm": False,
            "bk_username": global_data["created_by"],
        }

        # 1. 调用 dbs 接口关闭删除保护
        try:
            KubernetesApi.partial_update_cluster({**base_params, "terminationPolicy": "Delete"}, use_admin=True)
        except (ApiRequestError, ApiResultError) as e:
            self.log_error(_("关闭集群[{}]删除保护失败: {}").format(cluster_name, e))
            return False

        # 等待删除保护关闭生效
        sleep(DISABLE_DELETION_PROTECTION_WAIT_SECONDS)

        # 2. 调用 dbs 接口删除集群
        try:
            KubernetesApi.delete_cluster({**base_params}, use_admin=True)
        except (ApiRequestError, ApiResultError) as e:
            self.log_error(_("删除 surrealdb 集群[{}]失败: {}").format(cluster_name, e))
            return False

        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class DestroySurrealDBComponent(Component):
    name = __name__
    code = "destroy_surrealdb"
    bound_service = DestroySurrealDBService
