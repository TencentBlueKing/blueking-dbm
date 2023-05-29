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
from dataclasses import asdict
from typing import List

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.redis.redis_context_dataclass as flow_context
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.redis.redis_act_playload import RedisActPayload

logger = logging.getLogger("flow")


class GetRedisActPayloadService(BaseService):
    """
    获取redis_act_payload 类，存入到流程上下文中
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        # 传入调用结果，不需要监听任务
        cluster_info = kwargs["cluster"]
        if kwargs["is_update_trans_data"]:
            # 表示合并上下文的内容
            cluster_info = {**kwargs["cluster"], **asdict(trans_data)}
            self.log_info(_("集群元信息:{}").format(cluster_info))

        trans_data.redis_act_payload = RedisActPayload(ticket_data=global_data, cluster=cluster_info)

        self.log_info("successfully")
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", requiredc=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class GetRedisActPayloadComponent(Component):
    name = __name__
    code = "get_redis_act_payload"
    bound_service = GetRedisActPayloadService
