# -*- coding: utf-8 -*-
from backend.flow.utils.job_host.context import JobHostTransData


def test_job_host_trans_data_keeps_fields_after_set():
    ctx = JobHostTransData(job_host_id=9, created_this_run=True, job_host_ip="192.168.0.1")
    assert hasattr(ctx, "set")
    ctx.set("step1", "step1")
    assert ctx.get("step1") == "step1"
    assert ctx.job_host_id == 9
    assert ctx.created_this_run is True
    assert ctx.job_host_ip == "192.168.0.1"
