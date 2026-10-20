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
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.flow.engine.bamboo.scene.mongodb.mongodb_deferred_deinstall import _normalize_instance_type
from backend.flow.engine.bamboo.scene.mongodb.sub_task.replicaset_replace import _build_deferred_deinstall_infos
from backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_check_meta import (
    MongoDeferredDeinstallCheckMeta,
)
from backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_poll_gse import (
    MongoDeferredDeinstallPollGse,
)
from backend.ticket.constants import TicketType


def test_normalize_instance_type():
    assert _normalize_instance_type({"instance_type": "mongos"}) == "mongos"
    assert _normalize_instance_type({"role": "mongod"}) == "mongod"
    assert _normalize_instance_type({"role": ["mongos"]}) == "mongos"
    assert _normalize_instance_type({}) == "mongod"


def test_build_deferred_deinstall_infos():
    info = {"instances": [{"cluster_id": 128, "port": 27001, "cluster_name": "rs1"}]}
    old_instances = [{"ip": "127.0.0.1", "port": 27001, "bk_cloud_id": 0, "set_id": "rs1"}]
    infos = _build_deferred_deinstall_infos(info, old_instances, "mongod")
    assert len(infos) == 1
    assert infos[0]["cluster_id"] == 128
    assert infos[0]["instance_type"] == "mongod"
    assert infos[0]["ip"] == "127.0.0.1"


def test_check_meta_sets_machine_exists():
    svc = MongoDeferredDeinstallCheckMeta()
    svc.log_info = MagicMock()
    data = MagicMock()
    data.outputs = SimpleNamespace()
    data.get_one_of_inputs.return_value = {"ip": "127.0.0.1", "bk_cloud_id": 0}

    with patch(
        "backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_check_meta.Machine"
    ) as machine_cls:
        machine_cls.objects.filter.return_value.exists.return_value = True
        assert svc._execute(data, None) is True
        assert data.outputs.machine_exists == 1

        machine_cls.objects.filter.return_value.exists.return_value = False
        assert svc._execute(data, None) is True
        assert data.outputs.machine_exists == 0

        data.get_one_of_inputs.return_value = {"ip": "127.0.0.1", "bk_cloud_id": 0, "force_physical": True}
        assert svc._execute(data, None) is True
        assert data.outputs.machine_exists == 1


def test_poll_gse_finishes_when_already_alive():
    svc = MongoDeferredDeinstallPollGse()
    svc.log_info = MagicMock()
    data = MagicMock()
    data.outputs = SimpleNamespace()
    data.get_one_of_inputs.return_value = {"ip": "127.0.0.1", "bk_cloud_id": 0, "poll_interval_sec": 300}

    with patch(
        "backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_poll_gse._probe_gse_alive_once",
        return_value=True,
    ):
        assert svc._execute(data, None) is True
        assert data.outputs.gse_alive == 1


def test_deferred_ticket_type_constant():
    assert TicketType.MONGODB_DEFERRED_DEINSTALL.value == "MONGODB_DEFERRED_DEINSTALL"


def test_format_deferred_targets_dedupes_ip():
    from backend.flow.utils.mongodb.deferred_deinstall_ticket import _format_deferred_targets

    assert (
        _format_deferred_targets(
            [
                {"ip": "127.0.0.10", "port": 27001},
                {"ip": "127.0.0.10", "port": 27002},
            ]
        )
        == "127.0.0.10"
    )
    assert (
        _format_deferred_targets(
            [
                {"ip": "127.0.0.1", "port": 27001},
                {"ip": "127.0.0.2", "port": 27001},
            ]
        )
        == "127.0.0.1;127.0.0.2"
    )


