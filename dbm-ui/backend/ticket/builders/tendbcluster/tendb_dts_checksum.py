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

from backend.ticket.builders.mysql.mysql_dts_checksum import force_dts_checksum_details
from backend.ticket.builders.tendbcluster.tendb_checksum import TendbChecksumDetailSerializer, TendbChecksumFlowBuilder


class TendbDtsChecksumDetailSerializer(TendbChecksumDetailSerializer):
    """
    ticket_param = {
        'ticket_type': TicketType.TENDBCLUSTER_DTS_CHECKSUM,
        "creator": 'admin',
        'helpers': [],
        'bk_biz_id': 21,
        'remark': TicketType.TENDBCLUSTER_DTS_CHECKSUM,
        'details': {
            'runtime_hour': 48,
            'timing': '2026-07-24T12:15:00+08:00',
            'infos': [
                {
                    'cluster_id': 126,
                    'checksum_scope': 'all',
                    'backup_infos': [
                        {
                            'db_patterns': ['*'],
                            'ignore_dbs': [],
                            'table_patterns': ['*'],
                            'ignore_tables': [],
                        }
                    ]
                }
            ],
            'need_manual_confirm': False,
        }
    }

    tk = Ticket.create_ticket(**ticket_param)
    """

    def validate(self, attrs):
        force_dts_checksum_details(attrs)
        return super().validate(attrs)


# @builders.BuilderFactory.register(TicketType.TENDBCLUSTER_DTS_CHECKSUM)
class TendbDtsChecksumFlowBuilder(TendbChecksumFlowBuilder):
    """
    TenDBCluster DTS 校验整个需要重新讨论
    """

    serializer = TendbDtsChecksumDetailSerializer

    def patch_ticket_detail(self):
        force_dts_checksum_details(self.ticket.details)
        super().patch_ticket_detail()
