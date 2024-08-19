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

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mongodb.migrate_meta import MongoDBMigrateMeta

logger = logging.getLogger("flow")


class MongoDBMigrateMetaService(BaseService):
    """
    根据单据类型执行相关功能
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        # global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        # if trans_data is None or trans_data == "${trans_data}":
        #     # 表示没有加载上下文内容，则在此添加
        #     trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
        #
        # if kwargs["is_update_trans_data"]:
        #     # 表示合并上下文的内容
        #     cluster_info = {**asdict(trans_data), **kwargs["cluster"]}
        #     self.log_info(_("集群元信息:{}").format(cluster_info))
        result = MongoDBMigrateMeta(info=kwargs).action()
        self.log_info("mongodb operate successfully")
        data.outputs["trans_data"] = trans_data
        return result

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MongoDBMigrateMetaComponent(Component):
    name = __name__
    code = "mongodb_migrate_meta"
    bound_service = MongoDBMigrateMetaService
