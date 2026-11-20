# -*- coding: utf-8 -*-
"""ExecHost ensure SubBuilder 包装。"""

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.utils.exec_host.ensure import ExecHostEnsureInput, add_exec_host_ensure_acts

__all__ = ["ExecHostEnsureInput", "add_exec_host_ensure_acts", "exec_host_ensure_subflow"]


def exec_host_ensure_subflow(inp: ExecHostEnsureInput) -> SubBuilder:
    sub = SubBuilder(
        root_id=inp.root_id,
        data={
            "bk_biz_id": inp.bk_biz_id,
            "bk_cloud_id": inp.bk_cloud_id,
            "uid": inp.root_id,
            "creator": inp.creator,
        },
    )
    add_exec_host_ensure_acts(sub, inp)
    return sub
