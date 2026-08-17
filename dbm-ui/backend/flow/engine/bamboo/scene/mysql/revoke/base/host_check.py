# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

主机退回资源池判定公共类。

模块职责：
  - F1~F4 单机判据采集（返回 FactCheckOutcome / FactState 三态）：
    1) check_f1_ownership       —— F1 所有权（MachineEvent 最近事件 ticket 归属）
    2) check_f2_traffic         —— F2 客户端流量红线（按 role 策略路由：REMOTE_* 走 F2.c，BACKEND_* 走 F2.d，其他走 F2.a+F2.b）
    3) check_f3_dbm_residue     —— F3 DBM 残留（Machine/ProxyInstance/StorageInstance/Tuple 任一命中）
    4) check_f4_process         —— F4 进程存活（解析主机进程检查脚本的 ctx JSON）
  - 外部真相探针（供 F2 子判据内部消费；也可被联调脚本直接调用）：
    * check_clb_mapping / check_dns_mapping —— 完全不查 DBM 元数据，仅以 (ip, region) /
      (ip, bk_cloud_id) 查外部服务，避免"元数据已清 + 外部残留"的危险中间态被漏检
  - parse_process_check_result —— 进程检查脚本输出解析器

设计要点：
  - 只读无副作用；异常统一收敛为 reason_code="check_error"，不中断主链路
  - 结构化结果：reason_code（面向机器） / reason（面向人） / evidence（面向排查）

边界：
  - 本模块仅做"判定"不做"清理"；4 个方法结果正交互不掩盖
