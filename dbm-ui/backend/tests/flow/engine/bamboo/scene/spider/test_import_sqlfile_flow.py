# -*- coding: utf-8 -*-
from types import SimpleNamespace

import pytest
from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.spider import import_sqlfile_flow as mod
from backend.flow.engine.bamboo.scene.spider.import_sqlfile_flow import ImportSQLFlow
from backend.flow.plugins.components.collections.spider.check_remote_master_var_consistency import (
    CheckRemoteMasterVarConsistencyComponent,
)
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
        self.events = []
        self.ran = False
        _RecorderBuilder.created.append(self)

    def add_act(self, act_name, act_component_code, kwargs, **extra):
        act = {
            "act_name": act_name,
            "act_component_code": act_component_code,
            "kwargs": kwargs,
            **extra,
        }
        self.acts.append(act)
        self.events.append(("act", act))

    def add_parallel_acts(self, acts_list=None, **kwargs):
        acts = list(acts_list or kwargs.get("acts_list") or [])
        self.parallel_acts.append(acts)
        self.events.append(("parallel", acts))

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
        ("tokudb", False),
    ],
)
def test_ghost_collation_check_is_only_inserted_before_rocksdb_online_ddl(monkeypatch, engine, expected_check):
    acts = _build_flow(monkeypatch, engine)
    codes = [act["act_component_code"] for act in acts]

    assert CheckRemoteMasterVarConsistencyComponent.code not in codes
    assert acts[0]["act_name"] == _("检查可能阻塞DDL变更的活跃查询")
    if expected_check:
        check_index = codes.index(CheckRocksDBGhostCollationComponent.code)
        assert check_index == 1
        assert acts[check_index]["kwargs"] == {"cluster_id": 1}
        assert acts[check_index]["act_name"] == _("检查 RocksDB gh-ost collation 配置")
        assert acts[check_index + 1]["act_name"] == _("使用工具在线变更DDL")
    else:
        assert CheckRocksDBGhostCollationComponent.code not in codes
        assert [act["act_name"] for act in acts] == [
            _("检查可能阻塞DDL变更的活跃查询"),
            _("执行SQL导入"),
        ]


def _check_act_name(domain):
    return _("检查可能影响变更的参数一致性检查[{}]").format(domain)


def _run_semantic_check(monkeypatch, cluster_ids):
    domains = {cluster_id: "c{}.tendbcluster.db".format(index) for index, cluster_id in enumerate(cluster_ids)}

    def _get_cluster(**kwargs):
        cluster_id = kwargs["id"]
        return SimpleNamespace(id=cluster_id, immute_domain=domains[cluster_id])

    _RecorderBuilder.created = []
    monkeypatch.setattr(mod, "Builder", _RecorderBuilder)
    monkeypatch.setattr(mod.Cluster.objects, "get", _get_cluster)
    monkeypatch.setattr(
        ImportSQLFlow,
        "_ImportSQLFlow__get_master_ctl_info",
        lambda self, cluster_id: {
            "bk_biz_id": 100,
            "db_module_id": 1,
            "bk_cloud_id": 0,
            "port": 26000,
            "master_ctl_ip": "127.0.0.1",
        },
    )
    monkeypatch.setattr(
        ImportSQLFlow,
        "_ImportSQLFlow__get_remotedb_version_and_instance",
        lambda self, cluster_id: ("MySQL-5.7", "127.0.0.2", 20000),
    )
    monkeypatch.setattr(mod, "get_spider_version_and_charset", lambda **kwargs: ("utf8mb4", "3.7"))
    monkeypatch.setattr(
        ImportSQLFlow,
        "_ImportSQLFlow__get_distinct_spider_versions_with_config",
        lambda self, cluster_id, bk_cloud_id: [{"version": "3.7", "start_config": {}}],
    )
    monkeypatch.setattr(
        ImportSQLFlow,
        "_ImportSQLFlow__get_storage_start_config",
        lambda self, ip, port, bk_cloud_id: {},
    )
    monkeypatch.setattr(
        ImportSQLFlow,
        "_ImportSQLFlow__get_tdbctl_start_config",
        lambda self, ip, port, bk_cloud_id: {},
    )
    monkeypatch.setattr(mod, "parse_db_from_sqlfile", lambda **kwargs: None)
    monkeypatch.setattr(mod, "add_db_actuator_download_to_pipeline", lambda **kwargs: None)

    flow = ImportSQLFlow(
        root_id="root-semantic",
        data={
            "cluster_ids": list(cluster_ids),
            "charset": "utf8mb4",
            "execute_objects": [{"sql_files": ["change.sql"]}],
            "path": "/tmp/sql",
            "bk_biz_id": 100,
            "is_auto_commit": False,
        },
    )
    flow.sql_semantic_check_flow()
    return _RecorderBuilder.created[0]


def _acts_between(builder, start_name, end_name):
    names = []
    for kind, payload in builder.events:
        if kind == "act":
            names.append(payload["act_name"])
        else:
            names.append(None)
    start = names.index(start_name)
    end = names.index(end_name)
    return builder.events[start + 1 : end]


def test_semantic_check_waves_follow_cluster_id_order(monkeypatch):
    cluster_ids = [30, 10, 50, 20, 40, 15]
    builder = _run_semantic_check(monkeypatch, cluster_ids)
    between = _acts_between(builder, _("回显SQL语义检测单据信息"), _("备份测试库表结构"))

    assert len(between) == 2
    assert between[0][0] == "parallel"
    assert between[1][0] == "act"
    wave, single = between[0][1], between[1][1]
    assert len(wave) == 5
    for index, act in enumerate(wave):
        cluster_id = cluster_ids[index]
        assert act["act_component_code"] == CheckRemoteMasterVarConsistencyComponent.code
        assert act["kwargs"] == {"cluster_id": cluster_id}
        assert act["act_name"] == _check_act_name("c{}.tendbcluster.db".format(index))
    assert single["act_component_code"] == CheckRemoteMasterVarConsistencyComponent.code
    assert single["kwargs"] == {"cluster_id": cluster_ids[5]}
    assert single["act_name"] == _check_act_name("c5.tendbcluster.db")

    names = [payload["act_name"] for kind, payload in builder.events if kind == "act"]
    dump_at = names.index(_("备份测试库表结构"))
    assert names[dump_at + 1] == _("对SQL文件进行语义测试")
    assert names[dump_at + 2] == _("创建SQL执行单据")


def test_semantic_check_one_cluster_is_a_single_act(monkeypatch):
    builder = _run_semantic_check(monkeypatch, [7])
    between = _acts_between(builder, _("回显SQL语义检测单据信息"), _("备份测试库表结构"))

    assert [event[0] for event in builder.events].count("parallel") == 0
    assert len(between) == 1
    assert between[0][0] == "act"
    act = between[0][1]
    assert act["act_component_code"] == CheckRemoteMasterVarConsistencyComponent.code
    assert act["kwargs"] == {"cluster_id": 7}
    assert act["act_name"] == _check_act_name("c0.tendbcluster.db")
    check_acts = [
        payload
        for kind, payload in builder.events
        if kind == "act" and payload["act_component_code"] == CheckRemoteMasterVarConsistencyComponent.code
    ]
    assert len(check_acts) == 1
