# -*- coding: utf-8 -*-
"""ExecHost ensure 节点组装（使用 component code 字符串，避免拉起 pipeline Django 模型）。"""

from dataclasses import dataclass, field
from typing import Optional

from django.utils.translation import gettext as _

EXEC_HOST_RESOLVE_META = "exec_host_resolve_meta"
EXEC_HOST_REGISTER_META = "exec_host_register_meta"


@dataclass
class ExecHostEnsureInput:
    root_id: str
    bk_biz_id: int
    bk_cloud_id: int
    name: str
    ip: str = ""
    exec_host_id: Optional[int] = None
    deploy_path: str = ""
    version: str = ""
    db_type: str = ""
    purpose: str = ""
    tags: dict = field(default_factory=dict)
    creator: str = ""
    send_media_act: Optional[dict] = None


def add_exec_host_ensure_acts(pipeline, inp: ExecHostEnsureInput) -> None:
    if inp.exec_host_id:
        pipeline.add_act(
            act_name=_("加载执行机"),
            act_component_code=EXEC_HOST_RESOLVE_META,
            # 复用执行机时在流程内登记 root_id 引用：流程建好之前失败不会留下无主引用。
            kwargs={"exec_host_id": int(inp.exec_host_id), "acquire_root_id": inp.root_id},
        )
        return
    if not inp.ip:
        raise ValueError("ExecHost ensure requires ip when exec_host_id is empty")
    if inp.send_media_act:
        pipeline.add_act(**inp.send_media_act)
    pipeline.add_act(
        act_name=_("注册执行机"),
        act_component_code=EXEC_HOST_REGISTER_META,
        kwargs={
            "bk_biz_id": inp.bk_biz_id,
            "bk_cloud_id": inp.bk_cloud_id,
            "name": inp.name,
            "ip": inp.ip,
            "deploy_path": inp.deploy_path,
            "version": inp.version,
            "db_type": inp.db_type,
            "purpose": inp.purpose,
            "tags": inp.tags,
            "creator": inp.creator,
        },
    )
