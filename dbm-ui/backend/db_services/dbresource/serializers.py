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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import ClusterDeployPlan, Spec
from backend.db_services.dbresource.constants import ResourceOperation
from backend.db_services.dbresource.mock import RESOURCE_LIST_DATA, SPEC_DATA
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
    city = serializers.CharField(help_text=_("城市"), required=False)
    subzones = serializers.CharField(help_text=_("园区"), required=False)

    cpu = serializers.CharField(help_text=_("cpu资源限制"), required=False)
    mem = serializers.CharField(help_text=_("内存资源限制"), required=False)
    disk = serializers.CharField(help_text=_("磁盘资源限制"), required=False)
    disk_type = serializers.CharField(help_text=_("磁盘类型"), required=False, allow_null=True, allow_blank=True)
    mount_point = serializers.CharField(help_text=_("磁盘挂载点"), required=False, allow_null=True, allow_blank=True)

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
                # for_bizs 要转换为int
                if field == "for_bizs":
                    attrs[field] = list(map(int, attrs[field]))
                # cpu, mem, disk 需要转换为结构体
                elif field in ["cpu", "mem", "disk"]:
                    attrs[field] = {"min": int(attrs[field][0] or 0), "max": int(attrs[field][1] or (2 ** 31 - 1))}

    def validate(self, attrs):
        self.format_fields(
            attrs,
            fields=["for_bizs", "resource_types", "device_class", "hosts", "city", "subzones", "cpu", "mem", "disk"],
        )
        return attrs


class ResourceListResponseSerializer(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {"example": RESOURCE_LIST_DATA}


class ListDBAHostsSerializer(QueryHostsBaseSer):
    pass


class ResourceConfirmSerializer(serializers.Serializer):
    request_id = serializers.CharField(help_text=_("资源申请的request_id"))
    host_ids = serializers.ListField(help_text=_("主机ID列表"), child=serializers.IntegerField())


class ResourceDeleteSerializer(serializers.Serializer):
    bk_host_ids = serializers.ListField(help_text=_("主机ID列表"), child=serializers.IntegerField())


class ResourceUpdateSerializer(serializers.Serializer):
    class UpdateDetailSerializer(serializers.Serializer):
        bk_host_id = serializers.IntegerField(help_text=_("主机ID"))
        labels = serializers.DictField(help_text=_("Labels"), required=False)
        for_bizs = serializers.ListField(help_text=_("专用业务ID"), child=serializers.IntegerField(), required=False)
        resource_types = serializers.ListField(
            help_text=_("专属DB"),
            child=serializers.ChoiceField(choices=DBType.get_choices()),
            required=False,
        )
        storage_device = serializers.JSONField(help_text=_("磁盘挂载点信息"), required=False)

    data = serializers.ListSerializer(child=UpdateDetailSerializer())


class QueryOperationListSerializer(serializers.Serializer):
    operation_type = serializers.ChoiceField(
        help_text=_("操作类型"), choices=ResourceOperation.get_choices(), required=False
    )
    ticket_ids = serializers.CharField(help_text=_("过滤的单据ID列表"), required=False)
    task_ids = serializers.CharField(help_text=_("过滤的任务ID列表"), required=False)
    operator = serializers.CharField(help_text=_("操作者"), required=False)
    begin_time = serializers.CharField(help_text=_("操作开始时间"), required=False)
    end_time = serializers.CharField(help_text=_("操作结束时间"), required=False)
    status = serializers.ChoiceField(help_text=_("单据状态"), choices=TicketStatus.get_choices(), required=False)

    page_size = serializers.IntegerField(help_text=_("分页大小"), required=False, default=10)
    start = serializers.IntegerField(help_text=_("分页起始位置"), required=False, default=0)

    def validate(self, attrs):
        if attrs.get("ticket_ids"):
            attrs["bill_ids"] = attrs.pop("ticket_ids").split(",")

        if attrs.get("task_ids"):
            attrs["task_ids"] = attrs["task_ids"].split(",")

        attrs["offset"], attrs["limit"] = attrs.pop("start"), attrs.pop("page_size")
        return attrs


class SpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = Spec
        fields = "__all__"
        read_only_fields = ("spec_id",) + model.AUDITED_FIELDS
        swagger_schema_fields = {"example": SPEC_DATA}


class DeleteSpecSerializer(serializers.Serializer):
    spec_ids = serializers.ListField(help_text=_("规格id列表"), child=serializers.IntegerField())

    class Meta:
        swagger_schema_fields = {"example": {"spec_ids": [1, 2, 3]}}


class DeleteDeployPlanSerializer(serializers.Serializer):
    deploy_plan_ids = serializers.ListField(help_text=_("部署方案id列表"), child=serializers.IntegerField())

    class Meta:
        swagger_schema_fields = {"example": {"deploy_plan_ids": [1, 2, 3]}}


class ListSubzonesSerializer(serializers.Serializer):
    citys = serializers.ListField(help_text=_("逻辑城市"), child=serializers.CharField())


class ClusterDeployPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClusterDeployPlan
        fields = "__all__"
        read_only_fields = ("id",) + model.AUDITED_FIELDS
        swagger_schema_fields = {"example": {}}


class RecommendSpecSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    role = serializers.ChoiceField(help_text=_("实例类型"), choices=InstanceRole.get_choices(), required=False)
