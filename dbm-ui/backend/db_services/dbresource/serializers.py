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
from backend.components.hcm.client import HCMApi
from backend.components.xwork.client import XworkApi
from backend.configuration.constants import DBType
from backend.constants import INT_MAX
from backend.db_dirty.constants import MachineEventType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.spec import SpecClusterType, SpecMachineType
from backend.db_meta.models import Spec
from backend.db_meta.models.machine import DeviceClass, Machine
from backend.db_services.dbresource import mock
from backend.db_services.dbresource.constants import ResourceGroupByEnum, ResourceOperation
from backend.db_services.dbresource.mock import (
    RECOMMEND_SPEC_DATA,
    RESOURCE_LIST_DATA,
    RESOURCE_UPDATE_PARAMS,
    SPEC_DATA,
)
from backend.db_services.ipchooser.constants import BkOsTypeCode
from backend.db_services.ipchooser.serializers.base import QueryHostsBaseSer
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.common.field import DBTimezoneField
from backend.ticket.constants import TicketStatus


class ResourceImportSerializer(serializers.Serializer):
    class ResourceHostSerializer(serializers.Serializer):
        ip = serializers.CharField()
        host_id = serializers.IntegerField()
        bk_cloud_id = serializers.IntegerField()
        os_type = serializers.CharField(required=False, default=BkOsTypeCode.LINUX)

    for_biz = serializers.IntegerField(help_text=_("专属业务"))
    resource_type = serializers.CharField(help_text=_("专属DB"), allow_blank=True, allow_null=True)
    bk_biz_id = serializers.IntegerField(help_text=_("机器当前所属的业务id	"), default=env.DBA_APP_BK_BIZ_ID)
    hosts = serializers.ListSerializer(help_text=_("资源主机"), child=ResourceHostSerializer())
    labels = serializers.ListField(help_text=_("标签"), child=serializers.CharField(), required=False)
    return_resource = serializers.BooleanField(help_text=_("是否为退回资源"), required=False)

    def validate(self, attrs):
        host_id__ip_map = {host["host_id"]: host["ip"] for host in attrs["hosts"]}
        host_ids = list(host_id__ip_map.keys())

        # 如果主机存在元数据，则拒绝导入
        exist_hosts = list(Machine.objects.filter(bk_host_id__in=host_ids).values_list("ip", flat=True))
        if exist_hosts:
            raise serializers.ValidationError(_("导入失败，主机{}存在元数据，请检查后重新导入").format(exist_hosts))

        # 存在uwork或者是待裁撤主机，则不允许导入
        check_uwork = HCMApi.check_host_has_uwork(host_ids)
        if check_uwork:
            ips = [host_id__ip_map[host_id] for host_id in check_uwork.keys()]
            raise serializers.ValidationError(_("导入失败，检测主机{}有关联的uwork单据，请检查后重新导入").format(ips))

        host_ip__host_id_map = {host["ip"]: host["host_id"] for host in attrs["hosts"]}
        check_xwork = XworkApi.check_xwork_list(host_ip__host_id_map)
        if check_xwork:
            ips = [host_id__ip_map[host_id] for host_id in check_xwork.keys()]
            raise serializers.ValidationError(_("导入失败，检测主机{}有关联的xwork单据，请检查后重新导入").format(ips))

        check_dissolved = HCMApi.check_host_is_dissolved(host_ids)
        if check_dissolved:
            ips = [host_id__ip_map[host_id] for host_id in check_dissolved]
            raise serializers.ValidationError(_("导入失败，检测主机{}为待裁撤主机，请检查后重新导入").format(ips))

        return attrs


class ResourceApplySerializer(serializers.Serializer):
    class HostDetailSerializer(serializers.Serializer):
        group_mark = serializers.CharField(help_text=_("分组类型"))
        device_class = serializers.ListField(help_text=_("机型"), child=serializers.CharField(), required=False)
        spec = serializers.DictField(help_text=_("cpu&mem参数"), required=False)
        storage_spec = serializers.ListField(help_text=_("磁盘参数"), child=serializers.DictField(), required=False)
        location_spec = serializers.DictField(help_text=_("位置匹配参数"), required=False)
        labels = serializers.ListField(help_text=_("标签"), required=False, child=serializers.CharField())
        affinity = serializers.CharField(help_text=_("亲和性"), required=False)
        count = serializers.IntegerField(help_text=_("数量"))

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    resource_type = serializers.CharField(help_text=_("专属DB"), required=False, allow_null=True, allow_blank=True)
    for_biz_id = serializers.IntegerField(help_text=_("业务专属ID"), required=False)
    details = serializers.ListSerializer(help_text=_("资源申请参数"), child=HostDetailSerializer())


class ResourceImportResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": ""}


class ResourceListSerializer(serializers.Serializer):
    for_biz = serializers.IntegerField(help_text=_("专属业务"), required=False)
    for_bizs = serializers.ListField(help_text=_("专属业务列表"), child=serializers.IntegerField(), required=False)
    resource_type = serializers.CharField(help_text=_("专属DB"), required=False, allow_null=True, allow_blank=True)
    resource_types = serializers.ListField(help_text=_("专属DB列表"), child=serializers.CharField(), required=False)
    device_class = serializers.CharField(help_text=_("机型"), required=False)
    hosts = serializers.CharField(help_text=_("主机IP列表"), required=False)
    bk_cloud_ids = serializers.CharField(help_text=_("云区域ID列表"), required=False)
    city = serializers.CharField(help_text=_("城市"), required=False)
    subzones = serializers.CharField(help_text=_("园区"), required=False)
    subzone_ids = serializers.CharField(help_text=_("园区ID"), required=False)

    os_type = serializers.CharField(help_text=_("操作系统类型"), required=False)
    os_names = serializers.ListField(help_text=_("操作系统版本"), child=serializers.CharField(), required=False)
    cpu = serializers.CharField(help_text=_("cpu资源限制"), required=False)
    mem = serializers.CharField(help_text=_("内存资源限制"), required=False)
    disk = serializers.CharField(help_text=_("磁盘资源限制"), required=False)
    disk_type = serializers.CharField(help_text=_("磁盘类型"), required=False, allow_null=True, allow_blank=True)
    mount_point = serializers.CharField(help_text=_("磁盘挂载点"), required=False, allow_null=True, allow_blank=True)
    spec_id = serializers.IntegerField(help_text=_("过滤的规格ID"), required=False)

    agent_status = serializers.BooleanField(help_text=_("agent状态"), required=False)
    labels = serializers.CharField(help_text=_("标签列表id"), required=False)

    limit = serializers.IntegerField(help_text=_("单页数量"))
    offset = serializers.IntegerField(help_text=_("偏移量"))

    @staticmethod
    def format_fields(attrs, fields):
        # 用逗号方便前端URL渲染，这里统一转换为数组 or obj
        for field in fields:
            divider = "-" if field in ["cpu", "mem", "disk"] else ","

            if attrs.get(field):
                attrs[field] = attrs[field].split(divider)
                # bk_cloud_ids 要转换为int
                if field in ["bk_cloud_ids"]:
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
                "device_class",
                "hosts",
                "city",
                "subzones",
                "subzone_ids",
                "cpu",
                "mem",
                "disk",
                "bk_cloud_ids",
                "labels",
            ],
        )
        return attrs


class ResourceListResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": RESOURCE_LIST_DATA}


