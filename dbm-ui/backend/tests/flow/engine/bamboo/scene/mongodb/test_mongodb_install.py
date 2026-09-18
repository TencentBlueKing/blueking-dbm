# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from backend.flow.engine.bamboo.scene.mongodb.mongodb_install import MongoDBInstallFlow
from backend.flow.plugins.components.collections.mongodb.mongodb_apply_summary import (
    MongoReplicaSetApplySummaryComponent,
    MongoShardApplySummaryComponent,
)


def _init_flow(payload):
    with patch(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_install.calculate_cluster",
        return_value=payload,
    ), patch("backend.flow.engine.bamboo.scene.mongodb.mongodb_install.ActKwargs") as mock_act_kwargs_cls:
        mock_kwargs = MagicMock()
        mock_kwargs.payload = payload
        mock_kwargs.get_add_relationship_to_meta_kwargs.return_value = {}
        mock_kwargs.get_add_shard_to_cluster_kwargs.return_value = {}
        mock_kwargs.get_default_user_kwargs.return_value = {}
        mock_kwargs.get_save_default_pwd_kwargs.return_value = {}
        mock_kwargs.get_mongodb_cluster_init_kwargs.return_value = {}
        mock_kwargs.get_add_domain_to_dns_kwargs.return_value = {}
        mock_act_kwargs_cls.return_value = mock_kwargs
        flow = MongoDBInstallFlow(root_id="root-1", data=payload)
        flow.prepare_job = MagicMock()
        flow.install_dbmon = MagicMock()
        return flow, mock_kwargs


def test_multi_replicaset_install_appends_summary_after_dbmon():
    payload = {
        "bk_biz_id": 3,
        "city": "sz",
        "sets": [
            {"set_id": "app-rs1", "port": 27001, "nodes": [{"domain": "m1.rs1.app.db"}]},
            {"set_id": "app-rs2", "port": 27002, "nodes": [{"domain": "m1.rs2.app.db"}]},
        ],
    }
    fake_builder = MagicMock()
    flow, _ = _init_flow(payload)

    with patch("backend.flow.engine.bamboo.scene.mongodb.mongodb_install.Builder", return_value=fake_builder,), patch(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_install.replicaset_install",
        return_value=MagicMock(),
    ):
        flow.multi_replicaset_install_flow()

    summary_calls = [
        call
        for call in fake_builder.add_act.call_args_list
        if call.kwargs.get("act_component_code") == MongoReplicaSetApplySummaryComponent.code
    ]
    assert len(summary_calls) == 1
    assert summary_calls[0].kwargs["kwargs"]["items"] == [
        {"bk_biz_id": 3, "domain_name": "m1.rs1.app.db", "region": "sz", "port": 27001},
        {"bk_biz_id": 3, "domain_name": "m1.rs2.app.db", "region": "sz", "port": 27002},
    ]
    flow.install_dbmon.assert_called_once()
    fake_builder.run_pipeline.assert_called_once()


def test_cluster_install_appends_summary_after_dbmon():
    payload = {
        "bk_biz_id": 3,
        "city": "sz",
        "shards": [{"set_id": "s1"}],
        "config": {"set_id": "conf"},
        "mongos": {"domain": "mongos.cluster.app.db", "port": 27021},
    }
    fake_builder = MagicMock()
    flow, _ = _init_flow(payload)

    with patch("backend.flow.engine.bamboo.scene.mongodb.mongodb_install.Builder", return_value=fake_builder,), patch(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_install.replicaset_install",
        return_value=MagicMock(),
    ), patch(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_install.mongos_install",
        return_value=MagicMock(),
    ):
        flow.cluster_install_flow()

    summary_calls = [
        call
        for call in fake_builder.add_act.call_args_list
        if call.kwargs.get("act_component_code") == MongoShardApplySummaryComponent.code
    ]
    assert len(summary_calls) == 1
    assert summary_calls[0].kwargs["kwargs"]["items"] == [
        {
            "bk_biz_id": 3,
            "domain_name": "mongos.cluster.app.db",
            "region": "sz",
            "port": 27021,
        }
    ]
    flow.install_dbmon.assert_called_once()
    fake_builder.run_pipeline.assert_called_once()
