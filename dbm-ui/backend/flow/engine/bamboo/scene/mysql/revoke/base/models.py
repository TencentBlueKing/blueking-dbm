# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

主机退回资源池 · 判定模型核心数据结构。

模块职责：
  - 定义 F1~F4 单机判据与 G1 组级判据的 3 态结果类型（FactState / FactCheckOutcome）
  - 定义单机判据快照（HostRevokeFacts）与单机决策结论（HostDecision）
  - 定义组级判定单元（RevokeUnit / ResourceGroup）
  - 定义单机 / 组级最终判定结论（RevokeVerdict / GroupVerdict）

设计要点：
  - 所有 dataclass 使用 ``@dataclass(frozen=True)``：判定结果一经产出即不可变，避免下游误改
  - 复杂 evidence / 集合类字段一律 ``field(default_factory=...)``：规避 mutable default 陷阱
  - 三态命名遵循需求文档口径：YES/NO/UNKNOWN 分别对应 "命中/未命中/无法确认"

模块边界：
  - 本模块只定义数据结构，不含任何 IO / RPC / DB 调用
  - 判据采集在 host_check.py / group_check.py 中实现
  - 决策矩阵在 decision.py 中实现（纯函数）
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from django.utils.translation import gettext_lazy as _

from backend.flow.engine.revoke.exception import RevokeFlowBaseException
from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class FactState(StrStructuredEnum):
    """F/G 判据 3 态状态。

    使用场景：F1~F4 单机判据、G1/G2 组级判据的原子结果类型。

    :cvar YES: 判据成立（客观事实为真，如"MachineEvent 最近 ticket = 本单"）
    :cvar NO: 判据不成立（客观事实为假）
    :cvar UNKNOWN: 判据无法确认（数据源异常 / RPC 失败 / 超时 / 权限不足等）
    """

    YES = EnumField("yes", _("成立"))
    NO = EnumField("no", _("不成立"))
    UNKNOWN = EnumField("unknown", _("无法确认"))


class HostDecision(StrStructuredEnum):
    """单机决策结论。

    使用场景：`HostDecisionMatrix.classify()` 对每台机器 F1~F4 组合的映射产出。

    :cvar SKIP: F1 = NO / UNKNOWN；该机器已不属于本单据，什么都不做
    :cvar KEEP: F1=YES ∧ F2=YES ∧ F3=YES ∧ F4=YES；红线保留（正在服务）
    :cvar MANUAL: 出现异常 / 不一致 / UNKNOWN 组合；机器保持现状，等 DBA 手工介入
    :cvar RECYCLE: F1=YES ∧ F2=NO ∧ 进程状态确定；可按 F3/F4 evidence 精确清理并归还资源池
    """

    SKIP = EnumField("skip", _("跳过"))
    KEEP = EnumField("keep", _("保留"))
    MANUAL = EnumField("manual", _("挂起等人工"))
    RECYCLE = EnumField("recycle", _("可回收"))


class GroupDecision(StrStructuredEnum):
    """组级决策结论。

    使用场景：`GroupDecisionMatrix.classify()` 对 G1 + 组内单机结论组合的映射产出。

    :cvar GROUP_SKIP: 组内所有机器均 SKIP；整组不做任何动作
    :cvar GROUP_KEEP: 组内所有机器均 KEEP；红线保留整组
    :cvar GROUP_MANUAL: 组内出现混合 / MANUAL；整组挂起，不清理，输出告警日志
    :cvar GROUP_RECYCLE: 组内所有机器均 RECYCLE 且 G2 通过（或不适用）；走清理子流程
    """

    GROUP_SKIP = EnumField("group_skip", _("整组跳过"))
    GROUP_KEEP = EnumField("group_keep", _("整组保留"))
    GROUP_MANUAL = EnumField("group_manual", _("整组挂起"))
    GROUP_RECYCLE = EnumField("group_recycle", _("整组可回收"))


#: F 判据键名常量：用于 HostRevokeFacts / evidence 中的字段引用，避免散字符串硬编码
FACT_KEY_F1: str = "f1_ownership"
FACT_KEY_F2: str = "f2_traffic"
FACT_KEY_F3: str = "f3_dbm_residue"
FACT_KEY_F4: str = "f4_process"

