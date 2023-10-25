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
import abc
from dataclasses import dataclass, field
from typing import Dict, Tuple, Union

from django.db import models
from django.utils.translation import ugettext as _
from iam import Resource

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import AppCache
from backend.env import BK_IAM_SYSTEM_ID
from backend.iam_app.exceptions import ResourceNotExistError


@dataclass
class ResourceMeta(metaclass=abc.ABCMeta):
    """resource 属性定义"""

    system_id: str  # 系统ID
    id: str  # 资源ID
    name: str = ""  # 资源名
    selection_mode: str = ""  # 资源作用范围

    attribute: str = ""  # 资源属性
    attribute_display: str = ""  # 资源属性展示
    lookup_field: str = ""  # 资源在model中的查询字段
    display_fields: list = None  # 资源在model中的展示字段
    parent: "ResourceMeta" = None  # 资源父类

    for_select: bool = False  # 标识仅作为实例视图
    select_id: str = ""  # 资源实例视图ID

    def __post_init__(self):
        self.select_id = self.select_id or self.id

    @classmethod
    def Field(cls, value):
        return field(default_factory=lambda: value)

    @classmethod
    def _create_simple_instance(cls, instance_id: str, attr=None) -> Resource:
        attr = attr or {}
        return Resource(cls.system_id, cls.id, str(instance_id), attr)

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        """
        创建一个Resource，用于make_request中
        :param instance_id: 实例ID
        :param attr: 属性的kv对, 注如果存在拓扑结构则一定加上 _bk_iam_path_ 属性
        """
        raise NotImplementedError

    @classmethod
    def create_model_instance(cls, model: models.Model, instance_id: str, attr=None) -> Tuple[Resource, models.Model]:
        resource = cls._create_simple_instance(instance_id, attr)
        instance_queryset = model.objects.filter(pk=instance_id)

        if not instance_queryset.count():
            return resource, None

        display_fields = ResourceEnum.get_resource_by_id(cls.id).display_fields
        instance_name_values = instance_queryset.values(*display_fields)[0]
        instance_name = ":".join([str(instance_name_values[_field]) for _field in display_fields])
        instance = instance_queryset[0]
        # 更新resource的attribute，id和name
        resource.attribute.update(
            {
                cls.attribute: getattr(instance, cls.attribute),
                "id": instance_id,
                "name": instance_name,
            }
        )

        if cls.parent:
            # 默认是一层父类
            _bk_iam_path_ = "/{},{},{}/".format(
                cls.parent.system_id, cls.parent.id, getattr(instance, cls.parent.lookup_field)
            )
            resource.attribute["_bk_iam_path_"] = _bk_iam_path_

        return resource, instance

    @classmethod
    def to_json(cls) -> Dict:
        resource_json = {
            "id": cls.id,
            "name": cls.name,
            "name_en": cls.id,
            "description": cls.name,
            "provider_config": {"path": "/apis/iam/resource/"},
            "version": 1,
            "parents": [{"system_id": cls.parent.system_id, "id": cls.parent.id}] if cls.parent else [],
        }
        return resource_json


@dataclass
class BusinessResourceMeta(ResourceMeta):
    """业务resource 属性定义"""

    system_id: str = "bk_cmdb"
    id: str = "biz"
    name: str = _("业务")
    selection_mode: str = "instance"

    lookup_field: str = "bk_biz_id"

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        resource = cls._create_simple_instance(instance_id, attr)
        try:
            bk_biz_name = AppCache.objects.get(bk_biz_id=instance_id).bk_biz_name
        except AppCache.DoesNotExist:
            bk_biz_name = ""
        resource.attribute = {"id": str(instance_id), "name": str(bk_biz_name)}

        return resource


@dataclass
class DBTypeResourceMeta(ResourceMeta):
    """平台集群类型resource 属性定义"""

    system_id: str = BK_IAM_SYSTEM_ID
    id: str = "dbtype"
    name: str = _("DB类型")
    selection_mode: str = "instance"
    lookup_field: str = "db_type"

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        resource = cls._create_simple_instance(instance_id, attr)
        resource.attribute = {"id": str(instance_id), "name": DBType.get_choice_label(instance_id)}
        return resource


@dataclass
class TaskFlowResourceMeta(ResourceMeta):
    """任务流程resource 属性定义"""

    system_id: str = BK_IAM_SYSTEM_ID
    id: str = "flow"
    name: str = _("任务流程")
    selection_mode: str = "all"

    lookup_field: str = "root_id"
    display_fields: list = ResourceMeta.Field(["root_id"])
    attribute: str = "created_by"
    attribute_display: str = _("创建者")
    parent: ResourceMeta = BusinessResourceMeta()

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        from backend.flow.models import FlowTree

        resource, __ = cls.create_model_instance(FlowTree, instance_id, attr)
        return resource


