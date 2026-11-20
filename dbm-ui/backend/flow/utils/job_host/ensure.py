# -*- coding: utf-8 -*-
"""JobHost ensure 节点组装（使用 component code 字符串，避免拉起 pipeline Django 模型）。"""

from dataclasses import dataclass, field
from typing import Optional

from django.utils.translation import gettext as _

JOB_HOST_RESOLVE_META = "job_host_resolve_meta"
JOB_HOST_REGISTER_META = "job_host_register_meta"


@dataclass
class JobHostEnsureInput:
    root_id: str
    bk_biz_id: int
    bk_cloud_id: int
    name: str
    ip: str = ""
    job_host_id: Optional[int] = None
    deploy_path: str = ""
    version: str = ""
    db_type: str = ""
    purpose: str = ""
    tags: dict = field(default_factory=dict)
    creator: str = ""
    send_media_act: Optional[dict] = None


def add_job_host_ensure_acts(pipeline, inp: JobHostEnsureInput) -> None:
    if inp.job_host_id:
        pipeline.add_act(
            act_name=_("加载 JobHost"),
            act_component_code=JOB_HOST_RESOLVE_META,
            kwargs={"job_host_id": int(inp.job_host_id)},
        )
        return
    if not inp.ip:
        raise ValueError("JobHost ensure requires ip when job_host_id is empty")
    if inp.send_media_act:
        pipeline.add_act(**inp.send_media_act)
    pipeline.add_act(
        act_name=_("注册 JobHost"),
        act_component_code=JOB_HOST_REGISTER_META,
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
