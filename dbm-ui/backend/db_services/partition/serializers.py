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

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache, Cluster

from ...ticket.builders.common.field import DBTimezoneField
from ...ticket.builders.mysql.base import DBTableField
from ...ticket.builders.mysql.mysql_partition import PartitionV2ConfObjectSerializer
from . import mock


class PartitionListSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    immute_domains = serializers.CharField(help_text=_("集群域名"), required=False)
    dblikes = serializers.CharField(help_text=_("匹配库"), required=False)
    tblikes = serializers.CharField(help_text=_("匹配表"), required=False)
    domain_name = serializers.CharField(help_text=_("集群名称"), required=False)
    ids = serializers.CharField(help_text=_("策略ID"), required=False)
    status = serializers.CharField(help_text=_("最近执行状态"), required=False)

    limit = serializers.IntegerField(required=False, default=10)
    offset = serializers.IntegerField(required=False, default=0)

    def validate(self, attrs):
        # 过滤集群类型
        if attrs["cluster_type"] not in [
            ClusterType.TenDBCluster.value,
            ClusterType.TenDBHA.value,
            ClusterType.TenDBSingle.value,
        ]:
            raise serializers.ValidationError(_("目前集群类型仅支持tendbha、tengdbsingle、tendbcluster三种类型。"))
        filter_fields = ["immute_domains", "dblikes", "tblikes", "ids"]
        # 将过滤参数转为list
        for field in filter_fields:
            if field in attrs:
                attrs[field] = attrs[field].split(",")
        # id过滤类型为int
        if attrs.get("ids"):
            attrs["ids"] = list(map(int, attrs["ids"]))
        return attrs


class PartitionListResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock.PARTITION_LIST_DATA}


class PartitionCreateSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    dblikes = serializers.ListField(help_text=_("匹配库列表(支持通配)"), child=DBTableField(db_field=True))
    tblikes = serializers.ListField(help_text=_("匹配表列表(不支持通配)"), child=DBTableField())
    partition_column = serializers.CharField(help_text=_("分区字段"))
    partition_column_type = serializers.CharField(help_text=_("分区字段类型"))
    expire_time = serializers.IntegerField(help_text=_("过期时间"))
    partition_time_interval = serializers.IntegerField(help_text=_("分区间隔"))
    need_dry_run = serializers.BooleanField(help_text=_("是否需要获取分区执行数据"), required=False, default=True)
    auto_commit = serializers.BooleanField(help_text=_("是否自动创建单据"), required=False, default=False)

    def validate(self, attrs):
        # 如果自动创建单据，则必须要获取执行数据
        if attrs["auto_commit"] and not attrs["need_dry_run"]:
            raise serializers.ValidationError(_("在自动创建单据的条件下，请保证need_dry_run选项为真"))

        # 表不支持通配
        for tb in attrs["tblikes"]:
            if "%" in tb or "*" in tb:
                raise serializers.ValidationError(_("分区表不支持通配"))

        # 校验过期时间>=分区间隔，且为整数倍
        if attrs["expire_time"] and attrs["expire_time"] % attrs["partition_time_interval"]:
            raise serializers.ValidationError(_("过期时间大于等于分区间隔，且为分区间隔的整数倍"))

        # 补充集群信息
        cluster = Cluster.objects.get(id=attrs["cluster_id"])
        app = AppCache.objects.get(bk_biz_id=cluster.bk_biz_id)
        attrs.update(
            bk_biz_id=cluster.bk_biz_id,
            bk_biz_name=app.bk_biz_name,
            db_app_abbr=app.db_app_abbr,
            bk_cloud_id=cluster.bk_cloud_id,
            cluster_type=cluster.cluster_type,
            immute_domain=cluster.immute_domain,
            port=cluster.get_partition_port(),
            time_zone=cluster.time_zone,
            creator=self.context["request"].user.username,
            updator=self.context["request"].user.username,
        )

        return attrs


class PartitionUpdateSerializer(PartitionCreateSerializer):
    pass


class PartitionReinitializeSerializer(PartitionCreateSerializer):
    cluster_id = serializers.IntegerField(help_text=_("云区域ID"))
    dblikes = serializers.ListField(help_text=_("匹配库列表(支持通配)"), child=DBTableField(db_field=True))
    tblikes = serializers.ListField(help_text=_("匹配表列表(不支持通配)"), child=DBTableField())
    partition_column = serializers.CharField(help_text=_("分区字段"))
    partition_column_type = serializers.CharField(help_text=_("分区字段类型"))
    expire_time = serializers.IntegerField(help_text=_("过期时间"))
    partition_time_interval = serializers.IntegerField(help_text=_("分区间隔"))
    extra_partition = serializers.IntegerField(help_text=_("预留分区数"))
    need_dry_run = serializers.BooleanField(help_text=_("是否需要获取分区执行数据"), required=False, default=True)
    auto_commit = serializers.BooleanField(help_text=_("是否自动创建单据"), required=False, default=False)
    force = serializers.BooleanField(help_text=_("否表示是否强制执行,True 表示重新初始化"), required=False, default=False)


