# -*- coding: utf-8 -*-
"""JobHost destroy SubBuilder 包装。"""

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.utils.job_host.destroy import JobHostDestroyInput, add_job_host_destroy_acts

__all__ = ["JobHostDestroyInput", "add_job_host_destroy_acts", "job_host_destroy_subflow"]


def job_host_destroy_subflow(inp: JobHostDestroyInput) -> SubBuilder:
    sub = SubBuilder(
        root_id=inp.root_id,
        data={"uid": inp.root_id, "creator": inp.creator, "bk_biz_id": inp.bk_biz_id},
    )
    add_job_host_destroy_acts(sub, inp)
    return sub
