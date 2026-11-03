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
import random
from dataclasses import dataclass

import pytest

from backend.db_meta.api.cluster_state import (
    ClusterStateSchema,
    ClusterStateService,
    CommonClusterStateSchema,
    NativeStateField,
    StoredStateField,
    register_state_schema,
    registry,
)
from backend.db_meta.api.cluster_state.checks import check_cluster_state_schemas
from backend.db_meta.api.cluster_state.fields import CapacityField, PhaseField
from backend.db_meta.api.cluster_state.schemas.mysql import MySQLHAStateSchema
from backend.db_meta.enums import ClusterType, DrillDownType, StateFilterOperator, StateValueType
from backend.db_meta.exceptions import ClusterStateException
from backend.db_meta.models import Cluster, ClusterState
from backend.exceptions import ValidationError
from backend.tests.db_meta.api.cluster_state.base import StateFieldTestCase, create_cluster

pytestmark = pytest.mark.django_db


@dataclass
class DemoExtra:
    reason: str
    count: int = 0


class DemoSwitchField(StoredStateField):
    name = "demo switch"
    value_type = StateValueType.BOOL.value
    default_value = False
    filterable = True
    writable = True
    extra_class = DemoExtra


class DemoLevelField(StoredStateField):
    name = "demo level"
    value_type = StateValueType.ENUM.value
    choices = [("low", "低"), ("high", "高")]


class DemoUsageField(StoredStateField):
    name = "demo usage"
    value_type = StateValueType.NUMBER.value
    filterable = True


class DemoNoteField(StoredStateField):
    name = "demo note"
    value_type = StateValueType.STR.value
    filterable = True


class DemoSchema(CommonClusterStateSchema):
    switch = DemoSwitchField()
    level = DemoLevelField()
    usage = DemoUsageField()
    note = DemoNoteField()
    running_ticket = None


@pytest.fixture
def demo_schema(monkeypatch):
    schemas = {**registry.get_registered_schemas(), ClusterType.TenDBHA.value: DemoSchema}
    monkeypatch.setattr(registry, "_schema_registry", schemas)
    monkeypatch.setattr(registry, "_schema_conflicts", [])
    return DemoSchema


@pytest.fixture
def bk_biz_id():
    return random.randint(100000, 200000)


@pytest.fixture
def clusters(demo_schema, bk_biz_id):
    return [create_cluster(ClusterType.TenDBHA.value, bk_biz_id) for _ in range(3)]


class TestSchema:
    def test_inherit_and_remove_fields(self):
        assert set(DemoSchema.get_fields()) == {"phase", "status", "switch", "level", "usage", "note"}
        assert DemoSchema.get_field("switch").key == "switch"
        assert "running_ticket" in CommonClusterStateSchema.get_fields()

    def test_fields_as_class_attributes(self):
        assert DemoSchema.switch is DemoSchema.get_field("switch")
        assert CommonClusterStateSchema.phase.key == "phase"
        # 继承来的字段与父类是同一个实例，移除的字段为 None
        assert DemoSchema.phase is CommonClusterStateSchema.phase
        assert DemoSchema.running_ticket is None

    def test_declared_key(self):
        assert CommonClusterStateSchema.phase.key == PhaseField.key == "phase"
        assert MySQLHAStateSchema.capacity.key == CapacityField.key

        with pytest.raises(TypeError, match="declares key 'capacity'"):

            class WrongKeySchema(ClusterStateSchema):
                cap = CapacityField()

        with pytest.raises(TypeError, match="key"):
            DemoSwitchField(key="other")

    def test_field_name_shadowing_method(self):
        with pytest.raises(TypeError, match="get_fields"):

            class BadSchema(ClusterStateSchema):
                get_fields = DemoSwitchField()


