# -*- coding: utf-8 -*-
"""JobHost ensure SubBuilder 包装。"""

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.utils.job_host.ensure import JobHostEnsureInput, add_job_host_ensure_acts

__all__ = ["JobHostEnsureInput", "add_job_host_ensure_acts", "job_host_ensure_subflow"]


def job_host_ensure_subflow(inp: JobHostEnsureInput) -> SubBuilder:
    sub = SubBuilder(
        root_id=inp.root_id,
        data={
            "bk_biz_id": inp.bk_biz_id,
            "bk_cloud_id": inp.bk_cloud_id,
            "uid": inp.root_id,
            "creator": inp.creator,
        },
    )
    add_job_host_ensure_acts(sub, inp)
    return sub
