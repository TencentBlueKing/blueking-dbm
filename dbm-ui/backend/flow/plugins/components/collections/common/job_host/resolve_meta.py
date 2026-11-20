# -*- coding: utf-8 -*-
"""加载已有 JobHost 到 trans_data。"""

import logging

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.models.job_host import JobHost, JobHostStatus
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")

_ACTIVE = (JobHostStatus.DEPLOYING.value, JobHostStatus.RUNNING.value)


class JobHostResolveMetaService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = data.get_one_of_inputs("trans_data")
        job_host_id = kwargs.get("job_host_id")
        job_host = JobHost.objects.filter(id=job_host_id, status__in=_ACTIVE).first()
        if not job_host:
            self.log_error(_("JobHost not found or inactive: id={}").format(job_host_id))
            return False
        if trans_data is not None:
            trans_data.job_host_id = job_host.id
            trans_data.job_host_ip = job_host.ip
            trans_data.bk_cloud_id = job_host.bk_cloud_id
            trans_data.created_this_run = False
            data.outputs["trans_data"] = trans_data
        data.outputs.job_host_id = job_host.id
        self.log_info(_("JobHost loaded: id={} ip={}").format(job_host.id, job_host.ip))
        return True


class JobHostResolveMetaComponent(Component):
    name = __name__
    code = "job_host_resolve_meta"
    bound_service = JobHostResolveMetaService
