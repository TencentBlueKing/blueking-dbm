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
from typing import Dict, List, Union

from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Machine
from backend.flow.utils.cc_manage import CcManage

logger = logging.getLogger("root")


class DBAdministratorHandler(object):
    """DBA人员处理"""

    @staticmethod
    def upsert_biz_admins(bk_biz_id: int, db_admins: List[Dict[str, Union[str, List[str]]]]):
        from backend.db_periodic_task.local_tasks.db_monitor import update_dba_notice_group

        # 平台管理员
        db_type_platform_dba = {dba.db_type: dba.users for dba in DBAdministrator.objects.filter(bk_biz_id=0)}

        # 业务管理员
        db_type_biz_dba = {dba.db_type: dba.users for dba in DBAdministrator.objects.filter(bk_biz_id=bk_biz_id)}

        # 更新或创建业务管理员
        for dba in db_admins:
            db_type = dba["db_type"]
            new_dba = [user for user in dba["users"] if user]
            platform_dba = db_type_platform_dba.get(db_type, [])
            biz_dba = db_type_biz_dba.get(db_type, [])
            if new_dba == platform_dba and not biz_dba:
                # 业务新设置的与平台人员一致，则无需新建
                continue
            if new_dba == biz_dba:
                # 新 DBA 与 旧DBA 一致，也无需更新
                continue
            dba_obj, created = DBAdministrator.objects.update_or_create(
                bk_biz_id=bk_biz_id, db_type=db_type, defaults={"users": new_dba}
            )
            # 更新告警组
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
