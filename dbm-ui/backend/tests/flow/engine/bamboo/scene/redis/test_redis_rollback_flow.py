# -*- coding: utf-8 -*-
from unittest.mock import MagicMock

from backend.db_meta.enums import ClusterType


def test_gate_e_disk_thresholds():
    from backend.flow.plugins.components.collections.redis.redis_rollback import RedisRollbackDiskPrecheckService

    svc = RedisRollbackDiskPrecheckService.__new__(RedisRollbackDiskPrecheckService)
    svc.log_info = lambda *a, **k: None
    svc.log_error = lambda *a, **k: None
    enough = {"mount_on": "/data", "used_ratio": 10, "avail": 1000, "used": 100, "total": 2000}
    assert svc._check("2.2.2.2", "备份", enough, 200) is True
    assert svc._check("2.2.2.2", "备份", {**enough, "avail": 100}, 200) is False
    assert svc._check("2.2.2.2", "备份", {**enough, "used_ratio": 86}, 10) is False
    assert svc._check("2.2.2.2", "备份", {**enough, "used": 1800, "total": 2000, "avail": 200}, 100) is False


def test_disk_needs_split_or_shared_filesystem():
    from backend.flow.plugins.components.collections.redis.redis_rollback import disk_needs

    backup = {"mount_on": "/data"}
    data = {"mount_on": "/data1"}
    split = disk_needs(backup, data, download_bytes=100, unpacked_bytes=300)
    assert [(disk["mount_on"], need) for _, disk, need in split] == [("/data", 400), ("/data1", 300)]

    shared = disk_needs(backup, {"mount_on": "/data"}, download_bytes=100, unpacked_bytes=300)
    assert [(disk["mount_on"], need) for _, disk, need in shared] == [("/data", 400)]


def test_download_uses_each_hosts_own_backup_dir():
    from types import SimpleNamespace
    from unittest.mock import patch

    from backend.flow.plugins.components.collections.redis import redis_rollback as rollback_components
    from backend.flow.utils.redis.redis_context_dataclass import RedisRollbackContext

    trans_data = RedisRollbackContext(
        disk_used={"2.2.2.2": {"backup_dir": "/data"}, "3.3.3.3": {"backup_dir": "/data1/"}},
        backup_dir="/wrong",
    )
    svc = rollback_components.RedisRollbackDownloadService.__new__(rollback_components.RedisRollbackDownloadService)
    svc.log_info = svc.log_error = svc.log_debug = lambda *a, **k: None

    dest_dirs = {}
    with patch.object(rollback_components.RedisBackupApi, "download", return_value={"bill_id": 1}) as download:
        for ip in ("2.2.2.2", "3.3.3.3", "4.4.4.4"):
            kwargs = {
                "bk_cloud_id": 0,
                "task_ids": ["t1"],
                "dest_ip": ip,
                "login_user": "mysql",
                "login_passwd": "x",
                "set_trans_data_dataclass": RedisRollbackContext.__name__,
            }
            inputs = {"kwargs": kwargs, "trans_data": trans_data}
            data = SimpleNamespace(get_one_of_inputs=inputs.get, outputs=SimpleNamespace())
            ok = svc._execute(data, None)
            dest_dirs[ip] = (ok, download.call_args.kwargs["params"]["dest_dir"] if ok else None)

    assert dest_dirs["2.2.2.2"] == (True, "/data/dbbak/recover_redis")
    assert dest_dirs["3.3.3.3"] == (True, "/data1/dbbak/recover_redis")
    assert dest_dirs["4.4.4.4"] == (False, None)


def test_proxy_routing_covers_every_plan_item():
    """Temporary proxy must configure backends for all plan items (including placeholders)."""
    import inspect

    from backend.flow.engine.bamboo.scene.redis.redis_rollback import flow as rollback_flow

    source = inspect.getsource(rollback_flow.RedisRollbackFlow._deploy_proxy)
    assert "for item in plan.items" in source
    assert "is_placeholder" not in source


def test_flow_installs_inside_recover_act_and_uses_dedicated_cc_module():
    """Installation and restore complete within the recover act, followed by meta and CC transfer."""
    import inspect

    from backend.flow.engine.bamboo.scene.redis.redis_rollback import flow as rollback_flow

    source = inspect.getsource(rollback_flow.RedisRollbackFlow.build_cluster_rollback)
    assert "RedisBatchInstallAtomJob" not in source
    assert "redis_rollback_host_transfer" not in source
    # Rollback restore reuses generic actuator component instead of a redundant subclass.
    assert "RedisRollbackActuatorComponent" not in source

    recover_at = source.index("RedisActPayload.redis_rollback_payload.__name__")
    meta_at = source.index("RedisDBMeta.redis_install.__name__")
    cc_at = source.index("RedisDBMeta.redis_rollback_cc_transfer.__name__")
    assert recover_at < meta_at < cc_at