@dataclass
class ClusterResourceMeta(ResourceMeta):
    """集群资源resource 通用属性定义"""

    id: str = ""
    name: str = ""
    system_id: str = BK_IAM_SYSTEM_ID
    selection_mode: str = "all"

    lookup_field: str = "id"
    display_fields: list = ResourceMeta.Field(["immute_domain"])
    attribute: str = "creator"
    attribute_display: str = _("创建者")
    parent: ResourceMeta = BusinessResourceMeta()

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        from backend.db_meta.models.cluster import Cluster

        resource, __ = cls.create_model_instance(Cluster, instance_id, attr)
        return resource


@dataclass
class MySQLResourceMeta(ClusterResourceMeta):
    """mysql集群resource 属性定义"""

    id: str = "mysql"
    name: str = _("MySQL集群")


@dataclass
class TendbClusterResourceMeta(ClusterResourceMeta):
    """tendbcluster集群resource 属性定义"""

    id: str = "tendbcluster"
    name: str = _("TendbCluster集群")


@dataclass
class RedisResourceMeta(ClusterResourceMeta):
    """redis集群resource 属性定义"""

    id: str = "redis"
    name: str = _("Redis集群")


@dataclass
class EsResourceMeta(ClusterResourceMeta):
    """es集群resource 属性定义"""

    id: str = "es"
    name: str = _("ES集群")


@dataclass
class KafkaResourceMeta(ClusterResourceMeta):
    """kafka集群resource 属性定义"""

    id: str = "kafka"
    name: str = _("Kafka集群")


@dataclass
class HdfsResourceMeta(ClusterResourceMeta):
    """hdfs集群resource 属性定义"""

    id: str = "hdfs"
    name: str = _("HDFS集群")


@dataclass
class PulsarResourceMeta(ClusterResourceMeta):
    """pulsar集群resource 属性定义"""

    id: str = "pulsar"
    name: str = _("Pulsar集群")


@dataclass
class RiakResourceMeta(ClusterResourceMeta):
    """riak集群resource 属性定义"""

    id: str = "riak"
    name: str = _("Riak集群")


@dataclass
class InstanceResourceMeta(ClusterResourceMeta):
    """实例resource 属性定义"""

    id: str = ""
    name: str = ""
    # 实例默认展示字段为ip:port
    display_fields: list = ResourceMeta.Field(["machine__ip", "port"])

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        from backend.db_meta.models.instance import StorageInstance

        resource, __ = cls.create_model_instance(StorageInstance, instance_id, attr)
        return resource


@dataclass
class InfluxDBResourceMeta(InstanceResourceMeta):
    """influxdb实例resource 属性定义"""

    id: str = "influxdb"
    name: str = _("InfluxDB实例")


@dataclass
class MonitorPolicyResourceMeta(ResourceMeta):
    """监控策略实例resource 属性定义"""

    system_id: str = BK_IAM_SYSTEM_ID
    id: str = "monitor_policy"
    name: str = _("监控策略")
    selection_mode: str = "all"

    attribute: str = "creator"
    attribute_display: str = _("创建者")
    lookup_field: str = "id"
    display_fields: list = ResourceMeta.Field(["name"])
    parent: ResourceMeta = BusinessResourceMeta()

    @classmethod
    def get_bk_iam_path(cls, instance):
        biz_topo = "/{},{},{}".format(BusinessResourceMeta.system_id, BusinessResourceMeta.id, instance.bk_biz_id)
        dbtype_topo = "/{},{},{}".format(DBTypeResourceMeta.system_id, DBTypeResourceMeta.id, instance.db_type)
        slash = "/"
        if not instance.bk_biz_id:
            return dbtype_topo + slash
        else:
            return biz_topo + dbtype_topo + slash

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        from backend.db_monitor.models.alarm import MonitorPolicy

        resource, instance = cls.create_model_instance(MonitorPolicy, instance_id, attr)
        resource.attribute = {"id": str(instance_id), "name": instance.name, "creator": instance.creator}
        resource.attribute.update(_bk_iam_path_=cls.get_bk_iam_path(instance))
        return resource

    @classmethod
    def resource_type_chain(cls):
        return [
            {"system_id": BusinessResourceMeta.system_id, "id": BusinessResourceMeta.id},
            {"system_id": DBTypeResourceMeta.system_id, "id": DBTypeResourceMeta.id},
            {"system_id": cls.system_id, "id": cls.id},
        ]


@dataclass
class GlobalMonitorPolicyResourceMeta(MonitorPolicyResourceMeta):
    """标记为全局监控策略视图资源"""

    for_select: bool = True
    select_id: str = "global_monitor_policy"
    name: str = _("全局监控策略")

    @classmethod
    def instance_selection(cls):
        return {
            "id": f"{cls.select_id}_list",
            "name": _("{} 列表".format(cls.name)),
            "name_en": f"{cls.select_id} list",
            "resource_type_chain": [
                {"system_id": DBTypeResourceMeta.system_id, "id": DBTypeResourceMeta.id},
                {"system_id": cls.system_id, "id": cls.id},
            ],
        }


