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

from django.utils.translation import gettext as _
from rest_framework.response import Response

from backend.flow.engine.controller.k8s_vm import K8sVmController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class InstallK8sVmSceneApiView(FlowTestView):
    """
    api: /apis/v1/flow/scene/install_k8s_vm
    params:
    {
        {
            "created_by": "xxx",
            "remark": "xxxxx",
            "bk_biz_id": xxx,
            "ticket_type": "K8S_VICTORIAMETRICS_APPLY",
            "db_app_abbr": "xxxx",
            "bk_biz_name": "蓝鲸",
            "bk_cloud_id": 0,
            "bk_cloud_region": "测试区域",
            "city_code": "上海",
            "k8s_cluster_name": "测试集群",
            "major_version": "2.0.0",
            "db_version": "2.0.0",
            "cluster_type": "k8s_vm",
            "cluster_name": "k8s-vm-test1",
            "cluster_alias": "k8s-vm-test1",
            "component_list": [
                {
                    "component_name": "vminsert",
                    "replicas": 1,
                    "request_cpu": "1",
                    "request_memory": "1Gi",
                    "version": "1.115.0-2.0.0"
                },
                {
                    "component_name": "vmselect",
                    "replicas": 1,
                    "request_cpu": "1",
                    "request_memory": "1Gi",
                    "version": "1.115.0-2.0.0"
                },
                {
                    "component_name": "vmstorage",
                    "replicas": 1,
                    "request_cpu": "1",
                    "request_memory": "1Gi",
                    "storage": "100Gi",
                    "version": "1.115.0-2.0.0"
                }
            ]
        }
    }
    """

    def post(self, request):
        logger.info(_("开始部署K8s VM场景"))

        root_id = generate_root_id()
        logger.info("define root_id: {}".format(root_id))
        K8sVmController(root_id=root_id, ticket_data=request.data).vm_apply_scene()
        return Response({"root_id": root_id})
