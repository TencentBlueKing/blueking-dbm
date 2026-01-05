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
from collections import defaultdict

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
        bk_cloud_id = kwargs.get("bk_cloud_id", -1)

        if bk_cloud_id < 0:
            self.log_info("[{}] bk_cloud_id can't be none".format(kwargs["bk_cloud_id"]))
            return False

        if not cluster_ids and not instances:
            self.log_info(
                "[{}] cluster_ids = None and instance = None, skip cc standardize".format(kwargs["node_name"])
            )
            return False

        # 只传入了 cluster_id, 对整个集群做标准化
        if not instances:
            cluster_objs = Cluster.objects.filter(pk__in=cluster_ids)

            for cluster_obj in cluster_objs:
                storage_objs = cluster_obj.storageinstance_set.all()
                proxy_objs = cluster_obj.proxyinstance_set.exclude(
                    tendbclusterspiderext__spider_role__in=[
                        TenDBClusterSpiderRole.SPIDER_MNT,
                        TenDBClusterSpiderRole.SPIDER_SLAVE_MNT,
                    ]
                )

                operator = MysqlCCTopoOperator(list(cluster_objs))
                if storage_objs.exists():
                    operator.transfer_instances_to_cluster_module(storage_objs, is_increment=True)
                if proxy_objs.exists():
                    operator.transfer_instances_to_cluster_module(proxy_objs, is_increment=True)

            return True

        # cluster_ids 和 instances 同时传入
        # 对相关集群的特定实例做标准化
        ip_ports_map = defaultdict(set)
        for ins in instances:
            ip, port = ins.split(":")
            ip_ports_map[ip].add(port)

        for ip, ports in ip_ports_map.items():
            q = Q(**{"machine__bk_cloud_id": bk_cloud_id, "machine__ip": ip, "port__in": list(ports)})
            if cluster_ids:
                q &= Q(**{"cluster__id__in": cluster_ids})

            this_storage_objs = StorageInstance.objects.filter(q)
            this_proxy_objs = ProxyInstance.objects.filter(q).exclude(
                tendbclusterspiderext__spider_role__in=[
                    TenDBClusterSpiderRole.SPIDER_MNT,
                    TenDBClusterSpiderRole.SPIDER_SLAVE_MNT,
                ]
            )

            if this_storage_objs.exists():
                this_cluster_ids = list(this_storage_objs.values_list("cluster__id", flat=True).distinct())
                operator = MysqlCCTopoOperator(list(Cluster.objects.filter(pk__in=this_cluster_ids)))
                operator.transfer_instances_to_cluster_module(this_storage_objs, is_increment=True)

            if this_proxy_objs.exists():
                this_cluster_ids = list(this_proxy_objs.values_list("cluster__id", flat=True).distinct())
                operator = MysqlCCTopoOperator(list(Cluster.objects.filter(pk__in=this_cluster_ids)))
                operator.transfer_instances_to_cluster_module(this_proxy_objs, is_increment=True)

        self.log_info(_("[{}] CC 模块标准化完成".format(kwargs["node_name"])))
        return True


class ClusterStandardizeTransModuleComponent(Component):
    name = __name__
    code = "cluster_standardize_trans_module"
    bound_service = ClusterStandardizeTransModuleService