class ListDBAHostsSerializer(QueryHostsBaseSer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"), required=False, default=env.DBA_APP_BK_BIZ_ID)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs.get("conditions"):
            return attrs

        # ip这里需要精确查询
        attrs["conditions"] = [cond for cond in attrs["conditions"] if cond["field"] == "bk_host_innerip"]
        for cond in attrs["conditions"]:
            cond["operator"] = "equal"

        return attrs


class QueryDBAHostsSerializer(serializers.Serializer):
    bk_host_ids = serializers.CharField(help_text=_("主机ID列表(逗号分隔)"))


class ResourceConfirmSerializer(serializers.Serializer):
    request_id = serializers.CharField(help_text=_("资源申请的request_id"))
    host_ids = serializers.ListField(help_text=_("主机ID列表"), child=serializers.IntegerField())


class ResourceDeleteSerializer(serializers.Serializer):
    hosts = serializers.ListSerializer(help_text=_("主机列表"), child=HostInfoSerializer())
    event = serializers.ChoiceField(help_text=_("删除事件(移入故障池/撤销导入)"), choices=MachineEventType.get_choices())
    remark = serializers.CharField(help_text=_("备注"), required=False, default="")


class ResourceUpdateSerializer(serializers.Serializer):
    bk_host_ids = serializers.ListField(help_text=_("主机ID列表"), child=serializers.IntegerField())
    labels = serializers.ListField(help_text=_("标签"), required=False, child=serializers.CharField())
    for_biz = serializers.IntegerField(help_text=_("专用业务ID"), required=False)
    resource_type = serializers.CharField(help_text=_("专属DB"), allow_blank=True, allow_null=True, required=False)
    storage_device = serializers.JSONField(help_text=_("磁盘挂载点信息"), required=False)
    rack_id = serializers.CharField(help_text=_("机架ID"), required=False, allow_null=True, allow_blank=True)
    city_meta = serializers.JSONField(help_text=_("地域信息"), required=False)
    sub_zone_meta = serializers.JSONField(help_text=_("园区信息"), required=False)
    device_class = serializers.CharField(help_text=_("机型"), required=False)

    # def validate(self, attrs):
    #     machine_property = SystemSettings.get_setting_value(
    #         SystemSettingsEnum.MACHINE_PROPERTY.value, default=DEFAULT_MACHINE_PROPERTY
    #     )
    #     # 找出没有更新权限的字段
    #     unauthorized_fields = [
    #         self.fields[key].help_text for key in attrs.keys() if key in machine_property and not machine_property[key]
    #     ]
    #
    #     # 无权限字段抛出 ValidationError
    #     if unauthorized_fields:
    #         raise serializers.ValidationError(_("permission_error：没有更新属性：{}的权限").format(unauthorized_fields))
    #     return attrs

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
    ordering = serializers.CharField(max_length=255, help_text=_("排序字段"), default="-update_time")

    operator = serializers.CharField(help_text=_("操作者"), required=False)
    begin_time = DBTimezoneField(help_text=_("操作开始时间"), required=False)
    end_time = DBTimezoneField(help_text=_("操作结束时间"), required=False)
    status = serializers.ChoiceField(help_text=_("单据状态"), choices=TicketStatus.get_choices(), required=False)

    limit = serializers.IntegerField(help_text=_("分页大小"), required=False, default=10)
    offset = serializers.IntegerField(help_text=_("分页起始位置"), required=False, default=0)

    def validate_ordering(self, value):
        """验证排序字段是否合法。"""
        allowed_orderings = ["update_time", "-update_time", "total_count", "-total_count"]

        if value not in allowed_orderings:
            raise serializers.ValidationError(_("排序参数只能是 'update_time' 或 'total_count'。"))
        return value

    def validate(self, attrs):
        if attrs.get("ticket_ids"):
            attrs["bill_ids"] = attrs.pop("ticket_ids").split(",")

        if attrs.get("ticket_types"):
            attrs["bill_types"] = attrs.pop("ticket_types").split(",")

        if attrs.get("task_ids"):
            attrs["task_ids"] = attrs["task_ids"].split(",")

        if attrs.get("ip_list"):
            attrs["ip_list"] = attrs["ip_list"].split(",")

        if attrs.get("ordering"):
            attrs["orderby"] = attrs.pop("ordering")

        return attrs


class ResourceSummarySerializer(serializers.Serializer):
    # 聚合过滤字段
    db_type = serializers.CharField(help_text=_("db类型"))
    machine_type = serializers.ChoiceField(
        help_text=_("机器类型"), choices=SpecMachineType.get_choices(), required=False, default=""
    )
    cluster_type = serializers.ChoiceField(
        help_text=_("集群类型"), choices=SpecClusterType.get_choices(), required=False, default=""
    )
    spec_id_list = serializers.CharField(help_text=_("规格ID"), required=False, default="")
    enable_spec = serializers.BooleanField(help_text=_("仅聚合启用规格"), required=False, default=False)

    for_biz = serializers.IntegerField(help_text=_("专用业务ID"), required=False, default=0)
    city = serializers.CharField(help_text=_("城市名"), required=False, allow_blank=True)
    group_by = serializers.ChoiceField(help_text=_("聚合类型"), choices=ResourceGroupByEnum.get_choices())
    subzone_ids = serializers.CharField(help_text=_("园区"), required=False, default="")

    def validate(self, attrs):
        # 平铺列表字段
        attrs["subzone_ids"] = attrs["subzone_ids"].split(",") if attrs["subzone_ids"] else []
        attrs["spec_id_list"] = attrs["spec_id_list"].split(",") if attrs["spec_id_list"] else []
        attrs["spec_id_list"] = list(map(int, attrs["spec_id_list"]))
        # 把聚合过滤字段放在spec_param
        spec_param_fields = ["db_type", "machine_type", "cluster_type", "spec_id_list"]
        attrs["spec_param"] = {field: attrs.pop(field) for field in spec_param_fields}
        return attrs


class ResourceSummaryResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": mock.RESOURCE_SUMMARY_DATA}


class SpecSerializer(serializers.ModelSerializer):
    spec_db_type = serializers.SerializerMethodField(help_text=_("规格组件类型"))
    capacity = serializers.SerializerMethodField(help_text=_("规格容量"))

    class Meta:
        model = Spec
        fields = "__all__"
        read_only_fields = ("spec_id",) + model.AUDITED_FIELDS
        swagger_schema_fields = {"example": SPEC_DATA}

    def get_spec_db_type(self, obj):
        db_type = obj.spec_cluster_type
        return db_type

    def get_capacity(self, obj):
        return obj.capacity

    def validate_valid_cpu_mem(self, attrs):
        # 校验cpu,mem的值是int
        try:
            attrs["cpu"]["min"], attrs["cpu"]["max"] = int(attrs["cpu"]["min"]), int(attrs["cpu"]["max"])
            attrs["mem"]["min"], attrs["mem"]["max"] = float(attrs["mem"]["min"]), float(attrs["mem"]["max"])
        except ValueError:
            raise serializers.ValidationError(_("请保证CPU/MEM的取值为数字"))
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
        if (
            attrs["spec_cluster_type"] == SpecClusterType.TenDBCluster
            and attrs["spec_machine_type"] == SpecMachineType.BACKEND
        ):
            if not ("/data" in mount_points and set(mount_points).issubset(standard_mount_points)):
                raise serializers.ValidationError(
                    _("【{}】后端磁盘挂载点必须包含/data，可选/data1").format(attrs["spec_cluster_type"])
                )
        # TendisPlus/TendisSSD 磁盘必须包含/data，/data1可选
        if attrs["spec_machine_type"] in [
            SpecMachineType.TwemproxyTendisSSDInstance,
            SpecMachineType.TendisPredixyTendisplusCluster,
        ] and "/data" not in set(mount_points):
            raise serializers.ValidationError(_("【{}】后端磁盘挂载点必须包含/data").format(attrs["spec_machine_type"]))

    def validate(self, attrs):
        self.validate_valid_cpu_mem(attrs)
        self.validate_only_spec(attrs)
        self.validate_data_points(attrs)
        return attrs


class DeleteSpecSerializer(serializers.Serializer):
    spec_ids = serializers.ListField(help_text=_("规格id列表"), child=serializers.IntegerField())

    class Meta:
        swagger_schema_fields = {"example": {"spec_ids": [1, 2, 3]}}


class SpecEnableDisableSerializer(serializers.Serializer):
    spec_ids = serializers.ListField(help_text=_("规格id列表"), child=serializers.IntegerField())
    enable = serializers.BooleanField(help_text=_("是否启用"))


class VerifyDuplicatedSpecNameSerializer(serializers.Serializer):
    spec_cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=SpecClusterType.get_choices())
    spec_machine_type = serializers.ChoiceField(help_text=_("机器类型"), choices=SpecMachineType.get_choices())
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
    spec_cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=SpecClusterType.get_choices())
    spec_machine_type = serializers.ChoiceField(help_text=_("角色类型"), choices=SpecMachineType.get_choices())
    capacity = serializers.FloatField(help_text=_("当前容量需求"))
    future_capacity = serializers.IntegerField(help_text=_("未来容量需求"), required=False)
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
    city = serializers.CharField(help_text=_("城市"), default="default", required=False)


class SpecCostEstimateSerializer(serializers.Serializer):
    db_type = serializers.ChoiceField(help_text=_("组件类型"), choices=DBType.get_choices())
    resource_spec = serializers.JSONField(help_text=_("部署规格"))


class SpecCountResourceResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": {"spec1": 10, "spec2": 10}}


class ListCvmDeviceClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceClass
        fields = "__all__"
        swagger_schema_fields = {"example": mock.DEVICE_CLASS_DATA}


class UworkIpsSerializer(serializers.Serializer):
    ips = serializers.CharField(help_text=_("ip列表，多个ip以逗号分割"))

    def validate_ip_list(self, value):
        return value.split(",")


class AppendHostLabelSerializer(serializers.Serializer):
    bk_host_ids = serializers.ListField(help_text=_("主机ID列表"), child=serializers.IntegerField())
    labels = serializers.ListField(help_text=_("追加标签列表"), child=serializers.CharField())
