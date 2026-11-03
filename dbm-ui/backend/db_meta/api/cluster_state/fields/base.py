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
import re
from dataclasses import asdict, fields, is_dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type

from django.db.models import Q
from django.utils.translation import gettext as _

from backend.db_meta.api.cluster_state.values import StateDetail, StateValue
from backend.db_meta.enums import DrillDownType, StateFilterOperator, StateSource, StateStorageType, StateValueType
from backend.db_meta.exceptions import ClusterStateException
from backend.db_meta.models import Cluster, ClusterState

logger = logging.getLogger("root")

FIELD_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
# 与 ClusterState.state_str_value 的长度一致
STR_VALUE_MAX_LENGTH = 256
# Stored 字段批量写入时每条 SQL 的行数
BULK_WRITE_BATCH_SIZE = 500


class StateField:
    """
    集群状态字段基类。一个字段描述一种状态：取值类型、怎么读、怎么过滤、怎么写、怎么下钻。

    字段只负责单个状态的读写，不感知集群类型：集群类型有哪些字段由 ClusterStateSchema 声明，
    运行时统一经 ClusterStateService 调用。业务代码不要直接调用字段的读写方法，否则会绕过
    "该集群类型声明了这个字段"的校验。

    不要直接继承本类，按数据来源二选一：
    - NativeStateField：数据已有专表（如 Cluster.phase、ClusterDBHAExt），直接读原表，不冗余存储
    - StoredStateField：数据没有实体（如容量），存进 ClusterState 竖表，读、写、过滤由框架实现

    子类通过类属性声明元信息，在 Schema 中实例化时可以覆盖，如 CapacityField(help_text=...)。
    平台字段（会被多个组件挂载、或在组件外的代码中读写的字段）应在类上声明 key，
    调用方写 ClusterStateService.mark(cluster_id, CapacityField.key, ...)，不手写字符串。
    可覆盖的方法：
    - batch_get：批量读取。Native 必须实现，Stored 已实现
    - filter_q：过滤条件。filterable = True 的 Native 必须实现，Stored 已实现
    - mark / unmark：写入与清除。需要写入的 Native 实现，Stored 已实现
    - bulk_mark / bulk_unmark：批量写入，默认逐个调用 mark / unmark，一般不需要覆盖
    - get_detail：下钻内容。声明了 drilldown_type 时必须实现
    - normalize_value：取值校验与归一化。取值不是普通字符串或数字时覆盖（如单据 ID 列表）
    - get_display：展示文本。默认展示不合适时覆盖
    其余方法由框架使用，子类不需要覆盖。声明是否完整由 check 在 manage.py check 时校验。

    参考实现见 fields/common.py：PhaseField（最简单的 Native）、DBHADisabledField（可过滤、可写的 Native）、
    RunningTicketField（MULTI 取值 + 下钻）、CapacityField（Stored + extra_class）。
    """

    # 数据来源，见 StateSource，由 NativeStateField / StoredStateField 固定
    source: str = ""
    # 字段唯一标识。平台字段在类上声明，业务代码用 CapacityField.key 引用，Schema 属性名必须与之一致；
    # 未声明时由 Schema 元类按属性名注入。不能在实例化时传入
    key: str = ""
    # 展示名
    name: str = ""
    # 字段说明，包括数据来源
    help_text: str = ""
    # 取值类型，见 StateValueType
    value_type: str = ""
    # 可选值，格式与 StrStructuredEnum.get_choices() 一致：[(value, label), ...]
    # ENUM 必须声明；MULTI 声明时元素取值限定在其中，不声明时元素为自由值
    choices: List[Tuple[Any, str]] = []
    # 默认值。Stored 字段没有行时即为默认值；为 None 表示没有默认值，没有行时视为"未采集"
    default_value: Any = None
    # 是否支持列表过滤
    filterable: bool = False
    # 是否允许通过前端开关接口写入；内部服务调用 ClusterStateService 写入不受此限制
    writable: bool = False
    # 单元格下钻类型，见 DrillDownType；为 None 表示不可下钻。
    # 列表只下发取值，点击时前端调用详情接口，由 get_detail 按需查询下钻内容
    drilldown_type: Optional[str] = None

    def __init__(self, **kwargs: Any) -> None:
        """允许实例化时覆盖类属性，只接受已声明的属性，写错属性名直接报错；key 由字段类或 Schema 属性名决定"""
        for attr, value in kwargs.items():
            if attr == "key":
                raise TypeError(f"{self.__class__.__name__}: key is declared on the field class(schema attribute)")
            if not hasattr(self, attr):
                raise TypeError(f"{self.__class__.__name__} got an unexpected attribute: {attr}")
            setattr(self, attr, value)

    def batch_get(self, cluster_ids: List[int]) -> Dict[int, StateValue]:
        """
        批量读取一批集群的状态，返回 {cluster_id: StateValue}。
        cluster_ids 是同一集群类型的一批集群（列表接口为一页），要用固定次数的查询读完，不要逐个集群查询；
        每个传入且存在的集群都要有值，没有数据时返回 make_state(default_value) 或 make_state(None)
        """
        raise NotImplementedError

    def filter_q(self, op: str, values: List[Any]) -> Q:
        """
        返回作用于 Cluster queryset 的过滤条件。
        op 为 StateFilterOperator 的值；values 已经过 clean_filter_values 校验与归一化，IN 为取值列表，
        GTE / LTE 只有一个值。子查询写成 Q(id__in=xxx.values("cluster_id")) 这样的非相关子查询，
        不要用 OR 拼接两个子查询；判断口径必须与 batch_get 一致
        """
        raise NotImplementedError

    def get_detail(self, cluster: Cluster, state: StateValue) -> Optional[StateDetail]:
        """
        单元格下钻的内容，用户点击时由详情接口调用，可以按需查库。
        state 是该集群当前的读取结果，可直接复用其 detail；不提供详情时返回 None
        """
        return None

    def mark(self, cluster: Cluster, value: Any, extra: Any = None, operator: str = "") -> None:
        """
        写入状态，要求幂等；取值等于默认值时等同 unmark。extra 的结构由字段约定，需写在子类 docstring 中。
        默认不支持写入：Stored 字段由框架实现，需要写入的 Native 字段自行实现，优先委托给原表已有的写入方法
        """
        raise ClusterStateException(message=_("字段 {} 不支持写入").format(self.key))

    def unmark(self, cluster: Cluster, operator: str = "") -> None:
        """清除状态，恢复为默认值（没有默认值时为未采集）。默认不支持写入"""
        raise ClusterStateException(message=_("字段 {} 不支持写入").format(self.key))

    def bulk_mark(self, clusters: List[Cluster], values: Dict[int, Tuple[Any, Any]], operator: str = "") -> None:
        """
        批量写入，clusters 为同一集群类型的集群，values 为 {cluster_id: (value, extra)}。
        默认逐个调用 mark；Stored 字段已改为固定条数的批量 SQL，Native 字段有高频批量写入时再覆盖
        """
        for cluster in clusters:
            value, extra = values[cluster.id]
            self.mark(cluster, value, extra=extra, operator=operator)

    def bulk_unmark(self, clusters: List[Cluster], operator: str = "") -> None:
        """批量清除，默认逐个调用 unmark"""
        for cluster in clusters:
            self.unmark(cluster, operator=operator)

    @property
    def supported_operators(self) -> List[str]:
        """支持的过滤操作符，NUMBER 额外支持范围过滤"""
        if self.value_type == StateValueType.NUMBER:
            return [StateFilterOperator.IN.value, StateFilterOperator.GTE.value, StateFilterOperator.LTE.value]
        return [StateFilterOperator.IN.value]

    def clean_filter_values(self, op: str, values: List[Any]) -> List[Any]:
        """
        校验过滤操作符和取值并逐个归一化，结果可直接传给 filter_q；不合法时抛出 ClusterStateException。
        取值可以是 True / 80，也可以是接口参数里的 "true" / "80"；范围操作符只能有一个值
        """
        if op not in self.supported_operators:
            raise ClusterStateException(message=_("状态字段 {} 不支持过滤操作 {}").format(self.key, op))
        if not values or (op != StateFilterOperator.IN and len(values) != 1):
            raise ClusterStateException(message=_("状态字段 {} 的过滤值 {} 不合法").format(self.key, values))
        return [self.normalize_value(value) for value in values]

    def normalize_value(self, value: Any) -> Any:
        """
        按 value_type 校验并归一化取值，写入和过滤共用；不合法时抛出 ClusterStateException。
        BOOL 接受 True / "true" / 1 等，NUMBER 转为 int，STR 不超过 256 字符，ENUM 必须在 choices 中；
        MULTI 校验的是单个元素
        """
        if self.value_type == StateValueType.BOOL:
            if isinstance(value, bool):
                return value
            if str(value).lower() in ("true", "1"):
                return True
            if str(value).lower() in ("false", "0"):
                return False
        elif self.value_type == StateValueType.NUMBER:
            if not isinstance(value, bool):
                try:
                    return int(value)
                except (TypeError, ValueError):
                    pass
        elif self.value_type == StateValueType.STR:
            if value is not None and len(str(value)) <= STR_VALUE_MAX_LENGTH:
                return str(value)
        elif self.value_type == StateValueType.ENUM:
            if str(value) in self.choice_map:
                return str(value)
        elif self.value_type == StateValueType.MULTI:
            # MULTI 归一化的是单个元素；元素不是字符串时（如单据 ID）字段需重写本方法
            if not self.choices or str(value) in self.choice_map:
                return str(value)
        raise ClusterStateException(message=_("状态字段 {} 的取值 {} 不合法").format(self.key, value))

    @property
    def choice_map(self) -> Dict[str, str]:
        """{str(value): label}"""
        return {str(value): label for value, label in self.choices}

    def get_display(self, value: Any) -> str:
        """取值的展示文本：None 为空，列表逐个展示后逗号拼接，有 choices 时取 label，BOOL 为 是/否，其余 str(value)"""
        if value is None:
            return ""
        if isinstance(value, (list, tuple)):
            return ",".join(self.get_display(item) for item in value)
        label = self.choice_map.get(str(value))
        if label is not None:
            return str(label)
        if self.value_type == StateValueType.BOOL:
            return _("是") if value else _("否")
        return str(value)

    def make_state(self, value: Any, detail: Any = None, updated_at: Optional[datetime] = None) -> StateValue:
        """构造读取结果，display 按 get_display 自动生成；batch_get 的返回值都应通过它构造"""
        return StateValue(value=value, display=self.get_display(value), detail=detail, updated_at=updated_at)

    def to_schema(self) -> Dict[str, Any]:
        """schema 接口中的字段声明，前端据此渲染列和过滤器"""
        return {
            "key": self.key,
            "name": str(self.name),
            "help_text": str(self.help_text),
            "value_type": self.value_type,
            "choices": [{"value": value, "label": str(label)} for value, label in self.choices],
            "default_value": self.default_value,
            "filterable": self.filterable,
            "writable": self.writable,
            "drilldown_type": self.drilldown_type,
            "source": self.source,
        }

    def check(self) -> List[str]:
        """声明自检，由 Django system check（cluster_state.E002）调用，返回错误描述列表；子类可追加校验"""
        errors: List[str] = []
        if not FIELD_KEY_PATTERN.match(self.key or ""):
            errors.append(f"key '{self.key}' must match {FIELD_KEY_PATTERN.pattern}")
        if self.value_type not in StateValueType.get_values():
            errors.append(f"invalid value_type '{self.value_type}'")
        if self.value_type == StateValueType.ENUM and not self.choices:
            errors.append(f"value_type '{self.value_type}' requires choices")
        if self.filterable and type(self).filter_q is StateField.filter_q:
            errors.append("filterable field must implement filter_q")
        if self.drilldown_type is not None:
            if self.drilldown_type not in DrillDownType.get_values():
                errors.append(f"invalid drilldown_type '{self.drilldown_type}'")
            if type(self).get_detail is StateField.get_detail:
                errors.append("field with drilldown_type must implement get_detail")
        return errors


