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
from backend.ticket.builders.mysql.mysql_partition_v2 import PartitionV2ConfObjectSerializer

from ...ticket.builders.common.field import DBTimezoneField
from ...ticket.builders.mysql.base import DBTableField
from ...ticket.builders.mysql.mysql_partition import PartitionObjectSerializer
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


class PartitionCloneSourceV2Serializer(serializers.Serializer):
    immute_domain = serializers.CharField(help_text=_("源集群域名"))
    bk_cloud_id = serializers.IntegerField(help_text=_("源云区域ID"), min_value=0)
    bk_biz_id = serializers.IntegerField(help_text=_("源业务ID"))
    dblikes = serializers.ListField(
        help_text=_("源库名列表，为空表示全部库"),
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    tblikes = serializers.ListField(
        help_text=_("源表名列表，为空表示命中库范围内的全部表"),
        child=serializers.CharField(),
        required=False,
        default=list,
    )

    def validate(self, attrs):
        try:
            cluster = Cluster.objects.get(
                bk_biz_id=attrs["bk_biz_id"],
                bk_cloud_id=attrs["bk_cloud_id"],
                immute_domain=attrs["immute_domain"],
            )
        except Cluster.DoesNotExist:
            raise serializers.ValidationError(_("源集群不存在"))
        except Cluster.MultipleObjectsReturned:
            raise serializers.ValidationError(_("源集群查询结果不唯一"))

        attrs.update(
            bk_biz_id=cluster.bk_biz_id,
            bk_cloud_id=cluster.bk_cloud_id,
            immute_domain=cluster.immute_domain,
        )
        return attrs


class PartitionCloneTargetV2Serializer(serializers.Serializer):
    immute_domain = serializers.CharField(help_text=_("目标集群域名"))
    cluster_id = serializers.IntegerField(help_text=_("目标集群ID"), required=False)
    port = serializers.IntegerField(help_text=_("目标集群端口"), required=False)
    bk_cloud_id = serializers.IntegerField(help_text=_("目标云区域ID"), min_value=0)
    bk_biz_id = serializers.IntegerField(help_text=_("目标业务ID"))
    db_app_abbr = serializers.CharField(help_text=_("目标业务英文缩写"), required=False, allow_blank=True)
    bk_biz_name = serializers.CharField(help_text=_("目标业务名"), required=False, allow_blank=True)
    dblikes = serializers.ListField(
        help_text=_("目标库名列表，为空表示沿用源库名"),
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    tblikes = serializers.ListField(
        help_text=_("目标表名列表，为空表示沿用源表名"),
        child=serializers.CharField(),
        required=False,
        default=list,
    )

    def validate(self, attrs):
        cluster = self._get_target_cluster(attrs)
        try:
            app = AppCache.objects.get(bk_biz_id=cluster.bk_biz_id)
        except AppCache.DoesNotExist:
            raise serializers.ValidationError(_("目标集群所属业务不存在"))

        meta_fields = {
            "cluster_id": cluster.id,
            "immute_domain": cluster.immute_domain,
            "port": cluster.get_partition_port(),
            "bk_cloud_id": cluster.bk_cloud_id,
            "bk_biz_id": cluster.bk_biz_id,
            "db_app_abbr": app.db_app_abbr,
            "bk_biz_name": app.bk_biz_name,
        }
        inconsistent_fields = [
            field
            for field, value in meta_fields.items()
            if attrs.get(field) not in (None, "") and attrs[field] != value
        ]
        if inconsistent_fields:
            raise serializers.ValidationError(_("目标集群身份信息与元数据不一致: {}").format(", ".join(inconsistent_fields)))

        attrs.update(meta_fields)
        return attrs

    @staticmethod
    def _get_target_cluster(attrs):
        cluster_id = attrs.get("cluster_id")
        try:
            if cluster_id:
                return Cluster.objects.get(id=cluster_id)
            return Cluster.objects.get(
                bk_biz_id=attrs["bk_biz_id"],
                bk_cloud_id=attrs["bk_cloud_id"],
                immute_domain=attrs["immute_domain"],
            )
        except Cluster.DoesNotExist:
            raise serializers.ValidationError(_("目标集群不存在"))
        except Cluster.MultipleObjectsReturned:
            raise serializers.ValidationError(_("目标集群查询结果不唯一，请补充 cluster_id"))


class PartitionCloneInfoV2Serializer(serializers.Serializer):
    source = PartitionCloneSourceV2Serializer(help_text=_("源分区配置范围"))
    target = PartitionCloneTargetV2Serializer(help_text=_("目标集群信息"))

    def validate(self, attrs):
        source = attrs["source"]
        target = attrs["target"]
        source_dblikes = source["dblikes"]
        source_tblikes = source["tblikes"]
        target_dblikes = target["dblikes"]
        target_tblikes = target["tblikes"]

        if source_tblikes and not source_dblikes:
            raise serializers.ValidationError(_("指定源表时必须同时指定源库列表"))
        if target_dblikes and len(target_dblikes) != len(source_dblikes):
            raise serializers.ValidationError(_("目标库列表须与源库列表等长，或为空表示同名映射"))
        if target_tblikes and len(target_tblikes) != len(source_tblikes):
            raise serializers.ValidationError(_("目标表列表须与源表列表等长，或为空表示同名映射"))
        return attrs


class PartitionCloneV2Serializer(serializers.Serializer):
    """分区v2配置克隆序列化器"""

    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    operator = serializers.SerializerMethodField(help_text=_("操作者"))
    infos = PartitionCloneInfoV2Serializer(help_text=_("源集群到目标集群的克隆信息"), many=True, allow_empty=False)

    def get_operator(self, obj):
        return self.context["request"].user.username

    def validate_cluster_type(self, value):
        supported_cluster_types = {
            ClusterType.TenDBHA.value,
            ClusterType.TenDBSingle.value,
            ClusterType.TenDBCluster.value,
        }
        if value not in supported_cluster_types:
            raise serializers.ValidationError(_("分区配置克隆仅支持tendbha、tendbsingle、tendbcluster三种集群类型"))
        return value

    def validate(self, attrs):
        cluster_type = attrs["cluster_type"]
        target_cluster_ids = [info["target"]["cluster_id"] for info in attrs["infos"]]
        actual_cluster_types = set(
            Cluster.objects.filter(id__in=target_cluster_ids).values_list("cluster_type", flat=True)
        )
        if actual_cluster_types != {cluster_type}:
            raise serializers.ValidationError(_("所有目标集群类型必须与请求的cluster_type一致"))
        return attrs


class PartitionCloneV2ResponseSerializer(serializers.Serializer):
    """分区v2配置克隆响应序列化器"""

    success_count = serializers.IntegerField(help_text=_("克隆成功条数"))
    errors = serializers.ListField(help_text=_("未克隆配置的原因"), child=serializers.CharField())
    info = serializers.CharField(help_text=_("克隆结果说明"))


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
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    partition_objects = serializers.DictField(
        help_text=_("分区执行对象列表"), child=serializers.ListSerializer(child=PartitionObjectSerializer())
    )


class PartitionColumnVerifySerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_id = serializers.IntegerField(help_text=_("云区域ID"))
    dblikes = serializers.ListField(help_text=_("匹配库列表(支持通配)"), child=DBTableField(db_field=True))
    tblikes = serializers.ListField(help_text=_("匹配表列表(不支持通配)"), child=DBTableField())
    partition_column = serializers.CharField(help_text=_("分区字段"))
    partition_column_type = serializers.CharField(help_text=_("分区字段类型"))

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


# 分区v2执行接口
# 支持批量
class PartitionExecuteV2Serializer(serializers.Serializer):
    class PartitionInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        configs = serializers.ListField(help_text=_("分区配置列表"), child=PartitionV2ConfObjectSerializer())
        force = serializers.BooleanField(help_text=_("是否强制执行"), required=False, default=False)

    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    partition_infos = serializers.ListField(help_text=_("分区信息列表"), child=PartitionInfoSerializer())


class PartitionExecuteV2ResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock.PARTITION_EXECUTE_V2_DATA}


# 分区v2查询分区执行日志
class PartitionLogV2Serializer(serializers.Serializer):
    config_id = serializers.IntegerField(help_text=_("分区策略ID"))


class PartitionLogV2ResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock.PARTITION_LOG_V2_DATA}


