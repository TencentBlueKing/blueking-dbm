# -*- coding: utf-8 -*-
"""加载已有执行机 到 trans_data。"""

import logging

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.exec_host.models import ExecHost, ExecHostStatus
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.exec_host.context import coerce_exec_host_trans_data
from backend.flow.utils.exec_host.lease import acquire_exec_host_ref

logger = logging.getLogger("flow")

_ACTIVE = (ExecHostStatus.DEPLOYING.value, ExecHostStatus.RUNNING.value)


class ExecHostResolveMetaService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = coerce_exec_host_trans_data(data.get_one_of_inputs("trans_data"))
        exec_host_id = kwargs.get("exec_host_id")
        exec_host = ExecHost.objects.filter(id=exec_host_id, status__in=_ACTIVE).first()
        if not exec_host:
            self.log_error(_("ExecHost not found or inactive: id={}").format(exec_host_id))
            return False
        acquire_root_id = str(kwargs.get("acquire_root_id") or "").strip()
        if acquire_root_id:
            exec_host = acquire_exec_host_ref(exec_host.id, acquire_root_id)
            self.log_info(_("ExecHost referenced by root_id={}").format(acquire_root_id))
        trans_data.exec_host_id = exec_host.id
        trans_data.exec_host_ip = exec_host.ip
        trans_data.bk_cloud_id = exec_host.bk_cloud_id
        trans_data.created_this_run = False
        data.outputs["trans_data"] = trans_data
        data.outputs.exec_host_id = exec_host.id
        self.log_info(_("ExecHost loaded: id={} ip={}").format(exec_host.id, exec_host.ip))
        return True


class ExecHostResolveMetaComponent(Component):
    name = __name__
    code = "exec_host_resolve_meta"
    bound_service = ExecHostResolveMetaService
