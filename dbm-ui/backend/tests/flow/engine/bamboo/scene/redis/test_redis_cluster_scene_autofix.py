# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from unittest.mock import MagicMock, patch

import pytest

import backend.flow.engine.bamboo.scene.redis.redis_cluster_scene_auotfix as autofix_mod
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole, InstanceStatus
from backend.db_meta.models import BKCity, Cluster, Machine, NosqlStorageSetDtl, StorageInstance, StorageInstanceTuple
from backend.db_services.redis.autofix.bill import build_failed_only_send_msg_config
from backend.flow.engine.bamboo.scene.redis.redis_cluster_scene_auotfix import RedisClusterAutoFixSceneFlow
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.redis import redis_ticket as redis_ticket_mod
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.redis_ticket import RedisTicketComponent, RedisTicketService
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis import redis_act_playload as redis_act_playload_mod
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import get_twemproxy_cluster_server_shards
from backend.ticket.constants import TicketType


class _RecorderBuilder:
    """记录 act / sub_pipeline 编排顺序的伪 Builder"""

    created = []

    def __init__(self, root_id=None, data=None):
        self.root_id = root_id
        self.data = data
        self.events = []
        self.acts = []
        self.sub_pipelines = []
        self.parallel_sub_pipelines = []
        self.sub_name = None
        _RecorderBuilder.created.append(self)

    def add_act(self, act_name, act_component_code, kwargs, **extra):
        item = {"act_name": act_name, "act_component_code": act_component_code, "kwargs": kwargs, **extra}
        self.acts.append(item)
        self.events.append(("act", item))

    def add_sub_pipeline(self, sub_builder=None, **kwargs):
        sub_flow = sub_builder if sub_builder is not None else kwargs.get("sub_flow")
        self.sub_pipelines.append(sub_flow)
        self.events.append(("sub_pipeline", sub_flow))

    def add_parallel_sub_pipeline(self, sub_flow_list=None, **kwargs):
        flows = list(sub_flow_list or kwargs.get("sub_flow_list") or [])
        self.parallel_sub_pipelines.append(flows)
        self.events.append(("parallel_sub_pipeline", flows))

    def build_sub_process(self, sub_name, **kwargs):
        self.sub_name = sub_name
        return self

    def run_pipeline_with_sidecar(self, **kwargs):
        return self


def _make_flow(infos=None):
    flow = object.__new__(RedisClusterAutoFixSceneFlow)
    flow.root_id = "root-autofix-1"
    flow.data = {
        "uid": "202611250001",
        "bk_biz_id": 100,
        "created_by": "tester",
        "ticket_type": TicketType.REDIS_CLUSTER_AUTOFIX.value,
        "infos": infos or [],
    }
    flow.shutdown_clusters = []
    return flow


def _make_act_kwargs(cluster_type=ClusterType.TendisTwemproxyRedisInstance.value):
    kwargs = ActKwargs()
    kwargs.set_trans_data_dataclass = "CommonContext"
    kwargs.is_update_trans_data = True
    kwargs.bk_cloud_id = 0
    kwargs.cluster = {
        "bk_biz_id": "100",
        "bk_cloud_id": 0,
        "cluster_id": 10,
        "cluster_type": cluster_type,
        "cluster_name": "test-cluster",
        "immute_domain": "cache.drill.test.db",
        "proxy_port": 50000,
        "proxy_ips": ["1.1.1.1"],
        "backend_servers": ["2.2.2.2:30000"],
        "slave_ports": {"1.1.1.1": [30000, 30001]},
        "slave_master_map": {"1.1.1.1": "2.2.2.2"},
        "slave_ins_map": {
            "1.1.1.1:30000": "2.2.2.2:30000",
            "1.1.1.1:30001": "2.2.2.2:30001",
        },
        "db_version": "Redis-6",
    }
    return kwargs


