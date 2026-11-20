# -*- coding: utf-8 -*-
"""注册 JobHost 元数据。"""

import logging

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.api.cluster.jobhost import create
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class JobHostRegisterMetaService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = data.get_one_of_inputs("trans_data")
        job_host = create(
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
        if trans_data is not None:
            trans_data.job_host_id = job_host.id
            trans_data.job_host_ip = job_host.ip
            trans_data.bk_cloud_id = job_host.bk_cloud_id
            trans_data.created_this_run = True
            data.outputs["trans_data"] = trans_data
        data.outputs.job_host_id = job_host.id
        self.log_info(_("JobHost registered: id={} ip={}").format(job_host.id, job_host.ip))
        return True


class JobHostRegisterMetaComponent(Component):
    name = __name__
    code = "job_host_register_meta"
    bound_service = JobHostRegisterMetaService