# 分区v2查询分区字段类型
class PartitionFieldTypeV2Serializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    dblikes = serializers.ListField(help_text=_("匹配库列表(支持通配)"), child=DBTableField(db_field=True))
    tblikes = serializers.ListField(help_text=_("匹配表列表(不支持通配)"), child=DBTableField())
    partition_column = serializers.CharField(help_text=_("分区字段"))


class PartitionFieldTypeV2ResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock.PARTITION_FIELD_TYPE_V2_DATA}


class SaveAndExecuteV2Serializer(PartitionCreateSerializer):
    # 当前支持DictField+child为serializers.ListSerializer 或 serializers.ListField
    # 直接使用PartitionCreateSerializer导致swagger无法解析
    force = serializers.BooleanField(help_text=_("是否强制执行"), required=False, default=False)


class SaveAndExecuteV2ResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock.PARTITION_EXECUTE_V2_DATA}


class QueryConfByStatusSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    status = serializers.CharField(help_text=_("执行状态(如 SUCCEEDED / FAILED / WARNING)"))
    limit = serializers.IntegerField(required=False, default=10)
    offset = serializers.IntegerField(required=False, default=0)


class PartitionImportFailedItemSerializer(serializers.Serializer):
    """单条导入失败详情序列化器"""

    row = serializers.IntegerField(help_text=_("Excel行号"))
    cluster = serializers.CharField(help_text=_("集群"))
    dblikes = serializers.CharField(help_text=_("匹配库列表"))
    tblikes = serializers.CharField(help_text=_("匹配表列表"))
    partition_column = serializers.CharField(help_text=_("分区字段"))
    partition_column_type = serializers.CharField(help_text=_("分区字段类型"))
    expire_time = serializers.CharField(help_text=_("过期时间"))
    partition_time_interval = serializers.CharField(help_text=_("分区时间间隔"))
    error = serializers.CharField(help_text=_("失败原因"))


class PartitionExportImportFailedSerializer(serializers.Serializer):
    """下载导入失败详情序列化器"""

    failed_items = serializers.ListField(
        child=PartitionImportFailedItemSerializer(),
        help_text=_("导入失败详情列表"),
        min_length=1,
    )

    class Meta:
        swagger_schema_fields = {"description": _("下载导入失败详情为Excel文件")}
