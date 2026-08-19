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

import json
import logging
from typing import Any, Dict, List, Tuple

from django.utils.translation import gettext_lazy as _

from backend import env
from backend.components.base import BaseApi, DataAPI
from backend.components.domains import BKIAMV4_APIGW_DOMAIN
from backend.exceptions import ApiError

logger = logging.getLogger("root")

# 权限模型管理。system_id 固定为 bk_dbm，直接拼进路径
MODEL_URL = f"/api/v1/open/rbac/model/systems/{env.BK_IAM_SYSTEM_ID}"
# 鉴权
AUTH_URL = f"/api/v1/open/rbac/authorization/systems/{env.BK_IAM_SYSTEM_ID}"
# 授权管理
MGMT_URL = f"/api/v1/open/rbac/mgmt/systems/{env.BK_IAM_SYSTEM_ID}"
# 系统共享查询。注：IAM侧路径拼写为 rabc 而非 rbac，需照此调用
SHARE_MODEL_URL = f"/api/v1/open/rabc/share/model/systems/{env.BK_IAM_SYSTEM_ID}"

# 分页拉取的每页条数，list_role 协议明确上限为100，其余列表接口未给上限，统一按100取
LIST_PAGE_SIZE = 100
# 批量创建的分片大小，DBM有近500个动作，一次性提交容易触发网关的包体限制
BATCH_CREATE_SIZE = 100


class IAMV4DataAPI(DataAPI):
    """
    IAM V4 接口。与 DataAPI 的差异集中在响应形态上：
    1. 成功状态码不止200，批量创建返回201，更新/删除返回204且响应体为空
    2. 响应遵循蓝鲸新版API协议，成功只有 {"data": ..., "request_id": ...}，没有 result/code/message
    """

    SUCCESS_STATUS_CODES = (200, 201, 204)

    def _send(self, params: Any, headers: Dict, use_admin: bool = False):
        response = super()._send(params, headers, use_admin=use_admin)
        if response.status_code not in self.SUCCESS_STATUS_CODES:
            # 失败响应形态为 {"error": {"code": ..., "message": ...}}，交由基类按原文报错
            return response

        try:
            content = response.json()
        except ValueError:
            # 204 无响应体
            content = {}
        content.setdefault("data", None)
        content.update({"result": True, "code": 0, "message": ""})

        response.status_code = self.HTTP_STATUS_OK
        response._content = json.dumps(content).encode("utf-8")
        return response


