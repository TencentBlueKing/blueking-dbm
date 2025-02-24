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
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.mysql_module_operate import MysqlCCTopoOperator


class ClusterStandardizeTransModuleService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        if "cluster_id" in global_data:
            cluster_id = global_data["cluster_id"]
        else:
            cluster_id = kwargs["cluster_id"]

        cluster_obj = Cluster.objects.get(pk=cluster_id)

        MysqlCCTopoOperator(cluster_obj).transfer_instances_to_cluster_module(
            cluster_obj.storageinstance_set.all(), is_increment=True
        )
        MysqlCCTopoOperator(cluster_obj).transfer_instances_to_cluster_module(
            cluster_obj.proxyinstance_set.exclude(
                tendbclusterspiderext__spider_role__in=[
                    TenDBClusterSpiderRole.SPIDER_MNT,
                    TenDBClusterSpiderRole.SPIDER_SLAVE_MNT,
                ]
            ),
            is_increment=True,
        )

        self.log_info(_("[{}] CC 模块标准化完成".format(kwargs["node_name"])))
        return True


class ClusterStandardizeTransModuleComponent(Component):
    name = __name__
    code = "cluster_standardize_trans_module"
    bound_service = ClusterStandardizeTransModuleService
