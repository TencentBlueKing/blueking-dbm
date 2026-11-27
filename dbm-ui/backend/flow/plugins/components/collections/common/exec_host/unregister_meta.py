# -*- coding: utf-8 -*-
"""下线 ExecHost 元数据。"""

import logging

from django.db import transaction
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.enums import MachineType
from backend.db_meta.models import Machine
from backend.db_services.dbresource.handlers import ResourceHandler
from backend.exec_host.api import decommission
from backend.exec_host.models import ExecHost
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.exec_host.context import coerce_exec_host_trans_data
from backend.flow.utils.exec_host.lease import release_exec_host_ref

logger = logging.getLogger("flow")


class ExecHostUnregisterMetaService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = coerce_exec_host_trans_data(data.get_one_of_inputs("trans_data"))
        exec_host_id = kwargs.get("exec_host_id") or trans_data.exec_host_id
        if not exec_host_id:
            self.log_error(_("ExecHost id missing for unregister"))
            return False
        # 下架会删除 Machine，先记下 bk_host_id，回收后写入单据 recycle_hosts
        bk_host_id = self._exec_host_bk_host_id(int(exec_host_id))
        ticket_id = int(kwargs.get("ticket_id") or 0)
        root_id = str(kwargs.get("root_id") or "").strip()
        recycle_hosts = kwargs.get("recycle_hosts", True)
        only_if_created = kwargs.get("only_if_created", False)
        not_created = only_if_created and not trans_data.created_this_run
        if root_id:
            # 释放引用总要做；不是本次创建的执行机按 only_if_created 只释放不回收。
            outcome = release_exec_host_ref(
                int(exec_host_id),
                root_id,
                recycle_hosts=recycle_hosts and not not_created,
                updater=kwargs.get("creator", ""),
            )
            if outcome == "held":
                self.log_info(_("skip ExecHost destroy: id={} still referenced by another flow").format(exec_host_id))
            elif outcome == "kept":
                self.log_info(
                    _("skip ExecHost recycle: id={} recycle_hosts is false or not created in this run").format(
                        exec_host_id
                    )
                )
            elif outcome == "destroyed":
                self.log_info(_("ExecHost already destroyed: id={}").format(exec_host_id))
            else:
                self.log_info(_("ExecHost unregistered: id={}").format(exec_host_id))
                self._add_ticket_recycle_host(ticket_id, bk_host_id)
            return True
        if not_created:
            self.log_info(_("skip ExecHost destroy: not created in this run"))
            return True
        decommission(
            exec_host_id=int(exec_host_id),
            recycle_hosts=recycle_hosts,
            updater=kwargs.get("creator", ""),
        )
        self.log_info(_("ExecHost unregistered: id={}").format(exec_host_id))
        if recycle_hosts:
            self._add_ticket_recycle_host(ticket_id, bk_host_id)
        return True

    @staticmethod
    def _exec_host_bk_host_id(exec_host_id: int) -> int:
        exec_host = ExecHost.objects.filter(id=exec_host_id).first()
        if not exec_host:
            return 0
        machine = Machine.objects.filter(
            ip=exec_host.ip, bk_cloud_id=exec_host.bk_cloud_id, machine_type=MachineType.EXEC_HOST.value
        ).first()
        return machine.bk_host_id if machine else 0

    def _add_ticket_recycle_host(self, ticket_id: int, bk_host_id: int):
        """单据注册为回收类单据，成功后按 recycle_hosts 发起主机回收单（空闲检查、清理、退回资源池）。"""
        if not ticket_id or not bk_host_id:
            return
        from backend.ticket.models import Ticket

        try:
            new_hosts = ResourceHandler.standardized_resource_host([{"bk_host_id": bk_host_id}])
        except Exception as err:  # pylint: disable=broad-except
            # 主机已下架到待回收模块，这里失败不回滚下架，只提示人工发起回收
            self.log_error(
                _("ExecHost bk_host_id={} recycled but not added to ticket {} recycle_hosts: {}").format(
                    bk_host_id, ticket_id, err
                )
            )
            return
        with transaction.atomic():
            ticket = Ticket.objects.select_for_update().filter(id=ticket_id).first()
            if not ticket:
                return
            hosts = [host for host in ticket.details.get("recycle_hosts") or [] if host["bk_host_id"] != bk_host_id]
            hosts.extend(new_hosts)
            ticket.update_details(recycle_hosts=hosts)
        self.log_info(_("ExecHost bk_host_id={} added to ticket {} recycle_hosts").format(bk_host_id, ticket_id))


class ExecHostUnregisterMetaComponent(Component):
    name = __name__
    code = "exec_host_unregister_meta"
    bound_service = ExecHostUnregisterMetaService