class NativeStateField(StateField):
    """
    读取已有表的状态字段，不冗余存储，读写都落在原表上，原有的读写方不受影响。

    实现要求：
    - batch_get 必须实现，见 StateField.batch_get 的约定
    - filterable = True 时实现 filter_q；读取和过滤的判断口径要一致，建议抽一个返回 queryset 的方法共用，
      如 DBHADisabledField.disabled_records
    - 需要写入时实现 mark / unmark，优先委托给原表已有的写入方法（如 Cluster.disable_dbha），保留原有副作用
    - 原表在其他应用中时在方法内延迟 import，避免 db_meta 反向依赖导致循环引用（如 RunningTicketField）
    MULTI（多值）只允许 Native 字段使用，元素不是字符串时需覆盖 normalize_value
    """

    source = StateSource.NATIVE.value

    def check(self) -> List[str]:
        """额外校验必须实现 batch_get"""
        errors = super().check()
        if type(self).batch_get is StateField.batch_get:
            errors.append("NativeStateField must implement batch_get")
        return errors


class StoredStateField(StateField):
    """
    存放在 ClusterState 竖表的状态字段，读、写、过滤都由框架实现，子类只需声明类属性。

    存储规则：
    - 一个集群一个字段最多一行；ENUM / STR 存 state_str_value，BOOL / NUMBER 存 state_int_value（BOOL 存 0/1）
    - 声明了 default_value 时稀疏存储：取值等于默认值且没有 extra 时删除行，没有行即为默认值
    - 没有声明 default_value 时，没有行表示"未采集"，读取结果的 value 为 None
    - 需要随取值保存附带信息时声明 extra_class（dataclass）：写入的 extra 按其校验，读出为 StateValue.detail；
      给 extra_class 新增属性时要带默认值，读取时会忽略已不存在的旧 key
    不支持 MULTI；STR / ENUM 取值不超过 256 字符。数据由业务方通过 ClusterStateService.mark / bulk_mark 写入
    """

    source = StateSource.STORED.value
    # 需要扩展信息时声明 dataclass，extra 只能按该结构写入
    extra_class: Optional[Type[Any]] = None

    @property
    def storage_type(self) -> str:
        """落库类型：ENUM / STR 存字符串列，BOOL / NUMBER 存整数列"""
        if self.value_type in (StateValueType.ENUM, StateValueType.STR):
            return StateStorageType.STR.value
        return StateStorageType.INT.value

    @property
    def value_column(self) -> str:
        """取值所在的列名：state_str_value / state_int_value"""
        return f"state_{self.storage_type}_value"

    def to_db_value(self, value: Any) -> Any:
        """归一化后的取值转为落库值，BOOL 存为 0/1"""
        return str(value) if self.storage_type == StateStorageType.STR else int(value)

    def from_db_value(self, record: ClusterState) -> Any:
        """从记录中还原取值"""
        value = getattr(record, self.value_column)
        if value is None:
            return None
        if self.value_type == StateValueType.BOOL:
            return bool(value)
        return value

    def dump_extra(self, extra: Any) -> Dict[str, Any]:
        """extra 校验并序列化为 dict，接受 extra_class 实例或 dict"""
        if extra is None:
            return {}
        if self.extra_class is None:
            raise ClusterStateException(message=_("状态字段 {} 未声明 extra_class，不能写入 extra").format(self.key))
        if isinstance(extra, self.extra_class):
            return asdict(extra)
        if isinstance(extra, dict):
            try:
                return asdict(self.extra_class(**extra))
            except TypeError as err:
                raise ClusterStateException(message=_("状态字段 {} 的 extra 不合法: {}").format(self.key, err))
        raise ClusterStateException(message=_("状态字段 {} 的 extra 类型不合法").format(self.key))

    def load_extra(self, extra: Dict[str, Any]) -> Any:
        """库中的 extra 还原为 extra_class 实例，忽略 dataclass 中已不存在的旧 key"""
        if self.extra_class is None or not extra:
            return None
        names = {f.name for f in fields(self.extra_class)}
        try:
            return self.extra_class(**{name: value for name, value in extra.items() if name in names})
        except TypeError as err:
            logger.warning("cluster state %s load extra failed: %s, extra=%s", self.key, err, extra)
            return None

    def batch_get(self, cluster_ids: List[int]) -> Dict[int, StateValue]:
        """一次查询读取整页集群，没有行的集群取默认值"""
        records = ClusterState.objects.filter(cluster_id__in=cluster_ids, state_key=self.key)
        states = {
            record.cluster_id: self.make_state(
                self.from_db_value(record), detail=self.load_extra(record.extra), updated_at=record.update_at
            )
            for record in records
        }
        for cluster_id in cluster_ids:
            if cluster_id not in states:
                states[cluster_id] = self.make_state(self.default_value)
        return states

    def filter_q(self, op: str, values: List[Any]) -> Q:
        """
        稀疏存储下的过滤。没有行的集群取值为默认值，按默认值是否满足条件分两种写法：
        1. 默认值不满足：只命中有行且行内值满足条件的集群 -> id IN (满足条件的行)
        2. 默认值满足：没有行的集群也命中，等价于"不存在不满足条件的行" -> id NOT IN (不满足条件的行)
        两种写法都只有一个非相关子查询，MySQL 可转为 semijoin / antijoin；不要用 OR 拼接两个子查询，否则无法转换
        """
        records = ClusterState.objects.filter(state_key=self.key)
        if op == StateFilterOperator.IN:
            lookup = {f"{self.value_column}__in": [self.to_db_value(value) for value in values]}
        else:
            lookup = {f"{self.value_column}__{op}": self.to_db_value(values[0])}

        if self.default_matches(op, values):
            return ~Q(id__in=records.exclude(**lookup).values("cluster_id"))
        return Q(id__in=records.filter(**lookup).values("cluster_id"))

    def default_matches(self, op: str, values: List[Any]) -> bool:
        """默认值是否满足过滤条件"""
        if self.default_value is None:
            return False
        if op == StateFilterOperator.IN:
            return self.default_value in values
        if op == StateFilterOperator.GTE:
            return self.default_value >= values[0]
        if op == StateFilterOperator.LTE:
            return self.default_value <= values[0]
        raise ClusterStateException(message=_("状态字段 {} 不支持过滤操作 {}").format(self.key, op))

    def mark(self, cluster: Cluster, value: Any, extra: Any = None, operator: str = "") -> None:
        """写入状态，幂等；extra 为 extra_class 实例或同结构的 dict；取值等于默认值且没有 extra 时删除行"""
        self.bulk_mark([cluster], {cluster.id: (value, extra)}, operator=operator)

    def unmark(self, cluster: Cluster, operator: str = "") -> None:
        """删除行，恢复为默认值（没有默认值时为未采集）"""
        self.bulk_unmark([cluster], operator=operator)

    def bulk_mark(self, clusters: List[Cluster], values: Dict[int, Tuple[Any, Any]], operator: str = "") -> None:
        """
        批量写入，查询次数与集群数无关：
        取值等于默认值且没有 extra 的集群删除行（稀疏存储），其余集群用一条 upsert 写入。
        upsert 依赖 (cluster_id, state_key) 唯一索引，已有行只更新取值和更新人，保留创建人
        """
        records: List[ClusterState] = []
        reset_ids: List[int] = []
        for cluster in clusters:
            value, extra = values[cluster.id]
            value, extra_data = self.normalize_value(value), self.dump_extra(extra)
            if self.default_value is not None and value == self.default_value and not extra_data:
                reset_ids.append(cluster.id)
                continue
            record = ClusterState(
                cluster_id=cluster.id,
                state_key=self.key,
                state_value_type=self.storage_type,
                extra=extra_data,
                creator=operator,
                updater=operator,
            )
            setattr(record, self.value_column, self.to_db_value(value))
            records.append(record)

        if reset_ids:
            ClusterState.objects.filter(cluster_id__in=reset_ids, state_key=self.key).delete()
        if records:
            ClusterState.objects.bulk_create(
                records,
                batch_size=BULK_WRITE_BATCH_SIZE,
                update_conflicts=True,
                update_fields=[
                    "state_value_type",
                    "state_str_value",
                    "state_int_value",
                    "extra",
                    "updater",
                    "update_at",
                ],
            )

    def bulk_unmark(self, clusters: List[Cluster], operator: str = "") -> None:
        """批量删除行"""
        cluster_ids = [cluster.id for cluster in clusters]
        ClusterState.objects.filter(cluster_id__in=cluster_ids, state_key=self.key).delete()

    def check(self) -> List[str]:
        """额外校验 MULTI、extra_class、字符串长度、默认值"""
        errors = super().check()
        if self.value_type == StateValueType.MULTI:
            errors.append("value_type 'multi' is only allowed for NativeStateField")
        if self.extra_class is not None and not (
            isinstance(self.extra_class, type) and is_dataclass(self.extra_class)
        ):
            errors.append("extra_class must be a dataclass")
        too_long = [value for value, _label in self.choices if len(str(value)) > STR_VALUE_MAX_LENGTH]
        if too_long:
            errors.append(f"choice values exceed {STR_VALUE_MAX_LENGTH} chars: {too_long}")
        if self.default_value is not None:
            try:
                self.normalize_value(self.default_value)
            except ClusterStateException:
                errors.append(f"invalid default_value '{self.default_value}'")
        return errors
