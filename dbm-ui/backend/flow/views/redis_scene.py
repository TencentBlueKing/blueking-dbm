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
import uuid

from rest_framework.response import Response

from backend.db_meta.enums import ClusterType
from backend.flow.engine.controller.redis import RedisController
from backend.flow.views.base import FlowTestView

logger = logging.getLogger("flow")


class RedisClusterSlaveCutOffSceneApiView(FlowTestView):
    """
    /apis/v1/flow/scene/cutoff/redis_cluster_slave
    params:
    {
      "cluster_id":111, # 必须有
      "domain_name":"xxx.abc.dba.db",
      "cluster_type":"xxxxx",
      "db_version":"yyyyyy",
      "bk_biz_id":"",
      "bk_cloud_id":11,
      "hosts":[1.1.1.1,2.2.2.2], # 必须有
      "region":"xxxyw", # 可选
      "device_class":"S5.Large8" # 可选
      "ticket_type": "REDIS_CLUSTER_SLAVE_CUTOFF"
      "ip_source": "manual_input", # 手动输入/自动匹配资源池
      "assign_hosts":{"1.1.1.1":"6.6.6.6","2.2.2.2":"7.7.7.7,8.8.8.8"} # 可选
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_cluster_slave_cutoff_scene()
        return Response({"root_id": root_id})


class RedisClusterMasterCutOffSceneApiView(FlowTestView):
    """
    /apis/v1/flow/scene/cutoff/redis_cluster_master
    params:
    {
      "cluster_id":111, # 必须有
      "domain_name":"xxx.abc.dba.db",
      "cluster_type":"xxxxx",
      "db_version":"yyyyyy",
      "bk_biz_id":"",
      "bk_cloud_id":11,
      "hosts":[1.1.1.1,2.2.2.2], # 必须有
      "region":"xxxyw", # 可选
      "device_class":"S5.Large8" # 可选
      "ticket_type": "REDIS_CLUSTER_MASTER_CUTOFF"
      "ip_source": "manual_input", # 手动输入/自动匹配资源池
      "assign_hosts":{"1.1.1.1":"6.6.6.6","2.2.2.2":"7.7.7.7,8.8.8.8"} # 可选
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_cluster_master_cutoff_scene()
        return Response({"root_id": root_id})


class RedisInstallDbmonSceneApiView(FlowTestView):
    """
    /apis/v1/flow/scene/install/dbmon
    params:
    {
      "bk_biz_id":"", # 必须有
      "bk_cloud_id":11, # 必须有
      "hosts":[1.1.1.1,2.2.2.2],
      "ticket_type": "REDIS_INSTALL_DBMON"
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_install_dbmon_scene()
        return Response({"root_id": root_id})
