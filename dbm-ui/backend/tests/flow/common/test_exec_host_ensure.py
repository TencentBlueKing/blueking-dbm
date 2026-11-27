# -*- coding: utf-8 -*-
import pytest

from backend.flow.utils.exec_host.ensure import ExecHostEnsureInput, add_exec_host_ensure_acts
from backend.flow.utils.exec_host.resolve import resolve_exec_host_from_row


class _FakePipeline:
    def __init__(self):
        self.acts = []

    def add_act(self, **kwargs):
        self.acts.append(kwargs)


def test_ensure_requires_ip_when_not_reusing():
    pipe = _FakePipeline()
    with pytest.raises(ValueError, match="requires ip"):
        add_exec_host_ensure_acts(
            pipe,
            ExecHostEnsureInput(root_id="r1", bk_biz_id=1, bk_cloud_id=0, name="jh1"),
        )


def test_ensure_reuse_only_adds_resolve_act():
    pipe = _FakePipeline()
    add_exec_host_ensure_acts(
        pipe,
        ExecHostEnsureInput(root_id="r1", bk_biz_id=1, bk_cloud_id=0, name="jh1", exec_host_id=9),
    )
    assert len(pipe.acts) == 1
    assert pipe.acts[0]["kwargs"]["exec_host_id"] == 9


def test_ensure_new_adds_media_and_register():
    pipe = _FakePipeline()
    media = {"act_name": "send", "act_component_code": "send_media", "kwargs": {}}
    add_exec_host_ensure_acts(
        pipe,
        ExecHostEnsureInput(
            root_id="r1",
            bk_biz_id=1,
            bk_cloud_id=0,
            name="jh1",
            ip="127.0.0.8",
            db_type="mongodb",
            purpose="mongoshake_dts",
            send_media_act=media,
        ),
    )
    assert len(pipe.acts) == 2
    assert pipe.acts[0]["act_name"] == "send"
    assert pipe.acts[1]["kwargs"]["ip"] == "127.0.0.8"
    assert pipe.acts[1]["kwargs"]["purpose"] == "mongoshake_dts"


def test_resolve_exec_host_requires_ip_or_id():
    with pytest.raises(Exception, match="exec_host.ip"):
        resolve_exec_host_from_row({})


def test_resolve_exec_host_from_ticket_host():
    job_id, ip = resolve_exec_host_from_row({"exec_host": {"ip": "127.0.1.23"}})
    assert job_id is None
    assert ip == "127.0.1.23"
