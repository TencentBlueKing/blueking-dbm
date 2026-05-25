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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class SQLServerInstanceSummaryInputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    address = serializers.CharField(
        help_text=_("实例地址 ip:port，可选；不传时返回集群内全部实例的基础信息"),
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )


class SQLServerInstanceSummaryDataSerializer(serializers.Serializer):
    """单个实例的 SERVERPROPERTY + sys.dm_os_sys_info 摘要"""

    machine_name = serializers.CharField(help_text=_("主机名"), allow_null=True)
    server_name = serializers.CharField(help_text=_("服务名"), allow_null=True)
    instance_name = serializers.CharField(help_text=_("实例名，默认实例为空"), allow_null=True)
    product_version = serializers.CharField(help_text=_("产品版本号，例如 15.0.4188.2"), allow_null=True)
    product_level = serializers.CharField(help_text=_("产品级别，例如 RTM/SP1"), allow_null=True)
    edition = serializers.CharField(help_text=_("版本，例如 Enterprise/Standard"), allow_null=True)
    collation = serializers.CharField(help_text=_("默认排序规则"), allow_null=True)
    is_clustered = serializers.IntegerField(help_text=_("是否故障转移群集，1/0"), allow_null=True)
    is_hadr_enabled = serializers.IntegerField(
        help_text=_("是否启用 AlwaysOn，1/0；2008/2008R2 上为 NULL"),
        allow_null=True,
    )
    is_integrated_security_only = serializers.IntegerField(
        help_text=_("是否仅 Windows 身份验证，1/0"),
        allow_null=True,
    )
    cpu_count = serializers.IntegerField(help_text=_("CPU 逻辑核数"), allow_null=True)
    sqlserver_start_time = serializers.CharField(
        help_text=_("SQL Server 启动时间（用最早系统会话登录时间近似，全版本可用）"),
        allow_null=True,
    )
    sql_memory_used_mb = serializers.IntegerField(
        help_text=_(
            "SQL Server 进程当前已用物理内存（工作集），单位 MB；"
            "包含 buffer pool、plan cache、线程栈、Linked Server、CLR 等全部分配，"
            "因此可能略大于 sql_memory_max_mb（max server memory 不管控线程栈/部分第三方 DLL 等），属正常现象"
        ),
        allow_null=True,
    )
    sql_memory_max_mb = serializers.IntegerField(
        help_text=_(
            "max server memory 配置上限，单位 MB；2147483647 表示未限制。"
            "注意：该上限仅约束 SQL Server 内部内存管理器所管理的部分，"
            "不等于进程内存绝对上限，sql_memory_used_mb 在合理范围内超出属正常"
        ),
        allow_null=True,
    )
    sql_memory_min_mb = serializers.IntegerField(
        help_text=_("min server memory 配置下限，单位 MB"),
        allow_null=True,
    )


class SQLServerInstanceSummaryItemSerializer(serializers.Serializer):
    address = serializers.CharField(help_text=_("实例地址 ip:port"))
    role = serializers.CharField(help_text=_("实例内部角色，例如 master/slave"))
    is_stand_by = serializers.BooleanField(help_text=_("是否备份/standby 角色"))
    data = SQLServerInstanceSummaryDataSerializer(
        help_text=_("实例摘要数据；查询失败时为 null"),
        allow_null=True,
    )
    error_msg = serializers.CharField(
        help_text=_("单实例错误信息；为空字符串表示成功"),
        allow_blank=True,
    )


class SQLServerInstanceSummaryOutputSerializer(serializers.Serializer):
    cluster_domain = serializers.CharField(help_text=_("集群域名"))
    results = SQLServerInstanceSummaryItemSerializer(
        many=True,
        help_text=_("实例基础信息列表"),
    )
