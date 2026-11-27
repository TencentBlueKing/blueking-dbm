# -*- coding: utf-8 -*-
from backend.flow.utils.exec_host.context import ExecHostTransData, coerce_exec_host_trans_data


def test_exec_host_trans_data_keeps_fields_after_set():
    ctx = ExecHostTransData(exec_host_id=9, created_this_run=True, exec_host_ip="127.0.0.1")
    assert hasattr(ctx, "set")
    ctx.set("step1", "step1")
    assert ctx.get("step1") == "step1"
    assert ctx.exec_host_id == 9
    assert ctx.created_this_run is True
    assert ctx.exec_host_ip == "127.0.0.1"


def test_coerce_exec_host_trans_data_from_pipeline_str_and_dict():
    assert isinstance(coerce_exec_host_trans_data(""), ExecHostTransData)
    assert isinstance(coerce_exec_host_trans_data("${trans_data}"), ExecHostTransData)
    assert isinstance(coerce_exec_host_trans_data(None), ExecHostTransData)
    from_dict = coerce_exec_host_trans_data(
        {"exec_host_id": 3, "exec_host_ip": "127.0.0.2", "created_this_run": True, "bk_cloud_id": 0}
    )
    assert from_dict.exec_host_id == 3
    assert from_dict.exec_host_ip == "127.0.0.2"
    assert from_dict.created_this_run is True
    same = ExecHostTransData(exec_host_id=1)
    assert coerce_exec_host_trans_data(same) is same
    # str that would previously AttributeError on setattr
    coerced = coerce_exec_host_trans_data("")
    coerced.exec_host_id = 7
    assert coerced.exec_host_id == 7
