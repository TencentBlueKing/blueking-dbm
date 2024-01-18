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
import logging
from typing import List

from backend.components import CCApi
from backend.db_meta.models import AppCache, DBModule
from backend.db_services.cmdb.exceptions import BkAppAttrAlreadyExistException
from backend.dbm_init.constants import CC_APP_ABBR_ATTR
from backend.exceptions import ApiError
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.permission import Permission

logger = logging.getLogger("root")
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
    # 查询 CC 的业务对象属性（英文缩写）"""
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


def list_cc_obj_user(bk_biz_id: int) -> list:
    # 查询 CC 的角色对象
    roles = {
        attr["bk_property_id"]: attr["bk_property_name"]
        for attr in CCApi.search_object_attribute({"bk_obj_id": "biz"}, use_admin=True)
        if attr["bk_property_type"] == "objuser"
    }
    results = CCApi.search_business(
        {
            "fields": list(roles.keys()),
            "biz_property_filter": {
                "condition": "AND",
                "rules": [{"field": "bk_biz_id", "operator": "equal", "value": int(bk_biz_id)}],
            },
        },
        use_admin=True,
    ).get("info", [])
    try:
        biz_info = results[0]
    except IndexError:
        biz_info = {}
    cc_obj_users = [
        {
            "id": role,
            "display_name": role_display,
            "logo": "",
            "type": "group",
            "members": [] if not biz_info.get(role) else [member for member in biz_info[role].split(",")],
        }
        for role, role_display in roles.items()
    ]
    # TODO dbm 角色录入 cmdb ？不合适， db type 会导致角色太多
    #  考虑以虚拟角色维护 DBA
    return cc_obj_users


def get_or_create_cmdb_module_with_name(bk_biz_id: int, bk_set_id: int, bk_module_name: str) -> int:
    """
    根据名称获取模块id(不同组件属于到不同的模块)
    @param bk_biz_id: 业务ID
    @param bk_set_id: 集群ID
    @param bk_module_name: 模块名字
    """
    res = CCApi.search_module(
        {
            "bk_biz_id": bk_biz_id,
            "bk_set_id": bk_set_id,
            "condition": {"bk_module_name": bk_module_name},
        },
        use_admin=True,
    )

    if res["count"] > 0:
        return res["info"][0]["bk_module_id"]

    res = CCApi.create_module(
        {
            "bk_biz_id": bk_biz_id,
            "bk_set_id": bk_set_id,
            "data": {"bk_parent_id": bk_set_id, "bk_module_name": bk_module_name},
        },
        use_admin=True,
    )
    return res["bk_module_id"]


def search_set_id(bk_biz_id: int, bk_set_name: str) -> int or None:
    """
    根据名称获取集群id
    @param bk_biz_id: 业务ID
    @param bk_set_name: 集群名
    """
    res = CCApi.search_set(
        params={
            "bk_biz_id": bk_biz_id,
            "fields": ["bk_set_name", "bk_set_id"],
            "condition": {"bk_set_name": bk_set_name},
        },
        use_admin=True,
    )
    if res["count"] > 0:
        return res["info"][0]["bk_set_id"]


def get_or_create_set_with_name(bk_biz_id: int, bk_set_name: str) -> int:
    """
    根据名称获取拓扑中的集群id
    @param bk_biz_id: 业务ID
    @param bk_set_name: 集群名
    """
    bk_set_id = search_set_id(bk_biz_id, bk_set_name)
    # 先进行一次查询，如果不存在则创建
    if bk_set_id:
        return bk_set_id
    try:
        res = CCApi.create_set(
            params={
                "bk_biz_id": bk_biz_id,
                "data": {
                    "bk_parent_id": bk_biz_id,
                    "bk_set_name": bk_set_name,
                },
            },
            use_admin=True,
        )
        return res["bk_set_id"]
    except ApiError as err:
        # 并发下可能出现重复创建，这里进行查询返回
        logger.error(f"failed to create set: {err}")
        bk_set_id = search_set_id(bk_biz_id, bk_set_name)
        if bk_set_id is None:
            raise err
        else:
            return bk_set_id
