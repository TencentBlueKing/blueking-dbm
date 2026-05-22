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
from pipeline.core.flow.activity import Service, StaticIntervalGenerator

import backend.flow.utils.qdrant.qdrant_context_dataclass as flow_context
from backend.components import KubernetesApi
from backend.exceptions import ApiResultError
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class GetK8sQdrantClbDetailService(BaseService):
    """
    调用dbs创建接口查询CLB详情，使用pipeline schedule机制异步轮询
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(20)  # 每20秒轮询一次

    def _execute(self, data, parent_data) -> bool:
        """初始化，保存参数供_schedule使用"""
        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")
        if trans_data is None or trans_data == "${trans_data}":
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        # 保存到 outputs，_schedule 和下游节点共用
        data.outputs["trans_data"] = trans_data
        data.outputs["clb_id"] = trans_data.clb_id
        data.outputs["region_code"] = trans_data.region_code
        data.outputs["attempt"] = 0
        data.outputs["max_retries"] = 5
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        """异步轮询CLB详情"""
        trans_data = data.outputs["trans_data"]
        clb_id = data.outputs["clb_id"]
        region_code = data.outputs["region_code"]
        attempt = data.outputs["attempt"] + 1
        data.outputs["attempt"] = attempt
        max_retries = data.outputs["max_retries"]
        params = {
            "region": region_code,
            "clb_ids": [clb_id],
            "async_to_dbm": False,
        }

        try:
            clb_item_list = KubernetesApi.get_clb(params)
        except ApiResultError:
            clb_item_list = None

        if clb_item_list:
            # 获取到CLB详情，写入trans_data，结束调度
            trans_data.clb_detail = clb_item_list[0]
            self.finish_schedule()
            self.log_info(f"CLB {clb_id} detail ready.")
            return True

        if attempt >= max_retries:
            self.log_error(_("获取CLB详情失败"))
            return False

        self.log_info(f"CLB {clb_id} detail not ready yet, attempt {attempt}/{max_retries}. Next check in 20s...")
        return True  # 继续等待下一轮调度

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class GetK8sQdrantClbDetailComponent(Component):
    name = __name__
    code = "get_k8s_qdrant_clb_detail"
    bound_service = GetK8sQdrantClbDetailService
