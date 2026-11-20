# -*- coding: utf-8 -*-
"""注册执行机 元数据。"""

import logging

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.exec_host.api import create
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.exec_host.context import coerce_exec_host_trans_data

logger = logging.getLogger("flow")


class ExecHostRegisterMetaService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = coerce_exec_host_trans_data(data.get_one_of_inputs("trans_data"))
        exec_host = create(
            bk_biz_id=kwargs["bk_biz_id"],
            bk_cloud_id=kwargs["bk_cloud_id"],
            name=kwargs["name"],
            ip=kwargs["ip"],
            deploy_path=kwargs.get("deploy_path", ""),
            version=kwargs.get("version", ""),
            db_type=kwargs.get("db_type", ""),
            purpose=kwargs.get("purpose", ""),
            tags=kwargs.get("tags") or {},
            creator=kwargs.get("creator", ""),
        )
        trans_data.exec_host_id = exec_host.id
        trans_data.exec_host_ip = exec_host.ip
        trans_data.bk_cloud_id = exec_host.bk_cloud_id
        trans_data.created_this_run = True
        data.outputs["trans_data"] = trans_data
        data.outputs.exec_host_id = exec_host.id
        self.log_info(_("ExecHost registered: id={} ip={}").format(exec_host.id, exec_host.ip))
        return True


class ExecHostRegisterMetaComponent(Component):
    name = __name__
    code = "exec_host_register_meta"
    bound_service = ExecHostRegisterMetaService
