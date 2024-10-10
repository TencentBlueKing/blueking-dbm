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
import re

from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.components import CCApi
from backend.constants import IP_PORT_DIVIDER, IP_PORT_RE_PATTERN
from backend.db_dirty.models import DirtyMachine
from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_services.dbbase.constants import ResourceType
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.db_services.redis.resources.redis_cluster.query import RedisListRetrieveResource
from backend.dbm_init.constants import CC_APP_ABBR_ATTR
from backend.ticket.constants import TicketType


class IsClusterDuplicatedSerializer(serializers.Serializer):
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    name = serializers.CharField(help_text=_("集群名"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))


class IsClusterDuplicatedResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": {"is_duplicated": True}}


class QueryAllTypeClusterSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_types = serializers.CharField(help_text=_("集群类型(逗号分隔)"), required=False)
    immute_domain = serializers.CharField(help_text=_("集群域名"), required=False)
    # 额外过滤参数
    phase = serializers.ChoiceField(help_text=_("集群阶段状态"), required=False, choices=ClusterPhase.get_choices())

    def get_conditions(self, attr):
        conditions = {"bk_biz_id": attr["bk_biz_id"]}
        if attr.get("cluster_types"):
            conditions["cluster_type__in"] = attr["cluster_types"].split(",")
        if attr.get("immute_domain"):
            conditions["immute_domain__icontains"] = attr["immute_domain"]
        # 额外过滤参数
        if attr.get("phase"):
            conditions["phase"] = attr["phase"]
        return conditions


class QueryAllTypeClusterResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": [{"id": 47, "immute_domain": "mysql.dba.db.com"}]}


class CommonQueryClusterSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_types = serializers.CharField(help_text=_("集群类型(逗号分隔)"))
    cluster_ids = serializers.CharField(help_text=_("集群ID(逗号分割)"), required=False, default="")

    def validate(self, attrs):
        attrs["cluster_types"] = attrs["cluster_types"].split(",")
        attrs["cluster_ids"] = attrs["cluster_ids"].split(",") if attrs["cluster_ids"] else []
        return attrs


class CommonQueryClusterResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": []}


class ClusterFilterSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    exact_domain = serializers.CharField(help_text=_("域名精确查询(逗号分割)"), required=False, default="")
    cluster_ids = serializers.CharField(help_text=_("集群ID(逗号分割)"), required=False, default="")

    # 后续有其他过滤条件可以再加
    cluster_type = serializers.CharField(help_text=_("集群类型"), required=False)
    instance = serializers.CharField(help_text=_("实例查询(逗号分割)"), required=False, default="")

    def validate(self, attrs):
        cluster_ids = attrs["cluster_ids"].split(",") if attrs["cluster_ids"] else []
        exact_domains = attrs["exact_domain"].split(",") if attrs["exact_domain"] else []
        instances = attrs["instance"].split(",") if attrs["instance"] else []
        filters = Q(bk_biz_id=attrs["bk_biz_id"])
        filters &= Q(id__in=cluster_ids) if cluster_ids else Q()
        filters &= Q(immute_domain__in=exact_domains) if exact_domains else Q()
        filters &= Q(cluster_type=attrs["cluster_type"]) if attrs.get("cluster_type") else Q()
        instance_filters = Q()
        for instance in instances:
            if re.compile(IP_PORT_RE_PATTERN).match(instance):
                ip, port = instance.split(IP_PORT_DIVIDER)
                instance_filter = Q(storageinstance__machine__ip=ip, storageinstance__port=port) | Q(
                    proxyinstance__machine__ip=ip, proxyinstance__port=port
                )
                instance_filters |= instance_filter
        filters &= instance_filters
        attrs["filters"] = filters
        return attrs


class QueryBizClusterAttrsSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_type = serializers.CharField(help_text=_("集群类型"))
    cluster_attrs = serializers.CharField(help_text=_("查询集群属性字段(逗号分隔)"), default="")
    instances_attrs = serializers.CharField(help_text=_("查询实例属性字段(逗号分隔)"), default="")

    def validate_cluster_type(self, value):
        cluster_types = [ct.strip() for ct in value.split(",")]
        db_type_set = set()
        # 检查特殊case 'redis'
        if all(ct == "redis" for ct in cluster_types):
            return RedisListRetrieveResource.cluster_types
        for cluster_type in cluster_types:
            normalized_type = ClusterType.cluster_type_to_db_type(cluster_type)
            if not normalized_type:
                raise serializers.ValidationError(_("未知的集群类型：{}".format(cluster_type)))
            db_type_set.add(normalized_type)
        if len(db_type_set) > 1:
            raise serializers.ValidationError(_("所有集群类型必须属于同一种DBtype类型"))
        return cluster_types

    def validate(self, attrs):
        attrs["cluster_attrs"] = attrs["cluster_attrs"].split(",") if attrs["cluster_attrs"] else []
        attrs["instances_attrs"] = attrs["instances_attrs"].split(",") if attrs["instances_attrs"] else []
        return attrs


class ResourceAdministrationSerializer(serializers.Serializer):
    resource_type = serializers.ChoiceField(help_text=_("服务类型"), choices=ResourceType.get_choices())

    def to_representation(self, instance):
        resource_type = instance.get("resource_type")
        # 污点主机
        if resource_type == ResourceType.SPOTTY_HOST:
            cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
            bk_cloud_ids = DirtyMachine.objects.values_list("bk_cloud_id", flat=True).distinct()
            bk_cloud_id_list = [
                {"value": bk_cloud_id, "text": cloud_info.get(str(bk_cloud_id), {}).get("bk_cloud_name", "")}
                for bk_cloud_id in bk_cloud_ids
            ]
            # 业务信息
            biz_infos = CCApi.search_business(
                {
                    "fields": ["bk_biz_id", "bk_biz_name", CC_APP_ABBR_ATTR],
                },
                use_admin=True,
            ).get("info", [])
            # 构建一个以业务ID为键的字典，便于快速查找
            biz_info_dict = {biz_info["bk_biz_id"]: biz_info for biz_info in biz_infos}
            # 从DirtyMachine模型获取去重后的业务ID列表
            bk_biz_ids = list(DirtyMachine.objects.values_list("bk_biz_id", flat=True).distinct())
            # 构建结果列表,直接从字典中查找匹配的业务信息
            bk_biz_id_list = [
                {"value": bk_biz_id, "text": biz_info_dict[bk_biz_id]["bk_biz_name"]}
                for bk_biz_id in bk_biz_ids
                if bk_biz_id in biz_info_dict
            ]
            # 单据类型
            ticket_types = list(DirtyMachine.objects.all().values_list("ticket__ticket_type", flat=True).distinct())
            ticket_types_list = [
                {"value": ticket, "text": TicketType.get_choice_label(ticket)} for ticket in ticket_types
            ]
            resource_attrs = {
                "bk_cloud_id": bk_cloud_id_list,
                "bk_biz_ids": bk_biz_id_list,
                "ticket_types": ticket_types_list,
            }
            return resource_attrs
        elif resource_type == ResourceType.RESOURCE_RECORD:
            # 资源操作记录不需要表头筛选数据,后续这里补充其他表头筛选数据
            return {}


class QueryBizClusterAttrsResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": {"id": [1, 2, 3], "region": ["sz", "sh"]}}


class WebConsoleSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    cmd = serializers.CharField(help_text=_("sql语句"))
    # redis 额外参数
    db_num = serializers.IntegerField(help_text=_("数据库编号(redis 额外参数)"), required=False)
    raw = serializers.BooleanField(help_text=_("源编码(redis 额外参数)"), required=False)


class WebConsoleResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": [{"title1": "xxx", "title2": "xxx"}]}