#: F2 子判据键名常量
F2_SUB_KEY_DNS: str = "f2a_dns"
F2_SUB_KEY_CLB: str = "f2b_clb"
F2_SUB_KEY_TDBCTL: str = "f2c_tdbctl"
F2_SUB_KEY_PROXY_BACKENDS: str = "f2d_proxy_backends"

#: F3 子判据 evidence 键名常量：清理子流程根据这些键决定要执行哪些清理动作
F3_EV_KEY_MACHINE: str = "machine"
F3_EV_KEY_PROXIES: str = "proxies"
F3_EV_KEY_STORAGES: str = "storages"
F3_EV_KEY_TUPLES: str = "tuples"


@dataclass(frozen=True)
class FactCheckOutcome:
    """单条 F/G 判据的采集结果。

    职责：把一次判据检查的三态状态、结构化证据、异常原因收敛为不可变值对象。

    设计要点：
      - ``state`` 是决策矩阵的唯一输入维度
      - ``evidence`` 承载判据的具体命中项，供下游清理动作和日志展示复用
      - ``error`` 仅在 ``state == UNKNOWN`` 时有值，其他状态下应为 None

    :param state: 判据三态（YES / NO / UNKNOWN）
    :param evidence: 结构化证据 dict；具体键名由各判据方法自定义
    :param error: UNKNOWN 时携带原因；YES/NO 时应为 None
    :param reason: 人类可读的判定说明；便于日志展示，允许为空字符串
    """

    #: 判据三态
    state: FactState
    #: 结构化证据（例如 F3 evidence 中的 machine/proxies/storages/tuples 各自命中的对象 ID 列表）
    evidence: Dict[str, Any] = field(default_factory=dict)
    #: UNKNOWN 时的错误原因；YES/NO 时为 None
    error: Optional[str] = None
    #: 人类可读的判定说明
    reason: str = ""

    def __post_init__(self) -> None:
        """规范化空字段。

        :return: None
        边界：
          - ``evidence`` 传入 None 时会因 frozen=True 无法直接赋值，抛异常
          - ``state`` 类型非 FactState -> raise RevokeFlowBaseException
        """
        if not isinstance(self.state, FactState):
            raise RevokeFlowBaseException(
                "FactCheckOutcome.state must be FactState enum, got: {!r}".format(self.state)
            )
        # dataclass frozen=True 场景下，dict 默认值为 None 是非法的（field(default_factory) 已保证非 None）
        # 这里只做类型校验，不做重赋值
        if self.evidence is None:  # pragma: no cover  防御性检查
            raise RevokeFlowBaseException("FactCheckOutcome.evidence must not be None")

    @property
    def is_yes(self) -> bool:
        """是否为 YES 状态。"""
        return self.state == FactState.YES

    @property
    def is_no(self) -> bool:
        """是否为 NO 状态。"""
        return self.state == FactState.NO

    @property
    def is_unknown(self) -> bool:
        """是否为 UNKNOWN 状态。"""
        return self.state == FactState.UNKNOWN


@dataclass(frozen=True)
class HostRevokeFacts:
    """一台机器的 F1~F4 判据快照。

    职责：把单机 4 条 F 判据的采集结果打包为决策矩阵的输入。

    使用方式：
      facts = HostRevokeFacts(
          f1_ownership=checker.check_f1_ownership(unit=unit),
          f2_traffic=checker.check_f2_traffic(unit, alive_proxies),
          f3_dbm_residue=checker.check_f3_dbm_residue(unit),
          f4_process=checker.check_f4_process(process_ctx_json),
      )

    :param f1_ownership: F1 · 所有权（MachineEvent 反查）
    :param f2_traffic: F2 · 客户端流量红线（DNS/CLB/tdbctl/proxy 后端）
    :param f3_dbm_residue: F3 · DBM 元数据残留（Machine/Instance/Tuple）
    :param f4_process: F4 · 进程存活（本地 shell 脚本 + parse_process_check_result）
    """

    f1_ownership: FactCheckOutcome
    f2_traffic: FactCheckOutcome
    f3_dbm_residue: FactCheckOutcome
    f4_process: FactCheckOutcome

    def __post_init__(self) -> None:
        """校验四条 F 判据均已就位。

        :return: None
        边界：
          - 任一 F 字段为 None -> raise RevokeFlowBaseException
        """
        for name in (FACT_KEY_F1, FACT_KEY_F2, FACT_KEY_F3, FACT_KEY_F4):
            outcome = getattr(self, name)
            if not isinstance(outcome, FactCheckOutcome):
                raise RevokeFlowBaseException(
                    "HostRevokeFacts.{} must be FactCheckOutcome, got: {!r}".format(name, outcome)
                )