def test_deferred_deinstall_remark_includes_predecessor_ids():
    from backend.flow.utils.mongodb.deferred_deinstall_ticket import deferred_deinstall_ticket

    running = MagicMock()
    running.id = 486
    pre = MagicMock()
    pre.id = 485
    created = MagicMock()
    created.id = 490
    core = MagicMock()
    core.id = 10

    with (
        patch(
            "backend.flow.utils.mongodb.deferred_deinstall_ticket.Ticket.objects.select_for_update"
        ) as select_for_update,
        patch("backend.flow.utils.mongodb.deferred_deinstall_ticket._unlock_running_for_deferred") as unlock,
        patch(
            "backend.flow.utils.mongodb.deferred_deinstall_ticket._resolve_relate_ticket",
            return_value=pre,
        ),
        patch(
            "backend.flow.utils.mongodb.deferred_deinstall_ticket._resolve_autofix_core_id",
            return_value=10,
        ),
        patch("backend.flow.utils.mongodb.deferred_deinstall_ticket.Ticket.create_ticket", return_value=created) as ct,
        patch(
            "backend.flow.utils.mongodb.deferred_deinstall_ticket._prepare_deferred_infos",
            side_effect=lambda items: (items, []),
        ),
        patch("backend.ticket.flow_manager.manager.TicketFlowManager") as flow_mgr,
    ):
        select_for_update.return_value.get.return_value = running
        deferred_deinstall_ticket(
            infos=[
                {"ip": "127.0.0.10", "port": 27001, "bk_cloud_id": 0},
                {"ip": "127.0.0.10", "port": 27002, "bk_cloud_id": 0},
            ],
            creator="admin",
            bk_biz_id=3,
            parent_ticket=running,
        )
        select_for_update.return_value.get.assert_called_once_with(id=486)
        unlock.assert_called_once()
        remark = ct.call_args.kwargs["remark"]
        assert remark == "自动发起-延迟下架-127.0.0.10-自愈#10-来自单据#485"
        assert ct.call_args.kwargs["auto_execute"] is False
        pre.add_related_ticket.assert_called_once_with(created, done=True)
        flow_mgr.assert_called_once_with(ticket=created)
        flow_mgr.return_value.run_next_flow.assert_called_once()


def test_cleanup_meta_deletes_orphan_machine():
    from backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_cleanup_meta import (
        MongoDeferredDeinstallCleanupMeta,
    )

    svc = MongoDeferredDeinstallCleanupMeta()
    svc.log_info = MagicMock()
    svc.log_error = MagicMock()
    data = MagicMock()
    data.get_one_of_inputs.return_value = {"ip": "127.0.0.1", "bk_cloud_id": 0}
    machine = MagicMock()
    machine.bk_host_id = 576
    machine.bk_biz_id = 3
    machine.cluster_type = "MongoReplicaSet"

    with (
        patch(
            "backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_cleanup_meta.Machine"
        ) as machine_cls,
        patch(
            "backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_cleanup_meta.StorageInstance"
        ) as storage_cls,
        patch(
            "backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_cleanup_meta.ProxyInstance"
        ) as proxy_cls,
        patch(
            "backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_cleanup_meta.CcManage"
        ) as cc_cls,
    ):
        machine_cls.objects.filter.return_value.first.return_value = machine
        storage_cls.objects.filter.return_value.exists.return_value = False
        proxy_cls.objects.filter.return_value.exists.return_value = False
        assert svc._execute(data, None) is True
        cc_cls.return_value.recycle_host.assert_called_once_with([576])
        machine.delete.assert_called_once()


def test_cleanup_meta_recycles_snapshot_when_machine_gone():
    from backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_cleanup_meta import (
        MongoDeferredDeinstallCleanupMeta,
    )

    svc = MongoDeferredDeinstallCleanupMeta()
    svc.log_info = MagicMock()
    data = MagicMock()
    data.get_one_of_inputs.return_value = {
        "ip": "127.0.0.1",
        "bk_cloud_id": 0,
        "recycle_host": {
            "ip": "127.0.0.1",
            "bk_host_id": 576,
            "bk_biz_id": 3,
            "bk_cloud_id": 0,
            "cluster_type": "MongoReplicaSet",
        },
    }
    with (
        patch(
            "backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_cleanup_meta.Machine"
        ) as machine_cls,
        patch(
            "backend.flow.plugins.components.collections.mongodb.mongo_deferred_deinstall_cleanup_meta.CcManage"
        ) as cc_cls,
    ):
        machine_cls.objects.filter.return_value.first.return_value = None
        assert svc._execute(data, None) is True
        cc_cls.assert_called_once_with(3, "MongoReplicaSet")
        cc_cls.return_value.recycle_host.assert_called_once_with([576])


