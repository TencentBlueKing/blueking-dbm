# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest

from backend.flow.utils.redis.redis_rollback_exercise_resource import (
    all_infos_have_redis,
    build_apply_detail_from_machine,
)


@pytest.mark.django_db
def test_build_apply_detail_from_machine_uses_disk_mem_not_spec_id():
    cluster = MagicMock()
    cluster.bk_cloud_id = 0
    cluster.region = "sz"

    machine = MagicMock()
    machine.spec_config = {"cpu": {"min": 4, "max": 8}, "mem": {"min": 16, "max": 32}}
    machine.storage_device = {"/data": {"size": 200, "disk_type": "SSD"}}
    machine.spec_id = 999

    detail = build_apply_detail_from_machine(0, cluster, machine)

    assert detail["group_mark"] == "0_redis"
    assert detail["bk_cloud_id"] == 0
    assert detail["spec"]["cpu"] == {"min": 0, "max": 0}
    assert detail["spec"]["ram"]["min"] == 16 * 1024
    assert detail["storage_spec"][0]["min"] == 200
    assert "spec_id" not in detail
    assert detail["location_spec"] == {"city": "sz", "sub_zone_ids": []}


@pytest.mark.django_db
def test_build_apply_detail_from_machine_random_region_no_city_filter():
    cluster = MagicMock()
    cluster.bk_cloud_id = 0
    cluster.region = "default"

    machine = MagicMock()
    machine.spec_config = {"cpu": {"min": 2}, "mem": {"min": 3}}
    machine.storage_device = {"/data": {"size": 50}}
    machine.spec_id = 0

    detail = build_apply_detail_from_machine(0, cluster, machine)

    assert detail["location_spec"] == {"city": "", "sub_zone_ids": []}


def test_all_infos_have_redis():
    assert all_infos_have_redis([{"redis": [{"ip": "1.1.1.1"}]}]) is True
    assert all_infos_have_redis([{"redis": []}]) is False
    assert all_infos_have_redis([]) is False


@patch("backend.flow.utils.redis.redis_rollback_exercise_resource.DBResourceApi.resource_apply")
@patch("backend.flow.utils.redis.redis_rollback_exercise_resource.MachineEvent.host_event_trigger")
@patch("backend.flow.utils.redis.redis_rollback_exercise_resource.get_instance_machine")
@patch("backend.flow.utils.redis.redis_rollback_exercise_resource.Cluster.objects.get")
def test_apply_exercise_resources_marks_failure_on_api_error(
    mock_cluster_get, mock_get_machine, mock_event, mock_apply
):
    from backend.flow.utils.redis.redis_rollback_exercise_resource import apply_exercise_resources

    cluster = MagicMock()
    cluster.id = 1
    cluster.bk_cloud_id = 0
    cluster.region = "sz"
    mock_cluster_get.return_value = cluster
    mock_get_machine.return_value = MagicMock(
        spec_config={"cpu": {"min": 1}, "mem": {"min": 1}},
        storage_device={"/data": {"size": 100}},
        spec_id=0,
    )
    mock_apply.return_value = {"code": 1, "message": "lake"}

    ticket_data = {
        "bk_biz_id": 100,
        "uid": 1,
        "ticket_type": "REDIS_ROLLBACK_EXERCISE",
        "created_by": "system",
        "infos": [
            {
                "cluster_id": 1,
                "instance_ip": "1.1.1.1",
                "instance_port": 30000,
                "report_id": 10,
            }
        ],
    }

    result = apply_exercise_resources(ticket_data, "root-id")

    assert result.success is False
    mock_event.assert_not_called()
    assert mock_apply.call_args.kwargs["params"]["resource_type"] == "redis"
