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

from blue_krill.data_types.enum import EnumField, StructuredEnum


class MetaCheckSubType(str, StructuredEnum):
    InstanceBelong = EnumField("instance_belong", _("实例集群归属"))
    ReplicateRole = EnumField("replicate_role", _("数据同步实例角色"))
    ClusterTopo = EnumField("cluster_topo", _("集群结构"))
    AloneInstance = EnumField("alone_instance", _("孤立的实例"))
    StatusAbnormal = EnumField("status_abnormal", _("不属于RUNNING状态"))