def test_deferred_deinstall_kwargs_sends_replica_set_peers():
    from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

    ak = ActKwargs()
    ak.payload = {"bk_cloud_id": 0}
    ak.file_path = "/tmp/actuator"
    node = {
        "ip": "127.0.0.1",
        "port": 27001,
        "bk_cloud_id": 0,
        "cluster_id": 1,
        "set_id": "rs1",
    }
    member_self = SimpleNamespace(ip="127.0.0.1", port=27001)
    peer = SimpleNamespace(ip="127.0.0.2", port=27001)
    replica = SimpleNamespace(set_name="rs1", members=[member_self, peer])
    cluster = SimpleNamespace(get_config=lambda: None, get_shards=lambda: [replica])
    with patch.object(ak, "_resolve_deferred_deinstall_password", return_value="secret"), patch(
        "backend.flow.utils.mongodb.mongodb_dataclass.MongoRepository.fetch_one_cluster",
        return_value=cluster,
    ):
        kwargs = ak.get_mongo_deferred_deinstall_kwargs(node, "mongod", [node])
    payload = kwargs["db_act_template"]["payload"]
    assert payload["replicaSetPeers"] == ["127.0.0.2:27001"]
    assert payload["removedCheckAttempts"] == 36
    assert payload["removedCheckIntervalSec"] == 5


def test_resolve_deferred_deinstall_password_skips_empty_and_falls_back():
    """旧实例密码已删时服务常返回空串，须回退同集群其它实例。"""
    from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

    ak = ActKwargs()
    peer = MagicMock()
    peer.machine.ip = "127.0.0.2"
    peer.port = 27001
    peer.machine.bk_cloud_id = 0

    def fake_get_password(ip, port, bk_cloud_id, username):
        if ip == "127.0.0.1":
            return ""
        if ip == "127.0.0.2":
            return "secret"
        raise ValueError("missing")

    storage_qs = MagicMock()
    storage_qs.select_related.return_value.__getitem__ = MagicMock(return_value=[peer])
    proxy_qs = MagicMock()
    proxy_qs.select_related.return_value.__getitem__ = MagicMock(return_value=[])

    with (
        patch.object(ActKwargs, "get_password", side_effect=fake_get_password),
        patch("backend.db_meta.models.StorageInstance") as storage_cls,
        patch("backend.db_meta.models.ProxyInstance") as proxy_cls,
    ):
        storage_cls.objects.filter.return_value = storage_qs
        proxy_cls.objects.filter.return_value = proxy_qs
        assert ak._resolve_deferred_deinstall_password("127.0.0.1", 27001, 0, cluster_id=1) == "secret"


def test_prepare_deferred_infos_detaches_and_strips_cluster_lock():
    from backend.flow.utils.mongodb.deferred_deinstall_ticket import _prepare_deferred_infos

    infos = [
        {
            "ip": "127.0.0.1",
            "port": 27001,
            "bk_cloud_id": 0,
            "cluster_id": 128,
            "cluster_ids": [128],
            "instance_type": "mongod",
        }
    ]
    snap = {
        "ip": "127.0.0.1",
        "bk_host_id": 9,
        "bk_biz_id": 3,
        "bk_cloud_id": 0,
        "cluster_type": "MongoReplicaSet",
    }
    with (
        patch("backend.flow.utils.mongodb.deferred_deinstall_ticket._snapshot_deferred_runtime"),
        patch(
            "backend.flow.utils.mongodb.deferred_deinstall_ticket._detach_deferred_machine",
            return_value=snap,
        ) as detach,
    ):
        prepared, old_nodes = _prepare_deferred_infos(infos)
    detach.assert_called_once_with("127.0.0.1", 0)
    assert "cluster_id" not in prepared[0]
    assert "cluster_ids" not in prepared[0]
    assert prepared[0]["origin_cluster_id"] == 128
    assert prepared[0]["force_physical"] is True
    assert prepared[0]["recycle_host"]["bk_host_id"] == 9
    assert old_nodes == [{"ip": "127.0.0.1", "bk_biz_id": 3, "bk_host_id": 9, "bk_cloud_id": 0}]
    assert infos[0]["cluster_id"] == 128