class _IAMV4Api(BaseApi):
    MODULE = _("权限中心V4")
    BASE = BKIAMV4_APIGW_DOMAIN

    def generate_data_api(self, method, url, description, **kwargs):
        return IAMV4DataAPI(
            method=method, base=self.BASE, url=url, module=self.MODULE, description=description, **kwargs
        )

    def __init__(self):
        self.create_system = self.generate_data_api(
            method="POST",
            url="/api/v1/open/rbac/model/systems/",
            description=_("注册系统"),
        )
        self.retrieve_system = self.generate_data_api(
            method="GET",
            url=f"{MODEL_URL}/",
            description=_("查询系统信息"),
        )
        self.update_system = self.generate_data_api(
            method="PUT",
            url=f"{MODEL_URL}/",
            description=_("更新系统信息"),
        )
        self.retrieve_system_auth_token = self.generate_data_api(
            method="GET",
            url=f"{MODEL_URL}/auth-token/",
            description=_("获取系统AuthToken"),
        )
        self.share_retrieve_system = self.generate_data_api(
            method="GET",
            url=f"{SHARE_MODEL_URL}/",
            description=_("查询系统详情"),
        )
        self.batch_create_resource_type = self.generate_data_api(
            method="POST",
            url=f"{MODEL_URL}/resource-types/",
            description=_("批量创建资源类型"),
        )
        self.list_resource_type = self.generate_data_api(
            method="GET",
            url=f"{MODEL_URL}/resource-types/",
            description=_("查询资源类型列表"),
        )
        self.update_resource_type = self.generate_data_api(
            method="PUT",
            url=f"{MODEL_URL}/resource-types/{{resource_type_id}}/",
            description=_("更新资源类型"),
        )
        self.delete_resource_type = self.generate_data_api(
            method="DELETE",
            url=f"{MODEL_URL}/resource-types/{{resource_type_id}}/",
            description=_("删除资源类型"),
        )
        self.batch_create_action = self.generate_data_api(
            method="POST",
            url=f"{MODEL_URL}/actions/",
            description=_("批量创建操作"),
        )
        self.list_action = self.generate_data_api(
            method="GET",
            url=f"{MODEL_URL}/actions/",
            description=_("查询操作列表"),
        )
        self.update_action = self.generate_data_api(
            method="PUT",
            url=f"{MODEL_URL}/actions/{{action_id}}/",
            description=_("更新操作"),
        )
        self.delete_action = self.generate_data_api(
            method="DELETE",
            url=f"{MODEL_URL}/actions/{{action_id}}/",
            description=_("删除操作"),
        )
        self.batch_create_role = self.generate_data_api(
            method="POST",
            url=f"{MODEL_URL}/roles/",
            description=_("批量创建角色"),
        )
        self.list_role = self.generate_data_api(
            method="GET",
            url=f"{MODEL_URL}/roles/",
            description=_("查询角色列表"),
        )
        self.update_role = self.generate_data_api(
            method="PUT",
            url=f"{MODEL_URL}/roles/{{role_id}}/",
            description=_("更新角色"),
        )
        self.delete_role = self.generate_data_api(
            method="DELETE",
            url=f"{MODEL_URL}/roles/{{role_id}}/",
            description=_("删除角色"),
        )
        self.direct_auth = self.generate_data_api(
            method="POST",
            url=f"{AUTH_URL}/auth/",
            description=_("直接鉴权"),
        )
        # 一次返回该动作下所有资源类型的授权实例，调用方自行按类型过滤
        self.list_authorized_resource = self.generate_data_api(
            method="POST",
            url=f"{AUTH_URL}/relation/authorized-resources/",
            description=_("查询有权限的资源实例"),
        )
        # body为授权记录数组，单次最多20条，调用时必须带上 X-Bkiam-Operator 头
        self.add_authorization = self.generate_data_api(
            method="POST",
            url=f"{MGMT_URL}/authorizations/",
            description=_("批量角色授权"),
        )

    def batch_create_role_action(self, role_id: str, actions: List[Dict]):
        """
        批量给角色添加操作，actions项为 {id, resource_type_id}。
        body是数组，无法像其他接口那样用params渲染路径上的role_id，故单独构造
        """
        api = self.generate_data_api(
            method="POST", url=f"{MODEL_URL}/roles/{role_id}/actions/", description=_("批量添加角色操作")
        )
        return api(params=actions)

    def batch_delete_role_action(self, role_id: str, action_ids: List[str]):
        """批量删除角色操作，待删除的操作以query传递。IAM要求每种资源类型下至少保留一个操作"""
        api = self.generate_data_api(
            method="DELETE",
            url=f"{MODEL_URL}/roles/{role_id}/actions/?ids={','.join(action_ids)}",
            description=_("批量删除角色操作"),
        )
        return api()

    @staticmethod
    def _chunks(items: List, size: int = BATCH_CREATE_SIZE):
        for index in range(0, len(items), size):
            yield items[index : index + size]

    @staticmethod
    def _list_all(list_api: DataAPI) -> List[Dict]:
        """按页拉全列表接口的数据"""
        page, all_results, seen_ids = 1, [], set()
        while True:
            data = list_api(params={"page": page, "page_size": LIST_PAGE_SIZE})
            results = data.get("results") or [] if isinstance(data, dict) else (data or [])
            new_results = [item for item in results if item["id"] not in seen_ids]
            all_results.extend(new_results)
            seen_ids.update(item["id"] for item in new_results)
            # 未满一页说明已取完；本页没有新数据说明接口未按page分页，避免死循环
            if len(results) < LIST_PAGE_SIZE or not new_results:
                return all_results
            page += 1

    @staticmethod
    def _split_by_remote(local: List[Dict], remote: List[Dict]) -> Tuple[List, List]:
        """按id把本地定义分成待创建和待更新两部分"""
        remote_ids = {item["id"] for item in remote}
        created = [item for item in local if item["id"] not in remote_ids]
        updated = [item for item in local if item["id"] in remote_ids]
        return created, updated

    def migrate_model(self, model: Dict, dry_run: bool = False) -> Dict[str, Any]:
        """
        迁移权限模型，model 的结构为 {"system": {}, "resource_types": [], "actions": [], "roles": []}。

        V4没有V3的upsert与migration机制，创建与更新是分离的接口，需要先拉远端现状再判断走哪条。
        系统只做首次注册，已存在则不动；资源类型、操作和角色不存在则创建、存在则更新，不做删除。
        """
        try:
            self.retrieve_system()
            system_exists = True
        except ApiError as e:
            # 系统未注册时接口返回404，此处无法与网络异常区分，真实故障会在后续的写操作中再次暴露
            logger.info("[migrate_model] retrieve system failed, treat as unregistered: %s", e)
            system_exists = False

        # 系统必须先注册，后续的模型接口才可用
        if not system_exists and not dry_run:
            self.create_system(params=model["system"])

        # 获取创建资源/更新资源
        new_resources, mod_resources = self._split_by_remote(
            model["resource_types"], self._list_all(self.list_resource_type) if system_exists else []
        )
        # 获取创建操作/更新操作
        new_actions, mod_actions = self._split_by_remote(
            model["actions"], self._list_all(self.list_action) if system_exists else []
        )
        # 获取创建角色/更新角色
        remote_roles = self._list_all(self.list_role) if system_exists else []
        new_roles, mod_roles = self._split_by_remote(model["roles"], remote_roles)

        # 角色的动作只能增量追加，V4没有整体覆盖的接口
        remote_role_actions = {item["id"]: {a["id"] for a in item.get("actions") or []} for item in remote_roles}
        add_role_actions = {
            role["id"]: [a for a in role["actions"] if a["id"] not in remote_role_actions[role["id"]]]
            for role in mod_roles
        }
        add_role_actions = {role_id: actions for role_id, actions in add_role_actions.items() if actions}

        if not dry_run:
            # 资源类型：动作与角色都引用它，必须最先注册
            for chunk in self._chunks(new_resources):
                self.batch_create_resource_type(params=chunk)
            # 资源类型的 name 与 ancestors 均可更新
            for item in mod_resources:
                params = {"resource_type_id": item["id"], "name": item["name"], "ancestors": item["ancestors"]}
                self.update_resource_type(params=params)
            # 操作：角色引用它，需先于角色注册
            for chunk in self._chunks(new_actions):
                self.batch_create_action(params=chunk)
            # 操作只能更新 name，资源类型变更需要重建操作
            for item in mod_actions:
                self.update_action(params={"action_id": item["id"], "name": item["name"]})
            # 角色：创建时一并带上全量动作
            for chunk in self._chunks(new_roles):
                self.batch_create_role(params=chunk)
            # 角色只能更新 name 与 description，不含动作
            for item in mod_roles:
                params = {"role_id": item["id"], "name": item["name"], "description": item["description"]}
                self.update_role(params=params)
            # 存量角色的动作变更走单独的接口追加
            for role_id, actions in add_role_actions.items():
                for chunk in self._chunks(actions):
                    self.batch_create_role_action(role_id, chunk)

        summary = {
            "dry_run": dry_run,
            "system": "exists" if system_exists else "created",
            "resource_types": {
                "created": [item["id"] for item in new_resources],
                "updated": [item["id"] for item in mod_resources],
            },
            "actions": {
                "created": [item["id"] for item in new_actions],
                "updated": [item["id"] for item in mod_actions],
            },
            "roles": {
                "created": [item["id"] for item in new_roles],
                "updated": [item["id"] for item in mod_roles],
                "action_added": {role_id: [a["id"] for a in acts] for role_id, acts in add_role_actions.items()},
            },
        }
        # 变更项可达数百个，日志只记数量，明细由返回值给调用方
        counts = {
            key: {field: len(value) for field, value in item.items()}
            for key, item in summary.items()
            if isinstance(item, dict)
        }
        logger.info("[migrate_model] dry_run=%s, changes=%s", dry_run, json.dumps(counts, ensure_ascii=False))
        return summary


IAMV4Api = _IAMV4Api()
