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
import logging
from typing import Any, Dict, List, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DEFAULT_CLUSTER_STATE_DISPLAY_FIELDS, SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.api.cluster_state import ClusterStateService
from backend.db_meta.exceptions import ClusterStateException
from backend.db_meta.models import Cluster

logger = logging.getLogger("root")


class ClusterStateHandler:
    def __init__(self, bk_biz_id: int):
        self.bk_biz_id = bk_biz_id

    @classmethod
    def get_display_fields(cls, cluster_type: str, field_keys: List[str]) -> List[str]:
        """
        读取展示配置，过滤掉该集群类型未声明的字段。
        配置里没有该集群类型时取默认值，新接入的集群类型不需要先改线上配置
        """
        config = SystemSettings.get_setting_value(
            SystemSettingsEnum.CLUSTER_STATE_DISPLAY_FIELDS.value, default=DEFAULT_CLUSTER_STATE_DISPLAY_FIELDS
        )
        display_fields = (config or {}).get(cluster_type, DEFAULT_CLUSTER_STATE_DISPLAY_FIELDS.get(cluster_type, []))
        unknown_fields = [key for key in display_fields if key not in field_keys]
        if unknown_fields:
            logger.warning("cluster state display fields %s not declared for %s", unknown_fields, cluster_type)
        return [key for key in display_fields if key in field_keys]

    def get_schema(self, cluster_type: str) -> Dict[str, Any]:
        state_fields = ClusterStateService.get_fields(cluster_type)
        return {
            "cluster_type": cluster_type,
            "fields": [state_field.to_schema() for state_field in state_fields.values()],
            "display_fields": self.get_display_fields(cluster_type, list(state_fields)),
        }

    def get_detail(self, cluster_id: int, key: str) -> Optional[Dict[str, Any]]:
        cluster = Cluster.objects.filter(id=cluster_id, bk_biz_id=self.bk_biz_id).first()
        if cluster is None:
            raise ClusterStateException(message=_("业务 {} 下不存在集群 {}").format(self.bk_biz_id, cluster_id))
        detail = ClusterStateService.get_detail(cluster, key)
        return detail.to_dict() if detail else None
