"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.utils.translation import ugettext as _

from backend.components.mysql_partition.client import DBPartitionApi
from backend.db_services.partition.constants import PARTITION_NO_EXECUTE_CODE
from backend.db_services.partition.exceptions import DBPartitionCreateException
from backend.db_services.partition.serializers import PartitionDryRunSerializer
from backend.exceptions import ApiRequestError, ApiResultError
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


class PartitionHandler(object):
    """分区管理视图的处理函数"""

    @classmethod
    def create_and_execute_partition(cls, create_data):
        # 创建分区
        try:
            DBPartitionApi.create_conf(params=create_data)
        except (ApiRequestError, ApiResultError) as e:
            raise DBPartitionCreateException(_("分区管理创建失败，创建参数:{}, 错误信息: {}").format(create_data, e))

        # 判断是否需要执行分区
        partition_dry_run = PartitionDryRunSerializer(data=create_data)
        partition_info = DBPartitionApi.dry_run(partition_dry_run.data, raw=True)
        if partition_info["code"] == PARTITION_NO_EXECUTE_CODE:
            return

        # 执行分区单据
        create_data.update(partition_objects=partition_info["data"])
        Ticket.create_ticket(
            ticket_type=TicketType.MYSQL_PARTITION,
            creator=create_data["creator"],
            bk_biz_id=create_data["bk_biz_id"],
            remark=_("创建分区后自动执行的分区单据"),
            details=create_data,
            auto_execute=True,
        )
