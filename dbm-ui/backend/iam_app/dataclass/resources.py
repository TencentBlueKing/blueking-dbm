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
from django.utils.translation import gettext as _
from iam import Resource

from backend.components import DBPrivManagerApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import AppCache
from backend.env import BK_IAM_SYSTEM_ID, ENABLE_IAM_V4
from backend.iam_app.constans import COMMON_DB_TYPE, GLOBAL_BIZ_ID_V4, RoleActionLabel
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

    # ---------------- IAM V4 字段 ----------------
    # V4 的资源类型只有 id/name/ancestors 三个字段，其余字段仅在 DBM 本地使用
    ancestors_v4: List["ResourceMeta"] = None  # V4 资源拓扑，从根到直接上级，顶层资源为空
    # 该资源及其关联动作不同步到V4。V4要求祖先链是严格的层级链，多平行父级的资源暂时无法注册
    iamv4_disable: bool = False
    # 该资源不同步到V3，用于V4专有的资源类型
    iamv3_disable: bool = False
    # 资源创建后授予创建者的角色，为空表示不做创建者授权。V4没有属性授权，改为对实例直接授权
    creator_role_v4: RoleActionLabel = None

    def __post_init__(self):
        self.select_id = self.select_id or self.id

    @classmethod
    def Field(cls, value):
        return field(default_factory=lambda: value)

    def _create_simple_instance(self, instance_id: str, attr=None) -> Resource:
        attr = attr or {}
        return Resource(self.system_id, self.id, str(instance_id), attr)

    def create_instance(self, instance_id: str, attr=None) -> Resource:
        """
        创建一个Resource，用于make_request中
        :param instance_id: 实例ID
        :param attr: 属性的kv对, 注如果存在拓扑结构则一定加上 _bk_iam_path_ 属性
        """
        raise NotImplementedError

    def batch_create_instances(self, instance_ids: list, attr=None) -> List[Resource]:
        """
        批量创建resource，默认实现是for调用create_instance，子类可覆写
        :param instance_ids: 实例ID列表
        :param attr: 属性的kv对, 注如果存在拓扑结构则一定加上 _bk_iam_path_ 属性
        """
        resources = [self.create_instance(instance_id, attr) for instance_id in instance_ids]
        return resources

    def create_model_instance(
        self, model: models.Model, instance_id: str, instance: models.Model = None, attr=None
    ) -> Tuple[Resource, models.Model]:
        """
        创建模型实例，即该实例数据是存储在数据库中
        :param model: django模型
        :param instance_id: 实例ID
        :param instance: 实例
        :param attr: 实例属性
        """
        resource = self._create_simple_instance(instance_id, attr)

        try:
            instance = instance or model.objects.get(pk=instance_id)
        except model.DoesNotExist:
            raise ResourceNotExistError(_("未找到模型[{}]的实例[{}]").format(model.__name__, instance_id))

        display_fields = ResourceEnum.get_resource_by_id(self.id).display_fields
        instance_name_values = [str(getattr(instance, _field)) for _field in display_fields]
        instance_name = ":".join(instance_name_values)
        # 更新resource的attribute，id和name
        resource.attribute.update(
            {
                self.attribute: getattr(instance, self.attribute),
                "id": instance_id,
                "name": instance_name,
            }
        )
        # 默认是一层父类 TODO: 拓扑结构目前是/{resource_type},{resource_id}/
        if self.parent:
            _bk_iam_path_ = "/{},{}/".format(self.parent.id, getattr(instance, self.parent.lookup_field))
            resource.attribute["_bk_iam_path_"] = _bk_iam_path_

        return resource, instance

    def batch_create_model_instances(
        self, model: models.Model, instance_ids: list, instance_queryset: models.QuerySet = None, attr: dict = None
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
            instance_tuple_list.append(self.create_model_instance(model, instance.pk, instance, attr))
        return instance_tuple_list

    def batch_create_with_iam_path(
        self, model: models.Model, instance_ids: list, instance_queryset: models.QuerySet = None, attr: dict = None
    ) -> List[Tuple[Resource, models.Model]]:
        """
        批量创建模型实例，带有自定义iam_path
        :param model: django模型
        :param instance_ids: 实例ID列表
        :param instance_queryset: 实例查询集
        :param attr: 实例属性
        """
        if not hasattr(self, "get_bk_iam_path"):
            raise NotImplementedError
        tuples = self.batch_create_model_instances(model, instance_ids, instance_queryset, attr)
        resources_tuple_list = []
        for resource, instance in tuples:
            resource.attribute.update(_bk_iam_path_=self.get_bk_iam_path(instance))
            resources_tuple_list.append((resource, instance))
        return resources_tuple_list

    def to_json(self) -> Dict:
        resource_json = {
            "id": self.id,
            "name": self.name,
            "name_en": self.id,
            "description": self.name,
            "provider_config": {"path": "/apis/iam/resource/"},
            "version": 1,
            "parents": [{"system_id": self.parent.system_id, "id": self.parent.id}] if self.parent else [],
        }
        return resource_json

    def make_ancestor_filter(self, instance_id: str) -> Dict:
        """反向拉取时本资源作为祖先，转换为子资源的数据查询条件。"""
        return {self.lookup_field: instance_id}

    def get_ancestors_v4(self) -> List["ResourceMeta"]:
        """
        获取V4的资源拓扑，顺序为从根到直接上级。
        V4的拓扑与V3的parent/resource_type_chain不通用，只认 ancestors_v4 的显式声明
        """
        return self.ancestors_v4 or []

    def to_json_v4(self) -> Dict:
        """V4的资源类型定义"""
        resource_json = {
            "id": self.id,
            "name": self.name,
            "ancestors": [resource.id for resource in self.get_ancestors_v4()],
        }
        return resource_json

    def make_resource_v4(self, resources: List[Resource]) -> Union[Resource, None]:
        """V4一个动作只关联一个资源类型，默认按类型匹配，需要合成实例的资源类型可覆写"""
        return next((resource for resource in resources if resource.type == self.id), None)


@dataclass
class BusinessResourceMeta(ResourceMeta):
    """业务resource 属性定义"""

    system_id: str = "bk_cmdb"
    id: str = "biz"
    name: str = _("业务")
    selection_mode: str = "instance"

    lookup_field: str = "bk_biz_id"

    def create_instance(self, instance_id: str, attr=None) -> Resource:
        resource = self._create_simple_instance(instance_id, attr)
        try:
            bk_biz_name = AppCache.objects.get(bk_biz_id=instance_id).bk_biz_name
        except AppCache.DoesNotExist:
            bk_biz_name = ""
        resource.attribute = {"id": str(instance_id), "name": str(bk_biz_name)}

        return resource


@dataclass
class DBMBizResourceMeta(ResourceMeta):
    """DBM本地业务resource 属性定义

    V4当前不支持跨系统资源，故预留一份挂在dbm系统下的业务资源，数据源为本地的AppCache。
    资源ID与V3保持一致，使得 _bk_iam_path_ 的拓扑串在两个版本间通用。

    注：V4的资源类型定义与鉴权协议均不带system维度，业务资源直接复用 BUSINESS 即可，
    因此本资源目前不进 _all_resources，仅作为V4支持跨系统资源前的占位。
    """

    system_id: str = BK_IAM_SYSTEM_ID
    id: str = "biz"
    name: str = _("业务")
    selection_mode: str = "instance"

    lookup_field: str = "bk_biz_id"
    display_fields: list = ResourceMeta.Field(["bk_biz_name"])

    @staticmethod
    def get_biz_name(instance_id: str) -> str:
        # 全局资源没有真实业务，统一挂在虚拟业务下
        if str(instance_id) == str(GLOBAL_BIZ_ID_V4):
            return str(_("全局"))
        try:
            return AppCache.objects.get(bk_biz_id=instance_id).bk_biz_name
        except AppCache.DoesNotExist:
            return ""

    def create_instance(self, instance_id: str, attr=None) -> Resource:
        resource = self._create_simple_instance(instance_id, attr)
        resource.attribute = {"id": str(instance_id), "name": str(self.get_biz_name(instance_id))}

        return resource


@dataclass
class DBTypeResourceMeta(ResourceMeta):
    """平台集群类型resource 属性定义"""

    system_id: str = BK_IAM_SYSTEM_ID
    id: str = "dbtype"
    name: str = _("DB类型")
    selection_mode: str = "instance"
    lookup_field: str = "db_type"

    @staticmethod
    def get_display_name(db_type: str) -> str:
        if db_type == COMMON_DB_TYPE:
            return _("通用")
        return DBType.get_choice_label(db_type)

    def create_instance(self, instance_id: str, attr=None) -> Resource:
        resource = self._create_simple_instance(instance_id, attr)
        resource.attribute = {"id": str(instance_id), "name": self.get_display_name(instance_id)}
        return resource


@dataclass
class BizDBTypeResourceMeta(ResourceMeta):
    """业务DB类型resource 属性定义

    V4的一个动作只能关联一个资源类型，无法表达「业务 + DB类型」这种双维度的管控。
    这里把两者合成一个挂在业务下的资源类型，实例ID为 {业务ID}-{DB类型}，
    按业务授权时通过祖先链自动覆盖其下所有DB类型。仅V4使用。
    """

    system_id: str = BK_IAM_SYSTEM_ID
    id: str = "biz_dbtype"
    name: str = _("业务DB类型")
    selection_mode: str = "instance"
    lookup_field: str = "biz_db_type"
    parent: ResourceMeta = field(default_factory=BusinessResourceMeta)

    ancestors_v4: List[ResourceMeta] = ResourceMeta.Field([DBMBizResourceMeta()])
    iamv3_disable: bool = True

    @staticmethod
    def make_instance_id(bk_biz_id: Union[int, str], db_type: str) -> str:
        # DB类型自身含下划线(如 k8s_surrealdb)，用连字符分隔避免解析歧义
        return "{}-{}".format(bk_biz_id, db_type)

    @staticmethod
    def parse_instance_id(instance_id: str) -> Tuple[str, str]:
        bk_biz_id, __, db_type = str(instance_id).partition("-")
        return bk_biz_id, db_type

    def create_instance(self, instance_id: str, attr=None) -> Resource:
        resource = self._create_simple_instance(instance_id, attr)
        bk_biz_id, db_type = self.parse_instance_id(instance_id)
        resource.attribute = {
            "id": str(instance_id),
            "name": str(DBTypeResourceMeta.get_display_name(db_type) or db_type),
            "_bk_iam_path_": "/{},{}/".format(BusinessResourceMeta.id, bk_biz_id),
        }
        return resource

    def make_ancestor_filter(self, instance_id: str) -> Dict:
        """本资源是合成的，作为祖先过滤子资源时要拆回业务与DB类型两个维度"""
        bk_biz_id, db_type = self.parse_instance_id(instance_id)
        return {BusinessResourceMeta.lookup_field: bk_biz_id, DBTypeResourceMeta.lookup_field: db_type}

    def make_resource_v4(self, resources: List[Resource]) -> Union[Resource, None]:
        """上层仍按V3传入业务与DB类型两个实例，这里合成V4的单个资源实例"""
        biz = next((item for item in resources if item.type == BusinessResourceMeta.id), None)
        db_type = next((item for item in resources if item.type == DBTypeResourceMeta.id), None)
        if not biz or not db_type:
            return None
        return self.create_instance(self.make_instance_id(biz.id, db_type.id))


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
    parent: ResourceMeta = field(default_factory=BusinessResourceMeta)

    # V3挂在单据分类下，V4的单据分类没有业务维度，改挂业务DB类型
    ancestors_v4: List[ResourceMeta] = ResourceMeta.Field([DBMBizResourceMeta(), BizDBTypeResourceMeta()])

    def create_instance(self, instance_id: str, attr=None) -> Resource:
        from backend.flow.models import FlowTree

        resource, instance = self.create_model_instance(FlowTree, instance_id, attr)
        resource.attribute.update(_bk_iam_path_=self.get_bk_iam_path(instance))
        return resource

    def batch_create_instances(self, instance_ids: list, attr=None) -> List[Resource]:
        from backend.flow.models import FlowTree

        resources = [item[0] for item in self.batch_create_with_iam_path(FlowTree, instance_ids, attr=attr)]
        return resources

    def get_bk_iam_path(self, instance):
        return TicketResourceMeta.make_iam_path(instance.bk_biz_id, instance.db_type)

    def resource_type_chain(self):
        return [
            {"system_id": BusinessResourceMeta.system_id, "id": BusinessResourceMeta.id},
            {"system_id": DBTypeResourceMeta.system_id, "id": DBTypeResourceMeta.id},
            {"system_id": self.system_id, "id": self.id},
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
    parent: ResourceMeta = field(default_factory=BusinessResourceMeta)

    # V3挂在单据分类下，V4的单据分类没有业务维度，改挂业务DB类型
    ancestors_v4: List[ResourceMeta] = ResourceMeta.Field([DBMBizResourceMeta(), BizDBTypeResourceMeta()])

    def create_instance(self, instance_id: str, attr=None) -> Resource:
        from backend.ticket.models import Ticket

        resource, instance = self.create_model_instance(Ticket, instance_id, attr)
        resource.attribute.update(_bk_iam_path_=self.get_bk_iam_path(instance))
        return resource

    def batch_create_instances(self, instance_ids: list, attr=None) -> List[Resource]:
        from backend.ticket.models import Ticket

        resources = [item[0] for item in self.batch_create_with_iam_path(Ticket, instance_ids, attr=attr)]
        return resources

    @staticmethod
    def make_iam_path(bk_biz_id: Union[int, str], db_type: str) -> str:
        """
        单据与任务流程的拓扑路径，无DB类型的归入通用。
        V3挂在全局的DB类型下，V4挂在业务DB类型下
        """
        db_type = db_type or COMMON_DB_TYPE
        if ENABLE_IAM_V4:
            child_topo = "{},{}".format(
                BizDBTypeResourceMeta.id, BizDBTypeResourceMeta.make_instance_id(bk_biz_id, db_type)
            )
        else:
            child_topo = "{},{}".format(DBTypeResourceMeta.id, db_type)
        return "/{},{}/{}/".format(BusinessResourceMeta.id, bk_biz_id, child_topo)

    def get_bk_iam_path(self, instance):
        return TicketResourceMeta.make_iam_path(instance.bk_biz_id, instance.group)

    def resource_type_chain(self):
        return [
            {"system_id": BusinessResourceMeta.system_id, "id": BusinessResourceMeta.id},
            {"system_id": DBTypeResourceMeta.system_id, "id": DBTypeResourceMeta.id},
            {"system_id": self.system_id, "id": self.id},
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
    parent: ResourceMeta = field(default_factory=BusinessResourceMeta)

    ancestors_v4: List[ResourceMeta] = ResourceMeta.Field([DBMBizResourceMeta()])

    def create_instance(self, instance_id: str, attr=None) -> Resource:
        from backend.db_meta.models.cluster import Cluster

        resource, __ = self.create_model_instance(Cluster, instance_id, attr)
        return resource

    def batch_create_instances(self, instance_ids: list, attr=None) -> List[Resource]:
        from backend.db_meta.models.cluster import Cluster

        resources = [item[0] for item in self.batch_create_model_instances(Cluster, instance_ids, attr=attr)]
        return resources


@dataclass
class MySQLResourceMeta(ClusterResourceMeta):
    """mysql集群resource 属性定义"""

    id: str = "mysql"
    name: str = _("MySQL集群")
    creator_role_v4: RoleActionLabel = RoleActionLabel.MYSQL_CREATOR


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
class OracleResourceMeta(ClusterResourceMeta):
    """oracle集群resource 属性定义"""

    id: str = "oracle"
    name: str = _("Oracle集群")


@dataclass
class InstanceResourceMeta(ClusterResourceMeta):
    """实例resource 属性定义"""

    id: str = ""
    name: str = ""
    # 实例默认展示字段为ip:port
    display_fields: list = ResourceMeta.Field(["ip_port"])

    def create_instance(self, instance_id: str, attr=None) -> Resource:
        from backend.db_meta.models.instance import StorageInstance

        resource, __ = self.create_model_instance(StorageInstance, instance_id, attr)
        return resource

    def batch_create_instances(self, instance_ids: list, attr=None) -> List[Resource]:
        from backend.db_meta.models.instance import StorageInstance

        resources = [item[0] for item in self.batch_create_model_instances(StorageInstance, instance_ids, attr=attr)]
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
    parent: ResourceMeta = field(default_factory=BusinessResourceMeta)

    ancestors_v4: List[ResourceMeta] = ResourceMeta.Field([DBMBizResourceMeta()])

    def create_instance(self, instance_id: str, account: dict = None, attr=None) -> Resource:
        resource = self._create_simple_instance(instance_id, attr)
        # 根据账号ID查询单个账号
        instance = account or DBPrivManagerApi.get_account(params={"ids": [int(instance_id)]})["results"][0]
        # 更新resource的attribute，id和name
        _bk_iam_path_ = "/{},{}/".format(self.parent.id, instance[self.parent.lookup_field])
        resource.attribute.update(
            {
                self.attribute: instance["creator"],
                "id": instance["id"],
                "name": instance["user"],
                "_bk_iam_path_": _bk_iam_path_,
            }
        )
        return resource

    def batch_create_instances(self, instance_ids: list, attr=None) -> List[Resource]:
        # 批量查询多个账号信息
        accounts = DBPrivManagerApi.get_account(params={"ids": list(map(int, instance_ids))})["results"] or []
        id__account = {item["id"]: item for item in accounts}
        # 批量创建实例
        resources: List[Resource] = [
            self.create_instance(id, id__account[id]) for id in instance_ids if id in id__account
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
class K8sSurrealResourceMeta(ClusterResourceMeta):
    """k8s SurrealDB 集群 resource 属性定义"""

    id: str = "k8s_surrealdb"
    name: str = _("K8s SurrealDB集群")


@dataclass
class K8sVictoriametricsResourceMeta(ClusterResourceMeta):
    """k8s VictoriaMetrics 集群 resource 属性定义"""

    id: str = "k8s_victoriametrics"
    name: str = _("K8s VictoriaMetrics集群")


@dataclass
class K8sRisingwaveResourceMeta(ClusterResourceMeta):
    """k8s Risingwave 集群 resource 属性定义"""

    id: str = "k8s_risingwave"
    name: str = _("K8s Risingwave集群")


@dataclass
class K8sMilvusResourceMeta(ClusterResourceMeta):
    """k8s Milvus 集群 resource 属性定义"""

    id: str = "k8s_milvus"
    name: str = _("K8s Milvus集群")


@dataclass
class K8sQdrantResourceMeta(ClusterResourceMeta):
    """k8s Qdrant 集群 resource 属性定义"""

    id: str = "k8s_qdrant"
    name: str = _("K8s Qdrant集群")


@dataclass
class K8sGreptimedbResourceMeta(ClusterResourceMeta):
    """k8s GreptimeDB 集群 resource 属性定义"""

    id: str = "k8s_greptimedb"
    name: str = _("K8s GreptimeDB集群")


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
    parent: ResourceMeta = field(default_factory=BusinessResourceMeta)
    # dbtype 是顶层资源，无法作为 biz 的下一级，该拓扑暂时无法在V4注册
    ancestors_v4: List[ResourceMeta] = ResourceMeta.Field([DBMBizResourceMeta(), DBTypeResourceMeta()])
    iamv4_disable: bool = True

    def get_bk_iam_path(self, instance):
        # TODO: 拓扑结构目前是/{resource_type},{resource_id}/
        biz_topo = "/{},{}".format(BusinessResourceMeta.id, instance.bk_biz_id)
        dbtype_topo = "/{},{}".format(DBTypeResourceMeta.id, instance.db_type)
        slash = "/"
        if not instance.bk_biz_id:
            return dbtype_topo + slash
        else:
            return biz_topo + dbtype_topo + slash

    def create_instance(self, instance_id: str, attr=None) -> Resource:
        from backend.db_monitor.models.alarm import MonitorPolicy

        resource, instance = self.create_model_instance(MonitorPolicy, instance_id, attr)
        resource.attribute.update(_bk_iam_path_=self.get_bk_iam_path(instance))
        return resource

    def batch_create_instances(self, instance_ids: list, attr=None) -> List[Resource]:
        from backend.db_monitor.models.alarm import MonitorPolicy

        resources = [item[0] for item in self.batch_create_with_iam_path(MonitorPolicy, instance_ids, attr=attr)]
        return resources

    def resource_type_chain(self):
        return [
            {"system_id": BusinessResourceMeta.system_id, "id": BusinessResourceMeta.id},
            {"system_id": DBTypeResourceMeta.system_id, "id": DBTypeResourceMeta.id},
            {"system_id": self.system_id, "id": self.id},
        ]


@dataclass
class GlobalMonitorPolicyResourceMeta(MonitorPolicyResourceMeta):
    """标记为全局监控策略视图资源"""

    for_select: bool = True
    select_id: str = "global_monitor_policy"
    name: str = _("全局监控策略")

    def instance_selection(self):
        return {
            "id": f"{self.select_id}_list",
            "name": _("{} 列表".format(self.name)),
            "name_en": f"{self.select_id} list",
            "resource_type_chain": [
                {"system_id": DBTypeResourceMeta.system_id, "id": DBTypeResourceMeta.id},
                {"system_id": self.system_id, "id": self.id},
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
    parent: ResourceMeta = field(default_factory=BusinessResourceMeta)
    # V3下告警组按是否有业务在biz/dbtype两条拓扑间切换，V4只能声明一条静态链路，故统一取两者
    # dbtype 是顶层资源，无法作为 biz 的下一级，该拓扑暂时无法在V4注册
    ancestors_v4: List[ResourceMeta] = ResourceMeta.Field([DBMBizResourceMeta(), DBTypeResourceMeta()])
    iamv4_disable: bool = True

    def get_bk_iam_path(self, instance):
        biz_topo = "/{},{}/".format(BusinessResourceMeta.id, instance.bk_biz_id)
        dbtype_topo = "/{},{}/".format(DBTypeResourceMeta.id, instance.db_type)
        if not instance.bk_biz_id:
            return dbtype_topo
        else:
            return biz_topo

    def create_instance(self, instance_id: str, attr=None) -> Resource:
        from backend.db_monitor.models.alarm import NoticeGroup

        resource, instance = self.create_model_instance(NoticeGroup, instance_id, attr)
        resource.attribute.update(_bk_iam_path_=self.get_bk_iam_path(instance))
        return resource


@dataclass
class GlobalNotifyGroupResourceMeta(NotifyGroupResourceMeta):
    """标记为全局告警组视图资源"""

    for_select: bool = True
    select_id: str = "global_notify_group"
    name: str = _("全局告警组")

    def instance_selection(self):
        return {
            "id": f"{self.select_id}_list",
            "name": _("{} 列表".format(self.name)),
            "name_en": f"{self.select_id} list",
            "resource_type_chain": [
                {"system_id": DBTypeResourceMeta.system_id, "id": DBTypeResourceMeta.id},
                {"system_id": self.system_id, "id": self.id},
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
    parent: ResourceMeta = field(default_factory=BusinessResourceMeta)
    ancestors_v4: List[ResourceMeta] = ResourceMeta.Field([DBMBizResourceMeta()])

    def create_instance(self, instance_id: str, attr=None) -> Resource:
        from backend.db_services.mysql.open_area.models import TendbOpenAreaConfig

        resource, __ = self.create_model_instance(TendbOpenAreaConfig, instance_id, attr)
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
    parent: ResourceMeta = field(default_factory=BusinessResourceMeta)
    ancestors_v4: List[ResourceMeta] = ResourceMeta.Field([DBMBizResourceMeta()])

    def create_instance(self, instance_id: str, attr=None) -> Resource:
        from backend.db_services.mysql.dumper.models import DumperSubscribeConfig

        resource, __ = self.create_model_instance(DumperSubscribeConfig, instance_id, attr)
        return resource


class ResourceEnum:
    """
    resource 枚举类
    """

    BUSINESS = BusinessResourceMeta()
    DBMBIZ = DBMBizResourceMeta()
    BIZ_DBTYPE = BizDBTypeResourceMeta()
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
    ORACLE = OracleResourceMeta()
    DBTYPE = DBTypeResourceMeta()
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
    K8S_SURREALDB = K8sSurrealResourceMeta()
    K8S_VICTORIAMETRICS = K8sVictoriametricsResourceMeta()
    K8S_RISINGWAVE = K8sRisingwaveResourceMeta()
    K8S_MILVUS = K8sMilvusResourceMeta()
    K8S_QDRANT = K8sQdrantResourceMeta()
    K8S_GREPTIMEDB = K8sGreptimedbResourceMeta()

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
        try:
            db_type = ClusterType.cluster_type_to_db_type(cluster_type)
        except ValueError:
            return None
        return getattr(cls, db_type.upper(), None)

    @classmethod
    def instance_type_to_resource_meta(cls, instance_role):
        """实例类型与资源的映射"""
        if instance_role == InstanceRole.INFLUXDB:
            return cls.INFLUXDB


def _is_registered_resource(resource: ResourceMeta) -> bool:
    """
    资源是否纳入资源字典。DBMBIZ 与 BUSINESS 共用 biz 这个ID，只能二选一：
    V4不支持跨系统资源，业务资源用挂在dbm下的 DBMBIZ；V3 仍用 cmdb 的 BUSINESS。
    """
    if resource.for_select:
        return False
    return resource is not (ResourceEnum.BUSINESS if ENABLE_IAM_V4 else ResourceEnum.DBMBIZ)


_all_resources = {
    resource.id: resource
    for resource in ResourceEnum.__dict__.values()
    if isinstance(resource, ResourceMeta) and _is_registered_resource(resource)
}

_extra_instance_selections = [
    resource
    for resource in ResourceEnum.__dict__.values()
    if isinstance(resource, ResourceMeta) and resource.for_select
]
