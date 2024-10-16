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
from typing import Dict, List, Tuple, Union

from django.db import models
from django.utils.translation import ugettext as _
from iam import Resource

from backend.components import DBPrivManagerApi
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
    def batch_create_instances(cls, instance_ids: list, attr=None) -> List[Resource]:
        """
        批量创建resource，默认实现是for调用create_instance，子类可覆写
        :param instance_ids: 实例ID列表
        :param attr: 属性的kv对, 注如果存在拓扑结构则一定加上 _bk_iam_path_ 属性
        """
        resources = [cls.create_instance(instance_id, attr) for instance_id in instance_ids]
        return resources

    @classmethod
    def create_model_instance(
        cls, model: models.Model, instance_id: str, instance: models.Model = None, attr=None
    ) -> Tuple[Resource, models.Model]:
        """
        创建模型实例，即该实例数据是存储在数据库中
        :param model: django模型
        :param instance_id: 实例ID
        :param instance: 实例
        :param attr: 实例属性
        """
        resource = cls._create_simple_instance(instance_id, attr)

        try:
            instance = instance or model.objects.get(pk=instance_id)
        except model.DoesNotExist:
            raise ResourceNotExistError(_("未找到模型[{}]的实例[{}]").format(model.__name__, instance_id))

        display_fields = ResourceEnum.get_resource_by_id(cls.id).display_fields
        instance_name_values = [str(getattr(instance, _field)) for _field in display_fields]
        instance_name = ":".join(instance_name_values)
        # 更新resource的attribute，id和name
        resource.attribute.update(
            {
                cls.attribute: getattr(instance, cls.attribute),
                "id": instance_id,
                "name": instance_name,
            }
        )
        # 默认是一层父类 TODO: 拓扑结构目前是/{resource_type},{resource_id}/
        if cls.parent:
            _bk_iam_path_ = "/{},{}/".format(cls.parent.id, getattr(instance, cls.parent.lookup_field))
            resource.attribute["_bk_iam_path_"] = _bk_iam_path_

        return resource, instance

    @classmethod
    def batch_create_model_instances(
        cls, model: models.Model, instance_ids: list, instance_queryset: models.QuerySet = None, attr: dict = None
    ) -> List[Tuple[Resource, models.Model]]:
        """
        批量创建模型实例
        :param model: django模型
        :param instance_ids: 实例ID列表
        :param instance_queryset: 实例查询集
        :param attr: 实例属性
        """
        instance_tuple_list: List[Tuple[Resource, models.Model]] = []
        instance_queryset = instance_queryset or model.objects.filter(pk__in=instance_ids)
        for instance in instance_queryset:
            instance_tuple_list.append(cls.create_model_instance(model, instance.pk, instance, attr))
        return instance_tuple_list

    @classmethod
    def batch_create_with_iam_path(
        cls, model: models.Model, instance_ids: list, instance_queryset: models.QuerySet = None, attr: dict = None
    ) -> List[Tuple[Resource, models.Model]]:
        """
        批量创建模型实例，带有自定义iam_path
        :param model: django模型
        :param instance_ids: 实例ID列表
        :param instance_queryset: 实例查询集
        :param attr: 实例属性
        """
        if not hasattr(cls, "get_bk_iam_path"):
            raise NotImplementedError
        tuples = cls.batch_create_model_instances(model, instance_ids, instance_queryset, attr)
        resources_tuple_list = []
        for resource, instance in tuples:
            resource.attribute.update(_bk_iam_path_=cls.get_bk_iam_path(instance))
            resources_tuple_list.append((resource, instance))
        return resources_tuple_list

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
class TicketGroupResourceMeta(DBTypeResourceMeta):
    """单据分类的resource 属性定义，与dbtype的唯一区别是多了个'其他'分类"""

    id: str = "ticket_group"
    name: str = _("单据分类")

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        resource = cls._create_simple_instance(instance_id, attr)
        resource.attribute = {"id": str(instance_id), "name": DBType.get_choice_label(instance_id)}
        if instance_id == "other":
            resource.attribute["name"] = _("其他")
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

        resource, instance = cls.create_model_instance(FlowTree, instance_id, attr)
        resource.attribute.update(_bk_iam_path_=cls.get_bk_iam_path(instance))
        return resource

    @classmethod
    def batch_create_instances(cls, instance_ids: list, attr=None) -> List[Resource]:
        from backend.flow.models import FlowTree

        resources = [item[0] for item in cls.batch_create_with_iam_path(FlowTree, instance_ids, attr=attr)]
        return resources

    @classmethod
    def get_bk_iam_path(cls, instance):
        biz_topo = "/{},{}".format(BusinessResourceMeta.id, instance.bk_biz_id)
        group_topo = "/{},{}".format(TicketGroupResourceMeta.id, instance.db_type or "other")
        slash = "/"
        return biz_topo + group_topo + slash

    @classmethod
    def resource_type_chain(cls):
        return [
            {"system_id": BusinessResourceMeta.system_id, "id": BusinessResourceMeta.id},
            {"system_id": TicketGroupResourceMeta.system_id, "id": TicketGroupResourceMeta.id},
            {"system_id": cls.system_id, "id": cls.id},
        ]


