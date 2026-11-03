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
from typing import Any, Dict, List, Mapping, Tuple

from django.db.models import Q
from django.utils.translation import gettext as _

from backend.db_meta.api.cluster_state.service import ClusterStateService
from backend.db_meta.enums import StateFilterOperator
from backend.db_meta.exceptions import ClusterStateException
from backend.exceptions import ValidationError

STATE_FILTER_PREFIX = "state__"


def collect_state_filters(params: Mapping[str, Any]) -> Dict[str, str]:
    """从请求参数中收集 state__ 开头的过滤参数"""
    return {key: params[key] for key in params if key.startswith(STATE_FILTER_PREFIX)}


def split_state_param(param: str) -> Tuple[str, str]:
    """state__{key} / state__{key}__gte / state__{key}__lte -> (key, op)"""
    body = param[len(STATE_FILTER_PREFIX) :]
    for op in (StateFilterOperator.GTE.value, StateFilterOperator.LTE.value):
        suffix = f"__{op}"
        if body.endswith(suffix):
            return body[: -len(suffix)], op
    return body, StateFilterOperator.IN.value


def build_state_filter_q(cluster_types: List[str], state_filters: Dict[str, str]) -> Q:
    """
    将列表接口的 state__* 参数转为 Cluster 过滤条件，多个参数之间 AND。
    参数值按逗号拆分后交给 ClusterStateService.filter_q，校验失败转为 ValidationError
    """
    query = Q()
    for param, raw in state_filters.items():
        key, op = split_state_param(param)
        values = [item.strip() for item in str(raw).split(",") if item.strip()]
        try:
            query &= ClusterStateService.filter_q(cluster_types, key, op, values)
        except ClusterStateException as err:
            raise ValidationError(_("状态过滤参数 {} 不合法: {}").format(param, err.message))
    return query
