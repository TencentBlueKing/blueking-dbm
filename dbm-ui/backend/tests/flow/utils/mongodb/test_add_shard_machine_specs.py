# -*- coding: utf-8 -*-
"""增加分片写入 meta 时补齐机器规格。"""

from unittest.mock import patch

from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs


def test_add_shard_machine_specs_from_patched_resource_spec():
    """资源申请回填后规格在 id 上，meta 要 spec_id / spec_config。"""
    spec = {
        "id": 195,
        "name": "2c4g",
        "cpu": {"max": 4, "min": 2},
        "mem": {"max": 8, "min": 2},
        "qps": {"max": 0, "min": 0},
        "device_class": [],
        "storage_spec": [{"max": 200, "min": 50, "type": "ALL", "mount_point": "/data"}],
        "count": 3,
    }
    machine_specs = ActKwargs.add_shard_machine_specs({"mongodb": spec})
    assert machine_specs["mongodb"]["spec_id"] == 195
    assert machine_specs["mongodb"]["spec_config"]["name"] == "2c4g"
    assert machine_specs["mongodb"]["spec_config"]["storage_spec"] == spec["storage_spec"]


def test_add_shard_machine_specs_from_split_role():
    spec = {"id": 7, "name": "4c8g", "count": 3}
    machine_specs = ActKwargs.add_shard_machine_specs({"mongodb_0": spec, "mongodb_1": spec})
    assert machine_specs == {"mongodb": {"spec_id": 7, "spec_config": spec}}


def test_add_shard_machine_specs_warns_for_unexpected_role():
    with patch("backend.flow.utils.mongodb.mongodb_dataclass.logger.warning") as warning:
        machine_specs = ActKwargs.add_shard_machine_specs({"shard_nodes": {"id": 7}})
    assert machine_specs == {}
    warning.assert_called_once_with("add shard: unexpected resource_spec keys=%s", ["shard_nodes"])


def test_add_shard_machine_specs_keeps_explicit_shape():
    spec_config = {"id": 3, "name": "kept"}
    resource_spec = {"mongodb": {"spec_id": 3, "spec_config": spec_config}}
    assert ActKwargs.add_shard_machine_specs(resource_spec) == {"mongodb": {"spec_id": 3, "spec_config": spec_config}}


def test_add_shard_to_meta_kwargs_writes_machine_specs():
    """按资源回填和 post_callback 后的真实 inner flow 结构验证。"""
    kwargs = ActKwargs()
    kwargs.payload = {
        "bk_biz_id": 3,
        "created_by": "admin",
        "hosts": [{"ip": "127.0.0.1", "bk_cloud_id": 0}],
    }
    info = {
        "cluster_id": 9,
        "node_count": 1,
        "shards": [{"set_id": "dba-s2", "port": 27021, "nodes": [{"ip": "127.0.0.2", "bk_cloud_id": 0}]}],
        "resource_spec": {"mongodb": {"id": 195, "name": "2c4g", "count": 3}},
        "mongo_add_shards": [[{"ip": "127.0.0.2", "spec": {"id": 195, "name": "2c4g"}}]],
    }
    result = kwargs.get_add_shard_to_meta_kwargs(info)
    assert result["machine_specs"]["mongodb"]["spec_id"] == 195
    assert result["machine_specs"]["mongodb"]["spec_config"]["name"] == "2c4g"