@dataclass
class TicketResourceMeta(ResourceMeta):
    """单据resource 属性定义"""

    system_id: str = BK_IAM_SYSTEM_ID
    id: str = "ticket"
    name: str = _("单据")
    selection_mode: str = "all"

    lookup_field: str = "id"
    display_fields: list = ResourceMeta.Field(["id"])
    attribute: str = "creator"
    attribute_display: str = _("创建者")
    parent: ResourceMeta = BusinessResourceMeta()

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        from backend.ticket.models import Ticket

        resource, instance = cls.create_model_instance(Ticket, instance_id, attr)
        resource.attribute.update(_bk_iam_path_=cls.get_bk_iam_path(instance))
        return resource

    @classmethod
    def batch_create_instances(cls, instance_ids: list, attr=None) -> List[Resource]:
        from backend.ticket.models import Ticket

        resources = [item[0] for item in cls.batch_create_with_iam_path(Ticket, instance_ids, attr=attr)]
        return resources

    @classmethod
    def get_bk_iam_path(cls, instance):
        biz_topo = "/{},{}".format(BusinessResourceMeta.id, instance.bk_biz_id)
        group_topo = "/{},{}".format(TicketGroupResourceMeta.id, instance.group or "other")
        slash = "/"
        return biz_topo + group_topo + slash

    @classmethod
    def resource_type_chain(cls):
        return [
            {"system_id": BusinessResourceMeta.system_id, "id": BusinessResourceMeta.id},
            {"system_id": TicketGroupResourceMeta.system_id, "id": TicketGroupResourceMeta.id},
            {"system_id": cls.system_id, "id": cls.id},
        ]


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

    @classmethod
    def batch_create_instances(cls, instance_ids: list, attr=None) -> List[Resource]:
        from backend.db_meta.models.cluster import Cluster

        resources = [item[0] for item in cls.batch_create_model_instances(Cluster, instance_ids, attr=attr)]
        return resources


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
class DorisResourceMeta(ClusterResourceMeta):
    """doris集群resource 属性定义"""

    id: str = "doris"
    name: str = _("DORIS集群")


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
class MongoDBResourceMeta(ClusterResourceMeta):
    """mongodb集群resource 属性定义"""

    id: str = "mongodb"
    name: str = _("Mongodb集群")


@dataclass
class SQLServerResourceMeta(ClusterResourceMeta):
    """sqlserver集群resource 属性定义"""

    id: str = "sqlserver"
    name: str = _("SQLServer集群")


