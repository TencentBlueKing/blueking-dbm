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

from django.utils.translation import gettext as _

from backend.db_report.enums import TdbctlUpgradeStatus
from backend.db_report.models import TdbctlUpgradeRecord
from backend.flow.consts import StateType
from backend.flow.signal.callback_map import create_ticket_handler
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


# 定义 flow 状态到 TdbctlUpgradeStatus 的映射
FLOW_STATUS_TO_UPGRADE_STATUS_MAP = {
    StateType.FAILED: TdbctlUpgradeStatus.FAILED.value,
    StateType.REVOKED: TdbctlUpgradeStatus.FAILED.value,
    StateType.RUNNING: TdbctlUpgradeStatus.RUNNING.value,
}


@create_ticket_handler(TicketType.TENDBCLUSTER_TDBCTL_UPGRADE)
def tdbctl_upgrade_callback_handler(root_id: str, node_id: str, status: StateType, **kwargs):
    """
    TenDBCluster tdbctl 升级的信号状态处理函数

    根据 flow 的不同状态更新 TdbctlUpgradeRecord 的 status：
    - StateType.FAILED/REVOKED: 更新 status 为 FAILED
    - StateType.FINISHED: 更新 status 为 SUCCESS

    注意：
    - RUNNING 状态已在流程构建时设置
    - SKIPPED 状态在版本检查时设置
    - 只处理最终状态（FINISHED/FAILED/REVOKED）

    Args:
        root_id: 流程根ID
        node_id: 节点ID
        status: 当前状态
        **kwargs: 其他参数
    """
    logger.info(_("执行 tdbctl 升级信号处理器，root_id={}, node_id={}, status={}").format(root_id, node_id, status))

    # 只处理最终状态
    if status not in FLOW_STATUS_TO_UPGRADE_STATUS_MAP:
        logger.debug(_("状态 {} 不是最终状态，跳过处理").format(status))
        return

    try:
        # 获取对应的升级状态
        upgrade_status = FLOW_STATUS_TO_UPGRADE_STATUS_MAP[status]

        # 查找所有关联此 task_id 且非成功状态的记录（已成功的记录不再更新）
        records = TdbctlUpgradeRecord.objects.filter(task_id=root_id).exclude(status=TdbctlUpgradeStatus.SUCCESS.value)
        if not records.exists():
            logger.info(_("未找到需要更新的 TdbctlUpgradeRecord（可能已成功或不存在），root_id={}").format(root_id))
            return

        # 更新所有记录的状态
        update_fields = ["status", "update_at"]
        error_msg = ""

        if status in [StateType.FAILED, StateType.REVOKED]:
            error_msg = _("流程执行失败或被撤销，状态: {}").format(status)
            update_fields.append("error_msg")
            logger.warning(_("tdbctl 升级失败，root_id={}, status={}").format(root_id, status))
        elif status == StateType.RUNNING:
            logger.info(_("tdbctl 升级中，root_id={}, status={}").format(root_id, status))
        # 批量更新状态
        update_kwargs = {"status": upgrade_status}
        if error_msg:
            update_kwargs["error_msg"] = error_msg

        updated_count = records.update(**update_kwargs)
        logger.info(
            _("TdbctlUpgradeRecord 状态更新成功，root_id={}, 新状态={}, 更新记录数={}").format(root_id, upgrade_status, updated_count)
        )

        # 更新历史记录中的最后一条记录的状态
        for record in records:
            if record.upgrade_history and len(record.upgrade_history) > 0:
                last_history = record.upgrade_history[-1]
                if last_history.get("task_id") == root_id:
                    last_history["status"] = upgrade_status
                    if error_msg:
                        last_history["error_msg"] = error_msg
                    record.save(update_fields=["upgrade_history"])

        # 如果升级成功，更新 upgraded_version
        if status == StateType.FINISHED:
            for record in records:
                record.upgraded_version = record.target_version
                record.save(update_fields=["upgraded_version"])

    except Exception as e:
        logger.error(_("tdbctl 升级信号处理器执行失败: {}").format(str(e)))
        return
