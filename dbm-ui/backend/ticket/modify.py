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
import copy
import logging

from django.db import transaction
from django.utils.translation import gettext as _

from backend.components import ItsmApiAdapter as ItsmApi
from backend.configuration.models import DBAdministrator
from backend.core import notify
from backend.ticket.builders import BuilderFactory
from backend.ticket.constants import (
    FlowContext,
    FlowType,
    OperateNodeActionType,
    TicketFlowStatus,
    TicketModifyType,
    TicketStatus,
    TodoStatus,
    TodoType,
)
from backend.ticket.exceptions import (
    TicketAlreadyApprovedException,
    TicketContentChangedException,
    TicketContentVersionMissingException,
    TicketModifyForbiddenException,
    TicketModifyStatusException,
)
from backend.ticket.flow_manager.manager import TicketFlowManager
from backend.ticket.handler import TicketHandler
from backend.ticket.models import Flow, Ticket, TicketSnapshot

logger = logging.getLogger("root")


class TicketModifyHandler:
    """
    单据改单服务
    三种模式共用同一份事务骨架：
      - 代为修改(ON_BEHALF)：审批人在待审批阶段，拒绝外部 ITSM 单据后转入待确认修改
      - 重新编辑(RE_EDIT)：提单人在待审批/待确认修改阶段重新编辑内容(待审批阶段撤销旧审批单并重新提单)
      - 调整申请(ADJUST_APPLY)：处理人在待补货阶段，调整资源申请条件并重新申领

    改单后的 flow 操作规则：
      - 已结束的 flow 冻结为 SKIPPED + 出口词，不删除
      - 未执行的 PENDING 尾巴用新的 ticket.details 覆盖(不删除、不重建 id)
      - 需要在中间插入新节点(确认修改 / 新一轮审批)时，用 context.next_flow 链表重建整单流程顺序
    """

    @classmethod
    def modify(cls, ticket_id, operator, mode, details, remark="", version=None, change_count=0):
        """改单统一入口，事务内完成乐观锁/权限/状态校验并分发到具体模式"""
        with transaction.atomic():
            ticket = Ticket.objects.select_for_update().get(id=ticket_id)

            # 内容版本乐观锁：version 由前端随提交传入，当前版本 = 已落库的改单快照数
            if version is not None and cls._current_version(ticket) != version:
                raise TicketContentChangedException()

            if mode == TicketModifyType.ON_BEHALF.value:
                cls.on_behalf_modify(ticket, operator, details, remark, change_count)
            elif mode == TicketModifyType.RE_EDIT.value:
                cls.re_edit(ticket, operator, details, remark, change_count)
            elif mode == TicketModifyType.ADJUST_APPLY.value:
                cls.adjust_apply(ticket, operator, details, remark, change_count)
            else:
                raise TicketModifyForbiddenException()

            # 状态流转在 TicketFlowManager.update_ticket_status 中通过新的 ticket 实例落库，
            # 这里刷新本地实例的状态，保证返回给前端/上层调用方的 ticket.status 与 DB 一致
            ticket.refresh_from_db(fields=["status"])
            return ticket

    @staticmethod
    def _current_version(ticket):
        """当前内容版本号 = 已落库的改单快照数。

        Ticket 表数据量大，不为其新增字段；每次改单都会落一条 TicketSnapshot，
        记录数即版本号，前端提交的 version 与此值比对即可实现乐观锁。
        """
        return TicketSnapshot.objects.filter(ticket_id=ticket.id).count()

    @staticmethod
    def check_content_version(ticket, version):
        """审批通过/拒绝时校验内容版本，version 必传。

        版本号与改单提交的乐观锁同源（改单快照数），待审批阶段提单人每次重新编辑都会落一条
        RE_EDIT 记录使版本递增，审批人持旧版本操作即被拦截。
        审批通过/拒绝属终态操作，缺少 version 说明前端未带上版本号，直接拒绝，避免漏校验放行。
        """
        if version is None:
            raise TicketContentVersionMissingException()
        if TicketModifyHandler._current_version(ticket) != version:
            raise TicketContentChangedException()

    @staticmethod
    def _notify_creator(ticket, operator, mode, remark):
        """改单后通知提单人：异步发送，事务提交后再投递，避免读到未提交数据"""
        transaction.on_commit(
            lambda: notify.send_modify_notify.apply_async(args=(ticket.id, operator, mode.value, remark))
        )

    @staticmethod
    def _notify_approvers(ticket):
        """重新编辑后通知审批人：复用现网「进入待审批」通知，不新增通知类型"""
        transaction.on_commit(lambda: notify.send_msg.apply_async(args=(ticket.id,)))

    # ------------------------------------------------------------------
    # 代为修改：审批人 -> 拒绝外部 ITSM -> 待确认修改
    # ------------------------------------------------------------------
    @classmethod
    def on_behalf_modify(cls, ticket, operator, details, remark, change_count):
        cls._check_approve_permission(ticket, operator)
        if ticket.status != TicketStatus.APPROVE:
            raise TicketModifyStatusException(status=TicketStatus.get_choice_label(ticket.status))

        itsm_flow = cls._get_running_itsm_flow(ticket)

        # 拒绝外部 ITSM 单据(审批人终止即拒单)，而非撤销
        TicketHandler.operate_itsm_ticket(
            ticket.id,
            action=OperateNodeActionType.TRANSITION,
            operator=operator,
            is_approved=False,
            action_message=remark or _("审批人代为修改"),
        )

        # 冻结审批节点并关闭其待办
        cls._freeze_flow(itsm_flow, exit_word=_("代为修改"), remark=remark)
        cls._close_flow_todos(itsm_flow, operator)

        # 覆盖详情并重新初始化派生字段(快照存前端传入、未初始化的原始详情)
        raw_details = copy.deepcopy(details)
        builder = cls._patch_details(ticket, details)
        cls._record(ticket, itsm_flow, TicketModifyType.ON_BEHALF, operator, remark, raw_details, change_count)

        # 插入确认修改节点并覆盖 pending 尾巴
        auto_confirm = operator == ticket.creator
        confirm_flow = cls._insert_flow_after(
            ticket,
            itsm_flow,
            Flow(
                ticket=ticket,
                flow_type=FlowType.CONFIRM_MODIFY.value,
                flow_alias=_("确认修改"),
                details={"operators": [ticket.creator], "auto_confirm": auto_confirm},
            ),
        )
        cls._rebuild_pending_tail(ticket, builder.build_tail_flows(), confirm_flow)

        if auto_confirm:
            # 提单人自身具备审批权限时的代为修改：提交即同步完成确认，不产待办/通知
            cls._auto_confirm_modify(ticket)
            TicketFlowManager(ticket=ticket).run_next_flow()
        else:
            # 运行确认修改节点：创建待确认修改待办，post_save 信号会把 status 置为 CONFIRM_PENDING
            TicketFlowManager(ticket=ticket).run_next_flow()
            # 通知提单人：内容已被审批人代为修改
            cls._notify_creator(ticket, operator, TicketModifyType.ON_BEHALF, remark)

    # ------------------------------------------------------------------
    # 重新编辑：提单人在待审批/待确认修改阶段重新编辑内容
    # ------------------------------------------------------------------
    @classmethod
    def re_edit(cls, ticket, operator, details, remark, change_count):
        if operator != ticket.creator:
            raise TicketModifyForbiddenException()
        if ticket.status == TicketStatus.CONFIRM_PENDING:
            cls._re_edit_from_confirm(ticket, operator, details, remark, change_count)
        elif ticket.status == TicketStatus.APPROVE:
            cls._re_edit_from_approve(ticket, operator, details, remark, change_count)
        else:
            raise TicketModifyStatusException(status=TicketStatus.get_choice_label(ticket.status))

    @classmethod
    def _re_edit_from_confirm(cls, ticket, operator, details, remark, change_count):
        """待确认修改阶段的重新编辑：结束确认修改节点，按需重审后重新执行"""
        confirm_flow = ticket.flows.filter(flow_type=FlowType.CONFIRM_MODIFY.value).first()

        # 冻结确认修改节点并关闭其待办
        cls._freeze_flow(confirm_flow, exit_word=_("重新编辑"), remark=remark)
        cls._close_flow_todos(confirm_flow, operator)

        # 覆盖详情并重新初始化派生字段(快照存前端传入、未初始化的原始详情)
        raw_details = copy.deepcopy(details)
        builder = cls._patch_details(ticket, details)
        cls._record(ticket, confirm_flow, TicketModifyType.RE_EDIT, operator, remark, raw_details, change_count)

        if builder.need_itsm:
            # 需要重审：在确认修改节点之后插入新一轮审批节点，覆盖尾巴
            itsm_flow = cls._insert_flow_after(ticket, confirm_flow, builder.build_itsm_flow())
            cls._rebuild_pending_tail(ticket, builder.build_tail_flows(), itsm_flow)
        else:
            # 免审批：直接覆盖尾巴并执行
            cls._rebuild_pending_tail(ticket, builder.build_tail_flows(), confirm_flow)

        TicketFlowManager(ticket=ticket).run_next_flow()

    @classmethod
    def _re_edit_from_approve(cls, ticket, operator, details, remark, change_count):
        """待审批阶段的重新编辑：先撤销旧审批单再重新提单，单据仍停待审批，支持多次编辑"""
        itsm_flow = cls._get_running_itsm_flow(ticket)
        if not itsm_flow:
            # 审批节点已结束(已被审批/终止)，禁止编辑
            raise TicketAlreadyApprovedException()

        # 覆盖详情并重新初始化派生字段(快照存前端传入、未初始化的原始详情)
        raw_details = copy.deepcopy(details)
        builder = cls._patch_details(ticket, details)
        cls._record(ticket, itsm_flow, TicketModifyType.RE_EDIT, operator, remark, raw_details, change_count)

        # 改后内容命中免审批策略：撤销外部 ITSM 单据，审批节点以「免审批」出口结束，直达待执行
        if not builder.need_itsm:
            TicketHandler.operate_itsm_ticket(ticket.id, action=OperateNodeActionType.WITHDRAW, operator=operator)
            cls._freeze_flow(itsm_flow, exit_word=_("免审批"))
            cls._close_flow_todos(itsm_flow, operator)
            cls._rebuild_pending_tail(ticket, builder.build_tail_flows(), itsm_flow)

            TicketFlowManager(ticket=ticket).run_next_flow()
            return

        # 仍需要审批：先撤销旧 ITSM 审批单，再重新提一张新审批单
        cls._recreate_itsm_ticket(ticket, itsm_flow, operator, builder)

        # 用新内容覆盖 pending 尾巴(不冻结、不插节点，单据仍待审批)
        cls._rebuild_pending_tail(ticket, builder.build_tail_flows(), itsm_flow)

        # 通知审批人：内容已被重新编辑(复用现网「进入待审批」通知)
        cls._notify_approvers(ticket)

    # ------------------------------------------------------------------
    # 调整申请：待补货阶段调整资源申请条件并重新申领
    # ------------------------------------------------------------------
    @classmethod
    def adjust_apply(cls, ticket, operator, details, remark, change_count):
        cls._check_replenish_permission(ticket, operator)
        if ticket.status != TicketStatus.RESOURCE_REPLENISH:
            raise TicketModifyStatusException(status=TicketStatus.get_choice_label(ticket.status))

        resource_flow = (
            ticket.flows.filter(flow_type__in=[FlowType.RESOURCE_APPLY.value, FlowType.RESOURCE_BATCH_APPLY.value])
            .exclude(status__in=[TicketFlowStatus.SUCCEEDED, TicketFlowStatus.SKIPPED])
            .first()
        )

        # 覆盖详情并重新初始化派生字段(快照存前端传入、未初始化的原始详情)
        raw_details = copy.deepcopy(details)
        builder = cls._patch_details(ticket, details)
        resource_builder = builder.resource_apply_builder or builder.resource_batch_apply_builder
        if not resource_builder:
            raise TicketModifyForbiddenException()

        cls._record(ticket, resource_flow, TicketModifyType.ADJUST_APPLY, operator, remark, raw_details, change_count)

        # 用重新初始化后的详情重建资源申请参数(覆盖 resource flow 的 details)
        resource_flow.details = resource_builder(ticket).get_params()
        resource_flow.save(update_fields=["details", "update_at"])

        # 覆盖资源申请节点及其之后的 flow(inner/自定义)，而非仅覆盖资源申请节点
        cls._rebuild_pending_tail(ticket, builder.build_post_resource_flows(), resource_flow)

        TicketFlowManager.get_ticket_flow_cls(resource_flow.flow_type)(resource_flow).retry()

        # 调整申请：仅当操作人非提单人时通知提单人
        if operator != ticket.creator:
            cls._notify_creator(ticket, operator, TicketModifyType.ADJUST_APPLY, remark)

    # ------------------------------------------------------------------
    # 权限校验
    # ------------------------------------------------------------------
    @staticmethod
    def _check_approve_permission(ticket, operator):
        """代为修改权限：与审批通过/拒绝同源，取业务下对应 DB 类型的管理员"""
        db_type = BuilderFactory.get_builder_cls(ticket.ticket_type).group
        admins = DBAdministrator.get_biz_db_type_admins(ticket.bk_biz_id, db_type)
        if operator not in admins:
            raise TicketModifyForbiddenException()

    @staticmethod
    def _check_replenish_permission(ticket, operator):
        """调整申请权限：与补货重试同权，取补货待办的处理人+协助人"""
        todo = ticket.todo_of_ticket.filter(type=TodoType.RESOURCE_REPLENISH, status=TodoStatus.TODO).first()
        if not todo or operator not in todo.operators + todo.helpers:
            raise TicketModifyForbiddenException()

    # ------------------------------------------------------------------
    # flow 操作 helper
    # ------------------------------------------------------------------
    @staticmethod
    def _get_running_itsm_flow(ticket):
        return ticket.flows.filter(flow_type=FlowType.BK_ITSM.value, status=TicketFlowStatus.RUNNING).first()

    @staticmethod
    def _recreate_itsm_ticket(ticket, itsm_flow, operator, builder):
        """待审批重新编辑：先撤销旧 ITSM 审批单，再重新提一张新 ITSM 审批单"""
        # 撤销旧 ITSM 审批单
        TicketHandler.operate_itsm_ticket(ticket.id, action=OperateNodeActionType.WITHDRAW, operator=operator)

        # 用改后内容重建 ITSM 参数，重新提单并更新 flow_obj_id
        new_params = builder.itsm_flow_builder(ticket).get_params()
        itsm_flow.details = new_params
        itsm_flow.flow_obj_id = ""
        itsm_flow.save(update_fields=["details", "flow_obj_id", "update_at"])
        data = ItsmApi.create_ticket(new_params)
        itsm_flow.flow_obj_id = data["sn"]
        itsm_flow.save(update_fields=["flow_obj_id", "update_at"])

    @staticmethod
    def _freeze_flow(flow, exit_word, remark=""):
        """冻结节点：置 SKIPPED + 出口词/说明，不删除"""
        flow.status = TicketFlowStatus.SKIPPED
        flow.context.update({FlowContext.EXIT_WORD.value: exit_word})
        if remark:
            flow.context[FlowContext.MODIFY_SUMMARY.value] = remark
        flow.save(update_fields=["status", "context", "update_at"])

    @staticmethod
    def _close_flow_todos(flow, operator):
        """关闭节点关联的待办"""
        for todo in flow.todo_of_flow.filter(status=TodoStatus.TODO):
            todo.set_status(operator, TodoStatus.DONE_SUCCESS)

    @staticmethod
    def _patch_details(ticket, details):
        """覆盖单据详情并走 builder.patch_ticket_detail 重新初始化派生字段。

        建单时 create_ticket 依次执行 patch_ticket_detail -> init_ticket_flows，
        改单同样要先 patch 再重建 flow：新 details 中依赖后端派生的字段(集群/规格/实例/主机信息、
        db_version/charset 等)在此刷新，后续 build_tail_flows/get_params 才能读到完整内容。
        返回补丁后的 builder，供调用方据此重建尾巴 flow。
        """
        ticket.details = details
        ticket.save(update_fields=["details", "update_at"])
        builder = BuilderFactory.create_builder(ticket)
        builder.patch_ticket_detail()
        return builder

    @classmethod
    def _record(cls, ticket, flow, mode, operator, remark, details, change_count):
        """落库改单快照：details 存前端传入、尚未经过单据初始化的原始详情"""
        TicketSnapshot.objects.create(
            ticket_id=ticket.id,
            flow_id=flow.id if flow else 0,
            mode=mode.value,
            operator=operator,
            remark=remark,
            details=details,
            change_count=change_count,
            creator=operator,
            updater=operator,
        )

    @staticmethod
    def _relink_flows(ordered_flows):
        """按给定顺序重写整单流程的 context.next_flow，形成单链表"""
        next_flow_key = FlowContext.NEXT_FLOW.value
        for idx, flow in enumerate(ordered_flows):
            next_id = ordered_flows[idx + 1].id if idx + 1 < len(ordered_flows) else None
            if next_id:
                if flow.context.get(next_flow_key) != next_id:
                    flow.context[next_flow_key] = next_id
                    flow.save(update_fields=["context", "update_at"])

            # 尾部节点没有next_flow
            elif next_flow_key in flow.context:
                flow.context.pop(next_flow_key, None)
                flow.save(update_fields=["context", "update_at"])

    @classmethod
    def _insert_flow_after(cls, ticket, anchor_flow, new_flow):
        """在 anchor_flow 之后插入 new_flow，并为整单流程补充 next_flow"""
        ordered = ticket.ordered_flows()
        anchor_idx = next(i for i, f in enumerate(ordered) if f.id == anchor_flow.id)
        new_flow.ticket = ticket
        new_flow.save()
        ordered.insert(anchor_idx + 1, new_flow)
        cls._relink_flows(ordered)
        return new_flow

    @classmethod
    def _rebuild_pending_tail(cls, ticket, new_flows, anchor_flow):
        """用 new_flows 模板覆盖 anchor_flow 之后的 PENDING 尾巴，并重建整单 next_flow"""
        ordered = ticket.ordered_flows()
        anchor_idx = next(i for i, f in enumerate(ordered) if f.id == anchor_flow.id)
        head = ordered[: anchor_idx + 1]
        old_pending = [f for f in ordered[anchor_idx + 1 :] if f.status == TicketFlowStatus.PENDING]

        next_flow_key = FlowContext.NEXT_FLOW.value
        kept = []
        for idx, new_flow in enumerate(new_flows):
            if idx < len(old_pending):
                old_flow = old_pending[idx]
                # 保留 next_flow 指针，其它上下文重置
                next_id = old_flow.context.get(next_flow_key) if isinstance(old_flow.context, dict) else None
                old_flow.flow_type = new_flow.flow_type
                old_flow.flow_alias = new_flow.flow_alias
                old_flow.details = new_flow.details
                old_flow.retry_type = new_flow.retry_type
                old_flow.context = {next_flow_key: next_id} if next_id else {}
                old_flow.flow_obj_id = ""
                old_flow.err_code = None
                old_flow.err_msg = None
                old_flow.status = TicketFlowStatus.PENDING
                old_flow.save(
                    update_fields=[
                        "flow_type",
                        "flow_alias",
                        "details",
                        "retry_type",
                        "context",
                        "flow_obj_id",
                        "err_code",
                        "err_msg",
                        "status",
                        "update_at",
                    ]
                )
                kept.append(old_flow)
            else:
                new_flow.save()
                kept.append(new_flow)

        # 结构收缩时删除多余 pending 节点
        for extra in old_pending[len(new_flows) :]:
            extra.delete()

        cls._relink_flows(head + kept)

    @staticmethod
    def _auto_confirm_modify(ticket):
        """代为修改时 operator==creator：直接结束确认修改节点(出口"确认无误")，不建待办/通知"""
        confirm_flow = ticket.flows.filter(
            flow_type=FlowType.CONFIRM_MODIFY.value, status=TicketFlowStatus.PENDING
        ).first()
        confirm_flow.context.update({FlowContext.EXIT_WORD.value: _("确认无误")})
        confirm_flow.status = TicketFlowStatus.SUCCEEDED
        confirm_flow.save(update_fields=["status", "context", "update_at"])
