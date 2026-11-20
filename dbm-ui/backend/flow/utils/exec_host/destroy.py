# -*- coding: utf-8 -*-
"""ExecHost destroy 节点组装。"""

from dataclasses import dataclass
from typing import Optional

from django.utils.translation import gettext as _

EXEC_HOST_UNREGISTER_META = "exec_host_unregister_meta"


@dataclass
class ExecHostDestroyInput:
    root_id: str
    creator: str = ""
    exec_host_id: Optional[int] = None
    recycle_hosts: bool = True
    only_if_created: bool = True
    bk_biz_id: int = 0
    # 回收后把主机写入该单据 recycle_hosts，单据成功后走标准主机回收单
    ticket_id: int = 0


def add_exec_host_destroy_acts(pipeline, inp: ExecHostDestroyInput) -> None:
    kwargs = {
        "recycle_hosts": inp.recycle_hosts,
        "creator": inp.creator,
        "only_if_created": inp.only_if_created,
        "root_id": inp.root_id,
    }
    if inp.exec_host_id:
        kwargs["exec_host_id"] = int(inp.exec_host_id)
    if inp.ticket_id:
        kwargs["ticket_id"] = int(inp.ticket_id)
    pipeline.add_act(
        act_name=_("销毁执行机"),
        act_component_code=EXEC_HOST_UNREGISTER_META,
        kwargs=kwargs,
    )
