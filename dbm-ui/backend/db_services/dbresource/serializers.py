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
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend import env
from backend.configuration.constants import DBType
from backend.constants import INT_MAX
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Spec
from backend.db_services.dbresource.constants import ResourceOperation
from backend.db_services.dbresource.mock import (
    RECOMMEND_SPEC_DATA,
    RESOURCE_LIST_DATA,
    RESOURCE_UPDATE_PARAMS,
    SPEC_DATA,
)
from backend.db_services.ipchooser.serializers.base import QueryHostsBaseSer
from backend.ticket.constants import TicketStatus


class ResourceImportSerializer(serializers.Serializer):
    class HostInfoSerializer(serializers.Serializer):
        ip = serializers.CharField()
        host_id = serializers.IntegerField()
        bk_cloud_id = serializers.IntegerField()

    for_bizs = serializers.ListSerializer(help_text=_("专属业务的ID列表"), child=serializers.IntegerField())
    resource_types = serializers.ListField(
        help_text=_("专属DB"), child=serializers.ChoiceField(choices=DBType.get_choices())
    )
    bk_biz_id = serializers.IntegerField(help_text=_("机器当前所属的业务id	"), default=env.DBA_APP_BK_BIZ_ID)
    hosts = serializers.ListSerializer(help_text=_("主机"), child=HostInfoSerializer())
    labels = serializers.DictField(help_text=_("标签信息"), required=False)


class ResourceApplySerializer(serializers.Serializer):
    class HostDetailSerializer(serializers.Serializer):
        group_mark = serializers.CharField(help_text=_("分组类型"))
        device_class = serializers.ListField(help_text=_("机型"), child=serializers.CharField(), required=False)
        spec = serializers.DictField(help_text=_("cpu&mem参数"), required=False)
        storage_spec = serializers.ListField(help_text=_("磁盘参数"), child=serializers.DictField(), required=False)
        location_spec = serializers.DictField(help_text=_("位置匹配参数"), required=False)
        labels = serializers.DictField(help_text=_("标签"), required=False)
        affinity = serializers.CharField(help_text=_("亲和性"), required=False)
        count = serializers.IntegerField(help_text=_("数量"))

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    resource_type = serializers.CharField(help_text=_("专属DB"), required=False)
    for_biz_id = serializers.IntegerField(help_text=_("业务专属ID"), required=False)
    details = serializers.ListSerializer(help_text=_("资源申请参数"), child=HostDetailSerializer())


class ResourceImportResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": ""}


class ResourceListSerializer(serializers.Serializer):
    class ResourceLimitSerializer(serializers.Serializer):
        min = serializers.IntegerField(help_text=_("资源最小值"), required=False)
        max = serializers.IntegerField(help_text=_("资源最大值"), required=False)

    for_bizs = serializers.CharField(help_text=_("专属业务"), required=False)
    resource_types = serializers.CharField(help_text=_("专属DB"), required=False)
    device_class = serializers.CharField(help_text=_("机型"), required=False)
    hosts = serializers.CharField(help_text=_("主机IP列表"), required=False)
    bk_cloud_ids = serializers.CharField(help_text=_("云区域ID列表"), required=False)
    city = serializers.CharField(help_text=_("城市"), required=False)
    subzones = serializers.CharField(help_text=_("园区"), required=False)

    cpu = serializers.CharField(help_text=_("cpu资源限制"), required=False)
    mem = serializers.CharField(help_text=_("内存资源限制"), required=False)
    disk = serializers.CharField(help_text=_("磁盘资源限制"), required=False)
    disk_type = serializers.CharField(help_text=_("磁盘类型"), required=False, allow_null=True, allow_blank=True)
    mount_point = serializers.CharField(help_text=_("磁盘挂载点"), required=False, allow_null=True, allow_blank=True)
    spec_id = serializers.IntegerField(help_text=_("过滤的规格ID"), required=False)

    agent_status = serializers.BooleanField(help_text=_("agent状态"), required=False)
    labels = serializers.DictField(help_text=_("标签信息"), required=False)

    limit = serializers.IntegerField(help_text=_("单页数量"))
    offset = serializers.IntegerField(help_text=_("偏移量"))

    @staticmethod
    def format_fields(attrs, fields):
        # 用逗号方便前端URL渲染，这里统一转换为数组 or obj
        for field in fields:
            divider = "-" if field in ["cpu", "mem", "disk"] else ","

            if attrs.get(field):
                attrs[field] = attrs[field].split(divider)
                # for_bizs,bk_cloud_ids 要转换为int
                if field in ["for_bizs", "bk_cloud_ids"]:
                    attrs[field] = list(map(int, attrs[field]))
                # cpu, mem, disk 需要转换为结构体
                elif field in ["mem"]:
                    attrs[field] = {"min": float(attrs[field][0] or 0), "max": float(attrs[field][1] or INT_MAX)}
                elif field in ["cpu", "disk"]:
                    attrs[field] = {"min": int(attrs[field][0] or 0), "max": int(attrs[field][1] or INT_MAX)}

        # 转换规格查询参数
        if attrs.get("spec_id"):
            spec = Spec.objects.get(spec_id=attrs["spec_id"])
            attrs["storage_spec"] = [
                {
                    "mount_point": storage_spec["mount_point"],
                    "disk_type": "" if storage_spec["type"] == "ALL" else storage_spec["type"],
                    "min": storage_spec["size"],
                    "max": INT_MAX,
                }
                for storage_spec in spec.storage_spec
            ]
            attrs["cpu"], attrs["mem"], attrs["device_class"] = spec.cpu, spec.mem, spec.device_class

        # 转换内存查询单位, GB --> MB
        if attrs.get("mem"):
            attrs["mem"] = {"min": int(attrs["mem"]["min"] * 1024), "max": int(attrs["mem"]["max"] * 1024)}

        # 格式化agent参数
        attrs["gse_agent_alive"] = str(attrs.get("agent_status", "")).lower()

    def validate(self, attrs):
        self.format_fields(
            attrs,
            fields=[
                "for_bizs",
                "resource_types",
                "device_class",
                "hosts",
                "city",
                "subzones",
                "cpu",
                "mem",
                "disk",
                "bk_cloud_ids",
            ],
        )
        return attrs


class ResourceListResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": RESOURCE_LIST_DATA}


class ListDBAHostsSerializer(QueryHostsBaseSer):
    pass


class QueryDBAHostsSerializer(serializers.Serializer):
    bk_host_ids = serializers.CharField(help_text=_("主机ID列表(逗号分隔)"))


class ResourceConfirmSerializer(serializers.Serializer):
    request_id = serializers.CharField(help_text=_("资源申请的request_id"))
    host_ids = serializers.ListField(help_text=_("主机ID列表"), child=serializers.IntegerField())


class ResourceDeleteSerializer(serializers.Serializer):
    bk_host_ids = serializers.ListField(help_text=_("主机ID列表"), child=serializers.IntegerField())


class ResourceUpdateSerializer(serializers.Serializer):
    bk_host_ids = serializers.ListField(help_text=_("主机ID列表"), child=serializers.IntegerField())
    labels = serializers.DictField(help_text=_("Labels"), required=False)
    for_bizs = serializers.ListField(help_text=_("专用业务ID"), child=serializers.IntegerField(), required=False)
    resource_types = serializers.ListField(
        help_text=_("专属DB"),
        child=serializers.ChoiceField(choices=DBType.get_choices()),
        required=False,
    )
    set_empty_biz = serializers.BooleanField(help_text=_("是否无专用业务"), required=False, default=False)
    set_empty_resource_type = serializers.BooleanField(help_text=_("是否无专用资源类型"), required=False, default=False)
    storage_device = serializers.JSONField(help_text=_("磁盘挂载点信息"), required=False)

    class Meta:
        swagger_schema_fields = {"example": RESOURCE_UPDATE_PARAMS}


class QueryOperationListSerializer(serializers.Serializer):
    operation_type = serializers.ChoiceField(
        help_text=_("操作类型"), choices=ResourceOperation.get_choices(), required=False
    )

    ticket_ids = serializers.CharField(help_text=_("过滤的单据ID列表"), required=False)
    ticket_types = serializers.CharField(help_text=_("过滤的单据类型列表"), required=False)
    task_ids = serializers.CharField(help_text=_("过滤的任务ID列表"), required=False)
    ip_list = serializers.CharField(help_text=_("过滤IP列表"), required=False)
    update_time = serializers.BooleanField(help_text=_("时间排序模式"), required=False, default=False)

    operator = serializers.CharField(help_text=_("操作者"), required=False)
    begin_time = serializers.CharField(help_text=_("操作开始时间"), required=False)
    end_time = serializers.CharField(help_text=_("操作结束时间"), required=False)
    status = serializers.ChoiceField(help_text=_("单据状态"), choices=TicketStatus.get_choices(), required=False)

    limit = serializers.IntegerField(help_text=_("分页大小"), required=False, default=10)
    offset = serializers.IntegerField(help_text=_("分页起始位置"), required=False, default=0)

    def validate(self, attrs):
        if attrs.get("ticket_ids"):
            attrs["bill_ids"] = attrs.pop("ticket_ids").split(",")

        if attrs.get("ticket_types"):
            attrs["bill_types"] = attrs.pop("ticket_types").split(",")

        if attrs.get("task_ids"):
            attrs["task_ids"] = attrs["task_ids"].split(",")

        if attrs.get("ip_list"):
            attrs["ip_list"] = attrs["ip_list"].split(",")

        attrs["orderby"] = "asc" if attrs["update_time"] else "desc"

        return attrs


class SpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = Spec
        fields = "__all__"
        read_only_fields = ("spec_id",) + model.AUDITED_FIELDS
        swagger_schema_fields = {"example": SPEC_DATA}

    def validate_valid_cpu_mem(self, attrs):
        # 校验cpu, mem是正确的范围
        if attrs["cpu"]["min"] > attrs["cpu"]["max"] or attrs["mem"]["min"] > attrs["mem"]["max"]:
            raise serializers.ValidationError(_("请保证CPU/MEM的最小最大范围合理"))

    def validate_only_spec(self, attrs):
        # 校验规格的集群-角色-名字必须唯一
        unique_filter = (
            Q(spec_cluster_type=attrs["spec_cluster_type"])
            & Q(spec_machine_type=attrs["spec_machine_type"])
            & Q(spec_name=attrs["spec_name"])
        )
        specs = Spec.objects.filter(unique_filter)
        # 排除掉更新的情况
        if specs.count() and getattr(self.instance, "spec_id", 0) != specs.first().spec_id:
            raise serializers.ValidationError(_("已存在同名规格，请保证集群类型-规格类型-规格名称必须唯一"))

        unique_filter = (
            Q(spec_cluster_type=attrs["spec_cluster_type"])
            & Q(spec_machine_type=attrs["spec_machine_type"])
            & Q(cpu=attrs["cpu"])
            & Q(mem=attrs["mem"])
            & Q(device_class=attrs["device_class"])
            & Q(storage_spec=attrs["storage_spec"])
            & Q(instance_num=attrs.get("instance_num", 1))
        )
        specs = Spec.objects.filter(unique_filter)
        if specs.count() and getattr(self.instance, "spec_id", 0) != specs.first().spec_id:
            raise serializers.ValidationError(_("已存在同种规格配置，请不要在相同规格类型下重复录入"))

    def validate_data_points(self, attrs):
        """校验磁盘的录入"""
        standard_mount_points = ["/data", "/data1"]
        mount_points = [storage["mount_point"] for storage in attrs["storage_spec"]]
        # TenDBCluster 磁盘录入只能是/data or /data和/data1
        if attrs["spec_cluster_type"] == ClusterType.TenDBCluster and attrs["spec_machine_type"] == MachineType.REMOTE:
            if not ("/data" in mount_points and set(mount_points).issubset(standard_mount_points)):
                raise serializers.ValidationError(
                    _("【{}】后端磁盘挂载点必须包含/data，可选/data1").format(attrs["spec_cluster_type"])
                )
        # TendisPlus/TendisSSD 磁盘必须包含/data和/data1
        if (
            attrs["spec_cluster_type"]
            in [
                ClusterType.TwemproxyTendisSSDInstance,
                ClusterType.TendisPredixyTendisplusCluster,
            ]
            and attrs["spec_machine_type"] in [MachineType.TENDISPLUS, MachineType.TENDISSSD]
        ):
            if "/data" not in set(mount_points):
                raise serializers.ValidationError(_("【{}】后端磁盘挂载点必须包含/data").format(attrs["spec_cluster_type"]))

    def validate(self, attrs):
        self.validate_valid_cpu_mem(attrs)
        self.validate_only_spec(attrs)
        self.validate_data_points(attrs)
        return attrs


class DeleteSpecSerializer(serializers.Serializer):
    spec_ids = serializers.ListField(help_text=_("规格id列表"), child=serializers.IntegerField())

    class Meta:
        swagger_schema_fields = {"example": {"spec_ids": [1, 2, 3]}}


class VerifyDuplicatedSpecNameSerializer(serializers.Serializer):
    spec_cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    spec_machine_type = serializers.ChoiceField(help_text=_("机器类型"), choices=MachineType.get_choices())
    spec_name = serializers.CharField(help_text=_("规格名称"))
    spec_id = serializers.IntegerField(help_text=_("规格ID(更新时传递)"), required=False)


class ListSubzonesSerializer(serializers.Serializer):
    citys = serializers.ListField(help_text=_("逻辑城市"), child=serializers.CharField())


class RecommendSpecSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"), required=False)
    instance_id = serializers.IntegerField(help_text=_("实例ID"), required=False)
    role = serializers.ChoiceField(help_text=_("实例类型"), choices=InstanceRole.get_choices())


class RecommendResponseSpecSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": RECOMMEND_SPEC_DATA}


class QueryQPSRangeSerializer(serializers.Serializer):
    spec_cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())
    spec_machine_type = serializers.ChoiceField(help_text=_("角色类型"), choices=MachineType.get_choices())
    capacity = serializers.IntegerField(help_text=_("当前容量需求"))
    future_capacity = serializers.IntegerField(help_text=_("未来容量需求"))
    shard_num = serializers.IntegerField(help_text=_("所需分片数"), required=False, default=0)


class QueryQPSRangeResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": {"min": 100, "max": 10000}}


class FilterClusterSpecSerializer(QueryQPSRangeSerializer):
    qps = serializers.JSONField(help_text=_("qps范围"), required=False)


class FilterClusterSpecResponseSerializer(QueryQPSRangeSerializer):
    class Meta:
        swagger_schema_fields = {"example": ""}


class GetMountPointResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": ["/data", "/data1"]}


class GetDiskTypeResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": ["HDD", "SSD"]}


class SpecCountResourceSerializer(serializers.Serializer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    spec_ids = serializers.ListField(help_text=_("规格ID列表"), child=serializers.IntegerField())


class SpecCountResourceResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": {"spec1": 10, "spec2": 10}}