@dataclass
class InstanceResourceMeta(ClusterResourceMeta):
    """实例resource 属性定义"""

    id: str = ""
    name: str = ""
    # 实例默认展示字段为ip:port
    display_fields: list = ResourceMeta.Field(["ip_port"])

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        from backend.db_meta.models.instance import StorageInstance

        resource, __ = cls.create_model_instance(StorageInstance, instance_id, attr)
        return resource

    @classmethod
    def batch_create_instances(cls, instance_ids: list, attr=None) -> List[Resource]:
        from backend.db_meta.models.instance import StorageInstance

        resources = [item[0] for item in cls.batch_create_model_instances(StorageInstance, instance_ids, attr=attr)]
        return resources


@dataclass
class InfluxDBResourceMeta(InstanceResourceMeta):
    """influxdb实例resource 属性定义"""

    id: str = "influxdb"
    name: str = _("InfluxDB实例")


@dataclass
class AccountResourceMeta(ResourceMeta):
    """账号实例resource 属性定义，其他集群的账号资源应该继承此类"""

    id: str = ""
    name: str = ""
    system_id: str = BK_IAM_SYSTEM_ID
    selection_mode: str = "all"

    lookup_field: str = "id"
    display_fields: list = ResourceMeta.Field(["user"])
    attribute: str = "creator"
    attribute_display: str = _("创建者")
    parent: ResourceMeta = BusinessResourceMeta()

    @classmethod
    def create_instance(cls, instance_id: str, account: dict = None, attr=None) -> Resource:
        resource = cls._create_simple_instance(instance_id, attr)
        # 根据账号ID查询单个账号
        instance = account or DBPrivManagerApi.get_account(params={"ids": [int(instance_id)]})["results"][0]
        # 更新resource的attribute，id和name
        _bk_iam_path_ = "/{},{}/".format(cls.parent.id, instance[cls.parent.lookup_field])
        resource.attribute.update(
            {
                cls.attribute: instance["creator"],
                "id": instance["id"],
                "name": instance["user"],
                "_bk_iam_path_": _bk_iam_path_,
            }
        )
        return resource

    @classmethod
    def batch_create_instances(cls, instance_ids: list, attr=None) -> List[Resource]:
        # 批量查询多个账号信息
        accounts = DBPrivManagerApi.get_account(params={"ids": list(map(int, instance_ids))})["results"]
        id__account = {item["id"]: item for item in accounts}
        # 批量创建实例
        resources: List[Resource] = [
            cls.create_instance(id, id__account[id]) for id in instance_ids if id in id__account
        ]
        return resources


@dataclass
class MySQLAccountResourceMeta(AccountResourceMeta):
    """MySQL账号实例resource 属性定义"""

    id: str = "mysql_account"
    name: str = _("MySQL 账号")


@dataclass
class SQLServerAccountResourceMeta(AccountResourceMeta):
    """SQLServer账号实例resource 属性定义"""

    id: str = "sqlserver_account"
    name: str = _("SQLServer 账号")


@dataclass
class MongoDBAccountResourceMeta(AccountResourceMeta):
    """MongoDB账号实例resource 属性定义"""

    id: str = "mongodb_account"
    name: str = _("MongoDB 账号")


@dataclass
class TendbClusterAccountResourceMeta(AccountResourceMeta):
    """Tendb账号实例resource 属性定义"""

    id: str = "tendbcluster_account"
    name: str = _("TendbCluster 账号")


