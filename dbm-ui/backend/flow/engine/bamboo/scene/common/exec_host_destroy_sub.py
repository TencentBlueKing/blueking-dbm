# -*- coding: utf-8 -*-
"""ExecHost destroy SubBuilder 包装。"""

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.utils.exec_host.destroy import ExecHostDestroyInput, add_exec_host_destroy_acts

__all__ = ["ExecHostDestroyInput", "add_exec_host_destroy_acts", "exec_host_destroy_subflow"]


def exec_host_destroy_subflow(inp: ExecHostDestroyInput) -> SubBuilder:
    sub = SubBuilder(
        root_id=inp.root_id,
        data={"uid": inp.root_id, "creator": inp.creator, "bk_biz_id": inp.bk_biz_id},
    )
    add_exec_host_destroy_acts(sub, inp)
    return sub
