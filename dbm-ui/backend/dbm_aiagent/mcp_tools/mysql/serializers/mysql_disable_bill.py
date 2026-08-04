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


class SubmitBillMySQLDisableInputSerializer(serializers.Serializer):
    # 单次批量提单的集群数量上限，避免超大 IN 查询与巨型单据 details
    MAX_CLUSTER_DOMAINS = 50

    bk_biz_id = serializers.IntegerField(help_text=_("业务 ID"))
    cluster_domains = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
        help_text=_("集群域名列表（至少一个，最多 {} 个）".format(MAX_CLUSTER_DOMAINS)),
    )

    def validate_cluster_domains(self, value):
        if len(value) > self.MAX_CLUSTER_DOMAINS:
            raise serializers.ValidationError(
                _("一次最多提交 {} 个集群，当前提交 {} 个").format(self.MAX_CLUSTER_DOMAINS, len(value))
            )
        return value