@dataclass
class VmResourceMeta(ClusterResourceMeta):
    """vm集群resource 属性定义"""

    id: str = "vm"
    name: str = _("VM集群")


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
        # TODO: 拓扑结构目前是/{resource_type},{resource_id}/
        biz_topo = "/{},{}".format(BusinessResourceMeta.id, instance.bk_biz_id)
        dbtype_topo = "/{},{}".format(DBTypeResourceMeta.id, instance.db_type)
        slash = "/"
        if not instance.bk_biz_id:
            return dbtype_topo + slash
        else:
            return biz_topo + dbtype_topo + slash

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        from backend.db_monitor.models.alarm import MonitorPolicy

        resource, instance = cls.create_model_instance(MonitorPolicy, instance_id, attr)
        resource.attribute.update(_bk_iam_path_=cls.get_bk_iam_path(instance))
        return resource

    @classmethod
    def batch_create_instances(cls, instance_ids: list, attr=None) -> List[Resource]:
        from backend.db_monitor.models.alarm import MonitorPolicy

        resources = [item[0] for item in cls.batch_create_with_iam_path(MonitorPolicy, instance_ids, attr=attr)]
        return resources

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
class NotifyGroupResourceMeta(ResourceMeta):
    """告警组实例resource 属性定义"""

    system_id: str = BK_IAM_SYSTEM_ID
    id: str = "notify_group"
    name: str = _("告警组")
    selection_mode: str = "all"

    attribute: str = "creator"
    attribute_display: str = _("创建者")
    lookup_field: str = "id"
    display_fields: list = ResourceMeta.Field(["name"])
    parent: ResourceMeta = BusinessResourceMeta()

    @classmethod
    def get_bk_iam_path(cls, instance):
        biz_topo = "/{},{}/".format(BusinessResourceMeta.id, instance.bk_biz_id)
        dbtype_topo = "/{},{}/".format(DBTypeResourceMeta.id, instance.db_type)
        if not instance.bk_biz_id:
            return dbtype_topo
        else:
            return biz_topo

    @classmethod
    def create_instance(cls, instance_id: str, attr=None) -> Resource:
        from backend.db_monitor.models.alarm import NoticeGroup

        resource, instance = cls.create_model_instance(NoticeGroup, instance_id, attr)
        resource.attribute.update(_bk_iam_path_=cls.get_bk_iam_path(instance))
        return resource


@dataclass
class GlobalNotifyGroupResourceMeta(NotifyGroupResourceMeta):
    """标记为全局告警组视图资源"""

    for_select: bool = True
    select_id: str = "global_notify_group"
    name: str = _("全局告警组")

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
    TICKET = TicketResourceMeta()
    MYSQL = MySQLResourceMeta()
    TENDBCLUSTER = TendbClusterResourceMeta()
    REDIS = RedisResourceMeta()
    # INFLUXDB = InfluxDBResourceMeta()
    ES = EsResourceMeta()
    DORIS = DorisResourceMeta()
    KAFKA = KafkaResourceMeta()
    HDFS = HdfsResourceMeta()
    PULSAR = PulsarResourceMeta()
    RIAK = RiakResourceMeta()
    MONGODB = MongoDBResourceMeta()
    SQLSERVER = SQLServerResourceMeta()
    DBTYPE = DBTypeResourceMeta()
    TICKET_GROUP = TicketGroupResourceMeta()
    MONITOR_POLICY = MonitorPolicyResourceMeta()
    GLOBAL_MONITOR_POLICY = GlobalMonitorPolicyResourceMeta()
    NOTIFY_GROUP = NotifyGroupResourceMeta()
    GLOBAL_NOTIFY_GROUP = GlobalNotifyGroupResourceMeta()
    OPENAREA_CONFIG = OpenareaConfigResourceMeta()
    DUMPER_SUBSCRIBE_CONFIG = DumperSubscribeConfigResourceMeta()
    MYSQL_ACCOUNT = MySQLAccountResourceMeta()
    SQLSERVER_ACCOUNT = SQLServerAccountResourceMeta()
    MONGODB_ACCOUNT = MongoDBAccountResourceMeta()
    TENDBCLUSTER_ACCOUNT = TendbClusterAccountResourceMeta()
    VM = VmResourceMeta()

    @classmethod
    def get_resource_by_id(cls, resource_id: Union[ResourceMeta, str]):
        if isinstance(resource_id, ResourceMeta):
            return resource_id
        if resource_id not in _all_resources:
            raise ResourceNotExistError(_("资源类型ID不存在: {}").format(resource_id))

        return _all_resources[resource_id]

    @classmethod
    def cluster_type_to_resource_meta(cls, cluster_type):
        """集群类型与资源的映射"""
        db_type = ClusterType.cluster_type_to_db_type(cluster_type)
        return getattr(cls, db_type.upper(), None)

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
