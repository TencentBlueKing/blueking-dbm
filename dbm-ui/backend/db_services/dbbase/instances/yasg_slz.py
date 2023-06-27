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


class CheckInstancesSLZ(serializers.Serializer):
    instance_addresses = serializers.ListField(
        help_text=_("实例地址列表"), child=serializers.CharField(help_text=_("实例地址(ip:port)"), required=True)
    )

    class Meta:
        swagger_schema_fields = {"example": {"instance_addresses": ["127.0.0.1", "127.0.0.1:20000"]}}


class CheckInstancesResSLZ(serializers.Serializer):
    class Meta:
        swagger_schema_fields = {
            "example": [
                {
                    "bk_host_id": 2000059062,
                    "ip": "127.0.0.1",
                    "bk_cloud_id": 0,
                    "port": 10000,
                    "cluster_id": 1,
                    "role": "proxy",
                    "meta": {"scope_type": "biz", "scope_id": "2005000194", "bk_biz_id": 2005000194},
                    "host_id": 2000059062,
                    "ipv6": "",
                    "cloud_id": 0,
                    "cloud_vendor": "",
                    "agent_id": "",
                    "host_name": "",
                    "os_name": "1",
                    "alive": 1,
                    "cloud_area": {"id": 0, "name": "default area"},
                    "biz": {"id": 2005000194, "name": _("测试业务")},
                    "bk_mem": None,
                    "bk_disk": None,
                    "bk_cpu": None,
                }
            ]
        }