def _patch_common_flow_deps(monkeypatch):
    _RecorderBuilder.created = []
    dbmon_calls = []

    class _FakeGetFileList:
        def __init__(self, db_type):
            self.db_type = db_type

        def redis_base(self):
            return ["redis_base.tar.gz"]

        def redis_dbmon(self):
            return ["dbactuator.tar.gz", "redis_tools.tar.gz", "bk-dbmon.tar.gz"]

    def _fake_cluster_ips_dbmon(root_id, ticket_data, sub_kwargs, param):
        dbmon_calls.append(param)
        return _RecorderBuilder().build_sub_process("fake-cluster-ips-dbmon")

    monkeypatch.setattr(autofix_mod, "Builder", _RecorderBuilder)
    monkeypatch.setattr(autofix_mod, "SubBuilder", _RecorderBuilder)
    monkeypatch.setattr(autofix_mod, "GetFileList", _FakeGetFileList)
    monkeypatch.setattr(autofix_mod, "ClusterIPsDbmonInstallAtomJob", _fake_cluster_ips_dbmon)
    monkeypatch.setattr(
        autofix_mod,
        "ClusterPredixyConfigServersRewriteAtomJob",
        lambda *args, **kwargs: _RecorderBuilder().build_sub_process("fake-predixy-rewrite"),
    )
    monkeypatch.setattr(
        autofix_mod,
        "ProxyBatchInstallAtomJob",
        lambda *args, **kwargs: _RecorderBuilder().build_sub_process("fake-proxy-install"),
    )
    monkeypatch.setattr(
        autofix_mod,
        "AccessManagerAtomJob",
        lambda *args, **kwargs: _RecorderBuilder().build_sub_process("fake-access-manager"),
    )
    monkeypatch.setattr(
        autofix_mod,
        "RedisBatchInstallAtomJob",
        lambda *args, **kwargs: _RecorderBuilder().build_sub_process("fake-redis-install"),
    )
    monkeypatch.setattr(
        autofix_mod,
        "RedisMakeSyncAtomJob",
        lambda *args, **kwargs: _RecorderBuilder().build_sub_process("fake-redis-makesync"),
    )
    monkeypatch.setattr(autofix_mod, "get_twemproxy_cluster_server_shards", lambda *args, **kwargs: {})
    monkeypatch.setattr(autofix_mod, "get_cache_backup_mode", lambda *args, **kwargs: "rdb")
    monkeypatch.setattr(
        RedisClusterAutoFixSceneFlow,
        "_RedisClusterAutoFixSceneFlow__get_cluster_config",
        staticmethod(
            lambda *args, **kwargs: {
                "redis_password": "pwd",
                "password": "ppwd",
                "redis_proxy_admin_password": "apwd",
                "port": 50000,
            }
        ),
    )
    return dbmon_calls


@pytest.mark.parametrize(
    "fix_info_extra, expected_immediate, expected_confirm",
    [
        ({"immediate_recycle": True, "need_manual_confirm": False}, True, False),
        ({"immediate_recycle": False, "need_manual_confirm": False}, False, False),
        ({"need_manual_confirm": False}, False, False),
        ({}, False, True),
    ],
    ids=["drill-immediate", "explicit-false", "legacy-no-confirm", "legacy-default"],
)
def test_proxy_fix_propagates_immediate_recycle(monkeypatch, fix_info_extra, expected_immediate, expected_confirm):
    _patch_common_flow_deps(monkeypatch)
    flow = _make_flow()
    flow_data = {**flow.data, "fix_info": {**fix_info_extra}}
    act_kwargs = _make_act_kwargs()

    sub = flow.proxy_fix(
        flow_data,
        act_kwargs,
        {
            "proxy": [{"ip": "1.1.1.1", "target": {"ip": "3.3.3.3"}}],
            "proxy_spec": {"id": 1},
        },
    )

    ticket_acts = [a for a in sub.acts if a["act_component_code"] == RedisTicketComponent.code]
    assert len(ticket_acts) == 1
    details = ticket_acts[0]["kwargs"]["ticket_details"]
    assert details["immediate_recycle"] is expected_immediate
    assert details["infos"][0]["need_manual_confirm"] is expected_confirm
    assert details["infos"][0]["proxy"] == ["1.1.1.1"]


