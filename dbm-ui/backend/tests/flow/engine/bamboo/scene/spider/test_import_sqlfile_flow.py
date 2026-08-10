# -*- coding: utf-8 -*-
from types import SimpleNamespace

import pytest
from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.spider import import_sqlfile_flow as mod
from backend.flow.engine.bamboo.scene.spider.import_sqlfile_flow import ImportSQLFlow
from backend.flow.plugins.components.collections.spider.check_rocksdb_ghost_collation import (
    CheckRocksDBGhostCollationComponent,
)


class _FakeClusters:
    def __init__(self, cluster):
        self.cluster = cluster

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


def _build_flow(monkeypatch, engine):
    cluster = SimpleNamespace(
        id=1,
        bk_cloud_id=0,
        immute_domain="test.tendbcluster.db",
        major_version="MySQL-5.7",
        db_module_id=1,
        cluster_type="tendbcluster",
        bk_biz_id=100,
        tendbcluster_ctl_primary_address=lambda: "127.0.0.1:26000",
        proxyinstance_set=SimpleNamespace(filter=lambda **kwargs: []),
    )
    _RecorderBuilder.created = []
    monkeypatch.setattr(mod, "Builder", _RecorderBuilder)
    monkeypatch.setattr(mod, "SubBuilder", _RecorderBuilder)
    monkeypatch.setattr(mod.Cluster.objects, "filter", lambda **kwargs: _FakeClusters(cluster))
    monkeypatch.setattr(mod, "get_cluster_config", lambda *args, **kwargs: {})
    monkeypatch.setattr(mod, "get_engine_from_bk_mysql_config", lambda config: engine)
    monkeypatch.setattr(mod, "add_db_actuator_download_act", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        mod,
        "GetFileList",
        lambda *args, **kwargs: SimpleNamespace(mysql_import_sqlfile=lambda path, filelist: []),
    )

    flow = ImportSQLFlow(
        root_id="root-1",
        data={
            "cluster_ids": [cluster.id],
            "path": "/tmp/sql",
            "execute_objects": [{"sql_files": ["test.sql"]}],
        },
    )
    flow.import_sqlfile_flow()
    return _RecorderBuilder.created[1].acts


@pytest.mark.parametrize(
    ("engine", "expected_check"),
    [
        ("rocksdb", True),
        ("ROCKSDB", True),
        ("innodb", False),
    ],
)
def test_ghost_collation_check_is_only_inserted_before_rocksdb_online_ddl(monkeypatch, engine, expected_check):
    acts = _build_flow(monkeypatch, engine)
    codes = [act["act_component_code"] for act in acts]

    if expected_check:
        check_index = codes.index(CheckRocksDBGhostCollationComponent.code)
        assert acts[check_index]["kwargs"] == {"cluster_id": 1}
        assert acts[check_index]["act_name"] == _("检查 RocksDB gh-ost collation 配置")
        assert acts[check_index + 1]["act_name"] == _("使用工具在线变更DDL")
    else:
        assert CheckRocksDBGhostCollationComponent.code not in codes
        assert [act["act_name"] for act in acts] == [_("检查可能阻塞DDL变更的活跃查询"), _("执行SQL导入")]