class TestStoredField(StateFieldTestCase):
    cluster_type = ClusterType.TenDBHA.value

    def test_mark_is_sparse(self, clusters):
        cluster = clusters[0]
        ClusterStateService.mark(cluster.id, "switch", True, operator="admin")
        record = ClusterState.objects.get(cluster_id=cluster.id, state_key="switch")
        assert (record.state_value_type, record.state_int_value, record.state_str_value) == ("int", 1, None)
        assert self.get_state(cluster, "switch").value is True

        ClusterStateService.mark(cluster.id, "switch", False, operator="admin")
        assert not ClusterState.objects.filter(cluster_id=cluster.id, state_key="switch").exists()
        assert self.get_state(cluster, "switch").value is False

        ClusterStateService.mark(cluster.id, "switch", True)
        ClusterStateService.unmark(cluster.id, "switch")
        assert not ClusterState.objects.filter(cluster_id=cluster.id).exists()

    def test_mark_audit_fields(self, clusters):
        cluster = clusters[0]
        ClusterStateService.mark(cluster.id, "level", "low", operator="alice")
        ClusterStateService.mark(cluster.id, "level", "high", operator="bob")
        record = ClusterState.objects.get(cluster_id=cluster.id, state_key="level")
        assert (record.creator, record.updater, record.state_str_value) == ("alice", "bob", "high")
        assert ClusterState.objects.filter(cluster_id=cluster.id, state_key="level").count() == 1

    def test_extra_dataclass(self, clusters):
        cluster = clusters[0]
        ClusterStateService.mark(cluster.id, "switch", True, extra={"reason": "maintain"})
        state = self.get_state(cluster, "switch")
        assert state.detail == DemoExtra(reason="maintain", count=0)

        ClusterStateService.mark(cluster.id, "switch", True, extra=DemoExtra(reason="drill", count=2))
        assert self.get_state(cluster, "switch").detail == DemoExtra(reason="drill", count=2)

        ClusterState.objects.filter(cluster_id=cluster.id).update(extra={"reason": "old", "removed_key": 1})
        assert self.get_state(cluster, "switch").detail == DemoExtra(reason="old")

    def test_invalid_extra(self, clusters):
        cluster = clusters[0]
        with pytest.raises(ClusterStateException):
            ClusterStateService.mark(cluster.id, "switch", True, extra={"count": 1})
        with pytest.raises(ClusterStateException):
            ClusterStateService.mark(cluster.id, "level", "low", extra={"reason": "x"})
        assert not ClusterState.objects.filter(cluster_id=cluster.id).exists()

    def test_invalid_mark(self, clusters):
        cluster = clusters[0]
        with pytest.raises(ClusterStateException):
            ClusterStateService.mark(cluster.id, "level", "unknown")
        with pytest.raises(ClusterStateException):
            ClusterStateService.mark(cluster.id, "not_declared", 1)
        with pytest.raises(ClusterStateException):
            ClusterStateService.mark(cluster.id, "phase", "offline")
        with pytest.raises(ClusterStateException):
            ClusterStateService.mark(-1, "switch", True)
        assert not ClusterState.objects.filter(cluster_id=cluster.id).exists()

    def test_filter_bool_with_default(self, clusters):
        ClusterStateService.mark(clusters[0].id, "switch", True)
        ids = [cluster.id for cluster in clusters]
        assert self.filter_cluster_ids("state__switch", "true", clusters) == {ids[0]}
        assert self.filter_cluster_ids("state__switch", "false", clusters) == {ids[1], ids[2]}
        assert self.filter_cluster_ids("state__switch", "true,false", clusters) == set(ids)

        # 值等于默认值但带 extra 时会保留行，也要按默认值命中
        ClusterStateService.mark(clusters[1].id, "switch", False, extra={"reason": "keep"})
        assert ClusterState.objects.filter(cluster_id=ids[1], state_key="switch").exists()
        assert self.filter_cluster_ids("state__switch", "false", clusters) == {ids[1], ids[2]}
        assert self.filter_cluster_ids("state__switch", "true", clusters) == {ids[0]}

    def test_filter_number_range(self, clusters):
        ClusterStateService.mark(clusters[0].id, "usage", 50)
        ClusterStateService.mark(clusters[1].id, "usage", 90)
        ids = [cluster.id for cluster in clusters]
        assert self.filter_cluster_ids("state__usage__gte", "60", clusters) == {ids[1]}
        # 没有默认值时没有行表示未采集，范围过滤不命中
        assert self.filter_cluster_ids("state__usage__lte", "60", clusters) == {ids[0]}
        assert self.filter_cluster_ids("state__usage", "50,90", clusters) == {ids[0], ids[1]}
        assert self.get_state(clusters[2], "usage").value is None

    def test_str_value(self, clusters):
        ClusterStateService.mark(clusters[0].id, "note", "a" * 256)
        ClusterStateService.mark(clusters[1].id, "note", "maintain")
        record = ClusterState.objects.get(cluster_id=clusters[1].id, state_key="note")
        assert (record.state_value_type, record.state_str_value, record.state_int_value) == ("str", "maintain", None)
        assert self.get_state(clusters[1], "note").display == "maintain"
        assert self.filter_cluster_ids("state__note", "maintain", clusters) == {clusters[1].id}
        with pytest.raises(ClusterStateException):
            ClusterStateService.mark(clusters[2].id, "note", "a" * 257)

    def test_filter_invalid_params(self, clusters):
        for param, raw in [
            ("state__not_declared", "1"),
            ("state__level", "low"),
            ("state__switch__gte", "1"),
            ("state__switch", "maybe"),
            ("state__usage__gte", "1,2"),
            ("state__note__gte", "a"),
        ]:
            with pytest.raises(ValidationError):
                self.filter_cluster_ids(param, raw, clusters)

    def test_clear(self, clusters):
        ClusterStateService.mark(clusters[0].id, "switch", True)
        ClusterStateService.mark(clusters[1].id, "switch", True)
        ClusterStateService.clear(clusters[0].id)
        assert not ClusterState.objects.filter(cluster_id=clusters[0].id).exists()
        assert ClusterState.objects.filter(cluster_id=clusters[1].id).exists()

    def test_clear_orphans(self, clusters):
        ClusterStateService.mark(clusters[0].id, "switch", True)
        ClusterState.objects.create(cluster_id=-100, state_key="switch", state_value_type="int", state_int_value=1)
        assert ClusterStateService.clear_orphans() == 1
        assert not ClusterState.objects.filter(cluster_id=-100).exists()
        assert ClusterState.objects.filter(cluster_id=clusters[0].id).exists()

    def test_batch_get_skips_unregistered_cluster_type(self, clusters, bk_biz_id):
        redis_cluster = create_cluster(ClusterType.TendisPredixyTendisplusCluster.value, bk_biz_id)
        cluster_infos = [self.cluster_info(clusters[0]), self.cluster_info(redis_cluster)]
        ClusterStateService.fill_states(cluster_infos)
        assert set(cluster_infos[0]["states"]) == {"phase", "status", "switch", "level", "usage", "note"}
        assert "states" not in cluster_infos[1]