@pytest.mark.parametrize(
    "fix_info_extra, expected_immediate, expected_confirm",
    [
        ({"immediate_recycle": True, "need_manual_confirm": False}, True, False),
        ({"immediate_recycle": False, "need_manual_confirm": False}, False, False),
        ({"need_manual_confirm": False}, False, False),
        ({}, False, True),
    ],
    ids=["drill-immediate", "explicit-false", "legacy-no-confirm", "legacy-default"],
)
def test_slave_fix_propagates_immediate_recycle(monkeypatch, fix_info_extra, expected_immediate, expected_confirm):
    _patch_common_flow_deps(monkeypatch)
    flow = _make_flow()
    flow_data = {**flow.data, "fix_info": {**fix_info_extra}}
    act_kwargs = _make_act_kwargs()

    sub = flow.slave_fix(
        flow_data,
        act_kwargs,
        {
            "redis_slave": [{"ip": "1.1.1.1", "target": {"ip": "3.3.3.3"}}],
            "slave_spec": {"id": 2},
        },
    )

    ticket_acts = [a for a in sub.acts if a["act_component_code"] == RedisTicketComponent.code]
    assert len(ticket_acts) == 1
    details = ticket_acts[0]["kwargs"]["ticket_details"]
    assert details["immediate_recycle"] is expected_immediate
    assert details["infos"][0]["need_manual_confirm"] is expected_confirm
    assert details["infos"][0]["redis_slave"] == ["1.1.1.1"]


@pytest.mark.parametrize(
    "fix_info_extra, expected_immediate",
    [
        ({"immediate_recycle": True}, True),
        ({"immediate_recycle": False}, False),
        ({}, False),
    ],
    ids=["drill-immediate", "explicit-false", "legacy-omitted"],
)
def test_start_redis_autofix_summary_shutdown_propagates_immediate_recycle(
    monkeypatch, fix_info_extra, expected_immediate
):
    _patch_common_flow_deps(monkeypatch)
    cluster_fix = {
        "bk_biz_id": 100,
        "cluster_ids": [10],
        "immute_domain": "ins.drill.test.db",
        "redis_slave": [{"ip": "1.1.1.1", "target": {"ip": "3.3.3.3"}}],
        **fix_info_extra,
    }
    flow = _make_flow(infos=[cluster_fix])
    monkeypatch.setattr(autofix_mod, "GetFileList", lambda db_type: type("F", (), {"redis_base": lambda self: []})())
    monkeypatch.setattr(
        RedisClusterAutoFixSceneFlow,
        "get_cluster_info",
        staticmethod(lambda bk_biz_id, cluster_id: _make_act_kwargs(ClusterType.RedisInstance.value).cluster),
    )

    def _fake_cluster_fix(self, flow_data, cluster_kwargs, fix_params):
        self.shutdown_clusters.append(
            {
                "cluster_id": 10,
                "immute_domain": "ins.drill.test.db",
                "bk_cloud_id": 0,
                "redis_slave": ["1.1.1.1"],
            }
        )
        return _RecorderBuilder().build_sub_process("fake-cluster-fix")

    monkeypatch.setattr(RedisClusterAutoFixSceneFlow, "cluster_fix", _fake_cluster_fix)

    pipeline = flow.start_redis_auotfix()
    ticket_acts = [a for a in pipeline.acts if a["act_component_code"] == RedisTicketComponent.code]
    assert len(ticket_acts) == 1
    details = ticket_acts[0]["kwargs"]["ticket_details"]
    assert details["immediate_recycle"] is expected_immediate
    assert len(details["infos"]) == 1


