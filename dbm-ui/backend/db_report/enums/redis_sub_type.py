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

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class RedisCheckSubType(StrStructuredEnum):
    Exporter = EnumField("redis_exporter", _("redis_exporter"))

    # Agent check subtypes
    ClusterMemoryCapacityRisk = EnumField("cluster_memory_capacity_risk", _("Cluster memory capacity risk"))
    BackendLoadSkew = EnumField("backend_load_skew", _("Backend load skew"))
    BackendDataSkew = EnumField("backend_data_skew", _("Backend data skew"))

    @staticmethod
    def get_agent_check_subtypes():
        """Agent check subtypes"""

        return [
            RedisCheckSubType.ClusterMemoryCapacityRisk,
            RedisCheckSubType.BackendLoadSkew,
            RedisCheckSubType.BackendDataSkew,
        ]
