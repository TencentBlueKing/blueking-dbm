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
from django.utils.translation import ugettext as _

from blue_krill.data_types.enum import EnumField, StructuredEnum


class ResourceType(str, StructuredEnum):
    CLUSTER_NAME = EnumField("cluster_name", _("集群名"))
    CLUSTER_DOMAIN = EnumField("cluster_domain", _("集群域名"))
    INSTANCE = EnumField("instance", _("实例"))
    TICKET = EnumField("ticket", _("单号"))
    TASK = EnumField("task", _("任务"))
    MACHINE = EnumField("machine", _("主机"))
    RESOURCE_POOL = EnumField("resource_pool", _("资源池主机"))


class FilterType(str, StructuredEnum):
    CONTAINS = EnumField("CONTAINS", _("模糊"))
    EXACT = EnumField("EXACT", _("精确"))
