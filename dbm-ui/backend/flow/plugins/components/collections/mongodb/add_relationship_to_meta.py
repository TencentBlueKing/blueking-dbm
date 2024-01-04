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

from backend.db_meta.api.cluster.mongocluster import pkg_create_mongo_cluster
from backend.db_meta.api.cluster.mongorepset import pkg_create_mongoset
from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("json")


class ExecAddRelationshipOperation(BaseService):
    """
    NameServiceCreate服务
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行创建名字服务功能的函数
        global_data 单据全局变量，格式字典
        kwargs 私有变量
        """

        # 从流程节点中获取变量
        kwargs = data.get_one_of_inputs("kwargs")

        # 写入meta
        try:
            if kwargs["cluster_type"] == ClusterType.MongoReplicaSet.value:

                pkg_create_mongoset(
                    bk_biz_id=kwargs["bk_biz_id"],
                    name=kwargs["name"],
                    immute_domain=kwargs["immute_domain"],
                    alias=kwargs["alias"],
                    major_version=kwargs["major_version"],
                    storages=kwargs["storages"],
                    creator=kwargs["creator"],
                    bk_cloud_id=kwargs["bk_cloud_id"],
                    db_module_id=kwargs["db_module_id"],
                    region=kwargs["region"],
                    skip_machine=kwargs["skip_machine"],
                    spec_id=kwargs["spec_id"],
                    spec_config=kwargs["spec_config"],
                )
            elif kwargs["cluster_type"] == ClusterType.MongoShardedCluster.value:
                pkg_create_mongo_cluster(
                    bk_biz_id=kwargs["bk_biz_id"],
                    name=kwargs["name"],
                    immute_domain=kwargs["immute_domain"],
                    alias=kwargs["alias"],
                    major_version=kwargs["major_version"],
                    proxies=kwargs["proxies"],
                    configs=kwargs["configs"],
                    storages=kwargs["storages"],
                    creator=kwargs["creator"],
                    bk_cloud_id=kwargs["bk_cloud_id"],
                    region=kwargs["region"],
                    machine_specs=kwargs["machine_specs"],
                )
        except Exception as e:
            self.log_error("add relationship to meta fail, error:{}".format(str(e)))
            return False
        self.log_info("add mongodb relationship to meta successfully")
        return True

    # 流程节点输入参数
    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class ExecAddRelationshipOperationComponent(Component):
    """
    ExecAddRelationshipOperation组件
    """

    name = __name__
    code = "add_relationship_to_meta_operation"
    bound_service = ExecAddRelationshipOperation
