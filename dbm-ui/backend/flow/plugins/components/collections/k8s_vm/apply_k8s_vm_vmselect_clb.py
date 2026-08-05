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

import backend.flow.utils.k8s_vm.k8s_vm_context_dataclass as flow_context
from backend.components import KubernetesApi
from backend.exceptions import ApiRequestError, ApiResultError
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.k8s_vm.consts import VMSELECT_CLB_SUFFIX

logger = logging.getLogger("flow")


class ApplyK8sVmVmselectClbService(BaseService):
    """
    申请k8s vm vmselect clb
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        cluster_name = global_data["k8s_cluster_name"]

        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        try:
            regions_resp = KubernetesApi.get_regions()
        except (ApiRequestError, ApiResultError) as err:
            self.log_error(_("获取vmselect CLB区域信息失败: {}").format(err))
            return False
        region_code = ""
        vpc_id = ""
        region_name = ""
        for region in regions_resp:
            for k8s_cluster in region.get("k8sClusterList", []):
                if k8s_cluster.get("clusterName") == cluster_name:
                    region_code = region.get("regionCode", "")
                    vpc_id = k8s_cluster.get("vpcID", "")
                    region_name = region.get("regionName", "")
                    break
            if region_code:
                break

        if not region_code or not vpc_id:
            self.log_error(_("未找到与集群名称 {} 匹配的区域信息").format(cluster_name))
            return False

        params = {
            "region": region_code,
            "vpc_id": vpc_id,
            "clb_name": "{}-{}".format(cluster_name, VMSELECT_CLB_SUFFIX),
            "clb_nums": 1,
            "async_to_dbm": False,
        }
        try:
            clb_id = KubernetesApi.apply_clb(params)
        except (ApiRequestError, ApiResultError) as err:
            self.log_error(_("申请vmselect CLB失败: {}").format(err))
            return False
        if not clb_id or not isinstance(clb_id, str):
            self.log_error(_("字段类型错误: {} 需要 {} 类型").format(clb_id, "str"))
            return False

        trans_data.vmselect_clb_id = clb_id
        trans_data.vpc_id = vpc_id
        trans_data.region_code = region_code
        trans_data.region_name = region_name
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class ApplyK8sVmVmselectClbComponent(Component):
    name = __name__
    code = "apply_k8s_vm_vmselect_clb"
    bound_service = ApplyK8sVmVmselectClbService
