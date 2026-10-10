# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.exceptions import ValidationError

import backend.ticket.builders.redis.redis_toolbox_datastruct_task_delete as builder_module
from backend.db_meta.enums import DestroyedStatus
from backend.flow.engine.bamboo.scene.redis.redis_data_structure_task_delete import RedisDataStructureTaskDeleteFlow
from backend.ticket.builders.redis.redis_toolbox_datastruct_task_delete import (
    RedisDataStructureTaskDeleteDetailSerializer,
)
from backend.ticket.constants import TicketType

BUILDER = "backend.ticket.builders.redis.redis_toolbox_datastruct_task_delete"
FLOW = "backend.flow.engine.bamboo.scene.redis.redis_data_structure_task_delete"


def _task(task_id=7, version="rollback", destroyed=DestroyedStatus.NOT_DESTROYED):
    task = MagicMock()
    task.id = task_id
    task.prod_cluster = "cache.example.db"
    task.prod_cluster_id = 8
    task.bk_cloud_id = 0
    task.related_rollback_bill_id = 100
    task.destroyed_status = destroyed
    task.rollback_version = version
    return task


BK_BIZ_ID = 3


def _validate(attr):
    serializer = RedisDataStructureTaskDeleteDetailSerializer.InfoSerializer(context={"bk_biz_id": BK_BIZ_ID})
    return serializer.validate(attr)


def test_task_id_alone_fills_the_rest_from_the_record():
    with patch(f"{BUILDER}.TbTendisRollbackTasks") as model:
        model.DoesNotExist = Exception
        model.objects.get.return_value = _task()
        attr = _validate({"task_id": 7})

    model.objects.get.assert_called_once_with(id=7, bk_biz_id=BK_BIZ_ID)
    assert attr == {
        "task_id": 7,
        "prod_cluster": "cache.example.db",
        "cluster_id": 8,
        "bk_cloud_id": 0,
        "related_rollback_bill_id": 100,
    }


def test_task_id_must_point_to_an_undestroyed_record():
    with patch(f"{BUILDER}.TbTendisRollbackTasks") as model:
        model.DoesNotExist = Exception
        model.objects.get.return_value = _task(destroyed=DestroyedStatus.DESTROYED)
        with pytest.raises(ValidationError):
            _validate({"task_id": 7})


def test_task_id_of_another_biz_is_rejected_as_missing():
    class DoesNotExist(Exception):
        pass

    with patch(f"{BUILDER}.TbTendisRollbackTasks") as model:
        model.DoesNotExist = DoesNotExist
        model.objects.get.side_effect = DoesNotExist
        with pytest.raises(ValidationError) as exc:
            _validate({"task_id": 7})

    model.objects.get.assert_called_once_with(id=7, bk_biz_id=BK_BIZ_ID)
    assert "不存在" in str(exc.value)


def _legacy_attr():
    return {"related_rollback_bill_id": "100", "cluster_id": 8, "bk_cloud_id": 0}


def _patch_legacy(records):
    cluster = MagicMock(immute_domain="cache.example.db")
    cluster_patch = patch(f"{BUILDER}.Cluster")
    task_patch = patch(f"{BUILDER}.TbTendisRollbackTasks")
    cluster_model = cluster_patch.start()
    task_model = task_patch.start()
    cluster_model.objects.get.return_value = cluster
    task_model.objects.filter.return_value.__getitem__.return_value = records
    return [cluster_patch, task_patch]


def test_legacy_params_resolving_to_one_record_get_a_task_id():
    patches = _patch_legacy([_task(task_id=5, version="datastructure")])
    try:
        attr = _validate(_legacy_attr())
    finally:
        for p in patches:
            p.stop()
    assert attr["task_id"] == 5
    assert attr["prod_cluster"] == "cache.example.db"


def test_legacy_params_only_match_records_of_the_ticket_biz():
    patches = _patch_legacy([])
    task_model = builder_module.TbTendisRollbackTasks
    try:
        with pytest.raises(ValidationError) as exc:
            _validate(_legacy_attr())
    finally:
        for p in patches:
            p.stop()
    assert task_model.objects.filter.call_args.kwargs["bk_biz_id"] == BK_BIZ_ID
    assert "没有找到未销毁的实例" in str(exc.value)


def test_legacy_params_matching_several_records_are_rejected():
    patches = _patch_legacy([_task(task_id=5), _task(task_id=6)])
    try:
        with pytest.raises(ValidationError) as exc:
            _validate(_legacy_attr())
    finally:
        for p in patches:
            p.stop()
    assert "task_id" in str(exc.value)


def test_legacy_params_must_be_complete_without_task_id():
    with pytest.raises(ValidationError) as exc:
        _validate({"related_rollback_bill_id": "100"})
    assert "cluster_id" in str(exc.value)


def _flow():
    return RedisDataStructureTaskDeleteFlow(
        root_id="root-1",
        data={
            "uid": "uid-1",
            "bk_biz_id": 3,
            "ticket_type": TicketType.REDIS_DATA_STRUCTURE_TASK_DELETE.value,
            "infos": [
                {"task_id": 1, "related_rollback_bill_id": 100, "prod_cluster": "a.db", "rollback_version": "x"},
                {
                    "task_id": 2,
                    "related_rollback_bill_id": 100,
                    "prod_cluster": "b.db",
                    "rollback_version": "rollback",
                },
                {"related_rollback_bill_id": 200, "prod_cluster": "c.db"},
            ],
        },
    )


@patch(f"{FLOW}.Builder")
@patch(f"{FLOW}.RedisRollbackDestroyFlow")
@patch.object(RedisDataStructureTaskDeleteFlow, "build_cluster_task_delete")
@patch(f"{FLOW}.TbTendisRollbackTasks")
def test_flow_dispatches_by_the_stored_version(task_model, v1_build, v2_flow, builder):
    versions = {1: "rollback", 2: "datastructure"}
    task_model.objects.filter.side_effect = lambda id: MagicMock(
        values_list=MagicMock(return_value=MagicMock(first=MagicMock(return_value=versions[id])))
    )
    v1_build.side_effect = lambda info: "v1-" + info["prod_cluster"]
    v2_flow.return_value.build_cluster_destroy.side_effect = lambda info: "v2-" + info["prod_cluster"]

    _flow().redis_rollback_task_delete_flow()

    subs = builder.return_value.add_parallel_sub_pipeline.call_args.kwargs["sub_flow_list"]
    assert subs == ["v2-a.db", "v1-b.db", "v1-c.db"]
    queried = [call.kwargs["id"] for call in task_model.objects.filter.call_args_list]
    assert queried == [1, 2], "infos without task_id must not be looked up"
