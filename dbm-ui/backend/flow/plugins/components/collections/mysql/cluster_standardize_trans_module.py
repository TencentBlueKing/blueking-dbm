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
from django.db.models import Q
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.mysql_module_operate import MysqlCCTopoOperator


class ClusterStandardizeTransModuleService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        # global_data = data.get_one_of_inputs("global_data")

        cluster_ids = kwargs.get("cluster_ids", None)
        instances = kwargs.get("instances", None)
        if not cluster_ids and not instances:
            self.log_info(
                "[{}] cluster_ids = None and instance = None, skip cc standardize".format(kwargs["node_name"])
            )
            return True

        if cluster_ids:
            cluster_objs = Cluster.objects.filter(pk__in=cluster_ids)
            storage_objs = StorageInstance.objects.filter(cluster__in=cluster_objs)
            proxy_objs = ProxyInstance.objects.filter(cluster__in=cluster_objs).exclude(
                tendbclusterspiderext__spider_role__in=[
                    TenDBClusterSpiderRole.SPIDER_MNT,
                    TenDBClusterSpiderRole.SPIDER_SLAVE_MNT,
                ]
            )

        else:
            q = Q()
            for ins in instances:
                ip, port = ins.split(":")
                q |= Q(**{"machine__ip": ip, "port": port})

            storage_objs = StorageInstance.objects.filter(q)
            proxy_objs = ProxyInstance.objects.filter(q).exclude(
                tendbclusterspiderext__spider_role__in=[
                    TenDBClusterSpiderRole.SPIDER_MNT,
                    TenDBClusterSpiderRole.SPIDER_SLAVE_MNT,
                ]
            )

            cluster_ids = list(
                set(
                    list(storage_objs.values_list("cluster__pk", flat=True))
                    + list(proxy_objs.values_list("cluster__pk", flat=True))
                )
            )

            cluster_objs = Cluster.objects.filter(pk__in=cluster_ids)

        operator = MysqlCCTopoOperator(list(cluster_objs))
        operator.transfer_instances_to_cluster_module(instances=storage_objs, is_increment=True)
        operator.transfer_instances_to_cluster_module(instances=proxy_objs, is_increment=True)

        self.log_info(_("[{}] CC 模块标准化完成".format(kwargs["node_name"])))
        return True


class ClusterStandardizeTransModuleComponent(Component):
    name = __name__
    code = "cluster_standardize_trans_module"
    bound_service = ClusterStandardizeTransModuleService
