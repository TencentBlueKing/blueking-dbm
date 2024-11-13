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
from typing import Dict, List

from django.db import models
from django.utils.translation import ugettext as _
from iam.resource.provider import ListResult
from iam.resource.utils import Page

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.views.iam_provider import BaseModelResourceProvider

logger = logging.getLogger("root")


class ClusterResourceProvider(BaseModelResourceProvider):
    """
    集群资源的反向拉取基类
    """

    model: models.Model = Cluster
    resource_meta: ResourceMeta = None
    cluster_types: List[ClusterType] = []

    def list_instance(self, filter, page, **options):
        # 资源的模型
        filter.data_source = self.model
        # 资源模型提取的字段，通常第一个字段是主键，剩下的字段是展示字段
        filter.value_list = [self.resource_meta.lookup_field, *self.resource_meta.display_fields]
        # 资源过滤的字段
        filter.keyword_field = "immute_domain__icontains"
        # 资源其他过滤条件，会同keyword_field一起组成Q查询
        filter.conditions = {"cluster_type__in": self.cluster_types}
        return super().list_instance(filter, page, **options)

    def search_instance(self, filter, page, **options):
        return self.list_instance(filter, page, **options)

    def fetch_instance_info(self, filter, **options):
        filter.data_source = self.model
        return super().fetch_instance_info(filter, **options)

    def list_instance_by_policy(self, filter, page, **options):
        # 策略字段与模型字段之间的映射
        key_mapping = {
            f"{self.resource_meta.id}.id": "id",
            f"{self.resource_meta.id}.creator": "creator",
            f"{self.resource_meta.id}._bk_iam_path_": "bk_biz_id",
        }
        # 模型字段对应数据提取方法
        values_hook = {"bk_biz_id": lambda value: value[1:-1].split(",")[1]}
        return self._list_instance_by_policy(
            data_source=self.model,
            value_list=[self.resource_meta.lookup_field, *self.resource_meta.display_fields],
            key_mapping=key_mapping,
            value_hooks=values_hook,
            filter=filter,
            page=page,
        )

    def _list_instance_with_cluster_type(
        self,
        data_source: models.Model,
        condition: Dict,
        value_list: List[str],
        page: Page,
        cluster_type__label: Dict[str, str],
    ):
        """集群资源展示的时候加上类型标识"""
        queryset = data_source.objects.filter(**condition)[page.slice_from : page.slice_to]
        results = []
        for cluster in queryset:
            # cluster_type_label = cluster_type__label.get(cluster.cluster_type, cluster.cluster_type)
            # 暂时去掉对label的渲染，iam这里会有名字校验
            results.append({"id": cluster.id, "display_name": f"{cluster.immute_domain}"})
        return ListResult(results=results, count=len(results))


class MySQLResourceProvider(ClusterResourceProvider):
    resource_meta: ResourceMeta = ResourceEnum.MYSQL
    cluster_types: ClusterType = [ClusterType.TenDBSingle, ClusterType.TenDBHA]

    def _list_instance(self, data_source: models.Model, condition: Dict, value_list: List[str], page):
        cluster_type__label = {ClusterType.TenDBSingle: _("单节点"), ClusterType.TenDBHA: _("高可用")}
        return super()._list_instance_with_cluster_type(data_source, condition, value_list, page, cluster_type__label)


class TendbClusterResourceProvider(ClusterResourceProvider):
    resource_meta: ResourceMeta = ResourceEnum.TENDBCLUSTER
    cluster_types: ClusterType = [ClusterType.TenDBCluster]


class RedisClusterResourceProvider(ClusterResourceProvider):
    resource_meta: ResourceMeta = ResourceEnum.REDIS
    cluster_types: ClusterType = ClusterType.redis_cluster_types()


class EsClusterResourceProvider(ClusterResourceProvider):
    resource_meta: ResourceMeta = ResourceEnum.ES
    cluster_types: ClusterType = [ClusterType.Es]


class HdfsClusterResourceProvider(ClusterResourceProvider):
    resource_meta: ResourceMeta = ResourceEnum.HDFS
    cluster_types: ClusterType = [ClusterType.Hdfs]


class KafkaClusterResourceProvider(ClusterResourceProvider):
    resource_meta: ResourceMeta = ResourceEnum.KAFKA
    cluster_types: ClusterType = [ClusterType.Kafka]


class PulsarClusterResourceProvider(ClusterResourceProvider):
    resource_meta: ResourceMeta = ResourceEnum.PULSAR
    cluster_types: ClusterType = [ClusterType.Pulsar]


class DorisClusterResourceProvider(ClusterResourceProvider):
    resource_meta: ResourceMeta = ResourceEnum.DORIS
    cluster_types: ClusterType = [ClusterType.Doris]


class RiakClusterResourceProvider(ClusterResourceProvider):
    resource_meta: ResourceMeta = ResourceEnum.RIAK
    cluster_types: ClusterType = [ClusterType.Riak]


class MongoDBClusterResourceProvider(ClusterResourceProvider):
    resource_meta: ResourceMeta = ResourceEnum.MONGODB
    cluster_types: ClusterType = [ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet]

    def _list_instance(self, data_source: models.Model, condition: Dict, value_list: List[str], page):
        cluster_type__label = {ClusterType.MongoReplicaSet: _("副本集"), ClusterType.MongoShardedCluster: _("分片集")}
        return super()._list_instance_with_cluster_type(data_source, condition, value_list, page, cluster_type__label)


class SQLServerClusterResourceProvider(MySQLResourceProvider):
    resource_meta: ResourceMeta = ResourceEnum.SQLSERVER
    cluster_types: ClusterType = [ClusterType.SqlserverHA, ClusterType.SqlserverSingle]

    def _list_instance(self, data_source: models.Model, condition: Dict, value_list: List[str], page):
        cluster_type__label = {ClusterType.SqlserverSingle: _("单节点"), ClusterType.SqlserverHA: _("高可用")}
        return super()._list_instance_with_cluster_type(data_source, condition, value_list, page, cluster_type__label)
