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
from django.utils.translation import gettext_lazy as _

from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import (
    BaseRedisTicketFlowBuilder,
    RedisBasePauseParamBuilder,
    RedisOpsBaseDetailSerializer,
)
from backend.ticket.constants import TicketType


class RedisBackupDetailSerializer(RedisOpsBaseDetailSerializer):
    pass


class RedisBackupFlowParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_backup

    def format_ticket_data(self):
        """
        {
            "rules": [
                {
                    "cluster_id": 120,
                    "domain": "cache.twemproxyredisinstance.hs1.dba.db",
                    "target": "slave",
                    "backup_type": "normal_backup"
                },
                {
                    "cluster_id": 121,
                    "domain": "cache.twemproxyredisinstance.hs3.dba.db",
                    "target": "master",
                    "backup_type": "normal_backup"
                }
            ],
            "uid": 340,
            "ticket_type": "REDIS_BACKUP",
            "created_by": "admin",
            "bk_biz_id": 1111,
            "backup_server": {
                "url": "制品库地址",
                "bucket": "目标bucket",
                "password": "制品库token",
                "username": "制品库username",
                "project": "制品库project"
            }
        }
        """
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.REDIS_BACKUP)
class RedisBackupFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisBackupDetailSerializer
    inner_flow_builder = RedisBackupFlowParamBuilder
    inner_flow_name = _("集群备份")
    pause_node_builder = RedisBasePauseParamBuilder
    default_need_itsm = False


class RedisBackupAutoDetailSerializer(RedisOpsBaseDetailSerializer):
    """Redis 自动提交备份单据 detail 校验（结构同 REDIS_BACKUP）。"""

    pass


class RedisBackupAutoFlowParamBuilder(builders.FlowParamBuilder):
    """Redis 自动提交备份单据 flow 参数构造器，复用 redis_backup 控制器。"""

    controller = RedisController.redis_backup

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.REDIS_BACKUP_AUTO)
class RedisBackupAutoFlowBuilder(BaseRedisTicketFlowBuilder):
    """
    Redis 自动提交备份单据

    - 由其他 Redis 单据（如整机替换）在流程中"自动提单"，但备份任务的执行动作仍由 DBA 手动触发。
    - 单据创建时会记录超时时间，周期巡检任务会处理超过约定时间仍未执行的单据：
        * 若 DBA 还未点击执行（单据仍处于 TODO/PENDING/APPROVE 等待处理态），则自动终止；
        * 若 DBA 已经点击执行（单据进入 RUNNING 或已结束），则不做任何干预。
    """

    serializer = RedisBackupAutoDetailSerializer
    inner_flow_builder = RedisBackupAutoFlowParamBuilder
    inner_flow_name = _("待执行备份")
    editable = False
    # 由内部流程发起，跳过 ITSM 审批
    default_need_itsm = False
    # 备份的执行动作需要 DBA 手动确认触发，因此保留人工确认（pause）节点
    pause_node_builder = RedisBasePauseParamBuilder

    @property
    def need_itsm(self):
        return False

    @property
    def need_manual_confirm(self):
        return True