def test_deferred_kwargs_uses_snapshotted_peers_without_cluster():
    from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

    ak = ActKwargs()
    ak.payload = {"bk_cloud_id": 0}
    ak.file_path = "/tmp/actuator"
    node = {
        "ip": "127.0.0.1",
        "port": 27001,
        "bk_cloud_id": 0,
        "set_id": "rs1",
        "replica_set_peers": ["127.0.0.2:27001"],
    }

    def fake_get_password(ip, port, bk_cloud_id, username):
        if ip == "127.0.0.2":
            return "secret"
        return ""

    with (
        patch.object(ActKwargs, "get_password", side_effect=fake_get_password),
        patch("backend.flow.utils.mongodb.mongodb_dataclass.MongoRepository.fetch_one_cluster") as fetch,
    ):
        kwargs = ak.get_mongo_deferred_deinstall_kwargs(node, "mongod", [node])
    fetch.assert_not_called()
    payload = kwargs["db_act_template"]["payload"]
    assert payload["replicaSetPeers"] == ["127.0.0.2:27001"]
    assert payload["adminPassword"] == "secret"


def test_deferred_ticket_supplements_from_running_and_drops_parent_recycle_hosts():
    from backend.flow.utils.mongodb.deferred_deinstall_ticket import deferred_deinstall_ticket

    running = MagicMock()
    running.id = 600
    running.bk_biz_id = 3
    running.details = {
        "cluster_type": "MongoShardedCluster",
        "recycle_hosts": [
            {"ip": "127.0.0.10", "bk_host_id": 101, "bk_cloud_id": 0, "bk_biz_id": 3},
            {"ip": "127.0.0.11", "bk_host_id": 102, "bk_cloud_id": 0, "bk_biz_id": 3},
        ],
    }
    created = SimpleNamespace(id=601)

    with (
        patch(
            "backend.flow.utils.mongodb.deferred_deinstall_ticket.Ticket.objects.select_for_update"
        ) as select_for_update,
        patch("backend.flow.utils.mongodb.deferred_deinstall_ticket._unlock_running_for_deferred"),
        patch("backend.flow.utils.mongodb.deferred_deinstall_ticket._snapshot_deferred_runtime"),
        patch("backend.flow.utils.mongodb.deferred_deinstall_ticket._detach_deferred_machine", return_value=None),
        patch("backend.flow.utils.mongodb.deferred_deinstall_ticket._resolve_relate_ticket", return_value=running),
        patch("backend.flow.utils.mongodb.deferred_deinstall_ticket._resolve_autofix_core_id", return_value=0),
        patch("backend.flow.utils.mongodb.deferred_deinstall_ticket.Ticket.create_ticket", return_value=created) as ct,
        patch("backend.ticket.flow_manager.manager.TicketFlowManager") as flow_mgr,
    ):
        select_for_update.return_value.get.return_value = running
        deferred_deinstall_ticket(
            infos=[{"ip": "127.0.0.10", "port": 27021, "bk_cloud_id": 0, "instance_type": "mongos"}],
            creator="admin",
            bk_biz_id=3,
            parent_ticket=running,
        )

    select_for_update.return_value.get.assert_called_once_with(id=600)
    assert ct.call_args.kwargs["auto_execute"] is False
    flow_mgr.assert_called_once_with(ticket=created)
    flow_mgr.return_value.run_next_flow.assert_called_once()
    details = ct.call_args.kwargs["details"]
    assert details["infos"][0]["force_physical"] is True
    assert details["infos"][0]["recycle_host"]["bk_host_id"] == 101
    assert details["old_nodes"]["instance"] == [
        {"ip": "127.0.0.10", "bk_biz_id": 3, "bk_host_id": 101, "bk_cloud_id": 0}
    ]
    assert running.details["recycle_hosts"] == [
        {"ip": "127.0.0.11", "bk_host_id": 102, "bk_cloud_id": 0, "bk_biz_id": 3}
    ]
    running.save.assert_called_once_with(update_fields=["details", "update_at"])


