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
import collections
from typing import List

from backend.components import CCApi
from backend.db_meta.models import AppCache, DBModule
from backend.db_services.cmdb.exceptions import BkAppAttrAlreadyExistException
from backend.dbm_init.constants import CC_APP_ABBR_ATTR
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.permission import Permission

BIZModel = collections.namedtuple("BIZModel", ["bk_biz_id", "name", "english_name", "permission"])

ModuleModel = collections.namedtuple("ModuleModel", ["bk_biz_id", "db_module_id", "name"])


def list_bizs(user: str = "") -> List[BIZModel]:
    biz_infos = CCApi.search_business(
        {
            "fields": ["bk_biz_id", "bk_biz_name", CC_APP_ABBR_ATTR],
        },
        use_admin=True,
    ).get("info", [])

    # 填充权限字段
    biz_list = [
        BIZModel(biz["bk_biz_id"], biz["bk_biz_name"], biz.get(CC_APP_ABBR_ATTR) or "", {}) for biz in biz_infos
    ]
    biz_ids = [biz.bk_biz_id for biz in biz_list]
    biz_permission = Permission(username=user, request={}).policy_query(action=ActionEnum.DB_MANAGE, obj_list=biz_ids)

    for biz in biz_list:
        is_allowed = biz.bk_biz_id in biz_permission
        biz.permission[ActionEnum.DB_MANAGE.id] = is_allowed

    return sorted(biz_list, key=lambda biz: biz.permission[ActionEnum.DB_MANAGE.id], reverse=True)


def list_modules_by_biz(bk_biz_id: int, cluster_type: str) -> List[ModuleModel]:
    modules = DBModule.objects.filter(bk_biz_id=bk_biz_id, cluster_type=cluster_type)
    return [ModuleModel(m.bk_biz_id, m.db_module_id, m.db_module_name) for m in modules]


def set_db_app_abbr(bk_biz_id: int, db_app_abbr: str, raise_exception: bool = False):
    # 此处使用管理员账户请求(use_admin=True)，不校验用户对CMDB是否有查询/修改权限，在view层校验用户是否有修改英文缩写权限即可
    # 检查英文缩写是否已存在
    abbr = get_db_app_abbr(bk_biz_id)
    if not abbr:
        CCApi.update_business({"bk_biz_id": bk_biz_id, "data": {CC_APP_ABBR_ATTR: db_app_abbr}}, use_admin=True)
        AppCache.objects.update_or_create(defaults={"db_app_abbr": db_app_abbr}, bk_biz_id=bk_biz_id)
        return
    if raise_exception:
        raise BkAppAttrAlreadyExistException()


def get_db_app_abbr(bk_biz_id: int) -> str:
    abbr = CCApi.search_business(
        params={
            "fields": ["bk_biz_id", CC_APP_ABBR_ATTR],
            "biz_property_filter": {
                "condition": "AND",
                "rules": [{"field": "bk_biz_id", "operator": "equal", "value": int(bk_biz_id)}],
            },
        },
        use_admin=True,
    )["info"][0].get(CC_APP_ABBR_ATTR, "")
    return abbr
