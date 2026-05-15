# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.redis.redis_data_structure import RedisDataStructureFlow
from backend.flow.engine.bamboo.scene.redis.redis_data_structure_task_delete import RedisDataStructureTaskDeleteFlow
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs


def test_parse_shard_value_ranges_accepts_multiple_slot_ranges():
    shard_value = "1365-1637 10651-10923\n13382-13654 15020-15292 16111-16383"

    assert RedisDataStructureFlow.parse_shard_value_ranges(shard_value) == [
        (1365, 1637),
        (10651, 10923),
        (13382, 13654),
        (15020, 15292),
        (16111, 16383),
    ]


def test_parse_shard_value_ranges_accepts_mixed_ranges_and_single_slots():
    assert RedisDataStructureFlow.parse_shard_value_ranges("1-2 4 5-6") == [(1, 2), (4, 4), (5, 6)]


def test_parse_shard_value_ranges_ignores_migrating_and_importing_markers():
    shard_value = "[3->-node-b] 1-2 [4-<-node-a] 5-6"

    assert RedisDataStructureFlow.parse_shard_value_ranges(shard_value) == [(1, 2), (5, 6)]


def test_parse_shard_value_ranges_handles_production_tendisplus_sample():
    """Exact slot string observed in dbmon redis_fullbackup report payloads."""
    shard_value = "4097-4369 5189-5461 6828-7100 9559-9831 12290-12562"

    assert RedisDataStructureFlow.parse_shard_value_ranges(shard_value) == [
        (4097, 4369),
        (5189, 5461),
        (6828, 7100),
        (9559, 9831),
        (12290, 12562),
    ]


@patch("backend.flow.engine.bamboo.scene.redis.redis_data_structure.DataStructureHandler")
def test_get_backup_instance_by_bklog_accepts_non_contiguous_slots(mock_handler_cls):
    multi_range = "1365-1637 10651-10923\n13382-13654 15020-15292 16111-16382 16383"
    complement_range = "0-1364 1638-10650 10924-13381 13655-15019 15293-16110"
    mock_handler = MagicMock()
    mock_handler.query_donmain_backup_log.return_value = [
        {"source_ip": "3.3.3.3", "server_port": 30001, "shard_value": multi_range},
        {"source_ip": "3.3.3.3", "server_port": 30002, "shard_value": complement_range},
    ]
    mock_handler_cls.return_value = mock_handler

    instances, redis_instance_set = RedisDataStructureFlow.get_backup_instance_by_bklog(
        {"cluster_id": 1, "recovery_time_point": "2026-04-28T21:00:00+08:00"},
        ClusterType.TendisPredixyRedisCluster,
        is_drill=False,
    )

    assert instances == ["3.3.3.3:30001", "3.3.3.3:30002"]
    assert redis_instance_set == [
        f"3.3.3.3:30001 {multi_range}",
        f"3.3.3.3:30002 {complement_range}",
    ]


