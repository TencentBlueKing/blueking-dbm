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
from typing import Dict, List, Union

from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.constants import LEN_SHORT
from backend.configuration.constants import DEFAULT_DB_ADMINISTRATORS, PLAT_BIZ_ID, DBType


class DBAdministrator(models.Model):
    bk_biz_id = models.IntegerField(_("业务ID"))
    db_type = models.CharField(_("数据库类型"), choices=DBType.get_choices(), max_length=LEN_SHORT)
    users = models.JSONField(_("人员列表"))

    class Meta:
        verbose_name = _("DBA人员设置")
        verbose_name_plural = _("DBA人员设置")
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
            {"db_type": db_type, "db_type_display": DBType.get_choice_label(db_type), "users": users, "is_show": True}
            for db_type, users in db_type_users_map.items()
        ]

        # TODO: 暂时去掉对cloud的展示，看后续云区域管理设计后在考虑
        cloud_index = [admins["db_type"] for admins in db_admins].index(DBType.Cloud.value)
        db_admins[cloud_index]["is_show"] = False

        return db_admins

    @classmethod
    def upsert_biz_admins(cls, bk_biz_id: int, db_admins: List[Dict[str, Union[str, List[str]]]]):
        # 平台管理员
        db_type_platform_dba = {dba.db_type: dba.users for dba in cls.objects.filter(bk_biz_id=0)}

        # 业务管理员
        db_type_biz_dba = {dba.db_type: dba.users for dba in cls.objects.filter(bk_biz_id=bk_biz_id)}

        # 更新或创建业务管理员
        for dba in db_admins:
            db_type = dba["db_type"]
            new_dba = dba["users"]
            platform_dba = db_type_platform_dba.get(db_type, [])
            biz_dba = db_type_biz_dba.get(db_type, [])
            if set(new_dba) == set(platform_dba) and not biz_dba:
                # 业务新设置的与平台人员一致，则无需新建
                continue
            cls.objects.update_or_create(bk_biz_id=bk_biz_id, db_type=db_type, defaults={"users": new_dba})

    @classmethod
    def get_biz_db_type_admins(cls, bk_biz_id: int, db_type: str) -> List[str]:
        biz_admins = cls.list_biz_admins(bk_biz_id)
        for admin in biz_admins:
            if db_type == admin["db_type"]:
                return admin["users"] or DEFAULT_DB_ADMINISTRATORS
        return DEFAULT_DB_ADMINISTRATORS