def test_actuator_component_runs_with_rollback_context():
    """The shared actuator component must not assume every context has tendis_backup_info."""
    import json
    from types import SimpleNamespace
    from unittest.mock import patch

    from backend.flow.plugins.components.collections.redis import exec_actuator_script
    from backend.flow.utils.redis.redis_context_dataclass import RedisRollbackContext
    from backend.utils.string import base64_decode

    payload_builder = MagicMock()
    payload_builder.redis_rollback_payload.return_value = {
        "db_type": "dbactuator_redis",
        "action": "redis_rollback",
        "payload": {"dest_ip": "2.2.2.2"},
    }
    trans_data = RedisRollbackContext(redis_act_payload=payload_builder)
    inputs = {
        "kwargs": {
            "root_id": "r1",
            "node_id": "n1",
            "node_name": "recover",
            "set_trans_data_dataclass": RedisRollbackContext.__name__,
            "get_trans_data_ip_var": None,
            "exec_ip": "2.2.2.2",
            "bk_cloud_id": 0,
            "get_redis_payload_func": "redis_rollback_payload",
            "cluster": {},
            "is_update_trans_data": False,
        },
        "global_data": {"uid": 1},
        "trans_data": trans_data,
    }
    data = SimpleNamespace(get_one_of_inputs=inputs.get, outputs=SimpleNamespace())

    svc = exec_actuator_script.ExecuteDBActuatorScriptService.__new__(
        exec_actuator_script.ExecuteDBActuatorScriptService
    )
    svc._runtime_attrs = {"version": "v1"}
    svc.log_info = svc.log_error = lambda *a, **k: None

    with patch.object(exec_actuator_script, "FlowNode"), patch.object(
        exec_actuator_script.JobApi, "fast_execute_script", return_value={"job_instance_id": 1}
    ) as fast_execute:
        assert svc._execute(data, None) is True

    script = base64_decode(fast_execute.call_args.args[0]["script_content"])
    payload = json.loads(base64_decode(script.split("--payload ")[1].split()[0]))
    assert payload == {"dest_ip": "2.2.2.2"}


def test_rollback_payload_embeds_install_params():
    from backend.flow.utils.redis.redis_act_playload import RedisActPayload

    payload_builder = RedisActPayload.__new__(RedisActPayload)
    payload_builder.bk_biz_id = "3"
    install_payload = {"payload": {"ip": "2.2.2.2", "ports": [30000]}}
    payload_builder.get_redis_install_4_scene = MagicMock(return_value=install_payload)

    payload = RedisActPayload.redis_rollback_payload(
        payload_builder,
        ip="2.2.2.2",
        params={
            "dest_ip": "2.2.2.2",
            "immute_domain": "cache.example.db",
            "cluster_type": ClusterType.TendisTwemproxyRedisInstance.value,
            "db_version": "Redis-6",
            "instances": [{"source_ip": "1.1.1.1", "source_port": 30000, "dest_port": 30000, "full_files": ["a"]}],
        },
    )
    assert payload["payload"]["install"]["ports"] == [30000]
    install_params = payload_builder.get_redis_install_4_scene.call_args.kwargs["params"]
    assert install_params["ports"] == [30000]
    assert install_params["exec_ip"] == "2.2.2.2"


def test_rollback_payload_installs_empty_instances_too():
    """Placeholder instances without backup files must still be installed to occupy ports."""
    from backend.flow.utils.redis.redis_act_playload import RedisActPayload

    payload_builder = RedisActPayload.__new__(RedisActPayload)
    payload_builder.bk_biz_id = "3"
    payload_builder.get_redis_install_4_scene = MagicMock(return_value={"payload": {}})

    payload = RedisActPayload.redis_rollback_payload(
        payload_builder,
        ip="2.2.2.2",
        params={
            "dest_ip": "2.2.2.2",
            "immute_domain": "cache.example.db",
            "cluster_type": ClusterType.TendisTwemproxyRedisInstance.value,
            "db_version": "Redis-6",
            "instances": [
                {"source_ip": "1.1.1.1", "source_port": 30000, "dest_port": 30000, "full_files": ["a"]},
                {"source_ip": "1.1.1.2", "source_port": 30001, "dest_port": 30001, "full_files": []},
            ],
        },
    )

    install_params = payload_builder.get_redis_install_4_scene.call_args.kwargs["params"]
    assert install_params["ports"] == [30000, 30001]
    assert [inst["dest_port"] for inst in payload["payload"]["instances"]] == [30000, 30001]
