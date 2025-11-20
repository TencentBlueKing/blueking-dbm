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
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.doris.doris_context_dataclass as flow_context
from backend.components.cos.client import CosSDK
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.doris.consts import DorisResOpType

logger = logging.getLogger("flow")


class CosManageService(BaseService):
    """
    创建/删除 管理COS资源
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        # 从kwargs的res_op_type 判断COS资源操作类型
        if kwargs["res_op_type"] == DorisResOpType.CREATE_AND_BIND.value:
            # 创建COS资源
            return self.create_doris_cos_resource(global_data["res"])

        elif kwargs["res_op_type"] == DorisResOpType.UNTIE_AND_DELETE.value:
            # 删除独立集群 COS资源
            return self.delete_doris_cos_resource(global_data["res"])
        else:
            logger.warn("cluster {} no need to operate cos resource.".format(global_data["cluster_name"]))
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="command result", key="result", type="str")]

    def create_doris_cos_resource(self, res_info: dict) -> bool:
        # 创建DORIS COS资源, 添加账号访问权限
        cos = CosSDK(res_info)
        # 1. 创建COS桶资源
        status = cos.create_bucket()
        if status:
            # 2. 创建存储桶访问策略
            return cos.put_policy()
        else:
            return False

    def delete_doris_cos_resource(self, res_info: dict) -> bool:
        # 删除DORIS COS资源
        cos = CosSDK(res_info)
        return cos.delete_bucket()

    def get_doris_cos_resource(self, res_info: dict) -> str:
        # 获取doris cos资源 存储桶名称
        # params = {
        #     "account_id": res_info["account_id"],
        #     "region": res_info["region"],
        #     "name": res_info["name"],
        # }
        # resp = CosApi.list_cos_bucket(params=params)
        resp = CosSDK(res_info).list_buckets()
        return resp["data"]["buckets"][0]["name"]


class CosManageComponent(Component):
    name = __name__
    code = "cos_manage"
    bound_service = CosManageService
