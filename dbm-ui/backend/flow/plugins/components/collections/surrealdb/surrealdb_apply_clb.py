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
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.surrealdb.consts import CLB_NAME_SUFFIX

logger = logging.getLogger("flow")


class ApplySurrealDBClbService(BaseService):
    """
    申请 surrealdb clb
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        cluster_name = global_data["k8s_cluster_name"]

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        regions_resp = KubernetesApi.get_regions()

        # 匹配clusterName与cluster_name一致的数据，获取vpcID和regionCode
        region_code = ""
        vpc_id = ""
        for region in regions_resp:
            for k8s_cluster in region.get("k8sClusterList", []):
                if k8s_cluster.get("clusterName") == cluster_name:
                    region_code = region.get("regionCode", "")
                    vpc_id = k8s_cluster.get("vpcID", "")
                    break
            if region_code:
                break

        if not region_code or not vpc_id:
            self.log_error(_("未找到与集群名称 {} 匹配的区域信息").format(cluster_name))
            return False

        # 申请CLB
        params = {
            "region": region_code,
            "vpc_id": vpc_id,
            "clb_name": f"{cluster_name}-{CLB_NAME_SUFFIX}",
            "clb_nums": 1,
            "async_to_dbm": False,
        }

        clb_id = KubernetesApi.apply_clb(params)

        # 校验 apply_clb 返回值
        if not clb_id or not isinstance(clb_id, str):
            self.log_error(_("字段类型错误: {} 需要 {} 类型").format(clb_id, "str"))
            return False

        # 将clb_id写入上下文，供后续节点使用
        trans_data.clb_id = clb_id
        trans_data.vpc_id = vpc_id
        trans_data.region_code = region_code
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class ApplySurrealDBClbComponent(Component):
    name = __name__
    code = "apply_surrealdb_clb"
    bound_service = ApplySurrealDBClbService
