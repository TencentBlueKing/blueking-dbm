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
from backend.db_meta.models.sqlserver_dts import DtsStatus, SqlserverDtsInfo
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


class SQLServerDataMigrateHandler(object):
    """
    封装数据迁移相关接口
    """

    @classmethod
    def manual_terminate_sync(cls, ticket_id: int):
        """
        手动断开同步，需要发起一个断开同步的数据迁移单据
        @param ticket_id: 单据ID
        """
        ticket = Ticket.objects.get(id=ticket_id)
        # 直接沿用源单据details,标记手动终止
        ticket.details["manual_terminate"] = True
        return Ticket.create_ticket(
            ticket_type=TicketType.SQLSERVER_DATA_MIGRATE,
            creator=ticket.creator,
            bk_biz_id=ticket.bk_biz_id,
            remark=ticket.remark,
            details=ticket.details,
        )

    @classmethod
    def force_failed_migrate(cls, dts_id: int):
        """
        强制终止流程
        @param dts_id: int
        """
        # 修改dts迁移流程为已终止
        dts = SqlserverDtsInfo.objects.get(id=dts_id)
        dts.status = DtsStatus.Terminated.value
        dts.save()
