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

from .. import constants, exceptions


class PaginationSer(serializers.Serializer):
    start = serializers.IntegerField(help_text=_("数据起始位置"), required=False, default=0)
    page_size = serializers.IntegerField(
        help_text=_("拉取数据数量，不传或传 `-1` 表示拉取所有"),
        required=False,
        min_value=constants.CommonEnum.PAGE_RETURN_ALL_FLAG.value,
        max_value=500,
        default=constants.CommonEnum.PAGE_RETURN_ALL_FLAG.value,
    )


class ScopeSer(serializers.Serializer):
    scope_type = serializers.ChoiceField(help_text=_("资源范围类型"), choices=constants.ScopeType.list_choices())
    scope_id = serializers.CharField(help_text=_("资源范围ID"), min_length=1)
    # 最终只会使用 bk_biz_id
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"), required=False)
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), required=False)

    def validate(self, attrs):
        attrs["bk_biz_id"] = int(attrs["scope_id"])
        return attrs


class MetaSer(ScopeSer):
    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))

    def validate(self, attrs):
        return attrs


class TreeNodeSer(serializers.Serializer):
    object_id = serializers.CharField(help_text=_("节点类型ID"))
    instance_id = serializers.IntegerField(help_text=_("节点实例ID"))
    meta = MetaSer()


class HostSearchConditionSer(serializers.Serializer):
    ip = serializers.IPAddressField(label=_("内网IP"), required=False, protocol="ipv4")
    ipv6 = serializers.IPAddressField(label=_("内网IPv6"), required=False, protocol="ipv6")
    os_type = serializers.ChoiceField(label=_("操作系统类型"), required=False, choices=constants.OS_CHOICES)
    host_name = serializers.CharField(label=_("主机名称"), required=False, min_length=1)
    content = serializers.CharField(label=_("模糊搜索内容（支持同时对`主机IP`/`主机名`/`操作系统`进行模糊搜索"), required=False, min_length=1)


class ScopeSelectorBaseSer(serializers.Serializer):
    all_scope = serializers.BooleanField(help_text=_("是否获取所有资源范围的拓扑结构，默认为 `false`"), required=False, default=False)
    scope_list = serializers.ListField(help_text=_("要获取拓扑结构的资源范围数组"), child=ScopeSer(), default=[], required=False)


class QueryHostsBaseSer(PaginationSer):
    search_content = serializers.CharField(
        label=_("模糊搜索内容（支持同时对`主机IP`/`主机名`/`操作系统`进行模糊搜索"), required=False, allow_blank=True
    )
    bk_cloud_id = serializers.IntegerField(help_text=_("云区域过滤id"), required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        attrs["conditions"] = []
        search_content = attrs.pop("search_content", "")
        if search_content:
            for keyword in search_content.split():
                for field in ["bk_host_innerip", "bk_host_innerip_v6", "bk_host_name"]:
                    attrs["conditions"].append(
                        {"field": field, "operator": "contains", "value": keyword},
                    )
        attrs["page"] = {"start": attrs.pop("start"), "page_size": attrs.pop("page_size")}

        return attrs


class HostInfoWithMetaSer(serializers.Serializer):
    meta = MetaSer()
    cloud_id = serializers.IntegerField(help_text=_("云区域 ID"), required=False)
    ip = serializers.IPAddressField(help_text=_("IPv4 协议下的主机IP"), required=False, protocol="ipv4")
    host_id = serializers.IntegerField(help_text=_("主机 ID，优先取 `host_id`，否则取 `ip` + `cloud_id`"), required=False)

    def validate(self, attrs):
        if not ("host_id" in attrs or ("ip" in attrs and "cloud_id" in attrs)):
            raise exceptions.SerValidationError(_("请传入 host_id 或者 cloud_id + ip"))
        return attrs