@dataclass(frozen=True)
class RevokeUnit:
    """一台候选机器的判定输入单元。

    职责：Extractor 从 ticket_data 提取的最小判定单位，携带本单在该机器上的所有痕迹信息。

    设计要点：
      - 角色由 Extractor **硬编码指定**（如 "proxy" / "backend_master" / "backend_slave"），
        不依赖运行时反查 DBM 元数据，避免部署未完成时角色不可知
      - ``expected_ports`` 是本单在该机器上"应该"绑的端口；判定时用于反查残留 / 精确探测
      - 端口列表是有序 tuple（frozen dataclass 内不允许放 list 作 hashable 字段，
        虽然本类未强制 __hash__，但保持 tuple 便于跨节点序列化时的稳定性）

    :param ip: 主机 IP
    :param bk_host_id: 主机 ID
    :param bk_cloud_id: 云区域 ID
    :param bk_biz_id: 业务 ID
    :param role: 硬编码角色字符串，取值：proxy / backend_master / backend_slave /
        spider / remote_master / remote_slave / single / spider_slave / spider_mnt
    :param expected_ports: 本单在该机器上申领的端口列表（多实例场景 N 个）；
        F3/F4 判据据此按端口精确过滤；group_cleanup 据此按端口精确摘 DNS
    :param cluster_type: 集群类型（决定 F2.c tdbctl 判据是否启用；本次 HA 场景固定为 tendbha）
    """

    ip: str
    bk_host_id: int
    bk_cloud_id: int
    bk_biz_id: int
    role: str
    expected_ports: Tuple[int, ...] = field(default_factory=tuple)
    cluster_type: str = ""

    def __post_init__(self) -> None:
        """基础字段合法性校验。

        :return: None
        边界：
          - ip 空串 -> raise
          - bk_host_id / bk_cloud_id / bk_biz_id 非 int 或负数 -> raise
          - role 空串 -> raise
        """
        if not self.ip or not isinstance(self.ip, str):
            raise RevokeFlowBaseException("RevokeUnit.ip must be non-empty string")
        if not isinstance(self.bk_host_id, int) or self.bk_host_id < 0:
            raise RevokeFlowBaseException("RevokeUnit.bk_host_id must be non-negative int")
        if not isinstance(self.bk_cloud_id, int) or self.bk_cloud_id < 0:
            raise RevokeFlowBaseException("RevokeUnit.bk_cloud_id must be non-negative int")
        if not isinstance(self.bk_biz_id, int) or self.bk_biz_id <= 0:
            raise RevokeFlowBaseException("RevokeUnit.bk_biz_id must be positive int")
        if not self.role or not isinstance(self.role, str):
            raise RevokeFlowBaseException("RevokeUnit.role must be non-empty string")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RevokeUnit":
        """从 ``dataclasses.asdict`` 生成的 dict 兜回 :class:`RevokeUnit`。

        业务动因：kwargs / trans_data 在 bamboo 节点间传递建议使用 pure dict，
        反序列化时需显式将 list 兜回 tuple，并对基础字段做类型强转以防御 pickle 后类型漂移。

        :param d: 由 ``dataclasses.asdict(unit)`` 生成的 dict
        :return: :class:`RevokeUnit` 实例
        边界：
          - 必填字段（ip / bk_host_id / bk_cloud_id / bk_biz_id / role）缺失 -> KeyError
          - 字段类型 / 取值非法 -> 由 ``__post_init__`` 校验抛 ``RevokeFlowBaseException``
          - ``expected_ports`` / ``cluster_type`` 缺失时走字段默认值
        """
        return cls(
            ip=str(d["ip"]),
            bk_host_id=int(d["bk_host_id"]),
            bk_cloud_id=int(d["bk_cloud_id"]),
            bk_biz_id=int(d["bk_biz_id"]),
            role=str(d["role"]),
            expected_ports=tuple(d.get("expected_ports") or []),
            cluster_type=str(d.get("cluster_type") or ""),
        )