@dataclass
class DutyRuleResourceMeta(ResourceMeta):
    """监控策略实例resource 属性定义"""

    system_id: str = BK_IAM_SYSTEM_ID
    id: str = "duty_rule"
    name: str = _("轮值策略")
    selection_mode: str = "all"

    attribute: str = "creator"
    attribute_display: str = _("创建者")
    lookup_field: str = "id"
    display_fields: list = ResourceMeta.Field(["name"])
    parent: ResourceMeta = DBTypeResourceMeta()

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        from backend.db_monitor.models.alarm import DutyRule

        resource, __ = cls.create_model_instance(DutyRule, instance_id, attr)
        return resource


@dataclass
class OpenareaConfigResourceMeta(ResourceMeta):
    """开区模板实例resource 属性定义"""

    system_id: str = BK_IAM_SYSTEM_ID
    id: str = "openarea_config"
    name: str = _("开区模板")
    selection_mode: str = "all"

    attribute: str = "creator"
    attribute_display: str = _("创建者")
    lookup_field: str = "id"
    display_fields: list = ResourceMeta.Field(["cluster_type", "config_name"])
    parent: ResourceMeta = BusinessResourceMeta()

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        from backend.db_services.mysql.open_area.models import TendbOpenAreaConfig

        resource, __ = cls.create_model_instance(TendbOpenAreaConfig, instance_id, attr)
        return resource


@dataclass
class DumperSubscribeConfigResourceMeta(ResourceMeta):
    """数据订阅规则实例resource 属性定义"""

    system_id: str = BK_IAM_SYSTEM_ID
    id: str = "dumper_subscribe_config"
    name: str = _("数据订阅规则")
    selection_mode: str = "all"

    attribute: str = "creator"
    attribute_display: str = _("创建者")
    lookup_field: str = "id"
    display_fields: list = ResourceMeta.Field(["name"])
    parent: ResourceMeta = BusinessResourceMeta()

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        from backend.db_services.mysql.dumper.models import DumperSubscribeConfig

        resource, __ = cls.create_model_instance(DumperSubscribeConfig, instance_id, attr)
        return resource


class ResourceEnum:
    """
    resource 枚举类
    """

    BUSINESS = BusinessResourceMeta()
    TASKFLOW = TaskFlowResourceMeta()
    MYSQL = MySQLResourceMeta()
    TENDBCLUSTER = TendbClusterResourceMeta()
    REDIS = RedisResourceMeta()
    INFLUXDB = InfluxDBResourceMeta()
    ES = EsResourceMeta()
    KAFKA = KafkaResourceMeta()
    HDFS = HdfsResourceMeta()
    PULSAR = PulsarResourceMeta()
    RIAK = RiakResourceMeta()
    DBTYPE = DBTypeResourceMeta()
    MONITOR_POLICY = MonitorPolicyResourceMeta()
    GLOBAL_MONITOR_POLICY = GlobalMonitorPolicyResourceMeta()
    DUTY_RULE = DutyRuleResourceMeta()
    OPENAREA_CONFIG = OpenareaConfigResourceMeta()
    DUMPER_SUBSCRIBE_CONFIG = DumperSubscribeConfigResourceMeta()

    @classmethod
    def get_resource_by_id(cls, resource_id: Union[ResourceMeta, str]):
        if isinstance(resource_id, ResourceMeta):
            return resource_id
        if resource_id in cls.__dict__:
            return cls.__dict__[resource_id]
        if resource_id in _all_resources:
            return _all_resources[resource_id]

        raise ResourceNotExistError(_("资源类型ID不存在: {}").format(resource_id))

    @classmethod
    def cluster_type_to_resource_meta(cls, cluster_type):
        """集群类型与资源的映射"""
        if cluster_type in [ClusterType.TenDBSingle, ClusterType.TenDBHA]:
            return cls.MYSQL
        if cluster_type in ClusterType.redis_cluster_types():
            return cls.REDIS
        return getattr(cls, cluster_type.upper())

    @classmethod
    def instance_type_to_resource_meta(cls, instance_role):
        """实例类型与资源的映射"""
        if instance_role == InstanceRole.INFLUXDB:
            return cls.INFLUXDB


_all_resources = {
    resource.id: resource
    for resource in ResourceEnum.__dict__.values()
    if isinstance(resource, ResourceMeta) and not resource.for_select
}

_extra_instance_selections = [
    resource
    for resource in ResourceEnum.__dict__.values()
    if isinstance(resource, ResourceMeta) and resource.for_select
]
