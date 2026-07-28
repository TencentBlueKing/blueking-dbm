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


class TransferHostAcrossBizInputSerializer(serializers.Serializer):
    src_bk_biz_id = serializers.IntegerField(help_text=_("源业务 ID"))
    dst_bk_biz_id = serializers.IntegerField(help_text=_("目标业务 ID"))
    bk_host_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text=_("主机 ID 列表"),
    )

    def validate(self, attrs):
        if attrs["src_bk_biz_id"] == attrs["dst_bk_biz_id"]:
            raise serializers.ValidationError(_("src_bk_biz_id 与 dst_bk_biz_id 不能相同"))

        attrs["bk_host_ids"] = list(set(attrs["bk_host_ids"]))
        return attrs


class TransferHostAcrossBizOutputSerializer(serializers.Serializer):
    src_bk_biz_id = serializers.IntegerField(help_text=_("源业务 ID"))
    dst_bk_biz_id = serializers.IntegerField(help_text=_("目标业务 ID"))
    dst_idle_module_id = serializers.IntegerField(help_text=_("目标业务空闲机模块 ID"))
    bk_host_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text=_("已跨业务转移的主机 ID 列表"),
    )