def test_snapshot_deferred_runtime_never_stores_plaintext_admin_password():
    from backend.flow.utils.mongodb.deferred_deinstall_ticket import _snapshot_deferred_runtime

    infos = [{"ip": "127.0.0.1", "port": 27001, "bk_cloud_id": 0, "cluster_id": 1, "instance_type": "mongod"}]
    with patch("backend.flow.utils.mongodb.mongodb_dataclass.ActKwargs._deferred_replica_set_peers", return_value=[]):
        _snapshot_deferred_runtime(infos)
    assert infos[0]["replica_set_peers"] == []
    assert "admin_password" not in infos[0]


def test_resolve_deferred_deinstall_password_fallback_by_set_id_and_biz():
    from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

    ak = ActKwargs()
    ak.payload = {"bk_biz_id": 3}
    peer = MagicMock()
    peer.machine.ip = "127.0.0.2"
    peer.port = 27001
    peer.machine.bk_cloud_id = 0

    def fake_get_password(ip, port, bk_cloud_id, username):
        if ip == "127.0.0.2":
            return "secret"
        return ""

    dtl_qs = MagicMock()
    dtl_qs.filter.return_value = dtl_qs
    dtl_qs.values_list.return_value.first.return_value = 88

    storage_qs = MagicMock()
    storage_qs.select_related.return_value.__getitem__ = MagicMock(return_value=[peer])
    proxy_qs = MagicMock()
    proxy_qs.select_related.return_value.__getitem__ = MagicMock(return_value=[])

    with (
        patch.object(ActKwargs, "get_password", side_effect=fake_get_password),
        patch(
            "backend.db_meta.models.storage_set_dtl.NosqlStorageSetDtl.objects.filter", return_value=dtl_qs
        ) as dtl_f,
        patch("backend.db_meta.models.StorageInstance") as storage_cls,
        patch("backend.db_meta.models.ProxyInstance") as proxy_cls,
    ):
        storage_cls.objects.filter.return_value = storage_qs
        proxy_cls.objects.filter.return_value = proxy_qs
        pwd = ak._resolve_deferred_deinstall_password(
            "127.0.0.1", 27001, 0, cluster_id=None, peers=[], set_id="shard-s1", bk_biz_id=3
        )
    assert pwd == "secret"
    dtl_f.assert_called_once_with(seg_range="shard-s1")
    dtl_qs.filter.assert_called_once_with(bk_biz_id=3)


def test_deferred_ticket_on_commit_catches_run_next_flow_exception():
    from backend.flow.utils.mongodb.deferred_deinstall_ticket import deferred_deinstall_ticket

    created = SimpleNamespace(id=701)
    with (
        patch("backend.flow.utils.mongodb.deferred_deinstall_ticket._snapshot_deferred_runtime"),
        patch("backend.flow.utils.mongodb.deferred_deinstall_ticket._detach_deferred_machine", return_value=None),
        patch("backend.flow.utils.mongodb.deferred_deinstall_ticket._resolve_autofix_core_id", return_value=0),
        patch("backend.flow.utils.mongodb.deferred_deinstall_ticket.Ticket.create_ticket", return_value=created),
        patch("backend.ticket.flow_manager.manager.TicketFlowManager") as flow_mgr,
    ):
        flow_mgr.return_value.run_next_flow.side_effect = RuntimeError("celery down")
        ticket = deferred_deinstall_ticket(
            infos=[{"ip": "127.0.0.10", "port": 27001, "bk_cloud_id": 0}],
            creator="admin",
            bk_biz_id=3,
            parent_ticket=None,
        )
    assert ticket is created
    flow_mgr.return_value.run_next_flow.assert_called_once()
