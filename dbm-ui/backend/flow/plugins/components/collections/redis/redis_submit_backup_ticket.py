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
from datetime import timedelta
from time import sleep
from typing import List

from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.bk_web.constants import LEN_L_LONG
from backend.configuration.constants import PLAT_BIZ_ID, DBType
from backend.configuration.models.dba import DBAdministrator
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TICKET_EXPIRE_DEFAULT_CONFIG, FlowTypeConfig, TicketType
from backend.ticket.models import Ticket
from backend.ticket.models.ticket import TicketFlowsConfig

# 默认 3 小时内 DBA 未触发执行，则自动终止该备份单据
DEFAULT_AUTO_TERMINATE_SECONDS = 3 * 60 * 60


class RedisSubmitBackupTicketService(BaseService):
    """
    通用组件：由流程内部"自动提交"一张 Redis 备份单据（REDIS_BACKUP_AUTO），
    但备份任务的**执行动作仍需 DBA 在单据页面手动触发**。

    同时会在单据详情中记录超时时间：若在指定时间内（默认 3 小时）DBA 未点击执行，
    周期巡检任务会终止仍处于 TODO/PENDING/APPROVE 等待处理状态的单据；
    若 DBA 已经点击执行进入 RUNNING 或到达终态，则不做任何干预。

    kwargs:
        cluster_ids:    List[int]  待备份的集群 ID 列表（必填）
        bk_biz_id:      int        业务 ID（必填）
        created_by:     str        操作人（可选，缺省取 Redis DBA[0]）
        backup_target:  str        "slave" 或 "master"，默认 "slave"
        backup_type:    str        备份类型，默认 "normal_backup"
        auto_terminate_seconds: int  DBA 未触发执行的超时秒数，默认 3 小时
        remark:         str        单据备注（可选）
        parent_ticket_id: int      发起该子单据的父单据 ID（可选），用于关联展示
    """

    @staticmethod
    def _build_remark_with_clusters(remark: str, cluster_domains: List[str]) -> str:
        """在备注中补充集群信息，避免备注过长导致保存失败。"""
        if not cluster_domains:
            return remark[:LEN_L_LONG]

        display_domains = cluster_domains[:5]
        cluster_text = _("关联集群：{}").format(", ".join(display_domains))
        if len(cluster_domains) > len(display_domains):
            cluster_text = _("关联集群：{} 等{}个").format(", ".join(display_domains), len(cluster_domains))

        return "{}；{}".format(remark, cluster_text)[:LEN_L_LONG]

    @staticmethod
    def _ensure_backup_ticket_flow_config() -> None:
        """兜底确保自动提交的备份单据流程配置存在；正常应由平台初始化流程提前创建。"""
        config_filter = {"bk_biz_id": PLAT_BIZ_ID, "ticket_type": TicketType.REDIS_BACKUP_AUTO}
        if TicketFlowsConfig.objects.filter(**config_filter).exists():
            return

        lock_key = "ensure_backup_ticket_flow_config:redis_backup_auto"
        if not cache.add(lock_key, True, timeout=60):
            for attempt in range(6):
                sleep(0.5)
                if TicketFlowsConfig.objects.filter(**config_filter).exists():
                    return
            return

        try:
            if TicketFlowsConfig.objects.filter(**config_filter).exists():
                return
            TicketFlowsConfig.objects.create(
                **config_filter,
                creator="admin",
                updater="admin",
                group=DBType.Redis.value,
                editable=False,
                configs={
                    FlowTypeConfig.NEED_ITSM: False,
                    FlowTypeConfig.NEED_MANUAL_CONFIRM: True,
                    FlowTypeConfig.EXPIRE_CONFIG: TICKET_EXPIRE_DEFAULT_CONFIG,
                },
            )
        finally:
            cache.delete(lock_key)

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        global_data = data.get_one_of_inputs("global_data") or {}

        cluster_ids: List[int] = kwargs.get("cluster_ids") or []
        bk_biz_id = kwargs.get("bk_biz_id") or global_data.get("bk_biz_id")
        creator = kwargs.get("created_by") or global_data.get("created_by")
        backup_target = kwargs.get("backup_target", "slave")
        backup_type = kwargs.get("backup_type", "normal_backup")
        auto_terminate_seconds = int(kwargs.get("auto_terminate_seconds", DEFAULT_AUTO_TERMINATE_SECONDS))
        remark = kwargs.get("remark") or _("自动提交 Redis 备份单据")
        parent_ticket_id = kwargs.get("parent_ticket_id") or global_data.get("uid")

        if not cluster_ids:
            self.log_warning(_("cluster_ids 为空，跳过 Redis 备份单据自动提交"))
            return True

        if not bk_biz_id:
            self.log_error(_("bk_biz_id 缺失，无法自动提交 Redis 备份单据"))
            return False

        # 缺省 creator：取业务 Redis DBA 首位
        if not creator:
            redis_dbas = DBAdministrator.get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=DBType.Redis.value)
            creator = redis_dbas[0] if redis_dbas else "admin"

        # 组装 rules
        clusters = Cluster.objects.filter(id__in=cluster_ids, bk_biz_id=bk_biz_id)
        cluster_id_to_domain = {c.id: c.immute_domain for c in clusters}
        cluster_domains = []
        rules = []
        for cid in cluster_ids:
            if cid not in cluster_id_to_domain:
                self.log_warning(_("集群 {} 不属于业务 {}，跳过").format(cid, bk_biz_id))
                continue
            cluster_domains.append(cluster_id_to_domain[cid])
            rules.append(
                {
                    "cluster_id": cid,
                    "domain": cluster_id_to_domain[cid],
                    "target": backup_target,
                    "backup_type": backup_type,
                }
            )

        if not rules:
            self.log_warning(_("没有可用于备份的集群，跳过 Redis 备份单据自动提交"))
            return True

        remark = self._build_remark_with_clusters(remark, cluster_domains)
        details = {"rules": rules}
        if auto_terminate_seconds > 0:
            details.update(
                {
                    "auto_terminate_seconds": auto_terminate_seconds,
                    "auto_terminate_at": (timezone.now() + timedelta(seconds=auto_terminate_seconds)).isoformat(),
                }
            )
        self.log_info(_("自动提交 Redis 备份子单据，creator={}, bk_biz_id={}, rules={}").format(creator, bk_biz_id, rules))

        # 1) 创建子单据
        self._ensure_backup_ticket_flow_config()
        child_ticket = Ticket.create_ticket(
            ticket_type=TicketType.REDIS_BACKUP_AUTO,
            creator=creator,
            bk_biz_id=bk_biz_id,
            remark=remark,
            details=details,
        )
        self.log_info(_("Redis 备份子单据创建成功，ticket_id={}").format(child_ticket.id))

        # 2) 关联到父单据（若存在）
        if parent_ticket_id:
            try:
                parent_ticket = Ticket.objects.get(id=parent_ticket_id)
                parent_ticket.add_related_ticket(
                    related_ticket=child_ticket,
                    desc=_("自动发起 Redis 备份单据"),
                    done=True,
                )
            except Ticket.DoesNotExist:
                self.log_warning(_("父单据 {} 不存在，跳过关联").format(parent_ticket_id))
            except Exception as e:  # noqa
                # 关联失败不影响主流程
                self.log_warning(_("关联父单据 {} 失败: {}").format(parent_ticket_id, e))

        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class RedisSubmitBackupTicketComponent(Component):
    name = __name__
    code = "redis_submit_backup_ticket"
    bound_service = RedisSubmitBackupTicketService
