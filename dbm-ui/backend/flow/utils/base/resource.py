"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import List

from django.db import transaction

from backend.db_services.dbresource.handlers import ResourceHandler
from backend.ticket.models import Ticket

# 资源池相关的flow通用函数


def write_recycle_hosts_into_ticket(ticket_id: int, hosts: List):
    """
    将待回收的主机写入到ticket中
    @param ticket_id: 单据id
    @param hosts: 待回收主机(一个列表字典，item必须包含ip, bk_host_id，bk_cloud_id)
    """

    from backend.ticket.builders.common.base import HostInfoSerializer

    # 获取待回收主机
    hosts = HostInfoSerializer(hosts, many=True).data
    hosts = ResourceHandler.standardized_resource_host(hosts)

    # 追加到单据的recycle hosts信息
    # 绑定事务操作
    with transaction.atomic():
        # 使用 select_for_update 在事务内锁定这条记录，防止并发修改
        ticket = Ticket.objects.select_for_update().get(id=ticket_id)

        # 获取当前的 recycle_hosts 列表，如果不存在则使用空列表
        current_hosts = ticket.details.get("recycle_hosts", [])

        # 将新的 hosts 列表追加到现有列表中
        # 注意：这里假设 hosts 本身也是一个列表。如果是单个元素，请用 [hosts]
        updated_hosts = current_hosts + hosts

        # 更新 details 字典中的 recycle_hosts 键
        ticket.details["recycle_hosts"] = updated_hosts

        # 保存到数据库
        ticket.save()
