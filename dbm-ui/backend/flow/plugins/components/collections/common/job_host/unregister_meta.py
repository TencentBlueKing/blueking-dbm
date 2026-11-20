# -*- coding: utf-8 -*-
"""下线 JobHost 元数据。"""

import logging

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.api.cluster.jobhost import decommission
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class JobHostUnregisterMetaService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = data.get_one_of_inputs("trans_data")
        job_host_id = kwargs.get("job_host_id")
        if not job_host_id and trans_data is not None:
            job_host_id = getattr(trans_data, "job_host_id", None)
        if not job_host_id:
            self.log_error(_("JobHost id missing for unregister"))
            return False
        only_if_created = kwargs.get("only_if_created", False)
        if only_if_created and trans_data is not None and not getattr(trans_data, "created_this_run", False):
            self.log_info(_("skip JobHost destroy: not created in this run"))
            return True
        decommission(
            job_host_id=int(job_host_id),
            recycle_hosts=kwargs.get("recycle_hosts", True),
            updater=kwargs.get("creator", ""),
        )
        self.log_info(_("JobHost unregistered: id={}").format(job_host_id))
        return True


class JobHostUnregisterMetaComponent(Component):
    name = __name__
    code = "job_host_unregister_meta"
    bound_service = JobHostUnregisterMetaService
