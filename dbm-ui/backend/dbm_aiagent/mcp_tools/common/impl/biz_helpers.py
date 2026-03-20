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
from typing import List, Union

from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.models import AppCache


def get_biz_by_abbr(app_abbr: str, detailed: bool = False) -> Union[List[int], List[dict]]:
    """Return biz IDs or rich dicts matching `app_abbr` via db_app_abbr substring."""
    app_abbr = app_abbr.strip().lower()
    queryset = AppCache.objects.filter(db_app_abbr__icontains=app_abbr)
    if detailed:
        rows = queryset.values_list("bk_biz_id", "bk_biz_name", "db_app_abbr")
        return [{"bk_biz_id": bid, "app_name": name, "abbr": abbr} for bid, name, abbr in rows]
    return list(queryset.values_list("bk_biz_id", flat=True))


def get_managed_biz(username: str, db_type: DBType, detailed: bool = False) -> Union[List[int], List[dict]]:
    """
    Return biz IDs or rich dicts for bizs managed by `username` for `db_type`.

    Raises ValueError if the user manages no bizs of that type.
    """
    manage_biz_ids = list(
        DBAdministrator.objects.filter(db_type=db_type.value, users__0=username).values_list("bk_biz_id", flat=True)
    )
    if not manage_biz_ids:
        raise ValueError(f"No {db_type} biz found for user {username!r}")
    if detailed:
        rows = AppCache.objects.filter(bk_biz_id__in=manage_biz_ids).values_list(
            "bk_biz_id", "bk_biz_name", "db_app_abbr"
        )
        return [{"bk_biz_id": bid, "app_name": name, "abbr": abbr} for bid, name, abbr in rows]
    return manage_biz_ids