@pytest.mark.parametrize(
    "cluster_type",
    [
        ClusterType.TendisTwemproxyRedisInstance.value,
        ClusterType.TendisPredixyRedisCluster.value,
    ],
    ids=["twemproxy-cluster", "predixy-redis-cluster"],
)
def test_slave_fix_reinstalls_dbmon_for_master_and_new_slave_on_cluster_types(monkeypatch, cluster_type):
    dbmon_calls = _patch_common_flow_deps(monkeypatch)
    flow = _make_flow()
    flow_data = {**flow.data, "fix_info": {"immediate_recycle": False, "need_manual_confirm": True}}
    act_kwargs = _make_act_kwargs(cluster_type=cluster_type)
    act_kwargs.cluster["slave_ports"] = {"1.1.1.1": [30000], "1.1.1.9": [30001]}
    act_kwargs.cluster["slave_master_map"] = {"1.1.1.1": "2.2.2.2", "1.1.1.9": "2.2.2.2"}
    act_kwargs.cluster["slave_ins_map"] = {
        "1.1.1.1:30000": "2.2.2.2:30000",
        "1.1.1.9:30001": "2.2.2.2:30001",
    }

    sub = flow.slave_fix(
        flow_data,
        act_kwargs,
        {
            "redis_slave": [
                {"ip": "1.1.1.1", "target": {"ip": "3.3.3.3"}},
                {"ip": "1.1.1.9", "target": {"ip": "3.3.3.9"}},
            ],
            "slave_spec": {"id": 2},
        },
    )

    assert dbmon_calls == [
        {
            "cluster_domain": "cache.drill.test.db",
            "ips": ["2.2.2.2", "3.3.3.3", "3.3.3.9"],
            "is_stop": False,
        }
    ]

    meta_idx = next(
        idx
        for idx, (kind, item) in enumerate(sub.events)
        if kind == "act"
        and item["act_component_code"] == RedisDBMetaComponent.code
        and item["kwargs"]["cluster"].get("meta_func_name") == RedisDBMeta.redis_redo_slaves.__name__
    )
    dbmon_idx = next(
        idx
        for idx, (kind, item) in enumerate(sub.events)
        if kind == "sub_pipeline" and getattr(item, "sub_name", "") == "fake-cluster-ips-dbmon"
    )
    shutdown_idx = next(
        idx
        for idx, (kind, item) in enumerate(sub.events)
        if kind == "act" and item["act_component_code"] == RedisTicketComponent.code
    )
    assert meta_idx < dbmon_idx < shutdown_idx


def test_slave_fix_reinstalls_dbmon_for_master_and_new_slave_on_redis_instance(monkeypatch):
    dbmon_calls = _patch_common_flow_deps(monkeypatch)
    flow = _make_flow()
    flow_data = {**flow.data, "fix_info": {"immediate_recycle": True, "need_manual_confirm": False}}
    act_kwargs = _make_act_kwargs(cluster_type=ClusterType.TendisRedisInstance.value)

    sub = flow.slave_fix(
        flow_data,
        act_kwargs,
        {
            "redis_slave": [{"ip": "1.1.1.1", "target": {"ip": "3.3.3.3"}}],
            "slave_spec": {"id": 2},
        },
    )

    # 主从版单机可能跨多集群，必须走 bkdbmon_install_list_new 而非单域名的 ClusterIPsDbmonInstallAtomJob
    assert dbmon_calls == []

    trans_acts = [
        (idx, item)
        for idx, (kind, item) in enumerate(sub.events)
        if kind == "act" and item["act_component_code"] == TransFileComponent.code
    ]
    assert len(trans_acts) == 1
    trans_idx, trans_act = trans_acts[0]
    assert trans_act["kwargs"]["exec_ip"] == ["2.2.2.2", "3.3.3.3"]
    assert trans_act["kwargs"]["file_list"] == ["dbactuator.tar.gz", "redis_tools.tar.gz", "bk-dbmon.tar.gz"]

    dbmon_acts = [
        (idx, item)
        for idx, (kind, item) in enumerate(sub.events)
        if kind == "act"
        and item["act_component_code"] == ExecuteDBActuatorScriptComponent.code
        and item["kwargs"].get("get_redis_payload_func") == RedisActPayload.bkdbmon_install_list_new.__name__
    ]
    assert len(dbmon_acts) == 2
    assert [act["kwargs"]["exec_ip"] for _, act in dbmon_acts] == ["2.2.2.2", "3.3.3.3"]
    assert [act["kwargs"]["cluster"]["ip"] for _, act in dbmon_acts] == ["2.2.2.2", "3.3.3.3"]
    assert [act["kwargs"]["cluster"]["is_stop"] for _, act in dbmon_acts] == [False, False]

    meta_idx = next(
        idx
        for idx, (kind, item) in enumerate(sub.events)
        if kind == "act"
        and item["act_component_code"] == RedisDBMetaComponent.code
        and item["kwargs"]["cluster"].get("meta_func_name") == RedisDBMeta.redis_redo_slaves.__name__
    )
    disable_shield_idx = next(
        idx
        for idx, (kind, item) in enumerate(sub.events)
        if kind == "act" and item["act_component_code"] == DisableAlarmShieldComponent.code
    )
    assert meta_idx < trans_idx < dbmon_acts[0][0] < dbmon_acts[1][0] < disable_shield_idx
    assert len(flow.shutdown_clusters) == 1
    assert flow.shutdown_clusters[0]["redis_slave"] == ["1.1.1.1"]


