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
from backend.ticket import builders
from backend.ticket.builders.common.constants import MySQLChecksumTicketMode
from backend.ticket.builders.mysql.mysql_checksum import MySQLChecksumDetailSerializer, MySQLChecksumFlowBuilder
from backend.ticket.constants import TicketType


def force_dts_checksum_details(details: dict) -> None:
    details["dts_mode"] = True
    details["is_sync_non_innodb"] = False
    details["data_repair"] = {"is_repair": False, "mode": MySQLChecksumTicketMode.MANUAL}


class MySQLDtsChecksumDetailSerializer(MySQLChecksumDetailSerializer):
    """
    ticket_param = {
        'ticket_type': TicketType.MYSQL_DTS_CHECKSUM,
        "creator": 'admin',
        'helpers': [],
        'bk_biz_id': 21,
        'remark': TicketType.MYSQL_DTS_CHECKSUM,
        'details': {
            'runtime_hour': 48,
            'timing': '2026-07-24T12:15:00+08:00',
            'infos': [
                {
                    'db_patterns': ['*'],
                    'ignore_dbs': [],
                    'table_patterns': ['*'],
                    'ignore_tables': [],
                    'cluster_id': 127,
                }
            ],
            'need_manual_confirm': False,
            'dts_mode': True
        }
    }

    tk = Ticket.create_ticket(**ticket_param)
    """

    def validate(self, attrs):
        force_dts_checksum_details(attrs)
        return super().validate(attrs)


@builders.BuilderFactory.register(TicketType.MYSQL_DTS_CHECKSUM)
class MySQLDtsChecksumFlowBuilder(MySQLChecksumFlowBuilder):
    serializer = MySQLDtsChecksumDetailSerializer

    @property
    def need_itsm(self):
        """迁移流程自动挂出的校验子单，跳过 ITSM 审批。"""
        return False

    def patch_ticket_detail(self):
        force_dts_checksum_details(self.ticket.details)
        super().patch_ticket_detail()
