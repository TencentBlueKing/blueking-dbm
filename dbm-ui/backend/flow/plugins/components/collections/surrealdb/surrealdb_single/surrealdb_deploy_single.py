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

import backend.flow.utils.surrealdb.surrealdb_context_dataclass as flow_context
from backend.components import KubernetesApi
from backend.exceptions import ApiRequestError, ApiResultError
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.surrealdb.consts import NAMESPACE_PREFIX, SINGLE_TAGS, SINGLE_TOPO_NAME, STORAGE_ADDON_TYPE

logger = logging.getLogger("flow")


class DeploySurrealDBSingleService(BaseService):
    """
    调用dbs创建接口创建 surrealdb 集群
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        namespace = f"{NAMESPACE_PREFIX}-{global_data['db_app_abbr']}-{global_data['bk_biz_id']}"

        component_list = [
            {
                "componentName": item["component_name"],
                "version": global_data["db_version"],
                "replicas": item["replicas"],
                "request": {
                    "cpu": item["request_cpu"],
                    "memory": item["request_memory"],
                },
                "limit": {
                    "cpu": item.get("limit_cpu", item["request_cpu"]),
                    "memory": item.get("limit_memory", item["request_memory"]),
                },
                "volumeClaimTemplates": {
                    "accessModes": ["ReadWriteOnce"],
                    "storage": item["storage"],
                    "storageClassName": "cbs",
                    "volumeMode": "Filesystem",
                },
            }
            for item in global_data["component_list"]
        ]

        params = {
            "k8sClusterName": global_data["k8s_cluster_name"],
            "namespace": namespace,
            "clusterName": global_data["cluster_name"],
            "clusterAlias": global_data["cluster_alias"],
            "storageAddonType": STORAGE_ADDON_TYPE,
            "storageAddonVersion": global_data["major_version"],
            "addonClusterVersion": global_data["major_version"],
            "topoName": SINGLE_TOPO_NAME,
            "terminationPolicy": "DoNotTerminate",
            "bkBizId": global_data["bk_biz_id"],
            "bkBizName": global_data["bk_biz_name"],
            "bkAppAbbr": global_data["db_app_abbr"],
            "componentList": component_list,
            "async_to_dbm": False,
            "bk_username": global_data["created_by"],
            "tags": SINGLE_TAGS,
            "observeConfig": {
                "bkLogConfig": {"enabled": False},
                "svcMonitor": {"enabled": True, "interval": "60s", "labels": {}},
            },
        }
        try:
            KubernetesApi.create_cluster(params)
        except (ApiRequestError, ApiResultError) as e:
            self.log_error(_("部署 surrealdb 单机[{}]失败: {}").format(global_data["cluster_name"], e))
            return False
        trans_data.namespace = namespace
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class DeploySurrealDBSingleComponent(Component):
    name = __name__
    code = "deploy_surrealdb_single"
    bound_service = DeploySurrealDBSingleService
