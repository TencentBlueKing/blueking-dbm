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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, Machine, StorageInstance
from backend.db_services.quick_search.constants import FilterType, ResourceType
from backend.flow.models import FlowTree


class QSearchHandler(object):
    def __init__(self, bk_biz_ids=None, db_types=None, resource_types=None, filter_type=None):
        self.bk_biz_ids = bk_biz_ids
        self.db_types = db_types
        self.resource_types = resource_types
        self.filter_type = filter_type
        self.limit = 20

        # db_type -> cluster_type
        self.cluster_types = []
        if self.db_types:
            for db_type in self.db_types:
                self.cluster_types.extend(ClusterType.db_type_to_cluster_type(db_type))

    def search(self, keyword):
        result = {}
        target_resource_types = self.resource_types or ResourceType.get_values()
        for target_resource_type in target_resource_types:
            filter_func = getattr(self, f"filter_{target_resource_type}", None)
            if callable(filter_func):
                result[target_resource_type] = filter_func(keyword)

        return result

    def common_filter(self, objs):
        if self.bk_biz_ids:
            objs = objs.filter(bk_biz_id__in=self.bk_biz_ids)
        if self.db_types:
            objs = objs.filter(cluster_type__in=self.cluster_types)

        return list(objs[: self.limit].values())

    def filter_cluster_name(self, keyword):
        """过滤集群名"""

        qs = Q(name=keyword) if self.filter_type == FilterType.EXACT.value else Q(name__contains=keyword)
        objs = Cluster.objects.filter(qs)
        return self.common_filter(objs)

    def filter_cluster_domain(self, keyword):
        """过滤集群域名"""

        qs = (
            Q(immute_domain=keyword)
            if self.filter_type == FilterType.EXACT.value
            else Q(immute_domain__contains=keyword)
        )

        objs = Cluster.objects.filter(qs)
        return self.common_filter(objs)

    def filter_instance(self, keyword):
        """过滤实例"""

        if self.filter_type == FilterType.EXACT.value:
            qs = Q(machine__ip=keyword) | Q(name=keyword)
        else:
            qs = Q(machine__ip__contains=keyword) | Q(name__contains=keyword)

        objs = StorageInstance.objects.filter(qs)
        return self.common_filter(objs)

    def filter_task(self, keyword):
        """过滤任务"""

        if self.filter_type == FilterType.EXACT.value:
            qs = Q(root_id=keyword)
        else:
            qs = Q(root_id__contains=keyword)

        objs = FlowTree.objects.filter(qs)

        if self.bk_biz_ids:
            objs = objs.filter(bk_biz_id__in=self.bk_biz_ids)

        # TODO: db类型任务的过滤
        return list(objs[: self.limit].values())

    def filter_machine(self, keyword):
        """过滤主机"""

        if self.filter_type == FilterType.EXACT.value:
            qs = Q(ip=keyword) | Q(bk_host_id=keyword)
        else:
            qs = Q(ip__contains=keyword)

        objs = Machine.objects.filter(qs)
        return self.common_filter(objs)