@pytest.mark.parametrize(
    "with_msg_config", [True, False], ids=["drill-with-msg-config", "non-drill-without-msg-config"]
)
def test_autofix_shutdown_branches_propagate_send_msg_config(monkeypatch, with_msg_config):
    _patch_common_flow_deps(monkeypatch)
    msg_cfg = build_failed_only_send_msg_config() if with_msg_config else None

    # 1. proxy_fix 分支
    flow_proxy = _make_flow()
    if msg_cfg:
        flow_proxy.data["send_msg_config"] = msg_cfg
    sub_proxy = flow_proxy.proxy_fix(
        {
            **flow_proxy.data,
            "fix_info": {"immediate_recycle": with_msg_config, "need_manual_confirm": not with_msg_config},
        },
        _make_act_kwargs(),
        {"proxy": [{"ip": "1.1.1.1", "target": {"ip": "3.3.3.3"}}], "proxy_spec": {"id": 1}},
    )
    proxy_details = [a for a in sub_proxy.acts if a["act_component_code"] == RedisTicketComponent.code][0]["kwargs"][
        "ticket_details"
    ]
    assert proxy_details.get("send_msg_config") == msg_cfg

    # 2. slave_fix 单集群分支
    flow_slave = _make_flow()
    if msg_cfg:
        flow_slave.data["send_msg_config"] = msg_cfg
    sub_slave = flow_slave.slave_fix(
        {
            **flow_slave.data,
            "fix_info": {"immediate_recycle": with_msg_config, "need_manual_confirm": not with_msg_config},
        },
        _make_act_kwargs(),
        {"redis_slave": [{"ip": "1.1.1.1", "target": {"ip": "3.3.3.3"}}], "slave_spec": {"id": 2}},
    )
    slave_details = [a for a in sub_slave.acts if a["act_component_code"] == RedisTicketComponent.code][0]["kwargs"][
        "ticket_details"
    ]
    assert slave_details.get("send_msg_config") == msg_cfg

    # 3. start_redis_auotfix 主从汇总下架分支
    cluster_fix = {
        "bk_biz_id": 100,
        "cluster_ids": [10],
        "immute_domain": "ins.drill.test.db",
        "redis_slave": [{"ip": "1.1.1.1", "target": {"ip": "3.3.3.3"}}],
        "immediate_recycle": with_msg_config,
    }
    flow_summary = _make_flow(infos=[cluster_fix])
    if msg_cfg:
        flow_summary.data["send_msg_config"] = msg_cfg
    monkeypatch.setattr(autofix_mod, "GetFileList", lambda db_type: type("F", (), {"redis_base": lambda self: []})())
    monkeypatch.setattr(
        RedisClusterAutoFixSceneFlow,
        "get_cluster_info",
        staticmethod(lambda bk_biz_id, cluster_id: _make_act_kwargs(ClusterType.RedisInstance.value).cluster),
    )

    def _fake_cluster_fix(self, flow_data, cluster_kwargs, fix_params):
        self.shutdown_clusters.append(
            {"cluster_id": 10, "immute_domain": "ins.drill.test.db", "bk_cloud_id": 0, "redis_slave": ["1.1.1.1"]}
        )
        return _RecorderBuilder().build_sub_process("fake-cluster-fix")

    monkeypatch.setattr(RedisClusterAutoFixSceneFlow, "cluster_fix", _fake_cluster_fix)
    summary_pipeline = flow_summary.start_redis_auotfix()
    summary_details = [a for a in summary_pipeline.acts if a["act_component_code"] == RedisTicketComponent.code][0][
        "kwargs"
    ]["ticket_details"]
    assert summary_details.get("send_msg_config") == msg_cfg


