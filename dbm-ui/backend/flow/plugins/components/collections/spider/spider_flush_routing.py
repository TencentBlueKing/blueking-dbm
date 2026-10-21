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
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService


class SpiderFlushRoutingService(BaseService):
    """
    在中控 primary 执行 TDBCTL FLUSH ROUTING，将中控 mysql.servers 的路由全量下发到各 Spider 节点。

    背景：init_tdbctl_routing（not_flush_all=true）只写中控并同步 TDBCTL 节点，不会向 Spider 节点下发路由；
    spider 接入层灾备恢复 master 段依赖本动作在路由登记/表结构/权限恢复完成后补齐 Spider 本地路由。
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])

        # 优先用编排传入的中控地址；缺省时运行时从 DBMeta 重新解析，规避编排后中控 primary 漂移
        ctl_primary = kwargs.get("ctl_primary") or cluster.tendbcluster_ctl_primary_address()
        if IP_PORT_DIVIDER not in ctl_primary:
            ctl_primary = f"{ctl_primary}{IP_PORT_DIVIDER}{cluster.proxyinstance_set.first().admin_port}"

        rpc_params = {
            "addresses": [ctl_primary],
            "cmds": ["set tc_admin=1", "TDBCTL FLUSH ROUTING"],
            "force": False,
            "bk_cloud_id": cluster.bk_cloud_id,
        }
        self.log_info(f"exec TDBCTL FLUSH ROUTING on [{ctl_primary}]")
        res = DRSApi.rpc(rpc_params)
        if res[0]["error_msg"]:
            self.log_error(f"exec TDBCTL FLUSH ROUTING failed: {res[0]['error_msg']}")
            return False

        self.log_info(f"exec TDBCTL FLUSH ROUTING success on [{ctl_primary}]")
        return True


class SpiderFlushRoutingComponent(Component):
    name = __name__
    code = "spider_flush_routing"
    bound_service = SpiderFlushRoutingService
