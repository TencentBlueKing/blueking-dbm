# -*- coding: utf-8 -*-
"""从单据 infos 解析 JobHost（新建用 job_host.ip，复用用 job_host_id）。"""


def resolve_job_host_from_row(row: dict, bk_cloud_id: int = None):
    """
    返回 (job_host_id|None, ip)。
    复用时若提供 bk_cloud_id，会校验与 JobHost 记录一致（需 Django ORM）。
    """
    job_host_id = row.get("job_host_id")
    if job_host_id:
        from backend.db_meta.models.job_host import JobHost, JobHostStatus

        job = JobHost.objects.filter(
            id=job_host_id,
            status__in=(JobHostStatus.DEPLOYING.value, JobHostStatus.RUNNING.value),
        ).first()
        if not job:
            raise Exception("JobHost id={} not found or inactive".format(job_host_id))
        if bk_cloud_id is not None and job.bk_cloud_id != bk_cloud_id:
            raise Exception("JobHost bk_cloud_id differs from source cluster")
        return int(job_host_id), job.ip

    host = row.get("job_host") or {}
    ip = (host.get("ip") or "").strip()
    if not ip:
        raise Exception(
            "infos[].job_host.ip is required after resource apply "
            "(or pass infos[].job_host_id to reuse an existing JobHost)"
        )
    return None, ip