"""
import logging
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from django.utils.translation import gettext as _

from backend.components import CCApi, DRSApi
from backend.components.db_name_service.client import NameServiceApi
from backend.components.dns.client import DnsApi
from backend.configuration.models import BizSettings
from backend.db_dirty.models import MachineEvent
from backend.db_meta.enums import ClusterType, ClusterTypeMachineTypeDefine, InstanceRole
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance, StorageInstanceTuple
from backend.db_meta.models.cluster_monitor import ClusterMonitorTopo
from backend.db_services.cmdb.biz import get_or_create_resource_module
from backend.flow.engine.bamboo.scene.mysql.revoke.base.models import (
    F2_SUB_KEY_CLB,
    F2_SUB_KEY_DNS,
    F2_SUB_KEY_PROXY_BACKENDS,
    F2_SUB_KEY_TDBCTL,
    F3_EV_KEY_MACHINE,
    F3_EV_KEY_PROXIES,
    F3_EV_KEY_STORAGES,
    F3_EV_KEY_TUPLES,
    AccessLayerInstance,
    FactCheckOutcome,
    FactState,
    RevokeUnit,
)
from backend.flow.engine.revoke.exception import RevokeFlowBaseException
from backend.ticket.models import Ticket

logger = logging.getLogger("flow")


class HostCheckReasonCode:
    """判定结果 reason_code 枚举常量集合。

    职责：集中定义 4 个判定方法可能返回的所有 reason_code 字符串，
      供上层做分支处理（if/switch）时使用；面向机器、非展示文本。
    """

    #: 判定通过
    OK: str = "ok"

    #: 需求 3：未提供 region，无法判定 CLB 注册状态
    NO_REGION_INPUT: str = "no_region_input"
    #: 需求 3：IP 已注册在 CLB 上
    IP_REGISTERED_IN_CLB: str = "ip_registered_in_clb"
    #: 需求 3：IP 未注册在 CLB 上
    IP_NOT_REGISTERED_IN_CLB: str = "ip_not_registered_in_clb"

    #: 需求 4：IP 仍有 DNS 记录
    IP_HAS_DNS_RECORD: str = "ip_has_dns_record"
    #: 需求 4：IP 无 DNS 记录
    IP_NO_DNS_RECORD: str = "ip_no_dns_record"

    #: 需求 7（MySQL 主机进程存活检查）：主机上仍有 MySQL 家族进程 LISTEN
    #: （方案已收敛为"主机维度"扫描：只要命中白名单中任一 comm 即视为存活，
    #: 不再区分 process_missing / port_hijacked / partial_alive）
    MYSQL_STILL_ALIVE: str = "mysql_still_alive"

    #: 通用兜底：外部服务异常 / DB 查询异常
    CHECK_ERROR: str = "check_error"


@dataclass
class HostCheckResult:
    """单次判定的结构化结果。

    字段职责三分：
      * ``reason_code`` 面向机器（枚举分支）
      * ``reason``      面向人（展示文本，必填非空）
      * ``evidence``    面向排查（结构化证据）

    边界：
      - ``reason`` 强制非空字符串，若为空将在 ``__post_init__`` 抛异常
      - ``evidence`` 允许为空 dict，但不允许为 None
    """

    #: 判定是否通过
    passed: bool
    #: 结果分类枚举字符串，取值见 :class:`HostCheckReasonCode`
    reason_code: str
    #: 人类可读的原因说明，无论 passed 真假都必填非空
    reason: str
    #: 判定依据的关键证据字段，用于详细溯源
    evidence: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """校验 ``reason`` 非空、``evidence`` 非 None。

        :return: None
        边界：
          - ``reason`` 为 None / 空串 / 纯空白 -> raise RevokeFlowBaseException
          - ``evidence`` 为 None -> 自动置为 {}
        """
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise RevokeFlowBaseException(
                "HostCheckResult.reason must be non-empty string, got: {!r}".format(self.reason)
            )
        if self.evidence is None:
            self.evidence = {}


#: check_dns_mapping 中 evidence.records 仅保留的白名单字段
_DNS_RECORD_KEEP_FIELDS: Tuple[str, ...] = ("domain_name", "port", "status", "last_change_time")

#: 日志脱敏时需要剔除的敏感字段名（进程内小写匹配）
_SENSITIVE_FIELD_NAMES: frozenset = frozenset(
    {"clb_token", "servicetoken", "aliastoken", "token", "secret", "password"}
)


class HostRevokeChecker:
    """主机退回资源池判定公共类。

    职责：
      - 收敛 4 个独立、只读、无副作用的判定方法，供多个 revoke flow 复用
      - 每个判定方法各自返回 :class:`HostCheckResult`，结果正交互不掩盖
      - 外部服务调用异常统一封装为 CHECK_ERROR，不向上抛出中断流程

    使用方式：
        checker = HostRevokeChecker(
            root_id="root-xxx",
            ticket=ticket_obj,
            bk_biz_id=100,
            bk_cloud_id=0,
            ip="1.2.3.4",
            bk_host_id=123456,
        )
        # F 判据（3 态，供 revoke 决策矩阵消费）
        f1 = checker.check_f1_ownership()
        f2 = checker.check_f2_traffic(unit=unit, alive_proxies=..., clb_regions=[...])
        f3 = checker.check_f3_dbm_residue(unit=unit)
        f4 = HostRevokeChecker.check_f4_process(process_check_ctx_json=..., ip="1.2.3.4")
        # 外部真相探针（可单独调用，被 F2 子判据内部复用）
        r_clb = checker.check_clb_mapping(regions=["南京"])
        r_dns = checker.check_dns_mapping()

    线程安全：**非线程安全**（进程内可变状态），单个 revoke flow 内串行使用即可；
      如需并发，请为每个线程各起一个实例。

    边界：
      - 构造入参任一为空或类型不合法 -> 抛 :class:`RevokeFlowBaseException`
      - 判定方法内部任何 DB / API 异常均被捕获封装，不向上抛出
    """

    def __init__(
        self,
        root_id: str,
        ticket: Ticket,
        bk_biz_id: int,
        bk_cloud_id: int,
        ip: str,
        bk_host_id: int,
    ) -> None:
        """初始化判定器：只做赋值 + 参数校验，不做 IO/RPC/DB 调用。

        :param root_id: flow root_id，用于日志追踪
        :param ticket: 当前单据对象，需带有 ``id`` 属性
        :param bk_biz_id: 业务 id，> 0
        :param bk_cloud_id: 云区域 id，>= 0
        :param ip: 主机 IP，非空字符串
        :param bk_host_id: 主机 id，> 0
        :return: None
        边界：
          - 任一参数为空、类型不合法 -> raise RevokeFlowBaseException
        """
        if not isinstance(root_id, str) or not root_id.strip():
            raise RevokeFlowBaseException("root_id must be non-empty string")
        if ticket is None or not hasattr(ticket, "id"):
            raise RevokeFlowBaseException("ticket must be a Ticket instance with `id` attribute")
        if not isinstance(bk_biz_id, int) or bk_biz_id <= 0:
            raise RevokeFlowBaseException("bk_biz_id must be positive int")
        if not isinstance(bk_cloud_id, int) or bk_cloud_id < 0:
            raise RevokeFlowBaseException("bk_cloud_id must be non-negative int")
        if not isinstance(ip, str) or not ip.strip():
            raise RevokeFlowBaseException("ip must be non-empty string")
        if not isinstance(bk_host_id, int) or bk_host_id <= 0:
            raise RevokeFlowBaseException("bk_host_id must be positive int")

        self.root_id: str = root_id
        self.ticket: Ticket = ticket
        self.bk_biz_id: int = bk_biz_id
        self.bk_cloud_id: int = bk_cloud_id
        self.ip: str = ip
        self.bk_host_id: int = bk_host_id

    # ---------------- 私有工具 ----------------

    def _sanitize_evidence(self, evidence: Any) -> Any:
        """递归剔除敏感字段，用于日志与最终返回。

        :param evidence: 任意结构（dict / list / 标量）
        :return: 已剔除敏感字段的同结构对象
        边界：
          - 匹配以 :data:`_SENSITIVE_FIELD_NAMES` 为准（大小写不敏感）
          - 非 dict/list 直接返回原值
        """
        if isinstance(evidence, dict):
            cleaned: Dict[str, Any] = {}
            for k, v in evidence.items():
                if isinstance(k, str) and k.lower() in _SENSITIVE_FIELD_NAMES:
                    continue
                cleaned[k] = self._sanitize_evidence(v)
            return cleaned
        if isinstance(evidence, list):
            return [self._sanitize_evidence(item) for item in evidence]
        return evidence

    def _log_result(self, method: str, result: HostCheckResult) -> None:
        """按需求 7 的格式打印一行 INFO 汇总日志（含 reason）。

        :param method: 判定方法名，用于日志检索
        :param result: 判定结果对象
        :return: None
        边界：
          - passed=False 且 reason_code=CHECK_ERROR -> WARNING 级别
          - 其他情况 -> INFO 级别
        """
        line = (
            "[HostRevokeChecker][{root_id}][{ip}][{method}] "
            'passed={passed} reason_code={reason_code} reason="{reason}" evidence={evidence}'
        ).format(
            root_id=self.root_id,
            ip=self.ip,
            method=method,
            passed=result.passed,
            reason_code=result.reason_code,
            reason=result.reason,
            evidence=result.evidence,
        )
        if not result.passed and result.reason_code == HostCheckReasonCode.CHECK_ERROR:
            logger.warning(line)
        else:
            logger.info(line)

    def _build_result(
        self,
        method: str,
        passed: bool,
        reason_code: str,
        reason: str,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> HostCheckResult:
        """统一构造 :class:`HostCheckResult` 并触发日志。

        :param method: 判定方法名
        :param passed: 判定是否通过
        :param reason_code: 见 :class:`HostCheckReasonCode`
        :param reason: 人类可读原因（必填非空）
        :param evidence: 结构化证据；默认 {}
        :return: 已脱敏的 HostCheckResult
        边界：
          - evidence 内的敏感字段（如 clb_token）会被剔除
        """
        evidence = evidence or {}
        result = HostCheckResult(
            passed=passed,
            reason_code=reason_code,
            reason=reason,
            evidence=self._sanitize_evidence(evidence),
        )
        self._log_result(method=method, result=result)
        return result

    # ---------------- 需求 3：CLB 映射判定 ----------------

    def check_clb_mapping(self, regions: List[str]) -> HostCheckResult:
        """判定 IP 是否已注册在 CLB 后端上（完全不查 DBM 元数据）。

        怎么做：
          1) regions 全空 -> NO_REGION_INPUT（不使用 True 兜底）
          2) 遍历每个有效 region，调 NameServiceApi.clb_check_clb_register_target_by_ip
          3) 任一 region 的 clbinfos 存在 ip 匹配 **且 clbid 为非空字符串** -> 短路 IP_REGISTERED_IN_CLB
          4) 单个 region 抛异常时捕获、记入 failed_regions，继续遍历后续 region
          5) 遍历结束无命中但存在 failed_regions -> CHECK_ERROR（保守）
          6) 否则 -> IP_NOT_REGISTERED_IN_CLB

        判定条件设计说明：
          - 接口对任何入参 IP 都会返回一条记录（已通过生产双态样本验证）：
              · 已注册：{"ip": X, "registerclb": true, "region": "ap-nanjing", "clbid": "lb-xxx"}
              · 未注册：{"ip": X, "registerclb": false, "region": "", "clbid": ""}
          - 判定依据选取 **ip 匹配 + clbid 非空字符串**，而非 ``registerclb is True``：
              · ``registerclb`` 字段语义未在接口文档中明确说明，可能存在"健康状态" /
                "启用标志"等其他含义，直接作判据有误判风险
              · ``clbid`` 是业务层直接关心的"CLB 实体标识"：有 clbid 则确实挂在某个
                CLB 后端，这是接口返回中最权威的事实依据
              · 该口径与仓内已验证的 ``check_if_normal_for_cluster`` 用法一致
          - ``registerclb`` 原值作为 evidence 辅助观测字段落地，不参与判定决策

        :param regions: 需要检查的 region 列表；由调用方决定 region 来源
        :return: :class:`HostCheckResult`
        边界：
          - regions 内空字符串会被过滤；若全部为空视为 NO_REGION_INPUT
          - 单个 region 异常不中断整体遍历
          - clbid 字段缺失、为 None、空字符串、纯空白 -> 均视为未命中
        """
        method = "check_clb_mapping"

        # 步骤 1：region 输入合法性
        if not regions:
            return self._build_result(
                method=method,
                passed=False,
                reason_code=HostCheckReasonCode.NO_REGION_INPUT,
                reason=_("未提供 region，无法判定 CLB 注册状态"),
                evidence={"ip": self.ip, "regions": regions},
            )
        valid_regions: List[str] = [r for r in regions if isinstance(r, str) and r.strip()]
        if not valid_regions:
            return self._build_result(
                method=method,
                passed=False,
                reason_code=HostCheckReasonCode.NO_REGION_INPUT,
                reason=_("未提供 region，无法判定 CLB 注册状态"),
                evidence={"ip": self.ip, "regions": regions},
            )

        all_responses: Dict[str, Any] = {}
        failed_regions: Dict[str, str] = {}
        matched_clbid: Optional[str] = None
        matched_region: Optional[str] = None
        # 接口返回的 region 原值（与入参 region 口径可能不同，如入参"南京" vs 返回"ap-nanjing"）
        matched_region_from_api: Optional[str] = None
        # 接口返回的 registerclb 原值；仅作 evidence 辅助观测，不参与判定决策
        matched_registerclb_raw: Any = None

        # 步骤 2：遍历 region
        for region in valid_regions:
            try:
                resp = NameServiceApi.clb_check_clb_register_target_by_ip({"region": region, "ips": [self.ip]})
            except Exception as err:
                failed_regions[region] = str(err)
                logger.warning(
                    "[HostRevokeChecker][{}][{}][check_clb_mapping] region={} api error: {}".format(
                        self.root_id, self.ip, region, err
                    )
                )
                continue

            # 步骤 3：解析 clbinfos
            # 接口返回结构兼容两种格式：
            #   · 当前生产格式：{"clbinfos": [...]}（ApiGw 已自动剥 data 层）
            #   · 旧格式/raw 模式：{"data": {"clbinfos": [...]}}
            clbinfos: List[Dict[str, Any]] = []
            if isinstance(resp, dict):
                if isinstance(resp.get("clbinfos"), list):
                    clbinfos = resp["clbinfos"]
                elif isinstance(resp.get("data"), dict) and isinstance(resp["data"].get("clbinfos"), list):
                    clbinfos = resp["data"]["clbinfos"]

            # 落地本次 region 的原始响应到 all_responses，便于命中/未命中/异常各分支的 evidence 使用
            all_responses[region] = resp

            for info in clbinfos:
                if not isinstance(info, dict):
                    continue
                # 判定条件：ip 匹配 + clbid 为非空字符串
                # - 不依赖 registerclb 字段（语义不透明，可能是"健康状态"等其他含义）
                # - 直接看 CLB 实体标识 clbid 是否存在，这是业务层真正关心的事实
                clbid_raw: Any = info.get("clbid")
                if info.get("ip") != self.ip:
                    continue
                if not (isinstance(clbid_raw, str) and clbid_raw.strip() != ""):
                    continue
                matched_clbid = clbid_raw
                matched_region = region
                matched_region_from_api = info.get("region")
                matched_registerclb_raw = info.get("registerclb")
                break

            if matched_clbid is not None:
                break

        # 步骤 3 短路命中
        if matched_clbid is not None:
            return self._build_result(
                method=method,
                passed=False,
                reason_code=HostCheckReasonCode.IP_REGISTERED_IN_CLB,
                reason=_("该机器 IP 已注册在 CLB {} 上（region={}），需先解除绑定").format(matched_clbid, matched_region),
                evidence={
                    "ip": self.ip,
                    "matched_region": matched_region,
                    "matched_region_from_api": matched_region_from_api,
                    "matched_clbid": matched_clbid,
                    "checked_regions": valid_regions,
                    "registerclb_raw": matched_registerclb_raw,
                    "all_responses": all_responses,
                },
            )

        # 步骤 5：无命中但存在 failed_regions
        if failed_regions:
            return self._build_result(
                method=method,
                passed=False,
                reason_code=HostCheckReasonCode.CHECK_ERROR,
                reason=_("部分 region 查询clb失败，从保守出发视为不干净（failed_regions={}）").format(list(failed_regions.keys())),
                evidence={
                    "ip": self.ip,
                    "failed_regions": list(failed_regions.keys()),
                    "errors": failed_regions,
                    "all_responses": all_responses,
                },
            )

        # 步骤 6：全部干净
        return self._build_result(
            method=method,
            passed=True,
            reason_code=HostCheckReasonCode.IP_NOT_REGISTERED_IN_CLB,
            reason=_("IP 在 checked_regions={} 中均未注册到 CLB").format(valid_regions),
            evidence={
                "ip": self.ip,
                "checked_regions": valid_regions,
                "all_responses": all_responses,
            },
        )

    # ---------------- 需求 4：DNS 映射判定 ----------------

    def check_dns_mapping(self) -> HostCheckResult:
        """判定 IP 在 DNS 服务侧是否仍有域名解析（完全不查 DBM 元数据）。

        怎么做：
          1) 调 DnsApi.get_domain({"ip", "bk_cloud_id"}) 反查
          2) 返回值非 dict / 缺 detail 键 -> CHECK_ERROR
          3) detail 为空 -> IP_NO_DNS_RECORD
          4) detail 非空 -> IP_HAS_DNS_RECORD，records 仅保留定位字段

        :return: :class:`HostCheckResult`
        边界：
          - DnsApi 异常 -> CHECK_ERROR（保守策略，视为不干净）
          - passed=False 分支会在日志中打印完整 domain_name 列表
        """
        method = "check_dns_mapping"

        # 步骤 1：调用 DNS 接口
        try:
            resp = DnsApi.get_domain({"ip": self.ip, "bk_cloud_id": self.bk_cloud_id})
        except Exception as err:
            return self._build_result(
                method=method,
                passed=False,
                reason_code=HostCheckReasonCode.CHECK_ERROR,
                reason=_("DNS 接口调用失败：{}").format(err),
                evidence={
                    "ip": self.ip,
                    "bk_cloud_id": self.bk_cloud_id,
                    "error": str(err),
                    "trace": traceback.format_exc(limit=3),
                },
            )

        # 步骤 2：返回结构合法性
        if not isinstance(resp, dict) or "detail" not in resp:
            return self._build_result(
                method=method,
                passed=False,
                reason_code=HostCheckReasonCode.CHECK_ERROR,
                reason=_("DNS 接口返回结构异常（缺少 detail 键或非 dict）"),
                evidence={
                    "ip": self.ip,
                    "bk_cloud_id": self.bk_cloud_id,
                    "raw_response": resp,
                },
            )

        detail = resp.get("detail") or []
        if not isinstance(detail, list):
            return self._build_result(
                method=method,
                passed=False,
                reason_code=HostCheckReasonCode.CHECK_ERROR,
                reason=_("DNS 接口返回 detail 字段非 list"),
                evidence={
                    "ip": self.ip,
                    "bk_cloud_id": self.bk_cloud_id,
                    "raw_response": resp,
                },
            )

        # 步骤 3：detail 为空 -> 干净
        if not detail:
            return self._build_result(
                method=method,
                passed=True,
                reason_code=HostCheckReasonCode.IP_NO_DNS_RECORD,
                reason=_("DNS 服务无该 IP 的解析记录"),
                evidence={
                    "ip": self.ip,
                    "bk_cloud_id": self.bk_cloud_id,
                    "rowsNum": 0,
                },
            )

        # 步骤 4：detail 非空 -> 有残留
        records: List[Dict[str, Any]] = []
        all_domain_names: List[str] = []
        for item in detail:
            if not isinstance(item, dict):
                continue
            rec = {k: item.get(k) for k in _DNS_RECORD_KEEP_FIELDS if k in item}
            records.append(rec)
            dn = item.get("domain_name")
            if dn:
                all_domain_names.append(dn)

        rows_num: int = resp.get("rowsNum") if isinstance(resp.get("rowsNum"), int) else len(records)
        sample_domain: str = all_domain_names[0] if all_domain_names else ""

        # 需求 4.8：passed=False 时日志额外打印完整 domain_name 列表
        logger.info(
            "[HostRevokeChecker][{}][{}][check_dns_mapping] matched domains={}".format(
                self.root_id, self.ip, all_domain_names
            )
        )

        return self._build_result(
            method=method,
            passed=False,
            reason_code=HostCheckReasonCode.IP_HAS_DNS_RECORD,
            reason=_("该机器 IP 仍有 {} 条 DNS 记录（例：{}），需先清理 DNS").format(rows_num, sample_domain),
            evidence={
                "ip": self.ip,
                "bk_cloud_id": self.bk_cloud_id,
                "rowsNum": rows_num,
                "records": records,
            },
        )

    # ---------------- F1~F4 单机判据采集 ----------------

    def check_f1_ownership(self, unit: RevokeUnit) -> FactCheckOutcome:
        """F1 · 所有权判据：机器归属本单据 且 处于本 (bk_biz_id + db_type) 管控范围。

        判定分两段串行（任一段判 NO 即短路返回，段 1 优先）：

        段 1 · 属于本单据管控：
          - 从 ``self.ticket.details["parent_ticket"]`` 取 apply 原单据 id
            （RECYCLE_APPLY_HOST 的 details 由 :meth:`Ticket.create_recycle_ticket` 写入，
             parent_ticket = 真正申请这批机器的原 apply 单据 id）
          - 缺失 / 非法 → 直接抛 :class:`RevokeFlowBaseException` 短路给上层（契约违反）
          - 查 ``MachineEvent`` 表最近一次事件，``ticket_id == parent_ticket_id`` → 段 1 通过
          - 无事件 或 ticket 不匹配 → **F1=NO**（机器与本单无关联痕迹）

        段 2 · 属于本 (bk_biz_id + db_type) 管控范围（双通道任一命中即通过）：
          - 调 CCApi 查该 bk_host_id 的 bk_module_id 列表
          - 通道 A · 资源池模块：命中 :func:`get_or_create_resource_module` 的模块 id
              → 机器"还没交付"或"已归还到资源池"，视为本单管控内
          - 通道 B · DBM 集群模块：命中 :class:`ClusterMonitorTopo` 表中
              ``bk_biz_id == self.bk_biz_id`` 且
              ``machine_type ∈ ClusterTypeMachineTypeDefine[unit.cluster_type]`` 的模块
              → 机器"已交付到本 db_type 的集群模块下"，视为本单管控内
          - 通道 A / 通道 B 均不命中 → **F1=NO**（视为非法移动到其他业务 / 其他 db_type）

        :param unit: 判定所属 RevokeUnit；用 ``unit.cluster_type`` 反查 db_type
            对应的 machine_type 白名单，用于收紧 ClusterMonitorTopo 查询
        :return: :class:`FactCheckOutcome`
        :raises RevokeFlowBaseException: parent_ticket 缺失或非法（契约违反 · 短路上抛）
        边界：
          - MachineEvent DB 查询异常 → state=UNKNOWN
          - CC 接口异常 → state=UNKNOWN（外部服务保守降级，避免误清理）
          - 资源池模块获取失败 → state=UNKNOWN
          - ClusterMonitorTopo DB 查询异常 → state=UNKNOWN
          - CC 查询不到该主机（cc_records=[]） → state=NO（视作已从 CC 撤销）
          - unit.cluster_type 非法 → state=UNKNOWN
        """
        if not isinstance(unit, RevokeUnit):
            return FactCheckOutcome(
                state=FactState.UNKNOWN,
                error="unit is not RevokeUnit",
                reason=_("F1 输入 unit 类型非法"),
            )

        # ==================== 段 1：属于本单据管控 ====================
        parent_ticket_id: int = self._extract_parent_ticket_id()

        try:
            last_event = MachineEvent.objects.filter(bk_host_id=self.bk_host_id).order_by("-id").first()
        except Exception as err:
            logger.warning(
                "[HostRevokeChecker][{}][{}][check_f1_ownership] MachineEvent query error: {}".format(
                    self.root_id, self.ip, err
                )
            )
            return FactCheckOutcome(
                state=FactState.UNKNOWN,
                evidence={"bk_host_id": self.bk_host_id, "parent_ticket_id": parent_ticket_id, "error": str(err)},
                error=str(err),
                reason=_("F1 MachineEvent 查询异常：{}").format(err),
            )

        if last_event is None:
            return FactCheckOutcome(
                state=FactState.NO,
                evidence={
                    "bk_host_id": self.bk_host_id,
                    "parent_ticket_id": parent_ticket_id,
                    "last_event": None,
                },
                reason=_("F1=NO：机器无任何 MachineEvent 记录，与本单据无关联痕迹"),
            )

        last_event_ticket_id: Optional[int] = last_event.ticket_id
        if last_event_ticket_id != parent_ticket_id:
            return FactCheckOutcome(
                state=FactState.NO,
                evidence={
                    "bk_host_id": self.bk_host_id,
                    "parent_ticket_id": parent_ticket_id,
                    "last_event_id": last_event.id,
                    "last_event_type": last_event.event,
                    "last_event_ticket_id": last_event_ticket_id,
                },
                reason=_("F1=NO：机器最近一次事件关联单据 {} 与本单 apply parent_ticket {} 不一致").format(
                    last_event_ticket_id, parent_ticket_id
                ),
            )

        # ==================== 段 2：属于本 (bk_biz_id + db_type) 管控 ====================
        # 段 1 通过后段 2 的 evidence 基线，避免每个 return 分支都重写一遍
        f1_evidence_base: Dict[str, Any] = {
            "bk_host_id": self.bk_host_id,
            "parent_ticket_id": parent_ticket_id,
            "last_event_id": last_event.id,
            "last_event_type": last_event.event,
            "last_event_ticket_id": last_event_ticket_id,
        }

        # 2.1 反查本单 cluster_type 对应的 machine_type 白名单（等价"限定 db_type"）
        try:
            cluster_type_enum = ClusterType(unit.cluster_type)
            allowed_machine_types: List[str] = [mt.value for mt in ClusterTypeMachineTypeDefine[cluster_type_enum]]
        except (ValueError, KeyError) as err:
            logger.warning(
                "[HostRevokeChecker][{}][{}][check_f1_ownership] invalid cluster_type={!r}: {}".format(
                    self.root_id, self.ip, unit.cluster_type, err
                )
            )
            return FactCheckOutcome(
                state=FactState.UNKNOWN,
                evidence={**f1_evidence_base, "cluster_type": unit.cluster_type, "error": str(err)},
                error=str(err),
                reason=_("F1 unit.cluster_type={!r} 非法或未在 ClusterTypeMachineTypeDefine 中定义").format(unit.cluster_type),
            )

        # 2.2 CC 查询该主机的 bk_module_id 列表
        try:
            cc_records: List[Dict[str, Any]] = CCApi.find_host_biz_relations({"bk_host_id": [self.bk_host_id]}) or []
        except Exception as err:
            logger.warning(
                "[HostRevokeChecker][{}][{}][check_f1_ownership] CC find_host_biz_relations error: {}".format(
                    self.root_id, self.ip, err
                )
            )
            return FactCheckOutcome(
                state=FactState.UNKNOWN,
                evidence={**f1_evidence_base, "error": str(err), "trace": traceback.format_exc(limit=3)},
                error=str(err),
                reason=_("F1 CC 接口调用异常：{}").format(err),
            )

        if not cc_records:
            return FactCheckOutcome(
                state=FactState.NO,
                evidence={**f1_evidence_base, "cc_bk_module_ids": []},
                reason=_("F1=NO：CC 查询不到该主机（bk_host_id={}）").format(self.bk_host_id),
            )

        actual_bk_module_ids: List[int] = sorted(
            {int(rec.get("bk_module_id") or 0) for rec in cc_records if rec.get("bk_module_id")}
        )
        if not actual_bk_module_ids:
            return FactCheckOutcome(
                state=FactState.NO,
                evidence={**f1_evidence_base, "cc_records_count": len(cc_records), "cc_bk_module_ids": []},
                reason=_("F1=NO：CC 返回的 host_biz_relations 中未包含有效 bk_module_id"),
            )

        # 2.3 通道 A · 是否属于资源池模块
        try:
            resource_bk_module_id: int = int(get_or_create_resource_module())
        except Exception as err:
            logger.warning(
                "[HostRevokeChecker][{}][{}][check_f1_ownership] get_or_create_resource_module error: {}".format(
                    self.root_id, self.ip, err
                )
            )
            return FactCheckOutcome(
                state=FactState.UNKNOWN,
                evidence={**f1_evidence_base, "cc_bk_module_ids": actual_bk_module_ids, "error": str(err)},
                error=str(err),
                reason=_("F1 获取资源池模块 id 失败：{}").format(err),
            )

        # 2.4 通道 B · 是否属于本 (bk_biz_id + db_type) 的 ClusterMonitorTopo 模块
        # ClusterMonitorTopo 无 db_type 字段，用 machine_type__in 白名单等价过滤
        # 查询之前，需要用BizSettings.get_exact_hosting_biz查询它真正的托管业务在哪里。
        try:
            dbm_matched_module_ids: List[int] = sorted(
                set(
                    ClusterMonitorTopo.objects.filter(
                        bk_biz_id=BizSettings.get_exact_hosting_biz(self.bk_biz_id, unit.cluster_type),
                        machine_type__in=allowed_machine_types,
                        bk_module_id__in=actual_bk_module_ids,
                    )
                    .values_list("bk_module_id", flat=True)
                    .distinct()
                )
            )
        except Exception as err:
            logger.warning(
                "[HostRevokeChecker][{}][{}][check_f1_ownership] ClusterMonitorTopo query error: {}".format(
                    self.root_id, self.ip, err
                )
            )
            return FactCheckOutcome(
                state=FactState.UNKNOWN,
                evidence={
                    **f1_evidence_base,
                    "cc_bk_module_ids": actual_bk_module_ids,
                    "resource_bk_module_id": resource_bk_module_id,
                    "error": str(err),
                    "trace": traceback.format_exc(limit=3),
                },
                error=str(err),
                reason=_("F1 ClusterMonitorTopo 查询异常：{}").format(err),
            )

        hit_cluster_module: bool = bool(dbm_matched_module_ids)

        # 2.5 汇总判定（严格版 · 判定 A ∨ 判定 B）
        # 判定 A · 资源池独占：CC 只有一个模块，且等于资源池模块 id
        #   → 机器"从未交付"或"已完全归还资源池"，视为本单管控内
        # 判定 B · DBM 集群子集：CC 每一个模块都在本 (bk_biz_id + db_type) 的 ClusterMonitorTopo 集群模块池内
        #   → 机器"已完整交付到本 db_type 集群模块下"，视为本单管控内
        # 其他一律 F1=NO（混合状态 / 越界 / 非法移动）
        hit_resource_only: bool = len(actual_bk_module_ids) == 1 and actual_bk_module_ids[0] == resource_bk_module_id
        hit_full_dbm_subset: bool = hit_cluster_module and set(actual_bk_module_ids).issubset(
            set(dbm_matched_module_ids)
        )

        f1_evidence_full: Dict[str, Any] = {
            **f1_evidence_base,
            "cc_bk_module_ids": actual_bk_module_ids,
            "resource_bk_module_id": resource_bk_module_id,
            "dbm_matched_module_ids": dbm_matched_module_ids,
            "cluster_type": unit.cluster_type,
            "allowed_machine_types": allowed_machine_types,
            "hit_resource_only": hit_resource_only,
            "hit_full_dbm_subset": hit_full_dbm_subset,
        }

        if hit_resource_only:
            return FactCheckOutcome(
                state=FactState.YES,
                evidence=f1_evidence_full,
                reason=_("F1=YES：机器最近事件 ticket={} 与本单 apply parent_ticket={} 一致，且 CC 模块唯一且等于资源池模块 {}（未交付）").format(
                    last_event_ticket_id, parent_ticket_id, resource_bk_module_id
                ),
            )

        if hit_full_dbm_subset:
            return FactCheckOutcome(
                state=FactState.YES,
                evidence=f1_evidence_full,
                reason=_(
                    "F1=YES：机器最近事件 ticket={} 与本单 apply parent_ticket={} 一致，"
                    "且 CC 模块 {} 全部落在本业务 db_type={} 的 DBM 集群模块池内"
                ).format(last_event_ticket_id, parent_ticket_id, actual_bk_module_ids, unit.cluster_type),
            )

        return FactCheckOutcome(
            state=FactState.NO,
            evidence=f1_evidence_full,
            reason=_(
                "F1=NO：机器 CC 模块 {cc_modules} 既非独占资源池模块 {resource}，"
                "也未完全落在本业务 {biz} 的 db_type={ctype} 集群模块内（命中子集 {matched}），"
                "疑似非法移动或状态异常"
            ).format(
                cc_modules=actual_bk_module_ids,
                resource=resource_bk_module_id,
                biz=self.bk_biz_id,
                ctype=unit.cluster_type,
                matched=dbm_matched_module_ids,
            ),
        )

    def _extract_parent_ticket_id(self) -> int:
        """从 self.ticket.details 提取 parent_ticket（apply 原单据 id）。

        RECYCLE_APPLY_HOST 单据由 :meth:`Ticket.create_recycle_ticket` 创建，
        其 details 中的 ``parent_ticket`` 字段记录了发起主机回收的原 apply 单据 id。
        F1 判据必须用 parent_ticket 与 MachineEvent 记录的 ticket_id 比对，
        而不能用 RECYCLE 单据自身的 id（那是新单据、与 MachineEvent 永远不匹配）。

        :return: apply 原单据 id
        :raises RevokeFlowBaseException: details 非 dict / parent_ticket 缺失 / 非合法整数
            —— 契约违反场景，短路上抛让 pipeline FAILED，避免"F1 静默 NO 全部 SKIP"的假象
        """
        details = getattr(self.ticket, "details", None)
        if not isinstance(details, dict):
            raise RevokeFlowBaseException(
                "F1: ticket.details is not a dict (ticket_id={}, details_type={})".format(
                    self.ticket.id, type(details).__name__
                )
            )

        raw = details.get("parent_ticket")
        if raw is None:
            raise RevokeFlowBaseException(
                "F1: ticket.details['parent_ticket'] is missing (ticket_id={})".format(self.ticket.id)
            )

        try:
            return int(raw)
        except (TypeError, ValueError) as err:
            raise RevokeFlowBaseException(
                "F1: ticket.details['parent_ticket'] is not int-castable, got {!r} (ticket_id={}): {}".format(
                    raw, self.ticket.id, err
                )
            )

    #: F2.d 子判据适用的存储层角色（这些角色的流量入口唯一 = proxy 后端）
    _F2D_APPLICABLE_ROLES: frozenset = frozenset(
        {
            InstanceRole.BACKEND_MASTER.value,
            # BACKEND_REPEATER：HA 多级复制场景下的中继 master；理论上不会作为 revoke 候选，
            # 但其在集群架构语义上等同于 BACKEND_MASTER（作为下游 proxy 的后端引用），
            # 以防万一仍按 F2.d 路径判定
            InstanceRole.BACKEND_REPEATER.value,
        }
    )

    #: F2.c 子判据适用的存储层角色（这些角色的流量入口唯一 = tdbctl mysql.servers 路由）
    _F2C_APPLICABLE_ROLES: frozenset = frozenset(
        {
            InstanceRole.REMOTE_MASTER.value,
            # REMOTE_SLAVE：TenDBCluster 的 remote slave 节点，同样在 tdbctl mysql.servers
            # 路由表内（与 master 成对注册），下线必须查中控路由残留
            InstanceRole.REMOTE_SLAVE.value,
        }
    )

    def check_f2_traffic(
        self,
        unit: RevokeUnit,
        clb_regions: Optional[List[str]] = None,
        access_layer_proxies: Tuple[AccessLayerInstance, ...] = (),
        group_units: Tuple[RevokeUnit, ...] = (),
        host_process_check_ctx_by_ip: Optional[Dict[str, Any]] = None,
    ) -> FactCheckOutcome:
        """F2 · 客户端流量红线判据：按 role 策略路由到对应子判据（短路，不做无意义聚合）。

        怎么做（**策略路由模式** · 按 ``unit.role`` 决定走哪条判据路径，不再"全跑再聚合"）：

          路径 1 · F2.c 短路（REMOTE_MASTER / REMOTE_SLAVE）：
            - 架构语义：REMOTE 存储层对客户端的流量入口**唯一** = tdbctl mysql.servers 路由表；
              不挂 DNS、不挂 CLB，跑 F2.a/F2.b 无辨别力且会被接入层接口健康问题误伤
            - 实现：先按 F4 筛选 ``access_layer_proxies`` 得 ``alive_proxies``；若全不存活
              → 直接判 F2.c=NO（ctl_primary 都不在，不可能存在中控路由残留）；否则取
              首个 alive 入实例跑 :meth:`_sub_check_f2c_tdbctl_routing`

          路径 2 · F2.d 短路（BACKEND_MASTER / BACKEND_REPEATER）：
            - 架构语义：BACKEND 存储层对客户端的流量入口**唯一** = proxy backends 配置；
              不挂 DNS、不挂 CLB，跑 F2.a/F2.b 无辨别力
            - 实现：先按 F4 筛选 ``access_layer_proxies`` 得 ``alive_proxies``；若全不存活
              → 直接判 F2.d=NO（proxy 都不在，不可能存在后端引用）；否则对 alive 子集跑
              :meth:`_sub_check_f2d_proxy_backends`

          路径 3 · F2.a + F2.b 聚合（其他 role：PROXY / SPIDER / ORPHAN / BACKEND_SLAVE
            / SPIDER_SLAVE / SPIDER_MNT / 等）：
            - 架构语义：这些 role 的流量入口在 DNS / CLB（接入层职责）
            - F2.a · DNS：调 :meth:`check_dns_mapping`；DNS 服务里只要查到本机 IP 的
              **任何**解析记录 → F2.a=YES（红线：出现即视为客户端流量残留 / 跨业务混用）；
              DNS 完全无本机记录 → F2.a=NO；DNS 接口异常 → F2.a=UNKNOWN
            - F2.b · CLB：调 :meth:`check_clb_mapping`；命中 → F2.b=YES；未命中 → F2.b=NO；
              未提供 region 视为 NO；CLB 查询异常 → F2.b=UNKNOWN
            - 聚合：任一 YES → YES；全 NO → NO；无 YES 但有 UNKNOWN → UNKNOWN

        设计要点：
          - **按 role 路由，不该跑的根本不跑**：避免对 master 跑 DNS/CLB 这类架构上就不该有
            的判据，减少无谓 RPC、避免接入层接口异常把干净 master 阻塞到 MANUAL
          - **接入层存活性预判（F2.c / F2.d 共同前置）**：若 ``access_layer_proxies`` 装了但
            组内全部对应接入层机器均 F4=NO（进程不存在），说明接入层根本未部署或已被清掉
            —— 此时跑 proxyrpc / ctl SQL 必然协议错误，但语义上**可以证伪红线**（接入层
            不存在 ⇒ 不可能存在引用）→ 直接判 F2=NO，避免错误走 UNKNOWN → MANUAL 挂起；
            筛选规则见 :meth:`_filter_alive_access_layer`
          - **evidence 只放跑过的子判据**：短路分支 evidence 只含 ``f2c_tdbctl``
            （REMOTE_* 分支）或 ``f2d_proxy_backends``（BACKEND_* 分支）；聚合分支只含
            ``f2a_dns`` + ``f2b_clb``；不再写入 "skipped" 伪记录
          - F2.c / F2.d 的数据源**唯一**来自 ``access_layer_proxies`` 入参（由上层 group_judge
            组件透传自 ``ResourceGroup.access_layer_proxies``）；本方法不再临时反查 db_meta
          - 短路分支下 ``access_layer_proxies`` 为空 → 子判据判 UNKNOWN，决策矩阵走 MANUAL
            挂起等人工介入，守住"无法确认绝不默默清理"的安全边界

        :param unit: 判定所属机器单元
        :param clb_regions: CLB 需检查的 region 列表；None / 空 → F2.b 判 NO（不 UNKNOWN）；
            仅路径 3 消费，短路分支忽略
        :param access_layer_proxies: 同集群接入层探测入口清单（proxy 实例 / ctl_primary 单实例），
            默认空元组保持向后兼容；由上层调用方从 ``ResourceGroup.access_layer_proxies`` 透传；
            仅路径 1 / 路径 2 消费，路径 3 忽略
        :param group_units: 本组所有 ``RevokeUnit``，用于判断 ``access_layer_proxies[i].ip``
            是否属于本组（R3 跨组兜底）；仅路径 1 / 路径 2 消费
        :param host_process_check_ctx_by_ip: ``{ip: ctx_json}`` 本组所有机器的进程扫描快照
            （来自上游 ``MySQLHostProcessCheckComponent`` 节点写入的 trans_data），
            用于按 F4 口径判定本组接入层存活性；仅路径 1 / 路径 2 消费
        :return: :class:`FactCheckOutcome`；evidence 中仅包含实际跑过的子判据的 state 与命中详情
        边界：
          - unit 类型不合法 → 直接返回 UNKNOWN，避免误伤
          - 短路分支下 access_layer_proxies 为空 → 子判据判 UNKNOWN，走 MANUAL
          - 短路分支下 access_layer_proxies 非空但全部不存活 → 判 NO（证伪红线，走 RECYCLE）
        """
        if not isinstance(unit, RevokeUnit):
            return FactCheckOutcome(
                state=FactState.UNKNOWN,
                error="unit is not RevokeUnit",
                reason=_("F2 输入 unit 类型非法"),
            )

        # ==================== 路径 1 · F2.c 短路（REMOTE_MASTER / REMOTE_SLAVE）====================
        if unit.role in self._F2C_APPLICABLE_ROLES:
            # 接入层存活性预判：先按 F4 口径筛出 alive 子集；全死直接 NO（证伪红线）
            if access_layer_proxies:
                alive_proxies: Tuple[AccessLayerInstance, ...] = self._filter_alive_access_layer(
                    access_layer_proxies=access_layer_proxies,
                    group_units=group_units,
                    host_process_check_ctx_by_ip=host_process_check_ctx_by_ip or {},
                )
                if not alive_proxies:
                    return FactCheckOutcome(
                        state=FactState.NO,
                        evidence={
                            F2_SUB_KEY_TDBCTL: {
                                "state": FactState.NO.value,
                                "short_circuit": "no_alive_access_layer",
                                "checked_proxies": ["{}:{}".format(p.ip, p.port) for p in access_layer_proxies],
                                "reason": _("本组 ctl_primary 对应机器全部 F4=NO（进程未存活），不可能存在中控路由残留"),
                            }
                        },
                        reason=_("F2=NO：本组接入层（ctl_primary）均无进程存活，{} 角色不可能被引用").format(unit.role),
                    )
            else:
                alive_proxies = ()

            f2c_state, f2c_ev = self._sub_check_f2c_tdbctl_routing(unit, alive_proxies)
            evidence: Dict[str, Any] = {F2_SUB_KEY_TDBCTL: {"state": f2c_state.value, **f2c_ev}}
            if f2c_state == FactState.YES:
                return FactCheckOutcome(
                    state=FactState.YES,
                    evidence=evidence,
                    reason=_("F2=YES：{} 角色命中 tdbctl mysql.servers 路由残留（红线）").format(unit.role),
                )
            if f2c_state == FactState.UNKNOWN:
                return FactCheckOutcome(
                    state=FactState.UNKNOWN,
                    evidence=evidence,
                    error="F2.c unknown",
                    reason=_("F2=UNKNOWN：{} 角色 F2.c 无法确认，需人工介入").format(unit.role),
                )
            return FactCheckOutcome(
                state=FactState.NO,
                evidence=evidence,
                reason=_("F2=NO：{} 角色在 tdbctl mysql.servers 中无路由残留").format(unit.role),
            )

        # ==================== 路径 2 · F2.d 短路（BACKEND_MASTER / BACKEND_REPEATER）====================
        if unit.role in self._F2D_APPLICABLE_ROLES:
            # 接入层存活性预判：先按 F4 口径筛出 alive 子集；全死直接 NO（证伪红线）
            if access_layer_proxies:
                alive_proxies = self._filter_alive_access_layer(
                    access_layer_proxies=access_layer_proxies,
                    group_units=group_units,
                    host_process_check_ctx_by_ip=host_process_check_ctx_by_ip or {},
                )
                if not alive_proxies:
                    return FactCheckOutcome(
                        state=FactState.NO,
                        evidence={
                            F2_SUB_KEY_PROXY_BACKENDS: {
                                "state": FactState.NO.value,
                                "short_circuit": "no_alive_access_layer",
                                "checked_proxies": ["{}:{}".format(p.ip, p.port) for p in access_layer_proxies],
                                "reason": _("本组 proxy 全部 F4=NO（进程未存活），不可能存在后端引用"),
                            }
                        },
                        reason=_("F2=NO：本组接入层（proxy）均无进程存活，{} 角色不可能被引用").format(unit.role),
                    )
            else:
                alive_proxies = ()

            f2d_state, f2d_ev = self._sub_check_f2d_proxy_backends(unit, alive_proxies)
            evidence = {F2_SUB_KEY_PROXY_BACKENDS: {"state": f2d_state.value, **f2d_ev}}
            if f2d_state == FactState.YES:
                return FactCheckOutcome(
                    state=FactState.YES,
                    evidence=evidence,
                    reason=_("F2=YES：{} 角色命中 proxy 后端引用残留（红线）").format(unit.role),
                )
            if f2d_state == FactState.UNKNOWN:
                return FactCheckOutcome(
                    state=FactState.UNKNOWN,
                    evidence=evidence,
                    error="F2.d unknown",
                    reason=_("F2=UNKNOWN：{} 角色 F2.d 无法确认，需人工介入").format(unit.role),
                )
            return FactCheckOutcome(
                state=FactState.NO,
                evidence=evidence,
                reason=_("F2=NO：{} 角色未被任何 proxy 作为后端引用").format(unit.role),
            )

        # ==================== 路径 3 · F2.a + F2.b 聚合（其他 role）====================
        f2a_state, f2a_ev = self._sub_check_f2a_dns()
        f2b_state, f2b_ev = self._sub_check_f2b_clb(regions=clb_regions or [])

        evidence = {
            F2_SUB_KEY_DNS: {"state": f2a_state.value, **f2a_ev},
            F2_SUB_KEY_CLB: {"state": f2b_state.value, **f2b_ev},
        }
        sub_keys: Tuple[str, str] = (F2_SUB_KEY_DNS, F2_SUB_KEY_CLB)
        sub_states: Tuple[FactState, FactState] = (f2a_state, f2b_state)

        if FactState.YES in sub_states:
            hits = [name for name, s in zip(sub_keys, sub_states) if s == FactState.YES]
            return FactCheckOutcome(
                state=FactState.YES,
                evidence=evidence,
                reason=_("F2=YES：红线命中，子判据 {} 命中").format(hits),
            )
        if FactState.UNKNOWN in sub_states:
            unknowns = [name for name, s in zip(sub_keys, sub_states) if s == FactState.UNKNOWN]
            return FactCheckOutcome(
                state=FactState.UNKNOWN,
                evidence=evidence,
                error="unknown sub-facts: {}".format(unknowns),
                reason=_("F2=UNKNOWN：无子判据命中 YES，但子判据 {} 无法确认").format(unknowns),
            )
        return FactCheckOutcome(
            state=FactState.NO,
            evidence=evidence,
            reason=_("F2=NO：DNS / CLB 均未命中，无客户端流量残留"),
        )

    def _sub_check_f2a_dns(self) -> Tuple[FactState, Dict[str, Any]]:
        """F2.a · DNS 子判据（内部辅助）。

        判定语义（严格版 · 红线优先）：
          - 只要 DNS 服务里查到本机 IP 的任何解析记录 → **YES**（红线，禁止退回）
              * 无论域名是什么：出现即视为客户端流量残留 / 跨业务混用；
                此时清理机器风险极大
          - DNS 完全无本机记录 → NO（干净）
          - DNS 接口异常 → UNKNOWN（保守）

        :return: (state, evidence)；YES 时 evidence 列出 dns_records（原始记录）与
            domain_names（去重排序的域名列表，肉眼一眼看清）
        边界：
          - 本方法不依赖任何"预期域名"清单，只看 DNS 是否有本机记录
        """
        r = self.check_dns_mapping()
        # DNS 接口异常 → UNKNOWN
        if r.reason_code == HostCheckReasonCode.CHECK_ERROR:
            return FactState.UNKNOWN, {"error": r.reason, "evidence": r.evidence}
        # DNS 无记录 → NO（干净）
        if r.reason_code == HostCheckReasonCode.IP_NO_DNS_RECORD:
            return FactState.NO, {"dns_records": []}

        # 有 DNS 记录：一律红线 YES
        records: List[Dict[str, Any]] = r.evidence.get("records", []) if isinstance(r.evidence, dict) else []
        domain_names: List[str] = sorted({str(rec.get("domain_name")) for rec in records if rec.get("domain_name")})

        return FactState.YES, {
            "dns_records": records,
            "domain_names": domain_names,
        }

    def _sub_check_f2b_clb(self, regions: List[str]) -> Tuple[FactState, Dict[str, Any]]:
        """F2.b · CLB 子判据（内部辅助）。

        怎么做：
          - 复用 :meth:`check_clb_mapping` 判定本机 IP 是否在 CLB 后端
          - regions 空 → 直接 NO（不启用 CLB 检查）
          - CLB 命中 → YES；未命中 → NO；接口异常 → UNKNOWN

        :param regions: CLB 需检查的 region 列表
        :return: (state, evidence)
        边界：
          - regions 空视为 NO 而非 UNKNOWN（HA 场景通常不启用 CLB，避免误挂起）
        """
        if not regions:
            return FactState.NO, {"skipped": True, "reason": _("未配置 CLB regions，F2.b 不启用")}

        r = self.check_clb_mapping(regions=regions)
        if r.reason_code == HostCheckReasonCode.CHECK_ERROR:
            return FactState.UNKNOWN, {"error": r.reason, "evidence": r.evidence}
        if r.reason_code == HostCheckReasonCode.IP_REGISTERED_IN_CLB:
            return FactState.YES, {"matched": r.evidence}
        # NO_REGION_INPUT / IP_NOT_REGISTERED_IN_CLB → NO
        return FactState.NO, {"evidence": r.evidence}

    def _sub_check_f2c_tdbctl_routing(
        self, unit: RevokeUnit, access_layer_proxies: Tuple[AccessLayerInstance, ...]
    ) -> Tuple[FactState, Dict[str, Any]]:
        """F2.c · tdbctl 中控路由子判据（内部辅助，仅 REMOTE_MASTER / REMOTE_SLAVE 角色调用）。

        怎么做：
          - 取 ``access_layer_proxies[0]`` 作为 ctl_primary 探测入口（Extractor 已保证单实例口径）
          - 连 ``ctl_primary.ip:ctl_primary.port`` 执行 ``SELECT Host, Port FROM mysql.servers``
            （WHERE Host 过滤本机 IP，命中任一端口的记录即视为 ctl 路由残留）
          - 命中非空结果集 → YES；空结果集 → NO；连接 / SQL 异常 → UNKNOWN

        设计要点：
          - 复用项目既有的 ``DRSApi.rpc`` 单实例 SQL 查询通道，不新建连接池
          - 查询超时、权限不足、SQL 执行失败等异常统一归为 UNKNOWN，并记录 evidence 便于 DBA 排查

        :param unit: 判定所属机器（REMOTE_MASTER / REMOTE_SLAVE 角色）
        :param access_layer_proxies: 同集群接入层探测入口清单；首元素应为 ctl_primary 实例
        :return: (state, evidence)
        边界：
          - access_layer_proxies 为空 → **UNKNOWN**（REMOTE 角色要求查中控路由但 Extractor
            未装 ctl_primary，属于装配缺失，走 MANUAL 等人工介入；绝不默认 NO 走 RECYCLE）
          - access_layer_proxies[0] 字段非法（ip 空 / port 非正）→ UNKNOWN，记录 error
          - DRSApi.rpc 抛异常 / 返回 error_msg -> UNKNOWN，记录 error
        """
        if not access_layer_proxies:
            return FactState.UNKNOWN, {
                "error": "access_layer_proxies is empty, cannot query ctl mysql.servers",
                "reason": _("F2.c=UNKNOWN：REMOTE 角色要求查 ctl 中控路由但 Extractor 未装 ctl_primary"),
            }

        ctl_primary: AccessLayerInstance = access_layer_proxies[0]
        if not ctl_primary.ip or ctl_primary.port <= 0:
            return FactState.UNKNOWN, {
                "error": "ctl_primary field illegal: ip={!r} port={!r}".format(ctl_primary.ip, ctl_primary.port),
                "ctl_primary": {"ip": ctl_primary.ip, "port": ctl_primary.port},
            }

        ctl_address: str = "{}:{}".format(ctl_primary.ip, ctl_primary.port)
        # 走 DRSApi.rpc 单实例查询：参数化 Host 过滤，仅返回本机命中的 Host/Port 对
        sql: str = "SELECT Host, Port FROM mysql.servers WHERE Host = '{}'".format(unit.ip)

        try:
            resp = DRSApi.rpc(
                {
                    "addresses": [ctl_address],
                    "cmds": [sql],
                    "force": False,
                    "bk_cloud_id": int(ctl_primary.bk_cloud_id),
                }
            )
        except Exception as err:
            logger.warning(
                "[HostRevokeChecker][{}][{}][check_f2_traffic.f2c] DRSApi.rpc failed for ctl={} cloud_id={}: {}".format(
                    self.root_id, self.ip, ctl_address, ctl_primary.bk_cloud_id, err
                )
            )
            return FactState.UNKNOWN, {
                "ctl_primary": {"ip": ctl_primary.ip, "port": ctl_primary.port},
                "error": "DRSApi.rpc exception: {}".format(err),
            }

        if not isinstance(resp, list) or not resp:
            return FactState.UNKNOWN, {
                "ctl_primary": {"ip": ctl_primary.ip, "port": ctl_primary.port},
                "error": "DRSApi.rpc response invalid: {!r}".format(resp),
            }

        item = resp[0] if isinstance(resp[0], dict) else {}
        err_msg: str = item.get("error_msg") or ""
        if err_msg:
            return FactState.UNKNOWN, {
                "ctl_primary": {"ip": ctl_primary.ip, "port": ctl_primary.port},
                "error": "ctl SQL error: {}".format(err_msg),
            }

        # 解析 cmd_results.table_data，命中任意 Host 行即判 YES
        matched_rows: List[Dict[str, Any]] = []
        cmd_results = item.get("cmd_results") or []
        for cr in cmd_results:
            if not isinstance(cr, dict):
                continue
            for row in cr.get("table_data") or []:
                if not isinstance(row, dict):
                    continue
                row_host: str = str(row.get("Host") or row.get("host") or "").strip()
                row_port = row.get("Port") if row.get("Port") is not None else row.get("port")
                if row_host == unit.ip:
                    matched_rows.append({"Host": row_host, "Port": row_port})

        if matched_rows:
            return FactState.YES, {
                "ctl_primary": {"ip": ctl_primary.ip, "port": ctl_primary.port},
                "matched_rows": matched_rows,
            }
        return FactState.NO, {
            "ctl_primary": {"ip": ctl_primary.ip, "port": ctl_primary.port},
            "matched_rows": [],
        }

    def _sub_check_f2d_proxy_backends(
        self, unit: RevokeUnit, access_layer_proxies: Tuple[AccessLayerInstance, ...]
    ) -> Tuple[FactState, Dict[str, Any]]:
        """F2.d · proxy 后端引用子判据（内部辅助，仅 BACKEND_MASTER / BACKEND_REPEATER 角色调用）。

        怎么做：
          - 对每台 ``access_layer_proxies`` 中的 proxy 实例跑 ``DRSApi.proxyrpc SELECT * FROM backends``
          - 解析 backends 列表；命中 ``本机 IP:本单端口`` 任一组合 → YES
          - 全部 proxy 均未命中 → NO
          - 所有 RPC 均失败 → UNKNOWN

        设计要点：
          - 入参 ``access_layer_proxies`` 的 ``port`` 字段即为 proxy 的 **admin 查询端口**
            （由 Extractor 在装配时按 ``start_proxy_port`` 口径传入）；本方法不再做 admin_port 二次推导
          - ``bk_cloud_id`` 一律取自实例的 ``bk_cloud_id`` 字段，不再回退 self.bk_cloud_id

        :param unit: 判定所属机器（BACKEND_MASTER / BACKEND_REPEATER 角色）
        :param access_layer_proxies: 同集群 proxy 实例清单（AccessLayerInstance 列表）
        :return: (state, evidence)
        边界：
          - access_layer_proxies 为空 → **UNKNOWN**（BACKEND 角色要求查 proxy 后端但
            Extractor 未装 proxy 清单，属于装配缺失，走 MANUAL 等人工介入；绝不默认 NO 走 RECYCLE）
          - proxy 返回 error_msg -> 该 proxy 记入 failed_proxies，继续查其他
          - 部分 proxy 成功但均未命中 且 有 failed → NO（成功的 proxy 都没引用则视作 NO）
        """
        if not access_layer_proxies:
            return FactState.UNKNOWN, {
                "error": "access_layer_proxies is empty, cannot query proxy backends",
                "reason": _("F2.d=UNKNOWN：BACKEND 角色要求查 proxy 后端但 Extractor 未装 proxy 列表"),
            }

        expected_ports: List[int] = list(unit.expected_ports)
        # 构造 "ip:port" 匹配集合
        expected_targets: set = {"{}:{}".format(unit.ip, p) for p in expected_ports}

        matched_hits: List[Dict[str, Any]] = []
        failed_proxies: List[Dict[str, Any]] = []
        queried_proxies: List[str] = []

        # 按 bk_cloud_id 分组批量发 RPC（DRSApi.proxyrpc 支持一次多个 address 但要求同 cloud_id）
        cloud_groups: Dict[int, List[str]] = {}
        for p in access_layer_proxies:
            proxy_addr = "{}:{}".format(p.ip, p.port)
            cloud_id = int(p.bk_cloud_id)
            cloud_groups.setdefault(cloud_id, []).append(proxy_addr)
            queried_proxies.append(proxy_addr)

        for cloud_id, addresses in cloud_groups.items():
            try:
                resp = DRSApi.proxyrpc(
                    {
                        "addresses": addresses,
                        "cmds": ["SELECT * FROM backends;"],
                        "force": False,
                        "bk_cloud_id": cloud_id,
                    }
                )
            except Exception as err:
                logger.warning(
                    "[HostRevokeChecker][{}][{}][check_f2_traffic.f2d] proxyrpc failed for cloud_id={} addresses={}: {}".format(
                        self.root_id, self.ip, cloud_id, addresses, err
                    )
                )
                for a in addresses:
                    failed_proxies.append({"address": a, "error": str(err)})
                continue

            if not isinstance(resp, list):
                for a in addresses:
                    failed_proxies.append({"address": a, "error": "resp not list"})
                continue

            for item in resp:
                if not isinstance(item, dict):
                    continue
                addr = item.get("address", "")
                err_msg = item.get("error_msg") or ""
                if err_msg:
                    failed_proxies.append({"address": addr, "error": err_msg})
                    continue
                # 解析 cmd_results 里的 backends 表
                cmd_results = item.get("cmd_results") or []
                for cr in cmd_results:
                    if not isinstance(cr, dict):
                        continue
                    for row in cr.get("table_data") or []:
                        if not isinstance(row, dict):
                            continue
                        # backends 表通常字段名为 address；容错读一下 "backend"
                        backend_addr = str(row.get("address") or row.get("backend") or "").strip()
                        if backend_addr in expected_targets:
                            matched_hits.append(
                                {
                                    "proxy_address": addr,
                                    "backend_address": backend_addr,
                                }
                            )

        if matched_hits:
            return FactState.YES, {
                "matched_hits": matched_hits,
                "queried_proxies": queried_proxies,
                "failed_proxies": failed_proxies,
            }
        # 无命中但全部 RPC 都失败 → UNKNOWN
        if failed_proxies and len(failed_proxies) >= len(queried_proxies):
            return FactState.UNKNOWN, {
                "failed_proxies": failed_proxies,
                "queried_proxies": queried_proxies,
                "error": "all proxy RPCs failed",
            }
        # 部分成功但均未命中 → NO
        return FactState.NO, {
            "queried_proxies": queried_proxies,
            "failed_proxies": failed_proxies,
            "expected_targets": sorted(expected_targets),
        }

    @staticmethod
    def _filter_alive_access_layer(
        access_layer_proxies: Tuple[AccessLayerInstance, ...],
        group_units: Tuple[RevokeUnit, ...],
        host_process_check_ctx_by_ip: Dict[str, Any],
    ) -> Tuple[AccessLayerInstance, ...]:
        """按 F4 判据口径筛选"存活"的接入层实例（F2.c / F2.d 共用的存活性门控）。

        怎么做（规则映射）：
          - **R1 存活性 = F4 判据 state ∈ {YES, UNKNOWN}**：
              * YES → 主机 LISTEN 到 MySQL 家族进程 → 判为活
              * UNKNOWN → ctx 缺失 / 解析失败，无法确认 → 保守向上视为活（避免误清理）
              * NO → 明确无进程 LISTEN → 判为死，剔除
            判据直接复用 :meth:`check_f4_process` 纯函数，保证与 F4 判据产出口径完全一致，
            不在本方法内自己解析 ctx（否则 F4 判据升级后两处口径容易漂移）
          - **R3 跨组兜底**：若 ``access_layer_proxies[i].ip`` 不在本组 ``group_units`` 的任何
            一台机器 IP 内（典型场景：主从迁移退回时装入的 proxy IP 是老 proxy、不在本次
            revoke 的新机器组内），**一律视为活**；本组进程快照没有这些 IP 的 ctx，无法做
            F4 判定，必须保守向上保留 proxyrpc / ctl SQL 实查路径

        设计要点：
          - 本方法是**纯函数**（无 IO、无 RPC、无 DB），可独立单元测试
          - R3 的"保守向上"策略不是漏洞：若 ``access_layer_proxies`` 装了跨组 IP 但该 IP
            实际不可达 / 协议错误，下游 proxyrpc / ctl SQL 仍会按既有逻辑返回 UNKNOWN
            （R4 兜底），不会误清理
          - 返回类型保持 ``Tuple[AccessLayerInstance, ...]`` 与入参一致，供
            :meth:`_sub_check_f2c_tdbctl_routing` / :meth:`_sub_check_f2d_proxy_backends` 直接消费

        :param access_layer_proxies: 本组接入层探测入口清单（Extractor 装配，已校验非空）
        :param group_units: 本组所有 ``RevokeUnit``，用于判断 ``access_layer_proxies[i].ip``
            是否属于本组（R3 跨组兜底的组内 IP 集合）
        :param host_process_check_ctx_by_ip: ``{ip: ctx_json}`` 本组所有机器的进程扫描快照
        :return: 筛选后的存活接入层实例元组（可能为空：代表组内接入层全部 F4=NO）
        边界：
          - 入参 access_layer_proxies 为空 → 返回 ``()``；调用方自己处理 UNKNOWN 兜底
          - 入参 group_units 为空（极端场景）→ 所有 proxy 走 R3 保守路径视为活
          - host_process_check_ctx_by_ip 为空 dict → 组内 proxy 的 F4 判为 UNKNOWN
            （ctx 缺失）→ 仍视为活（R1 UNKNOWN 向上）
        """
        group_ips: Set[str] = {u.ip for u in group_units}
        alive: List[AccessLayerInstance] = []
        for p in access_layer_proxies:
            # R3: 跨组 IP 一律视为活（保守向上保留 proxyrpc / ctl SQL 实查路径）
            if p.ip not in group_ips:
                alive.append(p)
                continue
            # R1: 组内 IP 走 F4 判据口径；复用 check_f4_process 保证与 F4 产出一致
            f4_outcome = HostRevokeChecker.check_f4_process(host_process_check_ctx_by_ip.get(p.ip), ip=p.ip)
            if f4_outcome.state != FactState.NO:
                # YES（有进程）/ UNKNOWN（无法确认）均视为活
                alive.append(p)
        return tuple(alive)

    def check_f3_dbm_residue(self, unit: RevokeUnit) -> FactCheckOutcome:
        """F3 · DBM 元数据残留判据：Machine / ProxyInstance / StorageInstance / StorageInstanceTuple 任一命中即 YES。

        怎么做：
          - 查 :class:`Machine` 表本机记录；命中 → F3.d 存在
          - 查 :class:`ProxyInstance` / :class:`StorageInstance` 表本机 bk_host_id 相关记录，
            按 ``unit.expected_ports`` 精确过滤本单端口的实例（多实例场景避免误伤同机他单实例）
          - 查 :class:`StorageInstanceTuple` 表本机相关的主从关系记录
          - 任一有记录 → F3=YES，evidence 按需求文档 表 5 的键名分组记录命中的对象 ID / port

        :param unit: 判定所属机器单元（必填）；unit.expected_ports 用于精确过滤 instance，
            多实例场景下必须传入以避免整机误伤同机他单据实例
        :return: :class:`FactCheckOutcome`
        边界：
          - DB 查询异常 -> state=UNKNOWN，error 携带异常摘要
          - 全部四表均无本机相关记录 -> state=NO
          - unit.expected_ports 为空元组时视作"无端口约束"（当前 V2 场景不会走到这里，
            RevokeUnit 契约要求 expected_ports 非空）
        """
        if not isinstance(unit, RevokeUnit):
            return FactCheckOutcome(
                state=FactState.UNKNOWN,
                error="unit is not RevokeUnit",
                reason=_("F3 输入 unit 类型非法"),
            )
        expected_ports: Tuple[int, ...] = unit.expected_ports
        try:
            # ---- F3.d · Machine ----
            machine = Machine.objects.filter(bk_host_id=self.bk_host_id).first()
            machine_hit: Optional[Dict[str, Any]] = None
            if machine is not None:
                machine_hit = {
                    "bk_host_id": machine.bk_host_id,
                    "ip": machine.ip,
                    "machine_type": machine.machine_type,
                    "cluster_type": machine.cluster_type,
                }

            # ---- F3.a · ProxyInstance ----
            proxy_qs = ProxyInstance.objects.filter(machine__bk_host_id=self.bk_host_id)
            if expected_ports:
                proxy_qs = proxy_qs.filter(port__in=list(expected_ports))
            proxy_hits: List[Dict[str, Any]] = [{"id": p.pk, "port": p.port, "status": p.status} for p in proxy_qs]

            # ---- F3.a · StorageInstance ----
            storage_qs = StorageInstance.objects.filter(machine__bk_host_id=self.bk_host_id)
            if expected_ports:
                storage_qs = storage_qs.filter(port__in=list(expected_ports))
            storage_hits: List[Dict[str, Any]] = [
                {"id": s.pk, "port": s.port, "instance_role": s.instance_role, "status": s.status} for s in storage_qs
            ]

            # ---- F3.c · StorageInstanceTuple ----
            # 本机作为主(ejector) 或 作为从(receiver) 都算命中；
            # 分两次查再合并，避免引入额外的 Q import
            ejector_tuples = list(
                StorageInstanceTuple.objects.filter(ejector__machine__bk_host_id=self.bk_host_id).values_list(
                    "id", "ejector_id", "receiver_id"
                )
            )
            receiver_tuples = list(
                StorageInstanceTuple.objects.filter(receiver__machine__bk_host_id=self.bk_host_id).values_list(
                    "id", "ejector_id", "receiver_id"
                )
            )
            all_tuple_ids: set = set()
            tuple_hits: List[Dict[str, Any]] = []
            for tid, ej_id, rc_id in ejector_tuples + receiver_tuples:
                if tid in all_tuple_ids:
                    continue
                all_tuple_ids.add(tid)
                tuple_hits.append({"id": tid, "ejector_id": ej_id, "receiver_id": rc_id})

        except Exception as err:
            logger.warning(
                "[HostRevokeChecker][{}][{}][check_f3_dbm_residue] DB query error: {}".format(
                    self.root_id, self.ip, err
                )
            )
            return FactCheckOutcome(
                state=FactState.UNKNOWN,
                evidence={"bk_host_id": self.bk_host_id, "error": str(err)},
                error=str(err),
                reason=_("F3 元数据查询异常：{}").format(err),
            )

        evidence: Dict[str, Any] = {
            F3_EV_KEY_MACHINE: machine_hit,
            F3_EV_KEY_PROXIES: proxy_hits,
            F3_EV_KEY_STORAGES: storage_hits,
            F3_EV_KEY_TUPLES: tuple_hits,
        }
        if machine_hit is None and not proxy_hits and not storage_hits and not tuple_hits:
            return FactCheckOutcome(
                state=FactState.NO,
                evidence=evidence,
                reason=_("F3=NO：DBM 元数据无本机相关记录"),
            )
        return FactCheckOutcome(
            state=FactState.YES,
            evidence=evidence,
            reason=_("F3=YES：DBM 元数据有残留（Machine={} Proxy={} Storage={} Tuple={}）").format(
                bool(machine_hit), len(proxy_hits), len(storage_hits), len(tuple_hits)
            ),
        )

    @staticmethod
    def check_f4_process(process_check_ctx_json: Optional[Dict[str, Any]], ip: str) -> FactCheckOutcome:
        """F4 · 进程存活判据：解析上游 :class:`MySQLHostProcessCheckComponent` 输出的 ``<ctx>`` JSON。

        怎么做：
          - 复用现有 :meth:`parse_process_check_result` 的规范化逻辑
          - 映射规则：
            * parse 结果 passed=True + reason_code=OK → F4=NO（无 MySQL 家族进程 LISTEN）
            * parse 结果 passed=False + reason_code=MYSQL_STILL_ALIVE → F4=YES（有进程）
            * parse 结果 passed=False + reason_code=CHECK_ERROR → F4=UNKNOWN（脚本自身报错/结构异常）

        :param process_check_ctx_json: 上游 bamboo 节点写入 trans_data 的 <ctx> JSON dict；
            None 时表示上游节点未执行 / 失败，视为 UNKNOWN
        :param ip: 目标主机 IP，用于日志与 evidence
        :return: :class:`FactCheckOutcome`
        边界：
          - process_check_ctx_json 为 None -> state=UNKNOWN，error="ctx_json is None"
          - 其他解析异常收敛为 UNKNOWN
        """
        if process_check_ctx_json is None:
            return FactCheckOutcome(
                state=FactState.UNKNOWN,
                evidence={"ip": ip, "error": "ctx_json is None"},
                error="ctx_json is None",
                reason=_("F4=UNKNOWN：上游进程检查节点未产出 ctx JSON"),
            )

        r = HostRevokeChecker.parse_process_check_result(script_output_json=process_check_ctx_json, ip=ip)
        if r.reason_code == HostCheckReasonCode.OK:
            return FactCheckOutcome(
                state=FactState.NO,
                evidence={
                    "ip": ip,
                    "hits": r.evidence.get("hits", []),
                    "collect_tool": r.evidence.get("collect_tool"),
                },
                reason=_("F4=NO：主机无 MySQL 家族进程 LISTEN"),
            )
        if r.reason_code == HostCheckReasonCode.MYSQL_STILL_ALIVE:
            return FactCheckOutcome(
                state=FactState.YES,
                evidence={
                    "ip": ip,
                    "hits": r.evidence.get("hits", []),
                    "collect_tool": r.evidence.get("collect_tool"),
                },
                reason=_("F4=YES：主机仍有 {} 个 MySQL 家族进程 LISTEN").format(len(r.evidence.get("hits", []))),
            )
        # CHECK_ERROR 或其他兜底 → UNKNOWN
        return FactCheckOutcome(
            state=FactState.UNKNOWN,
            evidence={"ip": ip, "parse_evidence": r.evidence},
            error=r.reason,
            reason=_("F4=UNKNOWN：{}").format(r.reason),
        )

    # ---------------- 需求 7：MySQL 主机进程存活检查结果解析 ----------------

    @staticmethod
    def parse_process_check_result(
        script_output_json: Dict[str, Any],
        ip: str,
    ) -> HostCheckResult:
        """将 shell 脚本 ``<ctx>`` 中的 JSON 解析为统一的 :class:`HostCheckResult`。

        设计要点 / 怎么做：
          - **纯函数**：不查 DB、不发 RPC、不写日志（日志由调用方 Service 承担）
          - **主机维度语义**：只判断整机是否还有 MySQL 家族进程 LISTEN，
            不再基于端口列表做 alive / missing / hijacked 三态判定
          - 三分支：check_error > mysql_still_alive > ok

        :param script_output_json: 从脚本 ``<ctx>...</ctx>`` 段提取并 ``json.loads`` 得到的 dict；
            合法结构包含以下字段：
              * ``found_mysql_procs`` (bool)  是否命中 MySQL 家族进程
              * ``hits`` (list[dict])         命中详情，每项含 port/pid/proc_name
              * ``collect_tool`` (str/null)   实际使用的采集工具（ss / netstat）
              * ``error`` (str/null)          脚本自身错误信息
        :param ip: 目标主机 IP，仅用于组装 reason 便于排查
        :return: :class:`HostCheckResult`，reason_code 取值见 :class:`HostCheckReasonCode`
        边界：
          - 入参非 dict -> CHECK_ERROR，evidence.raw_output 携带原始入参
          - ``script_output_json.error`` 非空 -> CHECK_ERROR（如非 root / 无 ss & netstat）
          - 缺 ``hits`` 键 / 非 list -> CHECK_ERROR
          - ``hits`` 数组内元素结构非法（缺 port / pid / proc_name，或 port/pid 非整数）
            -> CHECK_ERROR
          - hits 非空 -> MYSQL_STILL_ALIVE（passed=False）
          - hits 为空 且 error 为空 -> OK（passed=True）
        """
        # 步骤 0：入参兜底（本方法是纯函数，即使 script_output_json 为 None 也应给出 CHECK_ERROR）
        if not isinstance(script_output_json, dict):
            return HostCheckResult(
                passed=False,
                reason_code=HostCheckReasonCode.CHECK_ERROR,
                reason=_("[{}] 脚本输出不是合法 dict：type={}").format(ip, type(script_output_json).__name__),
                evidence={"raw_output": script_output_json},
            )

        collect_tool = script_output_json.get("collect_tool")

        # 步骤 1：脚本自身报 error（如非 root / ss & netstat 均缺失）
        script_error = script_output_json.get("error")
        if script_error:
            return HostCheckResult(
                passed=False,
                reason_code=HostCheckReasonCode.CHECK_ERROR,
                reason=_("[{}] 脚本自身报错：{}").format(ip, script_error),
                evidence={
                    "raw_output": script_output_json,
                    "collect_tool": collect_tool,
                },
            )

        # 步骤 2：hits 结构合法性
        hits = script_output_json.get("hits")
        if not isinstance(hits, list):
            return HostCheckResult(
                passed=False,
                reason_code=HostCheckReasonCode.CHECK_ERROR,
                reason=_("[{}] 脚本输出结构异常：缺 hits 键或非 list").format(ip),
                evidence={"raw_output": script_output_json},
            )

        # 步骤 3：hits 数组内每一项做结构校验，规整成 List[Dict]
        normalized_hits: List[Dict[str, Any]] = []
        for idx, item in enumerate(hits):
            if not isinstance(item, dict):
                return HostCheckResult(
                    passed=False,
                    reason_code=HostCheckReasonCode.CHECK_ERROR,
                    reason=_("[{}] hits[{}] 非 dict：{!r}").format(ip, idx, item),
                    evidence={"raw_output": script_output_json},
                )
            try:
                port_val: int = int(item["port"])
                pid_val: int = int(item["pid"])
            except (KeyError, TypeError, ValueError) as err:
                return HostCheckResult(
                    passed=False,
                    reason_code=HostCheckReasonCode.CHECK_ERROR,
                    reason=_("[{}] hits[{}] 缺 port/pid 或非整数：{}").format(ip, idx, err),
                    evidence={"raw_output": script_output_json},
                )
            proc_name = item.get("proc_name")
            if not isinstance(proc_name, str) or not proc_name:
                return HostCheckResult(
                    passed=False,
                    reason_code=HostCheckReasonCode.CHECK_ERROR,
                    reason=_("[{}] hits[{}] 缺 proc_name 或非字符串：{!r}").format(ip, idx, proc_name),
                    evidence={"raw_output": script_output_json},
                )
            normalized_hits.append({"port": port_val, "pid": pid_val, "proc_name": proc_name})

        # 保持稳定顺序：按 port 升序
        normalized_hits.sort(key=lambda x: (x["port"], x["pid"], x["proc_name"]))

        # 步骤 4：三分支收敛
        if normalized_hits:
            hit_pairs = ", ".join(
                "{p}({n},pid={pid})".format(p=h["port"], n=h["proc_name"], pid=h["pid"]) for h in normalized_hits
            )
            return HostCheckResult(
                passed=False,
                reason_code=HostCheckReasonCode.MYSQL_STILL_ALIVE,
                reason=_("[{ip}] 主机仍有 {n} 个 MySQL 家族进程 LISTEN：{pairs}").format(
                    ip=ip, n=len(normalized_hits), pairs=hit_pairs
                ),
                evidence={
                    "collect_tool": collect_tool,
                    "hits": normalized_hits,
                },
            )

        # hits 为空 且 error 为空 -> OK
        return HostCheckResult(
            passed=True,
            reason_code=HostCheckReasonCode.OK,
            reason=_("[{ip}] 主机上未检测到 MySQL 家族进程 LISTEN").format(ip=ip),
            evidence={
                "collect_tool": collect_tool,
                "hits": [],
            },
        )