@dataclass(frozen=True)
class AccessLayerInstance:
    """同集群接入层探测入口实例（扁平三元组）。

    职责：承载 F2 子判据所需的"同集群上游接入层单实例坐标"。

    设计要点：
      - 本类是 F2 子判据的**纯数据载体**，由 Extractor 在构建 flow 前预装到
        ``ResourceGroup.access_layer_proxies``；判定阶段只读消费
      - 字段只保留 ip + port + bk_cloud_id 三要素，避免冗余其他字段导致 trans_data 膨胀
      - frozen=True + 字段均为基本类型（str / int），保证可直接 json 序列化、
        跨 bamboo 节点通过 trans_data 透传安全
      - 命名用 ``AccessLayerInstance`` 而非直接 ``Instance``，避免与
        ``backend.db_meta.models.instance.Instance`` 名称冲突

    使用场景：
      - TenDBHA 场景：Extractor 将本单 apply_info 的 proxy 实例清单装入 ``access_layer_proxies``
        （列表长度 = 本 apply_info 的 proxy 实例数），供 F2.d 判据对每个 proxy 发起后端查询
      - TenDBCluster 场景：Extractor 将 ctl_primary 装入 ``access_layer_proxies``
        （列表长度严格 = 1），供 F2.c 判据连 ctl 查 ``mysql.servers``
      - TenDBSingle 场景：Extractor 不装任何实例（无 proxy 层 / 无 ctl 中控），列表保持为空

    :param ip: 实例 IP，非空字符串
    :param port: 实例端口，正整数
    :param bk_cloud_id: 云区域 ID，非负整数；供下游 RPC（proxyrpc / DRS）定位实例使用

    边界：
      - ip 为空串 / 非 str -> raise RevokeFlowBaseException
      - port <= 0 或非 int -> raise RevokeFlowBaseException
      - bk_cloud_id < 0 或非 int -> raise RevokeFlowBaseException
    """

    ip: str
    port: int
    bk_cloud_id: int

    def __post_init__(self) -> None:
        """基础字段合法性校验。

        :return: None
        边界：参见类 docstring 的"边界"段。
        """
        if not self.ip or not isinstance(self.ip, str):
            raise RevokeFlowBaseException("AccessLayerInstance.ip must be non-empty string")
        if not isinstance(self.port, int) or self.port <= 0:
            raise RevokeFlowBaseException("AccessLayerInstance.port must be positive int")
        if not isinstance(self.bk_cloud_id, int) or self.bk_cloud_id < 0:
            raise RevokeFlowBaseException("AccessLayerInstance.bk_cloud_id must be non-negative int")

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AccessLayerInstance":
        """从 ``dataclasses.asdict`` 生成的 dict 兜回 :class:`AccessLayerInstance`。

        业务动因：kwargs / trans_data 在 bamboo 节点间传递建议使用 pure dict，
        反序列化时需按字段显式构造以绕过 frozen dataclass 的 isinstance 校验。

        :param d: 由 ``dataclasses.asdict(instance)`` 生成的 dict，必须包含
            ``ip`` / ``port`` / ``bk_cloud_id`` 三个键
        :return: :class:`AccessLayerInstance` 实例
        边界：
          - 关键字段缺失 -> KeyError（由 d[key] 直接抛出，调用方感知）
          - 字段类型非法 -> 由 ``__post_init__`` 校验抛 ``RevokeFlowBaseException``
        """
        return cls(
            ip=str(d["ip"]),
            port=int(d["port"]),
            bk_cloud_id=int(d["bk_cloud_id"]),
        )


