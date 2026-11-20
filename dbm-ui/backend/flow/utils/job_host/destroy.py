# -*- coding: utf-8 -*-
"""JobHost destroy 节点组装。"""

from dataclasses import dataclass
from typing import Optional

from django.utils.translation import gettext as _

JOB_HOST_UNREGISTER_META = "job_host_unregister_meta"


@dataclass
class JobHostDestroyInput:
    root_id: str
    creator: str = ""
    job_host_id: Optional[int] = None
    recycle_hosts: bool = True
    only_if_created: bool = True
    bk_biz_id: int = 0


def add_job_host_destroy_acts(pipeline, inp: JobHostDestroyInput) -> None:
    kwargs = {
        "recycle_hosts": inp.recycle_hosts,
        "creator": inp.creator,
        "only_if_created": inp.only_if_created,
    }
    if inp.job_host_id:
        kwargs["job_host_id"] = int(inp.job_host_id)
    pipeline.add_act(
        act_name=_("销毁 JobHost"),
        act_component_code=JOB_HOST_UNREGISTER_META,
        kwargs=kwargs,
    )
