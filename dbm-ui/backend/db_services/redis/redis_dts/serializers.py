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

from backend.db_services.redis.redis_dts.models import TbTendisDTSJob


class TbTendisDTSJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = TbTendisDTSJob
        fields = "__all__"


class TendisDtsHistoryJobSLZ(serializers.Serializer):
    cluster_name = serializers.CharField(help_text=_("集群名"), required=False, allow_blank=True)
    start_time = serializers.CharField(help_text=_("开始时间"), required=False)
    end_time = serializers.CharField(help_text=_("结束时间"), required=False)
    page = serializers.IntegerField(help_text=_("页码"), required=False, default=1)
    page_size = serializers.IntegerField(help_text=_("每页数量"), required=False, default=0)


class DtsJobTasksSLZ(serializers.Serializer):
    bill_id = serializers.IntegerField(help_text=_("单据ID"), required=True)
    src_cluster = serializers.CharField(help_text=_("源集群"), required=True)
    dst_cluster = serializers.CharField(help_text=_("目标集群"), required=True)


class DtsTaskIDsSLZ(serializers.Serializer):
    task_ids = serializers.ListField(
        help_text=_("子任务ID列表"), child=serializers.IntegerField(), allow_empty=False, required=True
    )


class DtsDataCopyBaseItemSLZ(serializers.Serializer):
    src_cluster = serializers.CharField(help_text=_("源集群"), required=True)
    src_cluster_password = serializers.CharField(help_text=_("源集群密码"), allow_blank=True)
    dst_cluster = serializers.CharField(help_text=_("目标集群"), required=True)
    dst_cluster_password = serializers.CharField(help_text=_("目标集群密码"), allow_blank=True)


class DtsTestRedisConnectionSLZ(serializers.Serializer):
    data_copy_type = serializers.CharField(help_text=_("数据复制类型"), required=True)
    infos = serializers.ListField(
        help_text=_("复制列表"), child=DtsDataCopyBaseItemSLZ(), allow_empty=False, required=True
    )
