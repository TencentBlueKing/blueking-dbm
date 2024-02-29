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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.views.iam_provider import BaseResourceProvider, CommonProviderMixin

logger = logging.getLogger("root")


class ClusterResourceProvider(BaseResourceProvider, CommonProviderMixin):
    """
    集群资源的反向拉取基类
    """

    model: models.Model = Cluster
    resource_meta: ResourceMeta = None
    cluster_types: List[ClusterType] = []

    def get_bk_iam_path(self, instance_ids, *args, **kwargs) -> Dict:
        return self.get_model_bk_iam_path(self.model, instance_ids, *args, **kwargs)

    def list_attr(self, **options):
        """查询某个资源类型可用于配置权限的属性列表"""
        return self._list_attr(id=self.resource_meta.attribute, display_name=self.resource_meta.attribute_display)

    def list_attr_value(self, filter, page, **options):
        """获取一个资源类型某个属性的值列表"""
        user_resource = self.list_user_resource()
        return self._list_attr_value(self.resource_meta.attribute, user_resource, filter, page, **options)

    def list_instance(self, filter, page, **options):
        # 资源的模型
        filter.model = self.model
        # 资源模型提取的字段，通常第一个字段是主键，剩下的字段是展示字段
        filter.value_list = [self.resource_meta.lookup_field, *self.resource_meta.display_fields]
        # 资源过滤的字段
        filter.keyword_field = "immute_domain"
        # 资源其他过滤条件，会同keyword_field一起组成Q查询
        filter.conditions = {"cluster_type__in": self.cluster_types}
        return super().list_instance(filter, page, **options)

    def search_instance(self, filter, page, **options):
        return self.list_instance(filter, page, **options)

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
            obj_model=self.model,
            value_list=[self.resource_meta.lookup_field, *self.resource_meta.display_fields],
            key_mapping=key_mapping,
            value_hooks=values_hook,
            filter=filter,
            page=page,
        )


class MySQLResourceProvider(ClusterResourceProvider):
    resource_meta: ResourceMeta = ResourceEnum.MYSQL
    cluster_types: ClusterType = [ClusterType.TenDBSingle, ClusterType.TenDBHA]

    def _list_instance(self, obj_model: models.Model, condition: Dict, value_list: List[str], page):
        # mysql资源展示的时候加上类型
        queryset = obj_model.objects.filter(**condition)[page.slice_from : page.slice_to]
        results = []
        for mysql in queryset:
            cluster_type = _("[单节点]") if mysql.cluster_type == ClusterType.TenDBSingle else _("[高可用]")
            results.append({"id": mysql.id, "display_name": f"{cluster_type}{mysql.immute_domain}"})
        return ListResult(results=results, count=len(results))


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


class RiakClusterResourceProvider(ClusterResourceProvider):
    resource_meta: ResourceMeta = ResourceEnum.RIAK
    cluster_types: ClusterType = [ClusterType.Riak]


class MongoDBClusterResourceProvider(ClusterResourceProvider):
    resource_meta: ResourceMeta = ResourceEnum.MONGODB
    cluster_types: ClusterType = [ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet]

    def _list_instance(self, obj_model: models.Model, condition: Dict, value_list: List[str], page):
        # mongodb资源展示的时候加上类型
        queryset = obj_model.objects.filter(**condition)[page.slice_from : page.slice_to]
        results: List[Dict[str, str]] = []
        for cluster in queryset:
            cluster_type = _("[副本集]") if cluster.cluster_type == ClusterType.MongoReplicaSet else _("[分片集]")
            results.append({"id": cluster.id, "display_name": f"{cluster_type}{cluster.immute_domain}"})
        return ListResult(results=results, count=len(results))
