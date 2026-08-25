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
import time
from typing import Dict, List

from celery import shared_task

from backend import env
from backend.components.iamv4.client import AUTH_BATCH_SIZE, AUTHORIZATION_EXPIRED_DAYS, IAMV4Api
from backend.iam_app.dataclass.resources import BizDBTypeResourceMeta, BusinessResourceMeta, ResourceEnum
from backend.iam_app.dataclass.roles import RoleMeta, _all_roles
from backend.utils.basic import chunk_lists

logger = logging.getLogger("celery")


def get_dba_role(db_type: str) -> RoleMeta:
    """组件DBA角色。vm、k8s 等未纳入预置角色的组件取不到"""
    return _all_roles.get("dbm_{}_dba".format(db_type))


def make_dba_authorizations(username: str, bk_biz_id: int, db_type: str) -> List[Dict]:
    """
    把组件DBA角色按授权维度拆成多条授权记录。

    IAM 的 related_resource_type_id 是单值，一条记录只覆盖角色内绑定该资源类型的那批操作，
    因此角色关联几种资源类型就有几条记录。每条填哪个实例由该资源类型的拓扑决定：
    祖先链含 biz_dbtype 的收敛到本组件，其余填业务，由祖先覆盖其下全部实例
    """
    role = get_dba_role(db_type)
    biz_resource = {"type": BusinessResourceMeta.id, "id": str(bk_biz_id)}
    biz_dbtype_resource = {
        "type": BizDBTypeResourceMeta.id,
        "id": BizDBTypeResourceMeta.make_instance_id(bk_biz_id, db_type),
    }

    authorizations = []
    resource_type_ids = {action.to_json_v4()["resource_type_id"] for action in role.get_actions()}
    for resource_type_id in sorted(resource_type_ids):
        if not resource_type_id:
            # 无关资源的操作，按协议传空数组
            resources = []
        else:
            resource = ResourceEnum.get_resource_by_id(resource_type_id)
            topo = resource.to_json_v4()["ancestors"] + [resource_type_id]
            if BizDBTypeResourceMeta.id in topo:
                resources = [biz_dbtype_resource]
            elif BusinessResourceMeta.id in topo:
                resources = [biz_resource]
            else:
                # 拓扑不在业务树下(如全局的dbtype)，业务实例不是它的祖先，授权会被IAM拒绝。
                continue
        authorizations.append(
            {
                "subject": {"type": "user", "id": username},
                "role_id": role.id,
                "related_resource_type_id": resource_type_id,
                "resources": resources,
            }
        )
    return authorizations


def _is_grantable(db_type: str) -> bool:
    """V4未开启或该组件没有预置DBA角色时跳过，不阻断调用方的主流程"""
    if not env.ENABLE_IAM_V4:
        logger.info("[dba_role] iam v4 disabled, skip.")
        return False
    if not get_dba_role(db_type):
        logger.warning("[dba_role] no dba role for db_type=%s, skip.", db_type)
        return False
    return True


@shared_task
def grant_dba_role(username: str, bk_biz_id: int, db_type: str, operator: str = env.DEFAULT_USERNAME):
    """
    授予某人某业务下某组件的DBA角色权限，用于DBA人员变更与周期性续期。
    对同一组 subject + role + resources 重复调用即为续期
    """
    if not _is_grantable(db_type):
        return

    expired_at = int(time.time()) + AUTHORIZATION_EXPIRED_DAYS * 24 * 3600
    authorizations = [
        dict(authorization, expired_at=expired_at)
        for authorization in make_dba_authorizations(username, bk_biz_id, db_type)
    ]
    for chunk in chunk_lists(authorizations, AUTH_BATCH_SIZE):
        IAMV4Api.add_authorization(params=chunk, headers={"X-Bkiam-Operator": operator})

    logger.info("[grant_dba_role] success. user=%s, biz=%s, db_type=%s", username, bk_biz_id, db_type)


@shared_task
def revoke_dba_role(username: str, bk_biz_id: int, db_type: str, operator: str = env.DEFAULT_USERNAME):
    """
    撤销某人某业务下某组件的DBA角色权限，用于DBA人员移出。
    撤销要用与授权完全一致的 role_id + subject + resources 三元组
    """
    if not _is_grantable(db_type):
        return

    authorizations = make_dba_authorizations(username, bk_biz_id, db_type)
    for chunk in chunk_lists(authorizations, AUTH_BATCH_SIZE):
        IAMV4Api.revoke_authorization(params=chunk, headers={"X-Bkiam-Operator": operator})

    logger.info("[revoke_dba_role] success. user=%s, biz=%s, db_type=%s", username, bk_biz_id, db_type)


@shared_task
def sync_dba_role(
    bk_biz_id: int,
    db_type: str,
    new_users: List[str],
    old_users: List[str],
    operator: str = env.DEFAULT_USERNAME,
):
    """
    DBA人员变更后同步IAM角色授权：新进的人授予角色，移出的人撤销。
    两个列表的交集不动，避免无谓的重复授权
    """
    if not _is_grantable(db_type):
        return

    granted, revoked = set(new_users) - set(old_users), set(old_users) - set(new_users)
    # 逐人调用，单个人失败不影响其余人的同步，失败的人由周期任务兜底重试
    for username in sorted(granted):
        try:
            grant_dba_role(username, bk_biz_id, db_type, operator)
        except Exception:  # pylint: disable=broad-except
            logger.exception("[sync_dba_role] grant failed. user=%s, biz=%s, db_type=%s", username, bk_biz_id, db_type)

    for username in sorted(revoked):
        try:
            revoke_dba_role(username, bk_biz_id, db_type, operator)
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                "[sync_dba_role] revoke failed. user=%s, biz=%s, db_type=%s", username, bk_biz_id, db_type
            )
