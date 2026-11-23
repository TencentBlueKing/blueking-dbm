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
from typing import Any, Dict, List

from django.db.models import Q, QuerySet
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import BizSettingsEnum
from backend.configuration.models import BizSettings
from backend.db_meta.api.cluster_state.fields.base import NativeStateField
from backend.db_meta.api.cluster_state.values import StateValue
from backend.db_meta.enums import ClusterType, StateValueType
from backend.db_meta.models import Cluster


class IndependentlyHostedField(NativeStateField):
    key = "independently_hosted"
    name = _("主机独立托管")
    value_type = StateValueType.BOOL.value
    filterable = False
    writable = False

    @classmethod
    def query_set(cls) -> QuerySet:
        return BizSettings.objects.filter(key=BizSettingsEnum.INDEPENDENT_HOSTING_DB_TYPES.value)

    def batch_get(self, cluster_ids: List[int]) -> Dict[int, StateValue]:
        cluster_objs = list(Cluster.objects.filter(id__in=cluster_ids).values("id", "bk_biz_id", "cluster_type"))
        bk_biz_ids = list(set(cluster_obj["bk_biz_id"] for cluster_obj in cluster_objs))

        independently_config = {
            record.bk_biz_id: set(record.value or []) for record in self.query_set().filter(bk_biz_id__in=bk_biz_ids)
        }

        res = {}

        for cluster_obj in cluster_objs:
            configured = independently_config.get(cluster_obj["bk_biz_id"], set())
            try:
                db_type = ClusterType.cluster_type_to_db_type(cluster_obj["cluster_type"])
            except ValueError:
                db_type = cluster_obj["cluster_type"]

            res[cluster_obj["id"]] = self.make_state(
                db_type in configured or cluster_obj["cluster_type"] in configured
            )

        return res

    def filter_q(self, op: str, values: List[Any]) -> Q:
        raise Exception(_("当前未支持"))

    def mark(self, cluster: Cluster, value: Any, extra: Any = None, operator: str = "") -> None:
        raise Exception(_("当前未支持"))

    def unmark(self, cluster: Cluster, operator: str = "") -> None:
        raise Exception(_("当前未支持"))