@pytest.mark.parametrize(
    "ticket_details_extra, expected_send_msg_config",
    [
        ({"send_msg_config": build_failed_only_send_msg_config()}, build_failed_only_send_msg_config()),
        ({}, None),
    ],
    ids=["passes-and-retains-send-msg-config", "omitted-defaults-to-none"],
)
def test_redis_ticket_service_propagates_send_msg_config(ticket_details_extra, expected_send_msg_config):
    service = RedisTicketService()
    service.log_info = MagicMock()
    ticket_details = {
        "immediate_recycle": bool(expected_send_msg_config),
        "infos": [{"cluster_id": 10, "redis_slave": ["1.1.1.1"]}],
        **ticket_details_extra,
    }
    data = MagicMock()
    data.get_one_of_inputs.return_value = {
        "bk_biz_id": 100,
        "immute_domain": "cache.drill.test.db",
        "ticket_type": TicketType.REDIS_CLUSTER_INSTANCE_SHUTDOWN.value,
        "ticket_details": ticket_details,
    }

    with patch.object(redis_ticket_mod.DBAdministrator, "get_biz_db_type_admins", return_value=["dba"]), patch.object(
        redis_ticket_mod, "get_ticket_heplers", return_value=["helper"]
    ), patch.object(redis_ticket_mod.Ticket, "create_ticket", return_value=MagicMock(id=888)) as mock_create:
        assert service._execute(data, MagicMock()) is True

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["send_msg_config"] == expected_send_msg_config
    # details 中保留 send_msg_config 以便 Ticket.create_recycle_ticket 透传给 RECYCLE_OLD_HOST
    assert call_kwargs["details"].get("send_msg_config") == expected_send_msg_config


def test_dbmon_reinstall_skips_faulty_old_slave_ips(monkeypatch):
    dbmon_calls = _patch_common_flow_deps(monkeypatch)
    flow = _make_flow()
    sub = _RecorderBuilder()
    act_kwargs = _make_act_kwargs()
    # 极端保护：即使 slave_master_map 中意外出现待下架故障机 IP，也不得对其下发 dbmon 重装
    act_kwargs.cluster["slave_master_map"] = {"1.1.1.1": "2.2.2.2", "1.1.1.9": "1.1.1.1"}

    flow._add_dbmon_reinstall_acts(
        sub,
        flow.data,
        act_kwargs,
        [
            {"ip": "1.1.1.1", "target": {"ip": "3.3.3.3"}},
            {"ip": "1.1.1.9", "target": {"ip": "3.3.3.9"}},
        ],
    )

    assert len(dbmon_calls) == 1
    assert dbmon_calls[0]["ips"] == ["2.2.2.2", "3.3.3.3", "3.3.3.9"]
    assert "1.1.1.1" not in dbmon_calls[0]["ips"]
    assert "1.1.1.9" not in dbmon_calls[0]["ips"]


