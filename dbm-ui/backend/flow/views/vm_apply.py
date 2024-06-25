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

from django.utils.translation import ugettext as _
from rest_framework.response import Response

from backend.flow.engine.controller.vm import VmController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class InstallVmSceneApiView(FlowTestView):
    """
    api: /apis/v1/flow/scene/install_vm
    params:
    {
        "bk_biz_id": 2005000002,
        "remark": "测试创建vm集群",
        "ticket_type": "VM_APPLY",
        "cluster_name": "viper-cluster",
        "cluster_alias": "测试集群",
        "ip_source": "manual_input",
        "city_code": "深圳",
        "db_app_abbr": "blueking",
        "db_version": "2.10.4",
        "username": "username",
        "password": "password",
        "vminsert_port": 8480,
        "vmselect_port": 8481,
        "uid":"2111"
        "created_by": "rtx",
        "domain": "vm.viper-cluster.blueking.db",
        "auth": 0,
        "retention_period": "180d",
        "replication_factor": 2
        "nodes": {
            "vmauth": [
                {"ip": "127.0.0.1", "bk_cloud_id": 0}
            ],
            "vmstorage": [
                {"ip": "127.0.0.2", "bk_cloud_id": 0}
            ],
            "vminsert": [
                {"ip": "127.0.0.3", "bk_cloud_id": 0}
            ],
            "vmselect": [
                {"ip": "127.0.0.6", "bk_cloud_id": 0}
            ]
        }
    }
    """

    def post(self, request):
        logger.info(_("开始部署Vm场景"))

        root_id = generate_root_id()
        logger.info("define root_id: {}".format(root_id))
        VmController(root_id=root_id, ticket_data=request.data).vm_apply_scene()
        return Response({"root_id": root_id})