@dataclass(frozen=True)
class ResourceGroup:
    """一组资源（一个 apply_info 单元）。

    职责：把一个 apply_info（N proxy + 1 master + 1 standby，承载 M 个集群）打包为组级判定原子单位。

    设计要点：
      - ``group_id`` 用于 trans_data 索引与日志追踪；建议由 Extractor 用 apply_info 索引拼接生成
      - ``units`` 保存本组所有候选机器；顺序由 Extractor 保证（proxy 在前 / backend 在后有助于阅读日志）
      - ``cluster_domains`` 是本组承载的所有集群主域名列表，供 G2 与清理动作使用
      - ResourceGroup 一级字段最小集，所有字段都有真实业务消费点；不保留"预留扩展"类死字段，
        避免未来维护者误以为该字段承载重要契约

    :param group_id: 组唯一标识（如 "apply_info_0"）
    :param units: 组内所有 RevokeUnit
    :param cluster_domains: 组承载的所有集群主域名
    :param clb_regions: F2.b CLB 校验所需的 region 列表。由 Extractor 装配：
        - 部署类单据（Single/HA/Spider Apply）：填 ``ticket_data["city"]`` 单元素元组
        - 非部署类单据（Add/Restore Slave / Migrate / Proxy Add/Switch）：由
          :func:`load_tendbha_cluster_meta` 查关联集群 ``Cluster.region`` 去重返回
        - 空元组：等价于"F2.b CLB 校验未开启"（下游 ``check_clb_mapping`` 返回 NO_REGION_INPUT）
    :param access_layer_proxies: 同集群接入层探测入口实例清单。
        - TenDBHA 场景：装本 apply_info 的 proxy 实例列表（长度 = len(proxy_ip_list)）
        - TenDBCluster 场景：装 ctl_primary 单实例（长度严格 = 1，首元素即 ctl_primary）
        - TenDBSingle 场景：保持默认空元组
        供 F2 子判据按 ``unit.role`` 分发消费（BACKEND_MASTER 走 F2.d / REMOTE_MASTER 走 F2.c）
    """

    group_id: str
    units: Tuple[RevokeUnit, ...]
    cluster_domains: Tuple[str, ...] = field(default_factory=tuple)
    clb_regions: Tuple[str, ...] = field(default_factory=tuple)
    access_layer_proxies: Tuple[AccessLayerInstance, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """校验组结构合法性。

        :return: None
        边界：
          - group_id 空串 -> raise
          - units 为空 -> raise（空组不应被 Extractor 产出）
          - units 内元素非 RevokeUnit -> raise
        """
        if not self.group_id or not isinstance(self.group_id, str):
            raise RevokeFlowBaseException("ResourceGroup.group_id must be non-empty string")
        if not self.units:
            raise RevokeFlowBaseException("ResourceGroup.units must not be empty")
        for u in self.units:
            if not isinstance(u, RevokeUnit):
                raise RevokeFlowBaseException("ResourceGroup.units element must be RevokeUnit, got: {!r}".format(u))
        for p in self.access_layer_proxies:
            if not isinstance(p, AccessLayerInstance):
                raise RevokeFlowBaseException(
                    "ResourceGroup.access_layer_proxies element must be AccessLayerInstance, got: {!r}".format(p)
                )

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ResourceGroup":
        """从 ``dataclasses.asdict`` 生成的 dict 兜回 :class:`ResourceGroup`。

        业务动因：bamboo 节点间 kwargs / trans_data 建议只传 pure dict / list / str /
        int / bool 等基本类型；本方法负责将 asdict 产出的全展平 dict 递归兜回成嵌套
        dataclass 结构（list[dict] → Tuple[RevokeUnit/AccessLayerInstance, ...]），
        与 ``@dataclass(frozen=True)`` 字段类型及 ``__post_init__`` isinstance 校验对齐。

        实现要点：
          - 嵌套子对象反序列化委派给 :meth:`RevokeUnit.from_dict` /
            :meth:`AccessLayerInstance.from_dict`，职责归位、新增字段只改子类一处
          - ``cluster_domains`` / ``access_layer_proxies`` 缺失时走字段默认值
          - ``units`` 不做容错，缺失直接走 ``__post_init__`` 的空组校验抛异常

        :param d: 由 ``dataclasses.asdict(group)`` 生成的 dict
        :return: :class:`ResourceGroup` 实例
        边界：
          - group_id / units 关键字段缺失 -> 由 ``__post_init__`` 校验抛 ``RevokeFlowBaseException``
          - units / access_layer_proxies 内元素格式非法 -> 由子类 from_dict 或 __post_init__ 抛异常
        """
        return cls(
            group_id=str(d.get("group_id") or ""),
            units=tuple(RevokeUnit.from_dict(x) for x in d.get("units") or []),
            cluster_domains=tuple(d.get("cluster_domains") or []),
            clb_regions=tuple(d.get("clb_regions") or []),
            access_layer_proxies=tuple(AccessLayerInstance.from_dict(p) for p in d.get("access_layer_proxies") or []),
        )


@dataclass(frozen=True)
class RevokeVerdict:
    """一台机器的单机最终判定结论。

    职责：`HostDecisionMatrix.classify()` 的产出；把 RevokeUnit + F 判据快照 收敛为决策 + 原因。

    :param unit: 判定所属的机器单元
    :param decision: 单机决策结论（SKIP / KEEP / MANUAL / RECYCLE）
    :param facts: 单机 F1~F4 判据快照
    :param reason: 人类可读的决策原因（如 "F2=YES，红线保留"）
    """

    unit: RevokeUnit
    decision: HostDecision
    facts: HostRevokeFacts
    reason: str = ""

    def __post_init__(self) -> None:
        """校验字段合法性。

        :return: None
        边界：
          - unit / facts 类型不匹配 -> raise
          - decision 类型不匹配 -> raise
        """
        if not isinstance(self.unit, RevokeUnit):
            raise RevokeFlowBaseException("RevokeVerdict.unit must be RevokeUnit")
        if not isinstance(self.decision, HostDecision):
            raise RevokeFlowBaseException("RevokeVerdict.decision must be HostDecision")
        if not isinstance(self.facts, HostRevokeFacts):
            raise RevokeFlowBaseException("RevokeVerdict.facts must be HostRevokeFacts")


@dataclass(frozen=True)
class GroupVerdict:
    """一组资源的组级最终判定结论。

    职责：`GroupDecisionMatrix.classify()` 的产出；把组内所有 RevokeVerdict + G1 收敛为组决策。

    :param group: 判定所属的资源组
    :param decision: 组决策结论（GROUP_SKIP / GROUP_KEEP / GROUP_MANUAL / GROUP_RECYCLE）
    :param verdicts: 组内每台机器的单机 RevokeVerdict
    :param g1: G1 · 组内一致性判据结果
    :param reason: 人类可读的组决策原因，特别是 GROUP_MANUAL 时的挂起原因文本
    """

    group: ResourceGroup
    decision: GroupDecision
    verdicts: Tuple[RevokeVerdict, ...]
    g1: FactCheckOutcome
    reason: str = ""

    def __post_init__(self) -> None:
        """校验字段合法性。

        :return: None
        边界：
          - group / decision / g1 类型不匹配 -> raise
          - verdicts 元素非 RevokeVerdict -> raise
          - verdicts 数量与 group.units 数量不一致 -> raise
        """
        if not isinstance(self.group, ResourceGroup):
            raise RevokeFlowBaseException("GroupVerdict.group must be ResourceGroup")
        if not isinstance(self.decision, GroupDecision):
            raise RevokeFlowBaseException("GroupVerdict.decision must be GroupDecision")
        if not isinstance(self.g1, FactCheckOutcome):
            raise RevokeFlowBaseException("GroupVerdict.g1 must be FactCheckOutcome")
        for v in self.verdicts:
            if not isinstance(v, RevokeVerdict):
                raise RevokeFlowBaseException(
                    "GroupVerdict.verdicts element must be RevokeVerdict, got: {!r}".format(v)
                )
        if len(self.verdicts) != len(self.group.units):
            raise RevokeFlowBaseException(
                "GroupVerdict.verdicts count ({}) != group.units count ({})".format(
                    len(self.verdicts), len(self.group.units)
                )
            )
