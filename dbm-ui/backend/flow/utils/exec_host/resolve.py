# -*- coding: utf-8 -*-
"""从单据 infos 解析 ExecHost（新建用 exec_host.ip，复用用 exec_host_id）。"""

from django.utils.translation import gettext as _


def resolve_exec_host_from_row(row: dict, bk_cloud_id: int = None):
    """
    返回 (exec_host_id|None, ip)。
    复用时若提供 bk_cloud_id，会校验与 ExecHost 记录一致（需 Django ORM）。
    """
    exec_host_id = row.get("exec_host_id")
    if exec_host_id:
        from backend.exec_host.models import ExecHost, ExecHostStatus

        job = ExecHost.objects.filter(
            id=exec_host_id,
            status__in=(ExecHostStatus.DEPLOYING.value, ExecHostStatus.RUNNING.value),
        ).first()
        if not job:
            raise Exception(_("执行机 id={} 不存在或未处于可用状态").format(exec_host_id))
        if bk_cloud_id is not None and job.bk_cloud_id != bk_cloud_id:
            raise Exception("ExecHost bk_cloud_id differs from source cluster")
        return int(exec_host_id), job.ip

    host = row.get("exec_host") or {}
    # 资源申请回填的是主机列表
    if isinstance(host, list):
        host = host[0] if host else {}
    ip = (host.get("ip") or "").strip()
    if not ip:
        raise Exception(
            "infos[].exec_host.ip is required after resource apply "
            "(or pass infos[].exec_host_id to reuse an existing ExecHost)"
        )
    return None, ip
