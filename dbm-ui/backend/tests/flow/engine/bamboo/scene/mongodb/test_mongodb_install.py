# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest
from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.mongodb.mongodb_install import MongoDBInstallFlow, mongodb_needs_sessions_balance
from backend.flow.plugins.components.collections.mongodb.mongodb_apply_summary import (
    MongoReplicaSetApplySummaryComponent,
    MongoShardApplySummaryComponent,
)
from backend.flow.utils.mongodb.mongodb_script_template import mongodb_grant_sessions_chunk_role_js_script


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
    flow = _init_flow(payload)[0]

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
        "db_version": "5.0.14",
        "shards": [{"set_id": "s1"}],
        "config": {"set_id": "conf"},
        "mongos": {"domain": "mongos.cluster.app.db", "port": 27021},
    }
    fake_builder = MagicMock()
    flow, mock_kwargs = _init_flow(payload)

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
    mock_kwargs.get_grant_sessions_chunk_role_kwargs.assert_not_called()
    mock_kwargs.get_balance_sessions_kwargs.assert_not_called()


def test_cluster_install_balances_sessions_for_mongodb_6():
    payload = {
        "bk_biz_id": 3,
        "city": "sz",
        "db_version": "6.0.4",
        "shards": [{"set_id": "s1"}],
        "config": {"set_id": "conf"},
        "mongos": {"domain": "mongos.cluster.app.db", "port": 27021},
    }
    fake_builder = MagicMock()
    flow, mock_kwargs = _init_flow(payload)

    with patch("backend.flow.engine.bamboo.scene.mongodb.mongodb_install.Builder", return_value=fake_builder,), patch(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_install.replicaset_install",
        return_value=MagicMock(),
    ), patch(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_install.mongos_install",
        return_value=MagicMock(),
    ):
        flow.cluster_install_flow()

    names = [call.kwargs.get("act_name") for call in fake_builder.add_act.call_args_list]
    init_name = _("MongoDB--cluster初始化设置")
    grant_name = _("MongoDB--授予config.system.sessions均衡权限")
    balance_name = _("MongoDB--均衡config.system.sessions")
    assert names.index(grant_name) == names.index(init_name) + 1
    assert names.index(balance_name) == names.index(grant_name) + 1
    mock_kwargs.get_grant_sessions_chunk_role_kwargs.assert_called_once_with()
    mock_kwargs.get_balance_sessions_kwargs.assert_called_once_with()


def test_cluster_install_skips_sessions_balance_before_mongodb_6():
    payload = {
        "bk_biz_id": 3,
        "city": "sz",
        "db_version": "5.0.14",
        "shards": [{"set_id": "s1"}],
        "config": {"set_id": "conf"},
        "mongos": {"domain": "mongos.cluster.app.db", "port": 27021},
    }
    fake_builder = MagicMock()
    flow, mock_kwargs = _init_flow(payload)

    with patch("backend.flow.engine.bamboo.scene.mongodb.mongodb_install.Builder", return_value=fake_builder,), patch(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_install.replicaset_install",
        return_value=MagicMock(),
    ), patch(
        "backend.flow.engine.bamboo.scene.mongodb.mongodb_install.mongos_install",
        return_value=MagicMock(),
    ):
        flow.cluster_install_flow()

    names = [call.kwargs.get("act_name") for call in fake_builder.add_act.call_args_list]
    assert _("MongoDB--授予config.system.sessions均衡权限") not in names
    assert _("MongoDB--均衡config.system.sessions") not in names
    mock_kwargs.get_grant_sessions_chunk_role_kwargs.assert_not_called()
    mock_kwargs.get_balance_sessions_kwargs.assert_not_called()


def test_sessions_balance_version_gate():
    assert mongodb_needs_sessions_balance("6.0.4")
    assert mongodb_needs_sessions_balance("6.0")
    assert mongodb_needs_sessions_balance("mongodb-7.0.28")
    assert mongodb_needs_sessions_balance("MongoDB-8.0.32")
    assert not mongodb_needs_sessions_balance("5.0.14")
    assert not mongodb_needs_sessions_balance("4.4.29")
    with pytest.raises(ValueError):
        mongodb_needs_sessions_balance("")
    with pytest.raises(ValueError):
        mongodb_needs_sessions_balance("not-a-version")


def test_cluster_install_rejects_invalid_db_version():
    payload = {
        "bk_biz_id": 3,
        "city": "sz",
        "db_version": "not-a-version",
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
    ), pytest.raises(
        ValueError
    ):
        flow.cluster_install_flow()

    fake_builder.run_pipeline.assert_not_called()


def test_grant_sessions_chunk_role_uses_commands_supported_by_legacy_mongo_shell():
    script = mongodb_grant_sessions_chunk_role_js_script("dba")

    assert "admin.createRole(" not in script
    assert "admin.grantRolesToUser(" not in script
    assert "createRole: roleName" in script
    assert "grantRolesToUser: username" in script
    assert script.count("admin.runCommand(") == 2
