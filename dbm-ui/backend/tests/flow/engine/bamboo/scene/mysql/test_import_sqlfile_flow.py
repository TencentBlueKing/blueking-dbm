# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.flow.engine.bamboo.scene.mysql import import_sqlfile_flow as mod
from backend.flow.engine.bamboo.scene.mysql.import_sqlfile_flow import ImportSQLFlow
from backend.flow.plugins.components.collections.mysql import check_sqlfile_md5 as check_mod
from backend.flow.plugins.components.collections.mysql.check_sqlfile_md5 import CheckSqlFileMd5Component
from backend.flow.plugins.components.collections.mysql.exec_actuator_script_with_bk_job_record import (
    ExecuteDBActuatorScriptWithBkJobRecordComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.ticket.constants import TicketType


class _FakeClusters:
    def __init__(self, cluster):
        self.cluster = cluster

    def prefetch_related(self, *args):
        return self

    def __iter__(self):
        return iter([self.cluster])

    def get(self, id):
        assert id == self.cluster.id
        return self.cluster


class _RecorderBuilder:
    created = []

    def __init__(self, *args, **kwargs):
        self.acts = []
        self.parallel_acts = []
        self.parallel_sub_pipelines = []
        self.ran = False
        _RecorderBuilder.created.append(self)

    def add_act(self, act_name, act_component_code, kwargs, **extra):
        self.acts.append(
            {
                "act_name": act_name,
                "act_component_code": act_component_code,
                "kwargs": kwargs,
                **extra,
            }
        )

    def add_parallel_acts(self, acts_list=None, **kwargs):
        self.parallel_acts.append(list(acts_list or kwargs.get("acts_list") or []))

    def add_parallel_sub_pipeline(self, sub_flow_list=None, **kwargs):
        self.parallel_sub_pipelines.append(list(sub_flow_list or kwargs.get("sub_flow_list") or []))

    def build_sub_process(self, sub_name):
        return {"sub_name": sub_name, "builder": self}

    def run_pipeline(self, *args, **kwargs):
        self.ran = True


def _run_flow(monkeypatch, extra_data):
    cluster = SimpleNamespace(id=1, bk_cloud_id=0, immute_domain="mysql.example.com")
    master = SimpleNamespace(machine=SimpleNamespace(ip="127.0.0.1"), port=20000)
    _RecorderBuilder.created = []
    monkeypatch.setattr(mod, "Builder", _RecorderBuilder)
    monkeypatch.setattr(mod, "SubBuilder", _RecorderBuilder)
    monkeypatch.setattr(mod.Cluster.objects, "filter", lambda **kwargs: _FakeClusters(cluster))
    monkeypatch.setattr(ImportSQLFlow, "_resolve_mysql_import_storage", lambda self, item: master)
    monkeypatch.setattr(mod, "add_db_actuator_download_act", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        mod,
        "GetFileList",
        lambda *args, **kwargs: SimpleNamespace(mysql_import_sqlfile=lambda path, filelist: []),
    )
    data = {
        "cluster_ids": [cluster.id],
        "path": "/tmp/sql",
        "execute_objects": [{"sql_files": ["change.sql"]}],
    }
    data.update(extra_data)

    ImportSQLFlow(root_id="root-1", data=data).import_sqlfile_flow()
    return _RecorderBuilder.created[0], _RecorderBuilder.created[1]


def test_md5_check_is_between_transfer_and_import(monkeypatch):
    parent, sub = _run_flow(
        monkeypatch,
        {
            "ticket_type": TicketType.MYSQL_IMPORT_SQLFILE.value,
            "sql_files_md5": {"change.sql": "d41d8cd98f00b204e9800998ecf8427e"},
        },
    )

    assert [group[-1]["act_component_code"] for group in parent.parallel_acts] == [
        TransFileComponent.code,
        CheckSqlFileMd5Component.code,
    ]
    check_act = parent.parallel_acts[1][0]
    assert check_act["skippable"] is True
    assert check_act["retryable"] is True
    assert check_act["error_ignorable"] is False
    assert check_act["kwargs"]["repo_path"] == "/tmp/sql"
    assert sub.acts[0]["act_component_code"] == ExecuteDBActuatorScriptWithBkJobRecordComponent.code


@pytest.mark.parametrize(
    ("extra_data", "reason", "ticket_type"),
    [
        ({}, "missing", None),
        ({"sql_files_md5": {}}, "empty", None),
        (
            {
                "ticket_type": TicketType.MYSQL_FORCE_IMPORT_SQLFILE.value,
                "sql_files_md5": {"change.sql": "d41d8cd98f00b204e9800998ecf8427e"},
            },
            "force",
            TicketType.MYSQL_FORCE_IMPORT_SQLFILE.value,
        ),
        (
            {
                "ticket_type": TicketType.TENDBCLUSTER_FORCE_IMPORT_SQLFILE.value,
                "sql_files_md5": {"change.sql": "d41d8cd98f00b204e9800998ecf8427e"},
            },
            "force",
            TicketType.TENDBCLUSTER_FORCE_IMPORT_SQLFILE.value,
        ),
    ],
)
def test_skip_cases_add_no_md5_node_and_log_reason(monkeypatch, extra_data, reason, ticket_type):
    log_info = MagicMock()
    monkeypatch.setattr(check_mod.logger, "info", log_info)
    parent, unused_sub = _run_flow(monkeypatch, extra_data)

    codes = [act["act_component_code"] for group in parent.parallel_acts for act in group]
    assert CheckSqlFileMd5Component.code not in codes
    log_text = str(log_info.call_args.args[0])
    assert "reason={}".format(reason) in log_text
    assert "ticket_type={}".format(ticket_type) in log_text
