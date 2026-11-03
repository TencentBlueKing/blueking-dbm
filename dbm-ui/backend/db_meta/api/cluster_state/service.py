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
import logging
from collections import defaultdict
from functools import reduce
from operator import or_
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext as _

from backend.db_meta.api.cluster_state.fields.base import StateField
from backend.db_meta.api.cluster_state.registry import get_schema
from backend.db_meta.api.cluster_state.values import StateDetail, StateValue
from backend.db_meta.exceptions import ClusterStateException
from backend.db_meta.models import Cluster, ClusterState

logger = logging.getLogger("root")


class ClusterStateService:
    """
    集群状态的统一入口，业务代码读、写、过滤集群状态都通过本类，不需要关心状态存在哪里。
    Service 按集群的 cluster_type 找到 Schema 中声明的字段再交给字段执行，并负责：
    校验该集群类型声明了这个字段、多种集群类型按类型分组、过滤取值的校验与归一化、批量写的事务。

    读取（返回 StateValue，判断用 .value，不要用 .display）：
    - get(cluster_id, key)：单个集群单个字段
    - get_states(cluster_id, keys=None)：单个集群的多个或全部字段
    - batch_get(cluster_ids, keys=None, strict=False)：一批集群，查询次数与集群数无关；
      默认单个字段读取失败只记日志（列表展示用），用于业务判断时传 strict=True
    过滤：
    - filter_q(cluster_types, key, op, values)：返回作用于 Cluster queryset 的 Q
    - filter_cluster_ids(cluster_ids, key, op, values)：在一批集群中筛出满足条件的 ID
    写入：
    - mark / unmark：单个集群；bulk_mark / bulk_unmark：同一字段批量写入，任一失败整体回滚
    生命周期：
    - clear：集群下架时调用；clear_orphans：周期任务兜底清理

    多个集群请用 batch_get / bulk_mark 一次处理，不要在循环里逐个调用 get / mark。
    异常统一为 ClusterStateException：集群不存在、集群类型未声明字段、取值或 extra 不合法、字段不支持写入等。
    """

    @classmethod
    def get_field(cls, cluster_type: str, key: str) -> StateField:
        """获取集群类型下声明的字段，未声明时抛出 ClusterStateException"""
        schema = get_schema(cluster_type)
        state_field = schema.get_field(key) if schema else None
        if state_field is None:
            raise ClusterStateException(message=_("集群类型 {} 未声明状态字段 {}").format(cluster_type, key))
        return state_field

    @classmethod
    def get_fields(cls, cluster_type: str) -> Dict[str, StateField]:
        """获取集群类型下声明的全部字段，未注册 Schema 时返回空"""
        schema = get_schema(cluster_type)
        return schema.get_fields() if schema else {}

    @classmethod
    def mark(cls, cluster_id: int, key: str, value: Any, extra: Any = None, operator: str = "") -> None:
        """
        写入单个集群的状态，幂等。value 按字段的 value_type 校验（"true" / "80" 这样的字符串也可以）；
        extra 为字段约定的附带信息，Stored 字段为 extra_class 实例或同结构的 dict
        """
        cluster = cls._get_cluster(cluster_id)
        cls.get_field(cluster.cluster_type, key).mark(cluster, value, extra=extra, operator=operator)

    @classmethod
    def unmark(cls, cluster_id: int, key: str, operator: str = "") -> None:
        """清除单个集群的状态，恢复为默认值（没有默认值时为未采集）"""
        cluster = cls._get_cluster(cluster_id)
        cls.get_field(cluster.cluster_type, key).unmark(cluster, operator=operator)

    @classmethod
    @transaction.atomic
    def bulk_mark(cls, key: str, values: Dict[int, Tuple[Any, Any]], operator: str = "") -> None:
        """
        批量写入同一个字段，values 为 {cluster_id: (value, extra)}，任一失败整体回滚。
        按集群类型分组后交给字段的 bulk_mark，Stored 字段每组只有固定几条 SQL
        """
        for state_field, clusters in cls._group_by_field(key, values.keys()):
            state_field.bulk_mark(clusters, values, operator=operator)

    @classmethod
    @transaction.atomic
    def bulk_unmark(cls, key: str, cluster_ids: Iterable[int], operator: str = "") -> None:
        """批量清除同一个字段，任一失败整体回滚"""
        for state_field, clusters in cls._group_by_field(key, cluster_ids):
            state_field.bulk_unmark(clusters, operator=operator)

    @classmethod
    def get(cls, cluster_id: int, key: str) -> StateValue:
        """读取单个集群的单个字段；集群不存在、字段未声明或读取失败时抛出异常"""
        cluster = cls._get_cluster(cluster_id)
        return cls.get_field(cluster.cluster_type, key).batch_get([cluster.id])[cluster.id]

    @classmethod
    def get_states(cls, cluster_id: int, keys: Optional[Iterable[str]] = None) -> Dict[str, StateValue]:
        """
        读取单个集群的状态合集，返回 {key: StateValue}；keys 为空时读取该集群类型声明的全部字段。
        每个字段至少一次查询，只关心少数字段时请传 keys；字段读取失败时抛出异常，未声明的 key 不返回
        """
        cluster = cls._get_cluster(cluster_id)
        return cls._batch_get_by_type({cluster.id: cluster.cluster_type}, keys, strict=True).get(cluster.id, {})

    @classmethod
    def batch_get(
        cls, cluster_ids: Iterable[int], keys: Optional[Iterable[str]] = None, strict: bool = False
    ) -> Dict[int, Dict[str, StateValue]]:
        """
        批量读取集群状态，返回 {cluster_id: {key: StateValue}}；keys 为空时读取全部字段。
        查询次数与集群数无关。strict 为 False 时单个字段读取失败只记日志、结果中缺少该 key（列表展示用）；
        用于业务判断时传 strict=True，读取失败直接抛出异常
        """
        cluster_types = dict(Cluster.objects.filter(id__in=cluster_ids).values_list("id", "cluster_type"))
        return cls._batch_get_by_type(cluster_types, keys, strict=strict)

    @classmethod
    def filter_q(cls, cluster_types: Iterable[str], key: str, op: str, values: List[Any]) -> Q:
        """
        返回作用于 Cluster queryset 的过滤条件，op 为 StateFilterOperator，values 为取值列表。
        同一个 key 在每种集群类型下由各自声明的字段解释，按集群类型 OR 拼接，未声明该字段的集群类型不命中；
        所有集群类型都未声明、字段不可过滤或取值不合法时抛出 ClusterStateException
        """
        cluster_types = list(dict.fromkeys(cluster_types))
        type_queries = []
        for cluster_type in cluster_types:
            schema = get_schema(cluster_type)
            state_field = schema.get_field(key) if schema else None
            if state_field is None:
                continue
            if not state_field.filterable:
                raise ClusterStateException(message=_("状态字段 {} 不支持过滤").format(key))
            type_queries.append(
                Q(cluster_type=cluster_type) & state_field.filter_q(op, state_field.clean_filter_values(op, values))
            )
        if not type_queries:
            raise ClusterStateException(message=_("集群类型 {} 未声明状态字段 {}").format(cluster_types, key))
        return reduce(or_, type_queries)

    @classmethod
    def filter_cluster_ids(cls, cluster_ids: Iterable[int], key: str, op: str, values: List[Any]) -> List[int]:
        """在给定集群中筛选满足状态条件的集群ID，集群类型从库中读取，规则同 filter_q"""
        clusters = Cluster.objects.filter(id__in=cluster_ids)
        cluster_types = clusters.values_list("cluster_type", flat=True).distinct()
        if not cluster_types:
            return []
        return list(clusters.filter(cls.filter_q(cluster_types, key, op, values)).values_list("id", flat=True))

    @classmethod
    def fill_states(cls, clusters: List[Dict[str, Any]]) -> None:
        """
        为列表接口的每一行集群挂载 states 字段，供前端直接渲染状态列，只包含取值，不包含下钻内容。
        clusters 为列表接口序列化后的集群信息，取其中的 id、cluster_type；未注册 Schema 的集群不挂载
        """
        cluster_map = {cluster["id"]: cluster for cluster in clusters}
        cluster_types = {cluster["id"]: cluster["cluster_type"] for cluster in clusters}
        for cluster_id, states in cls._batch_get_by_type(cluster_types).items():
            cluster_map[cluster_id]["states"] = {key: state.to_dict() for key, state in states.items()}

    @classmethod
    def get_detail(cls, cluster: Cluster, key: str) -> Optional[StateDetail]:
        """单个集群单个字段的下钻内容，前端点击单元格时调用"""
        state_field = cls.get_field(cluster.cluster_type, key)
        state = state_field.batch_get([cluster.id])[cluster.id]
        return state_field.get_detail(cluster, state)

    @classmethod
    def clear(cls, cluster_id: int) -> None:
        """集群下架时删除其在 ClusterState 中的全部状态行；Native 字段的原表数据由各自的下架逻辑处理"""
        ClusterState.objects.filter(cluster_id=cluster_id).delete()

    @classmethod
    def clear_orphans(cls, batch_size: int = 1000) -> int:
        """删除集群已不存在的状态行，返回删除的集群数"""
        state_cluster_ids = set(ClusterState.objects.values_list("cluster_id", flat=True).distinct())
        orphan_ids = sorted(state_cluster_ids - set(Cluster.objects.values_list("id", flat=True)))
        for index in range(0, len(orphan_ids), batch_size):
            ClusterState.objects.filter(cluster_id__in=orphan_ids[index : index + batch_size]).delete()
        return len(orphan_ids)

    @classmethod
    def _batch_get_by_type(
        cls, cluster_types: Dict[int, str], keys: Optional[Iterable[str]] = None, strict: bool = False
    ) -> Dict[int, Dict[str, StateValue]]:
        """
        按集群类型分组，每个字段对同类型的一组集群调用一次 batch_get。
        cluster_types 为 {cluster_id: cluster_type}，返回 {cluster_id: {key: StateValue}}；strict 含义见 batch_get
        """
        keys = set(keys) if keys is not None else None
        ids_by_type: Dict[str, List[int]] = defaultdict(list)
        for cluster_id, cluster_type in cluster_types.items():
            ids_by_type[cluster_type].append(cluster_id)

        result: Dict[int, Dict[str, StateValue]] = {}
        for cluster_type, cluster_ids in ids_by_type.items():
            state_fields = cls.get_fields(cluster_type)
            if not state_fields:
                continue
            for cluster_id in cluster_ids:
                result[cluster_id] = {}
            for key, state_field in state_fields.items():
                if keys is not None and key not in keys:
                    continue
                try:
                    states = state_field.batch_get(cluster_ids)
                except Exception:  # pylint: disable=broad-except
                    if strict:
                        raise
                    # 单个字段读取失败不影响集群列表，只缺少该字段
                    logger.exception("cluster state %s batch get failed, cluster_type=%s", key, cluster_type)
                    continue
                for cluster_id, state in states.items():
                    result[cluster_id][key] = state
        return result

    @classmethod
    def _group_by_field(cls, key: str, cluster_ids: Iterable[int]) -> List[Tuple[StateField, List[Cluster]]]:
        """按集群类型分组并取出各自声明的字段；集群不存在或类型未声明该字段时抛出 ClusterStateException"""
        cluster_ids = set(cluster_ids)
        clusters = list(Cluster.objects.filter(id__in=cluster_ids))
        missing = cluster_ids - {cluster.id for cluster in clusters}
        if missing:
            raise ClusterStateException(message=_("集群 {} 不存在").format(sorted(missing)))

        clusters_by_type: Dict[str, List[Cluster]] = defaultdict(list)
        for cluster in clusters:
            clusters_by_type[cluster.cluster_type].append(cluster)
        return [
            (cls.get_field(cluster_type, key), type_clusters)
            for cluster_type, type_clusters in clusters_by_type.items()
        ]

    @classmethod
    def _get_cluster(cls, cluster_id: int) -> Cluster:
        """获取集群，不存在时抛出 ClusterStateException"""
        try:
            return Cluster.objects.get(id=cluster_id)
        except Cluster.DoesNotExist:
            raise ClusterStateException(message=_("集群 {} 不存在").format(cluster_id))
