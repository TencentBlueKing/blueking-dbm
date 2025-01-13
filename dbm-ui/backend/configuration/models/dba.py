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
from typing import Dict, List, Tuple, Union

from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.constants import LEN_SHORT
from backend.configuration.constants import DEFAULT_DB_ADMINISTRATORS, PLAT_BIZ_ID, DBType


class DBAdministrator(models.Model):
    bk_biz_id = models.IntegerField(_("业务ID"))
    db_type = models.CharField(_("数据库类型"), choices=DBType.get_choices(), max_length=LEN_SHORT)
    users = models.JSONField(_("人员列表"))

    class Meta:
        verbose_name = verbose_name_plural = _("DBA人员设置(DBAdministrator)")
        unique_together = ("bk_biz_id", "db_type")

    @classmethod
    def list_biz_admins(cls, bk_biz_id: int) -> List[Dict[str, Union[str, List[str]]]]:
        """获取业务DBA人员"""
        # DBA 人员获取优先级： 业务 > 平台 > 默认空值
        valid_db_types = DBType.get_values()
        db_type_users_map = {db_type: [] for db_type in valid_db_types}
        # 仅过滤出当前系统支持的DB类型，忽略掉数据库中存量的数据
        for plat_dba in cls.objects.filter(bk_biz_id=PLAT_BIZ_ID, db_type__in=valid_db_types):
            db_type_users_map[plat_dba.db_type] = plat_dba.users
        for biz_dba in cls.objects.filter(bk_biz_id=bk_biz_id, db_type__in=valid_db_types):
            db_type_users_map[biz_dba.db_type] = biz_dba.users
        db_admins = [
            {
                "db_type": db_type,
                "db_type_display": DBType.get_choice_label(db_type),
                "users": users or ["admin"],
                "is_show": True,
            }
            for db_type, users in db_type_users_map.items()
        ]

        # TODO: 暂时去掉对cloud的展示，看后续云区域管理设计后在考虑
        cloud_index = [admins["db_type"] for admins in db_admins].index(DBType.Cloud.value)
        db_admins[cloud_index]["is_show"] = False

        return db_admins

    @classmethod
    def get_biz_db_type_admins(cls, bk_biz_id: int, db_type: str) -> List[str]:
        biz_admins = cls.list_biz_admins(bk_biz_id)
        for admin in biz_admins:
            if db_type == admin["db_type"]:
                return admin["users"] or DEFAULT_DB_ADMINISTRATORS
        return DEFAULT_DB_ADMINISTRATORS

    @classmethod
    def get_dba_for_db_type(cls, bk_biz_id: int, db_type: str) -> Tuple[List[str], List[str], List[str]]:
        """获取主dba、备dba、二线dba人员"""
        dba_list = cls.list_biz_admins(bk_biz_id)
        dba_content = next((dba for dba in dba_list if dba["db_type"] == db_type), {"users": []})
        users = dba_content.get("users", [])
        return users[:1], users[1:2], users[2:]

    @classmethod
    def get_manage_bizs(cls, db_type: str, username: str) -> Tuple[List[str], List[str]]:
        """获取待我处理，待我协助的业务"""
        manage_biz = DBAdministrator.objects.filter(db_type=db_type, users__0=username).values_list(
            "bk_biz_id", flat=True
        )

        assist_bizs = (
            DBAdministrator.objects.filter(db_type=db_type, users__contains=username)
            .exclude(users__0=username)
            .values_list("bk_biz_id", flat=True)
        )

        return list(manage_biz), list(assist_bizs)

    @classmethod
    def is_dba(cls, username: str) -> bool:
        return DBAdministrator.objects.filter(users__contains=username).exists()