def raise_read_error(self, cluster_ids):
    raise RuntimeError("read failed")


class TestServiceRead:
    def test_get(self, clusters):
        cluster = clusters[0]
        assert ClusterStateService.get(cluster.id, "switch").value is False
        ClusterStateService.mark(cluster.id, "usage", 60)
        assert ClusterStateService.get(cluster.id, "usage").value == 60
        assert ClusterStateService.get(clusters[1].id, "usage").value is None

    def test_get_strict_errors(self, clusters, monkeypatch):
        with pytest.raises(ClusterStateException):
            ClusterStateService.get(-1, "switch")
        with pytest.raises(ClusterStateException):
            ClusterStateService.get(clusters[0].id, "not_declared")
        monkeypatch.setattr(DemoUsageField, "batch_get", raise_read_error)
        with pytest.raises(RuntimeError):
            ClusterStateService.get(clusters[0].id, "usage")

    def test_get_states(self, clusters, bk_biz_id):
        cluster = clusters[0]
        ClusterStateService.mark(cluster.id, "switch", True)
        states = ClusterStateService.get_states(cluster.id)
        assert set(states) == {"phase", "status", "switch", "level", "usage", "note"}
        assert states["switch"].value is True

        states = ClusterStateService.get_states(cluster.id, keys=["switch", "not_declared"])
        assert set(states) == {"switch"}

        redis_cluster = create_cluster(ClusterType.TendisPredixyTendisplusCluster.value, bk_biz_id)
        assert ClusterStateService.get_states(redis_cluster.id) == {}
        with pytest.raises(ClusterStateException):
            ClusterStateService.get_states(-1)

    def test_get_states_raises_on_read_error(self, clusters, monkeypatch):
        monkeypatch.setattr(DemoUsageField, "batch_get", raise_read_error)
        with pytest.raises(RuntimeError):
            ClusterStateService.get_states(clusters[0].id)
        assert set(ClusterStateService.get_states(clusters[0].id, keys=["switch"])) == {"switch"}

    def test_batch_get_strict(self, clusters, monkeypatch):
        ids = [cluster.id for cluster in clusters]
        monkeypatch.setattr(DemoUsageField, "batch_get", raise_read_error)
        states = ClusterStateService.batch_get(ids)
        assert set(states) == set(ids)
        assert all("usage" not in item and "switch" in item for item in states.values())
        with pytest.raises(RuntimeError):
            ClusterStateService.batch_get(ids, strict=True)


