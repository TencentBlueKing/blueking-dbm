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
import datetime
import logging
from functools import wraps
from typing import Dict, List, Optional, Union

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend import env
from backend.components import BKMonitorV3Api, CCApi
from backend.configuration.constants import PLAT_BIZ_ID, DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.constants import AppManagedStatus, AppOperateType
from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import AppCache, AppOperate, Cluster, Machine
from backend.db_monitor.models import DispatchGroup, NoticeGroup
from backend.dbm_init.constants import CC_APP_ABBR_ATTR
from backend.exceptions import ApiError
from backend.flow.utils.cc_manage import CcManage
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import get_request_key_id
from backend.iam_app.handlers.permission import Permission

logger = logging.getLogger("root")
OPERATE_DBA_MAP = {0: _("primary_dba"), 1: _("standby_dba"), 2: _("sec_dba")}


def decorator_permission_field():
    def wrapper(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            response = view_func(*args, **kwargs)
            bk_biz_id = get_request_key_id(args[1], key="bk_biz_id")
            response.data.setdefault("permission", {})
            result = Permission().is_allowed(action=ActionEnum.GLOBAL_DBA_ADMIN_EDIT, resources=[])
            response.data["permission"].update({ActionEnum.GLOBAL_DBA_ADMIN_EDIT.id: result})
            if bk_biz_id:
                Permission.insert_external_permission_field(
                    response,
                    actions=[ActionEnum.DBA_ADMIN_EDIT, ActionEnum.DB_MANAGE],
                    resource_meta=ResourceEnum.BUSINESS,
                    resource_id=int(bk_biz_id),
                )

            return response

        return wrapped_view

    return wrapper


class DBAdministratorHandler(object):
    """DBA人员处理"""

    @staticmethod
    def upsert_biz_admins(
        bk_biz_id: int,
        db_admins: List[Dict[str, Union[str, List[str]]]],
        username: str = None,
        operates: Optional[List] = None,
    ):
        from backend.db_monitor.tasks import update_dba_notice_group

        # 业务管理员
        db_type_biz_dba = {dba.db_type: dba.users for dba in DBAdministrator.objects.filter(bk_biz_id=bk_biz_id)}

        # 更新或创建业务管理员
        for dba in db_admins:
            db_type = dba["db_type"]
            new_dba = [user for user in dba["users"] if user]
            biz_dba = db_type_biz_dba.get(db_type, [])
            if new_dba == biz_dba:
                # 新 DBA 与 旧DBA 一致，也无需更新
                continue
            dba_obj, created = DBAdministrator.objects.update_or_create(
                bk_biz_id=bk_biz_id,
                db_type=db_type,
                defaults={"users": new_dba, "updater": username or "system", "update_at": timezone.now()},
            )

            update_dba_notice_group.apply_async(kwargs={"dba_id": dba_obj.id})

            if not new_dba:
                continue

            # 更新主机主备负责人
            operator = new_dba[0]
            bk_bak_operator = new_dba[1] if len(new_dba) > 1 else operator
            cluster_types = ClusterType.db_type_to_cluster_types(db_type)
            for cluster_type in cluster_types or []:
                bk_host_ids = [
                    machine.bk_host_id
                    for machine in Machine.objects.filter(cluster_type=cluster_type, bk_biz_id=bk_biz_id)
                ]
                if not bk_host_ids:
                    continue
                CcManage.batch_update_host(
                    [
                        {
                            "bk_host_id": bk_host_id,
                            "operator": operator,
                            "bk_bak_operator": bk_bak_operator,
                        }
                        for bk_host_id in bk_host_ids
                    ],
                    need_monitor=True,
                )

        if operates:
            DBAdministratorHandler.create_app_operate(username, operates)

    @staticmethod
    def get_dba_component_info(username: str, bk_biz_id: int, db_type: str):
        if bk_biz_id and db_type:
            if DBAdministrator.objects.filter(bk_biz_id=bk_biz_id, db_type=db_type, users__contains=username).exists():
                return {"is_biz_dba": True}
            else:
                return {"is_biz_dba": False}
        else:
            db_types = (
                DBAdministrator.objects.filter(users__contains=username).values_list("db_type", flat=True).distinct()
            )
            component = [
                {
                    "db_type": db_type,
                    "db_type_display": DBType.get_choice_label(db_type),
                }
                for db_type in db_types
            ]
            return {"component": component}

    @staticmethod
    def manage_biz(bk_biz_id, db_admins, username, app_code=None):
        from backend.db_monitor.tasks import sync_biz_dispatch_policy

        app_instance = AppCache.objects.filter(bk_biz_id=bk_biz_id).first()

        # 如果有app_code，说明是用户填写的, cc那边没有需要更新cc
        if app_code:
            CCApi.update_business({"bk_biz_id": bk_biz_id, "db_app_abbr": app_code}, use_admin=True)

        # 如果是本地表没存在的业务，先创建本地缓存表
        if not app_instance:
            info = CCApi.search_business(
                params={
                    "biz_property_filter": {
                        "condition": "AND",
                        "rules": [{"field": "bk_biz_id", "operator": "equal", "value": int(bk_biz_id)}],
                    },
                },
                use_admin=True,
            )["info"][0]
            defaults = {
                "bk_biz_name": info["bk_biz_name"],
                "language": info["language"],
                "time_zone": info["time_zone"],
                "bk_biz_maintainer": info["bk_biz_maintainer"],
                "db_app_abbr": info.get(CC_APP_ABBR_ATTR) or app_code,
            }
            app_instance, created = AppCache.objects.update_or_create(
                defaults=defaults,
                bk_biz_id=bk_biz_id,
            )

        operates = list()
        operates.append(
            {
                "bk_biz_id": bk_biz_id,
                "type": AppOperateType.MANAGED,
            }
        )
        # 填了DBA管理员则更新
        if db_admins:
            for dba in db_admins:
                users = [user for user in dba["users"] if user]
                dba_list = [users[:1], users[1:2], users[2:]]

                for index, dba_user in enumerate(dba_list):
                    if not dba_user:
                        continue
                    operates.append(
                        {
                            "bk_biz_id": bk_biz_id,
                            "type": AppOperateType.DBA_CHANGE,
                            "role": OPERATE_DBA_MAP[index],
                            "db_type": dba["db_type"],
                            "before": "",
                            "after": ",".join(dba_user),
                        }
                    )
            DBAdministratorHandler.upsert_biz_admins(bk_biz_id, db_admins, username)

        app_instance.managed_time = datetime.datetime.now(timezone.utc)
        app_instance.status = AppManagedStatus.MANAGED
        app_instance.save()

        sync_biz_dispatch_policy.apply_async(kwargs={"bk_biz_id": PLAT_BIZ_ID})

        # 添加操作记录
        DBAdministratorHandler.create_app_operate(username, operates)

    @staticmethod
    def delete_biz_admin(bk_biz_id):
        """
        删除业务下的dba人员，告警组和分派规则
        """
        group_queryset = NoticeGroup.objects.filter(bk_biz_id=bk_biz_id)
        monitor_group_ids = group_queryset.values_list("monitor_group_id", flat=True)
        if monitor_group_ids:
            BKMonitorV3Api.delete_user_groups({"ids": list(monitor_group_ids), "bk_biz_ids": [env.DBA_APP_BK_BIZ_ID]})

        dispatch_group = DispatchGroup.objects.filter(bk_biz_id=bk_biz_id)
        monitor_dispatch_ids = dispatch_group.values_list("monitor_dispatch_id", flat=True)
        if monitor_dispatch_ids:
            BKMonitorV3Api.delete_rule_group(
                {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "group_ids": list(monitor_dispatch_ids)}
            )

        DBAdministrator.objects.filter(bk_biz_id=bk_biz_id).delete()
        group_queryset.delete()
        dispatch_group.delete()

    @staticmethod
    def cancel_manage_biz(bk_biz_id, username):
        from backend.db_monitor.tasks import sync_biz_dispatch_policy

        if Cluster.objects.filter(bk_biz_id=bk_biz_id).exclude(phase=ClusterPhase.DESTROY.value).exists():
            raise ApiError(_("该业务下仍有集群, 不可以取消纳管"))

        # 删除业务下的dba, 告警组，分派规则
        DBAdministratorHandler.delete_biz_admin(bk_biz_id)

        # 清理标签
        app_instance = AppCache.objects.get(bk_biz_id=bk_biz_id)
        app_instance.tags.clear()
        app_instance.status = AppManagedStatus.UNMANAGED
        app_instance.save()

        # 添加操作记录
        AppOperate.objects.create(
            creator=username,
            bk_biz_id=bk_biz_id,
            operate_type=AppOperateType.CANCEL_MANAGED,
        )
        # 取消纳管业务，更新分派规则
        sync_biz_dispatch_policy.apply_async(kwargs={"bk_biz_id": PLAT_BIZ_ID})

    @staticmethod
    def batch_upsert_biz_admins(update_info, operates, username):
        for info in update_info:
            DBAdministratorHandler.upsert_biz_admins(info["bk_biz_id"], info["db_admins"], username)

        DBAdministratorHandler.create_app_operate(username, operates)

    @staticmethod
    def create_app_operate(username, operates):

        operate_list = []

        for operate in operates:
            operate_list.append(
                AppOperate(
                    creator=username,
                    bk_biz_id=operate.get("bk_biz_id"),
                    operate_type=operate.get("type"),
                    change_before=operate.get("before", ""),
                    change_after=operate.get("after", ""),
                    role=operate.get("role", ""),
                    db_type=operate.get("db_type", ""),
                )
            )

        AppOperate.objects.bulk_create(operate_list)