class PartitionDisableSerializer(serializers.Serializer):
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    operator = serializers.SerializerMethodField(help_text=_("操作者"))
    ids = serializers.ListField(help_text=_("分区策略ID"), child=serializers.IntegerField())

    def get_operator(self, obj):
        return self.context["request"].user.username


class PartitionEnableSerializer(PartitionDisableSerializer):
    pass


class PartitionDeleteSerializer(PartitionDisableSerializer):
    pass


class PartitionLogSerializer(serializers.Serializer):
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    config_id = serializers.IntegerField(help_text=_("分区策略ID"))
    start_time = DBTimezoneField(help_text=_("开始时间"), required=False)
    end_time = DBTimezoneField(help_text=_("结束时间"), required=False)

    limit = serializers.IntegerField(required=False, default=10)
    offset = serializers.IntegerField(required=False, default=0)


class PartitionLogResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock.PARTITION_LOG_DATA}


class PartitionDryRunSerializer(serializers.Serializer):
    config_id = serializers.IntegerField(help_text=_("分区配置ID"))
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    port = serializers.SerializerMethodField(help_text=_("PORT"))

    def get_port(self, obj):
        return Cluster.objects.get(id=obj["cluster_id"]).get_partition_port()


class PartitionBatchDryRunSerializer(serializers.Serializer):
    """批量分区策略预执行序列化器"""

    partition_list = serializers.ListField(
        child=PartitionDryRunSerializer(), help_text=_("分区策略预执行参数列表"), min_length=1, max_length=100
    )

    class Meta:
        swagger_schema_fields = {"description": _("批量分区策略预执行参数")}


class PartitionDryRunResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock.PARTITION_DRY_RUN_DATA}


class PartitionBatchDryRunResponseSerializer(serializers.Serializer):
    """批量分区策略预执行响应序列化器"""

    results = serializers.ListField(child=PartitionDryRunResponseSerializer(), help_text=_("批量预执行结果列表"))

    class Meta:
        swagger_schema_fields = {"description": _("批量分区策略预执行结果")}


class PartitionRunSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    partition_infos = serializers.DictField(
        help_text=_("分区信息列表"), child=serializers.ListSerializer(child=PartitionV2ConfObjectSerializer())
    )


class PartitionColumnVerifySerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_id = serializers.IntegerField(help_text=_("云区域ID"))
    dblikes = serializers.ListField(help_text=_("匹配库列表(支持通配)"), child=DBTableField(db_field=True))
    tblikes = serializers.ListField(help_text=_("匹配表列表(不支持通配)"), child=DBTableField())
    partition_column = serializers.CharField(help_text=_("分区字段"))

    def validate(self, attrs):
        return attrs


class PartitionColumnVerifyResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock.PARTITION_FIELD_VERIFY_DATA}


class PartitionImportSerializer(serializers.Serializer):
    """Excel导入分区策略序列化器"""

    file = serializers.FileField(help_text=_("Excel文件"))

    class Meta:
        swagger_schema_fields = {"description": _("通过Excel文件导入分区策略")}


class PartitionImportResultSerializer(serializers.Serializer):
    """Excel导入结果序列化器"""

    success_count = serializers.IntegerField(help_text=_("成功导入数量"))
    failed_count = serializers.IntegerField(help_text=_("失败导入数量"))
    failed_items = serializers.ListField(child=serializers.DictField(), help_text=_("失败详情列表"))

    class Meta:
        swagger_schema_fields = {"description": _("Excel导入分区策略结果")}


class PartitionExportSerializer(serializers.Serializer):
    """分区策略导出序列化器"""

    export_type = serializers.ChoiceField(
        choices=[("all", _("所有策略")), ("selected", _("已选策略"))], help_text=_("导出类型：all-所有策略，selected-已选策略")
    )

    selected_ids = serializers.ListField(
        child=serializers.IntegerField(), help_text=_("已选策略ID列表，仅在export_type为selected时有效"), required=False, default=[]
    )

    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))

    def validate(self, attrs):
        # 过滤集群类型
        if attrs["cluster_type"] not in [
            ClusterType.TenDBCluster.value,
            ClusterType.TenDBHA.value,
            ClusterType.TenDBSingle.value,
        ]:
            raise serializers.ValidationError(_("目前集群类型仅支持tendbha、tengdbsingle、tendbcluster三种类型。"))
        filter_fields = ["selected_ids"]
        # 将selected_ids转换为int
        for field in filter_fields:
            if field in attrs:
                attrs[field] = list(map(int, attrs[field]))
        return attrs

    class Meta:
        swagger_schema_fields = {"description": _("分区策略导出参数")}


class PartitionExportResponseSerializer(serializers.Serializer):
    """分区策略导出响应序列化器"""

    file_content = serializers.CharField(help_text=_("导出的Excel文件内容（base64编码）"))
    file_name = serializers.CharField(help_text=_("导出的文件名"))
    total_count = serializers.IntegerField(help_text=_("导出的策略总数"))

    class Meta:
        swagger_schema_fields = {"description": _("分区策略导出结果")}


class PartitionLogDetailSerializer(serializers.Serializer):
    """分区日志详情序列化器"""

    config_id = serializers.ListSerializer(child=serializers.IntegerField(), help_text=_("分区策略ID"))

    class Meta:
        swagger_schema_fields = {"description": _("分区执行失败日志详情")}