class TestServiceFilter:
    def filter_ids(self, cluster_types, key, op, values, clusters):
        query = ClusterStateService.filter_q(cluster_types, key, op, values)
        queryset = Cluster.objects.filter(id__in=[cluster.id for cluster in clusters]).filter(query)
        return set(queryset.values_list("id", flat=True))

    def test_filter_q_accepts_typed_and_raw_values(self, clusters):
        ClusterStateService.mark(clusters[0].id, "switch", True)
        ClusterStateService.mark(clusters[1].id, "usage", 90)
        tendbha = [ClusterType.TenDBHA.value]
        for values in [[True], ["true"]]:
            assert self.filter_ids(tendbha, "switch", StateFilterOperator.IN.value, values, clusters) == {
                clusters[0].id
            }
        for values in [[80], ["80"]]:
            assert self.filter_ids(tendbha, "usage", StateFilterOperator.GTE.value, values, clusters) == {
                clusters[1].id
            }

    def test_filter_q_across_cluster_types(self, clusters, bk_biz_id):
        single = create_cluster(ClusterType.TenDBSingle.value, bk_biz_id)
        all_clusters = [*clusters, single]
        cluster_types = [ClusterType.TenDBHA.value, ClusterType.TenDBSingle.value]
        # TenDBSingle 未声明 switch，不命中
        assert self.filter_ids(cluster_types, "switch", "in", [False], all_clusters) == {c.id for c in clusters}
        assert self.filter_ids(cluster_types, "phase", "in", ["online"], all_clusters) == {c.id for c in all_clusters}

    def test_filter_q_invalid(self, clusters):
        tendbha = [ClusterType.TenDBHA.value]
        for key, op, values in [
            ("not_declared", "in", [1]),
            ("level", "in", ["low"]),
            ("switch", "gte", [1]),
            ("switch", "in", ["maybe"]),
            ("switch", "in", []),
            ("usage", "gte", [1, 2]),
        ]:
            with pytest.raises(ClusterStateException):
                ClusterStateService.filter_q(tendbha, key, op, values)

    def test_filter_cluster_ids(self, clusters, bk_biz_id):
        ClusterStateService.mark(clusters[0].id, "switch", True)
        ClusterStateService.mark(clusters[1].id, "switch", True)
        single = create_cluster(ClusterType.TenDBSingle.value, bk_biz_id)
        ids = [clusters[0].id, clusters[2].id, single.id]
        assert ClusterStateService.filter_cluster_ids(ids, "switch", "in", [True]) == [clusters[0].id]
        assert set(ClusterStateService.filter_cluster_ids(ids, "switch", "in", [False])) == {clusters[2].id}
        assert ClusterStateService.filter_cluster_ids([], "switch", "in", [True]) == []
        with pytest.raises(ClusterStateException):
            ClusterStateService.filter_cluster_ids([single.id], "switch", "in", [True])


class TestChecks:
    def test_registered_schemas_pass(self):
        assert check_cluster_state_schemas() == []

    def test_field_declaration_errors(self):
        class MultiStored(StoredStateField):
            value_type = StateValueType.MULTI.value
            choices = [("a", "a")]

        class TooLongChoice(StoredStateField):
            value_type = StateValueType.ENUM.value
            choices = [("a" * 257, "a")]

        class NativeWithoutBatchGet(NativeStateField):
            value_type = StateValueType.BOOL.value

        class NotDataclassExtra(StoredStateField):
            value_type = StateValueType.BOOL.value
            extra_class = dict

        class EnumWithoutChoices(StoredStateField):
            value_type = StateValueType.ENUM.value

        class FilterableWithoutQ(NativeStateField):
            value_type = StateValueType.BOOL.value
            filterable = True

        class BadDrillDown(NativeStateField):
            value_type = StateValueType.BOOL.value
            drilldown_type = "UNKNOWN"

        class DrillDownWithoutDetail(NativeStateField):
            value_type = StateValueType.BOOL.value
            drilldown_type = DrillDownType.TICKET_LIST.value

        for field_cls, keyword in [
            (MultiStored, "multi"),
            (TooLongChoice, "exceed"),
            (NativeWithoutBatchGet, "batch_get"),
            (NotDataclassExtra, "dataclass"),
            (EnumWithoutChoices, "choices"),
            (FilterableWithoutQ, "filter_q"),
            (BadDrillDown, "invalid drilldown_type"),
            (DrillDownWithoutDetail, "get_detail"),
        ]:
            state_field = field_cls()
            state_field.key = "demo"
            assert any(keyword in error for error in state_field.check()), field_cls.__name__

    def test_duplicated_registration(self, monkeypatch):
        monkeypatch.setattr(registry, "_schema_registry", {})
        monkeypatch.setattr(registry, "_schema_conflicts", [])
        monkeypatch.setattr(registry, "_discovered", True)

        @register_state_schema(cluster_types=["demo_type"])
        class FirstSchema(ClusterStateSchema):
            pass

        @register_state_schema(cluster_types=["demo_type"])
        class SecondSchema(ClusterStateSchema):
            pass

        errors = check_cluster_state_schemas()
        assert [error.id for error in errors] == ["cluster_state.E001"]
        assert registry.get_schema("demo_type") is FirstSchema