@pytest.mark.django_db
def test_get_twemproxy_cluster_server_shards_and_dbmon_params_with_transient_two_slaves(monkeypatch):
    """redis_redo_slaves 后、旧故障机下架前会出现 1 master -> 2 slaves（old UNAVAILABLE + new RUNNING），不得触发 MultipleObjectsReturned"""
    bk_city = BKCity.objects.first() or BKCity.objects.create(bk_idc_city_id=1, bk_idc_city_name="sz")
    cluster = Cluster.objects.create(
        bk_biz_id=100,
        bk_cloud_id=0,
        name="twem-autofix-test",
        db_module_id=0,
        immute_domain="cache.twem-two-slaves.test.db",
        cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
    )

    def _mk_machine(host_id, ip):
        return Machine.objects.create(
            ip=ip,
            bk_biz_id=100,
            bk_cloud_id=0,
            bk_host_id=host_id,
            bk_city=bk_city,
            cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
        )

    m_old_slave = _mk_machine(91001, "1.1.1.1")
    m_master = _mk_machine(91002, "2.2.2.2")
    m_new_slave = _mk_machine(91003, "3.3.3.3")

    master_inst = StorageInstance.objects.create(
        port=30000,
        machine=m_master,
        bk_biz_id=100,
        cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
        status=InstanceStatus.RUNNING.value,
        instance_role=InstanceRole.REDIS_MASTER.value,
        instance_inner_role=InstanceInnerRole.MASTER.value,
    )
    old_slave_inst = StorageInstance.objects.create(
        port=30000,
        machine=m_old_slave,
        bk_biz_id=100,
        cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
        status=InstanceStatus.UNAVAILABLE.value,
        instance_role=InstanceRole.REDIS_SLAVE.value,
        instance_inner_role=InstanceInnerRole.SLAVE.value,
    )
    new_slave_inst = StorageInstance.objects.create(
        port=30000,
        machine=m_new_slave,
        bk_biz_id=100,
        cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
        status=InstanceStatus.RUNNING.value,
        instance_role=InstanceRole.REDIS_SLAVE.value,
        instance_inner_role=InstanceInnerRole.SLAVE.value,
    )
    cluster.storageinstance_set.add(master_inst, old_slave_inst, new_slave_inst)
    NosqlStorageSetDtl.objects.create(
        bk_biz_id=100,
        cluster=cluster,
        instance=master_inst,
        seg_range="0-419999",
    )
    # 模拟 redis_redo_slaves 后、下架单执行前的双 tuple 过渡态
    StorageInstanceTuple.objects.create(ejector=master_inst, receiver=old_slave_inst)
    StorageInstanceTuple.objects.create(ejector=master_inst, receiver=new_slave_inst)

    shards = get_twemproxy_cluster_server_shards(100, cluster.id, {})
    assert shards["2.2.2.2"] == {"2.2.2.2:30000": "0-419999"}
    assert shards["3.3.3.3"] == {"3.3.3.3:30000": "0-419999"}

    monkeypatch.setattr(
        redis_act_playload_mod.AppCache, "get_app_attr", staticmethod(lambda bk_biz_id, attr: "testapp")
    )
    monkeypatch.setattr(redis_act_playload_mod, "get_cache_backup_mode", lambda **kwargs: "rdb")

    master_params = RedisActPayload.get_bkdbmon_servers_params(cluster, "2.2.2.2")
    assert master_params["meta_role"] == InstanceRole.REDIS_MASTER.value
    assert master_params["server_shards"] == {"2.2.2.2:30000": "0-419999"}

    new_slave_params = RedisActPayload.get_bkdbmon_servers_params(cluster, "3.3.3.3")
    assert new_slave_params["meta_role"] == InstanceRole.REDIS_SLAVE.value
    assert new_slave_params["server_shards"] == {"3.3.3.3:30000": "0-419999"}