@patch("backend.flow.engine.bamboo.scene.redis.redis_data_structure.GetFileList")
@patch("backend.flow.engine.bamboo.scene.redis.redis_data_structure.SubBuilder")
def test_init_builder_uses_isolated_cluster_global_data(mock_sub_builder, mock_get_file_list):
    mock_sub_builder.return_value = MagicMock()
    mock_get_file_list.return_value = MagicMock(redis_base=MagicMock(return_value=[]))

    source_ticket_data = {
        "uid": "uid-1",
        "bk_biz_id": 3,
        "ticket_type": "REDIS_DATA_STRUCTURE",
        "infos": [{"cluster_id": 1}, {"cluster_id": 2}],
    }
    cluster_infos = [
        {
            "cluster_type": ClusterType.TendisPredixyTendisplusCluster.value,
            "bk_biz_id": 100,
            "bk_cloud_id": 0,
            "immute_domain": "plus.test.dba.db",
            "domain_name": "plus.test.dba.db",
        },
        {
            "cluster_type": ClusterType.TendisRedisInstance.value,
            "bk_biz_id": 200,
            "bk_cloud_id": 0,
            "immute_domain": "cache.test.dba.db",
            "domain_name": "cache.test.dba.db",
        },
    ]

    flow = RedisDataStructureFlow(root_id="root-1", data=source_ticket_data)
    with patch.object(RedisDataStructureFlow, "_RedisDataStructureFlow__get_cluster_info", side_effect=cluster_infos):
        _, first_kwargs, first_global_data = flow._RedisDataStructureFlow__init_builder(
            "REDIS_DATA_STRUCTURE", {"cluster_id": 1}
        )
        _, second_kwargs, second_global_data = flow._RedisDataStructureFlow__init_builder(
            "REDIS_DATA_STRUCTURE", {"cluster_id": 2}
        )

    assert "cluster_type" not in source_ticket_data
    assert first_global_data is not second_global_data
    assert first_global_data["bk_biz_id"] == 3
    assert second_global_data["bk_biz_id"] == 3
    assert first_global_data["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value
    assert second_global_data["cluster_type"] == ClusterType.TendisRedisInstance.value
    assert first_kwargs.cluster["cluster_type"] == ClusterType.TendisPredixyTendisplusCluster.value
    assert second_kwargs.cluster["cluster_type"] == ClusterType.TendisRedisInstance.value


@pytest.mark.parametrize("is_drill", [True, False])
@patch("backend.flow.engine.bamboo.scene.redis.redis_data_structure.GetFileList")
@patch("backend.flow.engine.bamboo.scene.redis.redis_data_structure.redis_backupfile_download")
@patch("backend.flow.engine.bamboo.scene.redis.redis_data_structure.RedisBatchInstallAtomJob")
def test_build_cluster_data_structure_installs_dbmon_only_when_not_drill(
    mock_install_atom, mock_backup_download, mock_get_file_list, is_drill
):
    """Regression: data-structure flow installs dbmon iff this is not a drill.

    Drill runs spin up a short-lived temp host that should stay off the dbmon
    monitoring path; production data-structure runs keep the temp host monitored
    for the lifetime of the constructed cluster, and the cleanup flow uninstalls
    dbmon symmetrically.
    """
    mock_install_atom.return_value = MagicMock()
    mock_backup_download.return_value = MagicMock()
    mock_get_file_list.return_value = MagicMock(
        redis_actuator_backend=MagicMock(return_value=[]),
        redis_cluster_apply_proxy=MagicMock(return_value=[]),
        tendisplus_apply_proxy=MagicMock(return_value=[]),
    )

    pipeline = MagicMock()
    pipeline.build_sub_process.return_value = MagicMock()

    cluster_info = {
        "cluster_type": ClusterType.TendisTwemproxyRedisInstance.value,
        "bk_biz_id": 3,
        "bk_cloud_id": 0,
        "domain_name": "cache.test.dba.db",
        "db_version": "Redis-6",
        "proxy_port": 50000,
        "redis_master_set": ["1.1.1.1:30000 0-419999"],
        "redis_slave_set": ["1.1.1.2:30000 0-419999"],
        "master_ins_slave_ins_map": {"1.1.1.1:30000": "1.1.1.2:30000"},
    }
    act_kwargs = ActKwargs()
    act_kwargs.cluster = dict(cluster_info)
    act_kwargs.bk_cloud_id = 0
    cluster_global_data = {
        "uid": "uid-1",
        "bk_biz_id": 3,
        "ticket_type": "REDIS_DATA_STRUCTURE",
        "cluster_type": ClusterType.TendisTwemproxyRedisInstance.value,
        "is_rollback_drill": is_drill,
        "skip_mannual_confirm": True,
    }

    flow = RedisDataStructureFlow(
        root_id="root-1",
        data={
            "uid": "uid-1",
            "bk_biz_id": 3,
            "ticket_type": "REDIS_DATA_STRUCTURE",
            "is_rollback_drill": is_drill,
            "skip_mannual_confirm": True,
        },
    )

    info = {
        "cluster_id": 1,
        "bk_cloud_id": 0,
        "master_instances": ["1.1.1.1:30000"],
        "recovery_time_point": "2026-04-28 12:00:00",
        "redis": [{"ip": "1.1.1.3", "bk_cloud_id": 0, "bk_host_id": 1}],
        "resource_spec": {"redis": {"id": 1}},
    }

    with patch.object(
        RedisDataStructureFlow,
        "_RedisDataStructureFlow__init_builder",
        return_value=(pipeline, act_kwargs, cluster_global_data),
    ), patch.object(
        RedisDataStructureFlow,
        "_RedisDataStructureFlow__get_cluster_config",
        return_value={"kvstorecount": "3"},
    ), patch.object(
        RedisDataStructureFlow,
        "get_backup_instance_by_bklog",
        return_value=(["1.1.1.2:30000"], ["1.1.1.2:30000 0-419999"]),
    ), patch.object(
        RedisDataStructureFlow,
        "get_prod_temp_instance_pairs",
        return_value=([], []),
    ):
        flow.build_cluster_data_structure(info)

    assert mock_install_atom.called, "RedisBatchInstallAtomJob should be invoked once per redis host"
    expected_install_dbmon = not is_drill
    for call in mock_install_atom.call_args_list:
        assert call.args[1] is cluster_global_data
        assert call.args[1]["cluster_type"] == ClusterType.TendisTwemproxyRedisInstance.value
        assert call.kwargs["to_install_dbmon"] is expected_install_dbmon, (
            f"to_install_dbmon must be {expected_install_dbmon} when is_drill={is_drill}, "
            f"got {call.kwargs.get('to_install_dbmon')!r}"
        )
    component_codes = [call.kwargs.get("act_component_code") for call in pipeline.add_act.call_args_list]
    assert (AddAlarmShieldComponent.code in component_codes) is (not is_drill)
    assert (DisableAlarmShieldComponent.code in component_codes) is (not is_drill)


@pytest.mark.parametrize("is_drill", [True, False])
@patch("backend.flow.engine.bamboo.scene.redis.redis_data_structure_task_delete.GetFileList")
@patch("backend.flow.engine.bamboo.scene.redis.redis_data_structure_task_delete.SubBuilder")
@patch("backend.flow.engine.bamboo.scene.redis.redis_data_structure_task_delete.RedisBatchShutdownAtomJob")
def test_build_cluster_task_delete_skips_dbmon_uninstall_only_in_drill(
    mock_shutdown_atom, mock_sub_builder, mock_get_file_list, is_drill
):
    """Regression: cleanup flow skips dbmon uninstall iff this is a drill.

    Mirrors ``test_build_cluster_data_structure_installs_dbmon_only_when_not_drill``:
    drill runs never installed dbmon, so the teardown skips uninstall; production
    runs installed dbmon and must uninstall it on cleanup.
    """
    mock_shutdown_atom.return_value = MagicMock()
    mock_sub_builder.return_value = MagicMock()
    mock_get_file_list.return_value = MagicMock(
        redis_base=MagicMock(return_value=[]),
        redis_dbmon=MagicMock(return_value=[]),
    )

    flow = RedisDataStructureTaskDeleteFlow(
        root_id="root-1",
        data={
            "uid": "uid-1",
            "bk_biz_id": 3,
            "ticket_type": "REDIS_DATA_STRUCTURE_TASK_DELETE",
            "is_rollback_drill": is_drill,
            "skip_connections_check": False,
        },
    )

    info = {
        "related_rollback_bill_id": 1,
        "prod_cluster": "cache.test.dba.db",
        "bk_cloud_id": 0,
    }
    tasks_info = {
        "temp_cluster_type": ClusterType.TendisTwemproxyRedisInstance.value,
        "temp_instance_range": ["1.1.1.3:30000"],
        "temp_cluster_proxy": "1.1.1.3:50000",
    }

    flow.build_cluster_task_delete(info, tasks_info=tasks_info)

    assert mock_shutdown_atom.called, "RedisBatchShutdownAtomJob should be invoked once per host"
    for call in mock_shutdown_atom.call_args_list:
        params = call.args[3] if len(call.args) >= 4 else call.kwargs.get("param")
        assert params is not None, "Shutdown atom job should receive a params dict"
        assert params.get("skip_dbmon_uninstall") is is_drill, (
            f"skip_dbmon_uninstall must be {is_drill} when is_drill={is_drill}, "
            f"got {params.get('skip_dbmon_uninstall')!r}"
        )
