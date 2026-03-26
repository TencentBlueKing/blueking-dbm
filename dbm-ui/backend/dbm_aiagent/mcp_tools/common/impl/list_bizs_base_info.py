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
from typing import List, Optional

from django.db.models import Q

from backend.configuration.constants import DEFAULT_DB_ADMINISTRATORS, DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache


def list_bizs_base_info(
    bk_biz_ids: Optional[List[int]] = None,
    app_abbrs: Optional[List[str]] = None,
) -> List[dict]:
    """获取平台业务的中文名、英文名和组件负责人"""

    # 先收集所有匹配的 bk_biz_id，最终用一次 __in 查询
    matched_biz_ids: set = set()

    if bk_biz_ids:
        matched_biz_ids.update(bk_biz_ids)

    if app_abbrs:
        for abbr in app_abbrs:
            # icontains 无法利用索引，所以这里用 OR 查询不会有额外的性能损失
            matched_biz_ids.update(
                AppCache.objects.filter(Q(db_app_abbr__icontains=abbr) | Q(bk_biz_name__icontains=abbr)).values_list(
                    "bk_biz_id", flat=True
                )
            )

    if matched_biz_ids:
        apps = AppCache.objects.filter(bk_biz_id__in=matched_biz_ids)
    else:
        apps = AppCache.objects.all()

    res = []
    for app in apps:
        bk_biz_id = app.bk_biz_id
        abbr = app.db_app_abbr

        comp_infos = []
        for db_type in DBType.get_values():
            biz_db_admin = DBAdministrator.objects.filter(bk_biz_id=bk_biz_id, db_type=db_type)
            if biz_db_admin.exists():
                admins = [u for u in biz_db_admin.first().users if u != DEFAULT_DB_ADMINISTRATORS]
            else:
                admins = DEFAULT_DB_ADMINISTRATORS

            if db_type == DBType.MySQL:
                comp_infos.append(
                    {"db_type": DBType.MySQL, "cluster_type": ClusterType.TenDBSingle, "dbas": admins[0:2]}
                )
                comp_infos.append({"db_type": DBType.MySQL, "cluster_type": ClusterType.TenDBHA, "dbas": admins[0:2]})
            else:
                comp_infos.append({"db_type": db_type, "cluster_type": db_type, "dbas": admins[0:2]})

        res.append({"bk_biz_id": bk_biz_id, "abbr": abbr, "db_components": comp_infos})

    return res
