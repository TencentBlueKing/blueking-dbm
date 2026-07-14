# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

SQLServer 日志备份连续性校验模块。

模块职责：
    统一封装"日志链拉取 + 完整性判定 + 错误消息渲染"三阶段能力，替代早期散落在
    handlers.py 中的 query_binlogs_from_model / check_binlog_lsn_continuity /
    pre_check_log_backup_continuity 三个叠加式函数。

设计要点 / 数据源：
    - 数据源：SQLServerBinlogResult Model（从 kafka 消费落库）
    - 状态语义：5 态枚举 LogBackupChainStatus，包含 OK / EMPTY /
      MISSING_TAIL / MISSING_HEAD / DISCONTINUOUS（异常态优先级见 D3 决策）
    - 查询语义：分"尾部段"与"头部+中间段"两段独立查询，两段在 backup_end_time
      维度上"互斥不相交且互补"，不需要在拼装阶段做去重（安全性契约）
    - 输出契约：LogBackupChainResult（frozen dataclass），backup_infos 仅在
      OK 状态下有值；非 OK 一律为空列表（D5 决策）

关键数据语义约束（务必理解，否则易改错查询逻辑）：
    - SQLServerBinlogResult 的 backup_begin_time / backup_end_time 来源于
      SQLServer `RESTORE HEADERONLY` 的 BackupStartDate / BackupFinishDate，
      语义是"BACKUP LOG 命令的执行时间"（备份动作时间），**不是**"这份 .trn
      文件覆盖的事务时间区间"
    - 事务日志备份是瞬时动作（秒级），通常 begin ≈ end（同一秒完成）
    - 一份 .trn 文件的逻辑覆盖区间由 LSN 决定：(前一份 last_lsn, 本份 last_lsn]，
      对应的物理时间近似为：(前一份 backup_end_time, 本份 backup_end_time]
    - backup_end_time（BACKUP LOG 命令完成时刻）始终 >= 该份最后一条事务的提交时刻；
      若某份 end_time == restore_time，其 last_lsn 对应的事务时刻必然 < restore_time，
      以它为 tail 执行 STOPAT 会"滚不满"而残留 restoring 态（见 _query_tail_segment 说明）
    - 因此"覆盖 restore_time 的尾部备份" = **首个 backup_end_time > restore_time
      的记录**（LSN 视角下目标 target_lsn 落在该份的 (prev_last_lsn, last_lsn] 区间内，
      STOPAT 可在该份内部精确截停）
    - boundary 说明：restore_time == 某份 backup_end_time（恰好等于最新备份完成点）属
      非法构造时点，按 MISSING_TAIL 处理，要求用户选更早的回档时间点
    - 业务层无需做"时间 -> LSN"转换：SQLServer 恢复时通过 `RESTORE LOG ... WITH
      STOPAT` 自身按 LSN 精确停在 restore_time

上下游边界：
    - 上游：SQLServerRollbackHandler（暴露薄入口方法 fetch_and_check_log_backup_chain
      与 check_log_backup_chain_batch）
    - 下游：flow 场景 sqlserver_db_construct._get_log_backup_infos（按 status 分支使用）
      与 validator SqlserverDBConstructValidator.pre_check_log_backup_continuity
      （聚合非 OK 的 error_message 为字符串返回）
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from django.utils.translation import gettext as _

from backend.db_report.models.sqlserver_log_backup_result import SQLServerBinlogResult
from backend.utils.time import datetime2str, str2datetime

# ---------------------------------------------------------------------------
# 缺口分型常量：内部结构化缺口 dict 的 type 字段取值集合
# ---------------------------------------------------------------------------
# GAP_TYPE_MISSING_FIRST：全量末尾 LSN 未落入首份日志 [first_lsn, last_lsn]，即"首份日志缺失"
# GAP_TYPE_MISSING_MIDDLE：日志备份内部 prev.last_lsn != cur.first_lsn，即"中间日志缺失"
# GAP_TYPE_MISSING_TAIL：日志链未覆盖到 restore_time，即"末份日志缺失"
GAP_TYPE_MISSING_FIRST: str = "missing_first"
GAP_TYPE_MISSING_MIDDLE: str = "missing_middle"
GAP_TYPE_MISSING_TAIL: str = "missing_tail"


def _build_gap(
    gap_type: str,
    prev_file: str,
    prev_last_lsn: Any,
    next_file: str,
    next_first_lsn: Any,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """构造统一结构的日志备份缺口 dict，供 3 种分型判定共享同一数据形态。

    设计要点 / 怎么做：
      - 3 种分型（missing_first / missing_middle / missing_tail）共用同一结构，
        便于渲染函数按 type 分组统计与展示，也便于单元测试通过 type 直接断言
      - extra 用于承载分型特有字段，如末份分型的 restore_time / backup_end_time
      - 不做 LSN 类型收敛（允许 str 或 int），交由上层展示 & 比较逻辑处理

    :param gap_type: 分型标识，取值为 GAP_TYPE_MISSING_FIRST / _MIDDLE / _TAIL 之一
    :param prev_file: 前一份文件名（首份分型为全量文件名，末份分型可为占位符或空串）
    :param prev_last_lsn: 前一段末尾 LSN（首份分型为全量 last_lsn）
    :param next_file: 后一份文件名（末份分型可为空串）
    :param next_first_lsn: 后一段起始 LSN（末份分型可为空串）
    :param extra: 分型特有信息 dict，缺省 None 时置空 dict
    :return: 统一结构的缺口 dict，字段 type / prev_file / prev_last_lsn / next_file / next_first_lsn / extra

    边界 / 异常：
      - gap_type 不在分型枚举内 -> 不做校验，由上层渲染时按 type 分派
      - extra 为 None -> 内部转换为 {}，避免调用方防御性判空
    """
    return {
        "type": gap_type,
        "prev_file": prev_file,
        "prev_last_lsn": prev_last_lsn,
        "next_file": next_file,
        "next_first_lsn": next_first_lsn,
        "extra": extra or {},
    }


# ---------------------------------------------------------------------------
# 6 态校验结果枚举 + 结构化返回值 dataclass
# ---------------------------------------------------------------------------


class LogBackupChainStatus:
    """SQLServer 日志备份链完整性校验的 5 态状态码。

    设计说明：
      - 不用 Django `TextChoices` 是为了让本模块零 Django ORM 强依赖（除已引入的 Model），
        并让纯单元测试可无 django.setup() 环境断言枚举成员
      - 异常态优先级（D3 决策）：EMPTY > MISSING_TAIL > MISSING_HEAD > DISCONTINUOUS

    使用方式：
        result.status == LogBackupChainStatus.OK
        LogBackupChainStatus.is_valid(status)

    边界：
      - 未来若新增状态，需同步更新 `_ALL` 与优先级判定，避免遗漏
    """

    #: 无异常，日志链完整且连续
    OK: str = "ok"
    #: 查询到的日志列表为空（尾部段与头部+中间段均为空）
    EMPTY: str = "empty"
    #: 缺少尾部日志：没有任何一份日志的 backup_end_time >= restore_time
    MISSING_TAIL: str = "missing_tail"
    #: 缺少头部日志：全量末尾 LSN 未落入首份日志的 [first_lsn, last_lsn] 区间
    MISSING_HEAD: str = "missing_head"
    #: 日志链路不连续：相邻两份日志的 last_lsn 与 first_lsn 不衔接
    DISCONTINUOUS: str = "discontinuous"

    #: 所有合法状态值（供入参校验 / 遍历使用）
    _ALL: Tuple[str, ...] = (OK, EMPTY, MISSING_TAIL, MISSING_HEAD, DISCONTINUOUS)

    @classmethod
    def is_valid(cls, status: str) -> bool:
        """判定状态值是否合法。

        :param status: 待校验的状态值
        :return: True 表示合法（属于 5 态之一），False 表示非法
        """
        return status in cls._ALL


@dataclass(frozen=True)
class LogBackupChainResult:
    """SQLServer 日志备份链校验的结构化结果。

    职责：
      - 承载"状态 + 完整日志链 + 错误消息 + 结构化缺口明细"四类信息，供调用方按需消费
      - 采用 frozen dataclass，避免调用方误改状态字段导致语义漂移

    字段说明：
      - status：`LogBackupChainStatus` 6 态之一
      - db_name：本次校验对应的业务库名（便于批量调用时上下文回溯）
      - backup_infos：完整日志链，**仅在 status == OK 时有值**；其他态一律为 []（D5 决策）
      - error_message：业务化中文错误消息（仅在异常态下非空）
      - gaps：结构化缺口明细（仅在链路不连续 / 缺首份 / 缺尾份 / 尾份异常时有值），
        每项由 `_build_gap` 构造

    使用方式：
        result = handler.fetch_and_check_log_backup_chain(full_info, restore_time)
        if result.status == LogBackupChainStatus.OK:
            use(result.backup_infos)
        else:
            report(result.error_message)

    边界：
      - `frozen=True` 意味着不能直接修改字段；如需变更须新建实例
      - `backup_infos` 与 `gaps` 使用 `default_factory=list` 避免可变默认值陷阱
    """

    status: str
    db_name: str = ""
    backup_infos: List[Dict[str, Any]] = field(default_factory=list)
    error_message: str = ""
    gaps: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 核心校验类：LogBackupChainInspector
# ---------------------------------------------------------------------------

# datetime 字段清单：查询 Model 的 raw dict 需要把这些字段序列化为字符串，避免 JSON 序列化失败
# 保留这份常量而非散落在各方法内，便于未来 Model 新增时间字段时集中维护
_DATETIME_FIELDS: Tuple[str, ...] = (
    "created_at",
    "updated_at",
    "backup_task_start_time",
    "backup_task_end_time",
    "backup_begin_time",
    "backup_end_time",
)


class LogBackupChainInspector:
    """SQLServer 日志备份链校验器（单 DB 单入口）。

    职责：
      按需求 3~4 拆分为"尾部段查询 + 判定"与"头部+中间段查询 + LSN 判定"两阶段，
      再由 `inspect()` 主编排产出 6 态之一的 `LogBackupChainResult`。

    职责边界：
      - 本类只做"数据查询 + 完整性判定 + 错误渲染"，不做重试、不做副作用
      - 参数校验只在 `__init__` 做一次"必需字段存在性"轻量校验；LSN 类型不收敛，
        由内部字符串化比较兜底（SQLServer LSN 上报路径为 msdb.backupset 的
        numeric(25,0)，CAST 得到变长十进制纯数字字符串；相等比较用字符串安全，
        大小比较必须走 `_lsn_to_int` 数值化，见该方法说明）

    线程安全：
      非线程安全（含惰性缓存的临时状态）；单次调用生命周期内使用，勿跨请求复用实例

    使用方式：
        inspector = LogBackupChainInspector(cluster, full_info, restore_time)
        result: LogBackupChainResult = inspector.inspect()
    """

    def __init__(
        self,
        cluster: Any,
        full_backup_info: Dict[str, Any],
        restore_time: datetime,
    ) -> None:
        """初始化并做输入合法性轻量校验（禁止在此处做 IO / DB 调用）。

        :param cluster: db_meta.Cluster 实例，需含 id / immute_domain 字段
        :param full_backup_info: 全量备份信息 dict，全部为必需字段：
            - db_name：业务库名
            - backup_full_end_time：全量备份结束时间（str）
            - cluster_address：集群地址（错误消息展示用）
            - full_last_lsn：全量末尾 LSN（首份日志衔接判定的唯一依据）
            - full_file_name：全量备份文件名（错误消息定位来源）
            以上任一缺失均视为上游装配层异常，采用 fail-fast 策略直接抛错
        :param restore_time: 目标构造时点（datetime，可带 tzinfo）
        :return: None

        边界 / 异常：
          - full_backup_info 缺失任一必需字段 -> raise ValueError（非 6 态之内的输入错误）
          - restore_time 为 None -> raise ValueError
        """
        if restore_time is None:
            raise ValueError("restore_time is required")

        # 全部字段为必需字段：任一缺失即视为上游装配层 bug，fail-fast 抛错
        # 特别是 full_last_lsn / full_file_name：是首份 LSN 判定与错误定位的核心依据，
        # 缺失后即使能"跑通"也会误导 DBA 排查方向（"首份日志缺失" vs "全量记录异常"是两回事）
        required_fields: Tuple[str, ...] = (
            "db_name",
            "backup_full_end_time",
            "cluster_address",
            "full_last_lsn",
            "full_file_name",
        )
        missing = [f for f in required_fields if not full_backup_info.get(f)]
        if missing:
            raise ValueError("full_backup_info missing required fields: {fields}".format(fields=",".join(missing)))

        self.cluster: Any = cluster
        self.restore_time: datetime = restore_time

        # 从 full_backup_info 展开常用字段，减少后续方法多次 get 的噪声
        self.db_name: str = full_backup_info["db_name"]
        self.cluster_address: str = full_backup_info["cluster_address"]
        # full_last_lsn / full_file_name：SQLServer 定点回档强依赖字段；
        # 上游装配层必须下发，缺失已在 required_fields 校验中拦截
        self.full_last_lsn: str = str(full_backup_info["full_last_lsn"])
        self.full_file_name: str = full_backup_info["full_file_name"]
        # 顺带对 full_last_lsn 做一次严格数值校验：LSN 必须是纯十进制数字串
        # （见 _lsn_to_int 说明）。fail-fast 抛错，避免拖到判定阶段才因脏数据误判
        try:
            self._lsn_to_int(self.full_last_lsn)
        except ValueError as exc:
            raise ValueError(
                "full_backup_info.full_last_lsn is not a valid LSN (file_name={file_name}): {reason}".format(
                    file_name=self.full_file_name,
                    reason=str(exc),
                )
            )
        # 全量结束时间：同时保留 datetime（供 SQL 查询）与 str（供错误消息展示）两种形态
        self.full_end_time_str: str = full_backup_info["backup_full_end_time"]
        self.full_end_time: datetime = str2datetime(self.full_end_time_str)

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_backup_log(log: Dict[str, Any]) -> Dict[str, Any]:
        """将备份记录中的 datetime 字段统一转为字符串，避免下游 JSON 序列化失败。

        :param log: 备份记录 dict（Model.values() 结果）
        :return: 序列化后的新 dict（不修改入参）

        边界：
          - log 中缺失 datetime 字段 -> 跳过；空值 -> 跳过
        """
        serialized: Dict[str, Any] = log.copy()
        for f_name in _DATETIME_FIELDS:
            if f_name in serialized and serialized[f_name]:
                serialized[f_name] = datetime2str(serialized[f_name])
        return serialized

    @staticmethod
    def _lsn_to_int(lsn: Any) -> int:
        """将 SQLServer 备份 LSN 字符串转换为整数，用于数值大小比较。

        设计要点 / 怎么做：
          - 数据形态：LSN 来源于 SQLServer 系统表 `msdb.dbo.backupset.first_lsn /
            last_lsn`（类型 numeric(25,0)），上报侧走
            `CAST(bs.first_lsn AS VARCHAR(30))` 落库到
            `SQLServerBinlogResult.first_lsn / last_lsn`（CharField(30)），
            实际形态为**变长十进制纯数字字符串**（无冒号、无前导零填充）
          - 变长十进制字符串的字典序与数值序**不一致**（如 "9999999999" > "10000000000"
            为字典序 True，但数值上 9999999999 < 10000000000），因此凡涉及 `>` / `<`
            的 LSN 判定，必须先经本方法转成 int 再比较；相等比较（`==`）不受影响
          - 用 Python `int` 而非 `Decimal`：backupset LSN 定义为整数（numeric 25,0，
            小数位=0），int 语义精确且 Python int 为任意精度，25 位十进制远小于 2^128
          - **fail-fast 策略**：非法输入直接抛 `ValueError`，**不做静默兜底 0**。
            早期实现曾用"异常返回 0"策略，但会引入漏报隐患：
              例：first_first_lsn 是脏数据（返回 0）、first_last_lsn 正常，此时
              `0 > full_last_lsn_int` 恒 False、`first_last_lsn_int < full_last_lsn_int`
              视情况，若 `full_last_lsn` 恰好落入 [0, first_last_lsn] 区间即误判为"链路完整"，
              让真实的首份数据异常悄悄放行
            抛错后由上层（`_collect_head_and_middle_gaps` / `_head_check_by_tail` /
            `__init__`）用 try/except 包裹并补上 file_name / backup_id 上下文，
            与 `_require_backup_id` / tail_log 缺 first_lsn 等"数据上报异常"处理风格一致

        :param lsn: LSN 值，允许 str / int 入参
        :return: 转换后的整数

        边界 / 异常：
          - lsn 为 None / "" / 纯空白串 -> raise ValueError（视为上报数据缺失）
          - lsn 为非纯数字字符串（含冒号 hex、字母、负号等）-> raise ValueError
          - lsn 为负整数 -> raise ValueError（SQLServer LSN 语义上非负）
          - lsn 为 int（含 0，如 __init__ 阶段的占位）-> 直接返回；调用方若要
            禁止 0 需自行判定（本方法不做业务语义校验）
        """
        if lsn is None:
            raise ValueError("lsn is None")
        if isinstance(lsn, int):
            if lsn < 0:
                raise ValueError("lsn is negative int: {lsn}".format(lsn=lsn))
            return lsn
        text: str = str(lsn).strip()
        if not text:
            raise ValueError("lsn is empty string")
        try:
            value: int = int(text)
        except (TypeError, ValueError):
            raise ValueError("lsn is not a decimal integer: {lsn!r}".format(lsn=text))
        if value < 0:
            raise ValueError("lsn is negative: {lsn!r}".format(lsn=text))
        return value

    # ------------------------------------------------------------------
    # 阶段 1：尾部段查询 + 分类
    # ------------------------------------------------------------------

    def _query_tail_segment(self) -> Optional[Dict[str, Any]]:
        """查询"覆盖 restore_time"的尾部日志段：首个 backup_end_time > restore_time 的记录。

        SQL 条件（对应需求 3.1，方案 A 单条查询）：
          - cluster_id = self.cluster.id
          - dbname = self.db_name
          - backup_end_time > restore_time
          - 按 backup_end_time 升序取 first；未命中即视为 MISSING_TAIL

        数据语义（务必理解，参见模块级 docstring 的"关键数据语义约束"）：
          - backup_begin_time / backup_end_time 是"BACKUP LOG 命令的执行时间"，
            非"日志覆盖的事务时间区间"（begin ≈ end，同一秒瞬时点）
          - 一份 .trn 的逻辑覆盖区间由 LSN 决定：(前一份 last_lsn, 本份 last_lsn]，
            物理时间近似 (前一份 backup_end_time, 本份 backup_end_time]
          - backup_end_time 始终 >= 该份内最晚事务提交时刻；若某份 end_time == restore_time，
            其 last_lsn 对应的事务时刻必然 < restore_time
          - 因此 tail 必须选"首个 backup_end_time > restore_time"：该份的 LSN 区间
            (prev_last_lsn, last_lsn] 一定跨越 restore_time（前一份 last_lsn 对应 <= restore_time，
            本份完成于 > restore_time），下游 `RESTORE LOG ... WITH STOPAT=restore_time`
            能在**该份内部精确截停**在 restore_time，正常 RECOVERY 收尾
          - 若误选"end_time == restore_time"的那份当 tail：STOPAT 会"滚不满"
            （最晚事务 < restore_time），SQLServer 报 "left in the restoring state so that
            more roll forward can be performed" 而残留 restoring 态，无法收尾
          - 业务层无需做"时间 -> LSN"转换：STOPAT 内部按 LSN 精确停在 restore_time

        与 _query_head_middle_segment 的互斥不相交契约：
          - head_middle 段条件：backup_end_time <= restore_time
          - tail 段条件：      backup_end_time > restore_time
          - 边界 backup_end_time == restore_time 的记录归 head_middle 段（作为普通中间日志
            NORECOVERY 前滚），不归 tail 段；两段在 backup_end_time 维度上互斥不相交，
            因此 inspect() 拼装 backup_infos 时直接拼接、**无需去重**
            （若破坏此契约会导致 LSN 校验时自比误判 middle 缺失）

        主从多副本上报说明：
          - 同一次 BACKUP LOG 可能被主/从库各上报一次：backup_id 相同、backup_end_time 相同、
            host 不同 -> `.first()` 任取一条即可（LSN 相同，语义等价）
          - SQLServer 单库同一时刻通常只有一个 BACKUP LOG 命令在跑，
            "同时刻多份不同 backup_id" 数据物理上不会自然发生；若真发生，
            也不影响下游 RESTORE LOG WITH STOPAT 的恢复正确性（LSN 校验兜底）

        :return: 序列化后的单条 tail_log dict；未命中返回 None

        边界 / 异常：
          - 查询命中数为 0（restore_time 晚于最新备份的 backup_end_time，
            或 restore_time 恰好等于最新备份的 backup_end_time）-> 返回 None
            （后者属非法构造时点，由 inspect 层归为 MISSING_TAIL）
          - 命中记录缺失 backup_id -> raise ValueError（数据上报异常，fail-fast 便于排查）
        """
        # 单次查询：找"首个 backup_end_time > restore_time"的记录
        # 注：严格大于（非 >=），避免选中 end_time 恰好等于 restore_time 的那份
        # （其 last_lsn 对应事务时刻 < restore_time，选它当 tail 会导致 STOPAT 滚不满、残留 restoring 态）
        row = (
            SQLServerBinlogResult.objects.filter(
                cluster_id=self.cluster.id,
                dbname=self.db_name,
                backup_end_time__gt=self.restore_time,
            )
            .order_by("backup_end_time")
            .values()
            .first()
        )
        if row is None:
            return None

        # 强校验 backup_id 非空（数据上报侧应保证），并序列化 datetime 字段
        self._require_backup_id(row)
        return self._serialize_backup_log(row)

    # ------------------------------------------------------------------
    # 阶段 2：头部 + 中间段查询 + LSN 判定
    # ------------------------------------------------------------------

    def _query_head_middle_segment(self) -> List[Dict[str, Any]]:
        """查询"全量结束到 restore_time"之间的日志段（首份 + 中间，含 end_time == restore_time 的那份）。

        SQL 条件（对应需求 3.2）：
          - cluster_id = self.cluster.id
          - dbname = self.db_name
          - backup_end_time >= full_backup_info.backup_full_end_time
          - backup_end_time <= restore_time
          - 按 backup_id 去重，任意保留首见的一条（与 handlers.query_binlogs 语义一致；
            同一次备份批次的多副本上报视为等价重复）
          - 按 backup_end_time 升序返回

        与 _query_tail_segment 的互斥不相交契约：
          - head_middle 段条件：backup_end_time <= restore_time （**含边界**）
          - tail 段条件：      backup_end_time > restore_time  （**严格大于**）
          - 边界 backup_end_time == restore_time 的记录归 head_middle 段（作为普通中间日志
            NORECOVERY 前滚铺路到 tail 段），本方法**会**包含它，tail 段**不会**包含它
          - 两段在 backup_end_time 维度上互斥不相交，inspect() 拼装时无需去重

        :return: 去重且已序列化 datetime 的记录列表；按 backup_end_time 升序

        边界 / 异常：
          - 查询命中数为 0 -> 返回 []
          - 命中记录缺失 backup_id -> raise ValueError（数据上报异常，fail-fast 便于排查）
        """
        qs = SQLServerBinlogResult.objects.filter(
            cluster_id=self.cluster.id,
            dbname=self.db_name,
            backup_end_time__gte=self.full_end_time,
            backup_end_time__lte=self.restore_time,
        ).order_by("backup_end_time")

        # 按 backup_id 去重：项目内 handlers.query_binlogs 的现有语义先例
        seen_backup_ids: Set[str] = set()
        result: List[Dict[str, Any]] = []
        for row in qs.values():
            backup_id: str = self._require_backup_id(row)
            if backup_id in seen_backup_ids:
                continue
            seen_backup_ids.add(backup_id)
            result.append(self._serialize_backup_log(row))

        return result

    @staticmethod
    def _require_backup_id(row: Dict[str, Any]) -> str:
        """强校验 SQLServerBinlogResult 行数据的 backup_id 字段，缺失/为空即抛错。

        设计要点：
          - 上报侧应保证每条日志备份记录都携带非空 backup_id；缺失属于数据异常，
            应显式暴露而非静默兜底成 ""（后者会污染去重逻辑，导致悄悄丢弃中间日志）
          - 抛错时携带记录定位信息（id），
            便于 DBA 直接从 tb_sqlserver_binlog_result 表回查异常行

        :param row: `SQLServerBinlogResult.objects.values()` 返回的单行 dict
        :return: 非空的 backup_id 字符串

        边界 / 异常：
          - backup_id 缺失（key 不存在）/ 值为 None / 值为空串 -> raise ValueError
        """
        backup_id = row.get("backup_id")
        if not backup_id:
            raise ValueError(f"SQLServerBinlogResult record missing backup_id : id={row.get('id')}")
        return str(backup_id)

    def _collect_head_and_middle_gaps(self, head_middle_logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """在头部+中间段内做"首份 LSN + 中间 LSN 连续性"判定，产出结构化缺口。

        判定两阶段（对应需求 3.5 / 3.6）：
          - 阶段 A（首份 missing_first）：从 full_backup_info 读取 full_last_lsn，
            判定"全量末尾 LSN 是否落入首份日志 [first_lsn, last_lsn]"
          - 阶段 B（中间 missing_middle）：基于真实时间序（backup_end_time 升序，
            即 `_query_head_middle_segment` 返回的原始顺序）做"上一份 last_lsn ==
            下一份 first_lsn"两两滑窗比对，全部断档一次性聚合返回

        关键约束（务必理解，否则易改出漏报/误报）：
          - 本方法**严禁**对 head_middle_logs 按 last_lsn 重排序。SQLServer 备份
            LSN 上报路径为 msdb.backupset 的 numeric(25,0)，落库为**变长十进制
            纯数字字符串**（如 "34000000010000123"，无冒号、无前导零填充）；
            其字符串字典序与数值序不严格一致（跨十进制位数边界即翻车），因此：
              (1) 严禁按 last_lsn 字符串重排序：会同时引发漏报（真时序断档被排到
                  非相邻位置，滑窗从未比到）与误报（时序连续但被排到相邻的两份
                  LSN 不衔接，假阳性 missing_middle）
              (2) 阶段 A 的大小比较（`>` / `<`）必须走 `_lsn_to_int` 数值化，不能
                  用字符串字典序；阶段 B 的相等比较（`==`）用字符串安全，保留原状
          - head_middle_logs 由 _query_head_middle_segment 按 backup_end_time 升序返回，
            该顺序即真实备份时序；滑窗必须沿用此序，相邻即时序相邻
          - 调用后本方法**不修改** head_middle_logs 的顺序（保持 backup_end_time 升序），
            以满足 inspect() 拼装 backup_infos 与 _collect_tail_join_gap 取
            head_middle_logs[-1] 作为"时间序最后一份"的契约

        :param head_middle_logs: `_query_head_middle_segment` 返回的、按 backup_end_time
            升序的记录列表；本方法不对其重排序
        :return: 结构化缺口列表（可能包含 missing_first 与 missing_middle 混合项）

        边界 / 异常：
          - head_middle_logs 为空 -> 返回 []（由 inspect 层处理 EMPTY / D4 分支）
          - 单条日志 -> 仅做首份判定；无中间比对空间
          - full_last_lsn 由 __init__ 保证非空，本方法无需再做防御性判空
        """
        gaps: List[Dict[str, Any]] = []
        if not head_middle_logs:
            return gaps

        # 阶段 A：首份 LSN 判定（取时间序第一份，即 head_middle_logs[0]）
        # head_middle_logs 已由 _query_head_middle_segment 按 backup_end_time 升序返回，
        # 严禁对其按 last_lsn 重排序（变长十进制字符串字典序 ≠ 数值序，会漏报/误报真实断档）
        # full_last_lsn 在 __init__ 阶段已强制非空且格式合法
        first_log = head_middle_logs[0]
        first_first_lsn: str = str(first_log["first_lsn"])
        first_last_lsn: str = str(first_log["last_lsn"])

        # 断档判定：首份日志起点晚于全量末尾 或 首份日志末尾早于全量末尾
        # 注意：LSN 是变长十进制数字串，必须走 _lsn_to_int 做数值比较；
        # 直接字符串 `>` / `<` 在跨十进制位数边界时会误判（如 "9999999999" > "10000000000" 字典序为 True）
        # 若首份 LSN 字段异常（缺失 / 非纯数字），fail-fast 抛 ValueError，携带 file_name / backup_id
        # 便于 DBA 回查 SQLServerBinlogResult 脏行，避免"静默兜底"漏报真实断档
        try:
            first_first_lsn_int: int = self._lsn_to_int(first_first_lsn)
            first_last_lsn_int: int = self._lsn_to_int(first_last_lsn)
        except ValueError as exc:
            raise ValueError(
                "head_middle first_log has invalid LSN "
                "(backup_id={backup_id}, file_name={file_name}, first_lsn={first_lsn!r}, "
                "last_lsn={last_lsn!r}): {reason}".format(
                    backup_id=first_log.get("backup_id", ""),
                    file_name=first_log.get("file_name", ""),
                    first_lsn=first_first_lsn,
                    last_lsn=first_last_lsn,
                    reason=str(exc),
                )
            )
        full_last_lsn_int: int = self._lsn_to_int(self.full_last_lsn)
        if first_first_lsn_int > full_last_lsn_int or first_last_lsn_int < full_last_lsn_int:
            gaps.append(
                _build_gap(
                    gap_type=GAP_TYPE_MISSING_FIRST,
                    prev_file=self.full_file_name,
                    prev_last_lsn=self.full_last_lsn,
                    next_file=first_log["file_name"],
                    next_first_lsn=first_log["first_lsn"],
                )
            )

        # 阶段 B：中间 LSN 两两滑窗比对（沿用 backup_end_time 升序原序，不做重排）
        # 设计说明：
        #   - 以 head_middle_logs[0] 作为滑窗起点，从第二份开始比对，避免引入"哨兵值"
        #     早期实现用 `prev_last_lsn: Any = 0` 做首轮判定哨兵，存在两类问题：
        #       (1) 类型不一致：哨兵是 int、后续赋值为 str（CharField 落库），全程走 Any 逃避类型系统
        #       (2) 哨兵值语义碰撞：若上报数据真出现 last_lsn == "0" 的异常行（数值 0 在 LSN 域内
        #           虽罕见但并非绝对不可能），该行会被静默"跳过 continue"、不参与比较，
        #           与本模块"fail-fast、绝不静默兜底"原则冲突
        #   - 用 `[1:]` 切片跳过首份即可自然表达"从第二份开始滑窗"，无需哨兵；
        #     单条日志时切片为空、循环不执行，与"无中间比对空间"的语义一致
        #   - 显式 str() 收敛与阶段 A 保持一致；相等比较用字符串安全
        #     （同数值的十进制字符串表示唯一，`==` 语义等价于数值 `==`，且不引入 int 转换的 ValueError 风险）
        prev_last_lsn: str = str(head_middle_logs[0]["last_lsn"])
        prev_file_name: str = str(head_middle_logs[0]["file_name"])
        for log in head_middle_logs[1:]:
            cur_first_lsn: str = str(log["first_lsn"])
            cur_last_lsn: str = str(log["last_lsn"])
            cur_file_name: str = str(log["file_name"])

            if prev_last_lsn == cur_first_lsn:
                prev_last_lsn = cur_last_lsn
                prev_file_name = cur_file_name
                continue

            gaps.append(
                _build_gap(
                    gap_type=GAP_TYPE_MISSING_MIDDLE,
                    prev_file=prev_file_name,
                    prev_last_lsn=prev_last_lsn,
                    next_file=cur_file_name,
                    next_first_lsn=cur_first_lsn,
                )
            )
            # 断档后继续沿当前份推进，尽量把所有缺口一次性发现
            prev_last_lsn = cur_last_lsn
            prev_file_name = cur_file_name

        return gaps

    def _collect_tail_join_gap(
        self,
        head_middle_logs: List[Dict[str, Any]],
        tail_log: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """校验"head_middle 段最后一份"与"tail 段"之间的 LSN 衔接是否连续。

        设计要点 / 怎么做：
          - 单独一个方法专司跨段衔接判定，避免与 _collect_head_and_middle_gaps 的
            "段内滑窗"职责混淆；也便于 inspect() 主编排在阶段 5 之后统一合入 head_gaps
          - 衔接判定与段内一致：head_middle_logs[-1].last_lsn == tail_log.first_lsn
            相等即视为衔接，不等即视为中间断档，输出 GAP_TYPE_MISSING_MIDDLE 分型
            （从业务视角看，这个缺口本质是"某段中间日志丢失"，与段内 missing_middle 同源）
          - LSN 用字符串精确相等比较：SQLServer 备份 LSN 落库为变长十进制纯数字字符串，
            同一数值的字符串表示唯一，`==` 判定安全；此处**不做**大小比较，无需数值化

        为什么需要独立一步（历史教训）：
          - inspect() 曾经只对 head_middle 段内部滑窗，且直接把 tail_log append 到
            backup_infos，未校验跨段衔接；导致 head_middle[-1].last_lsn 与 tail.first_lsn
            之间的真实断档从未被拦截，validator 提交时判 OK，flow 执行期 RESTORE LOG 才爆
          - 本方法即为该缺口的直接补丁，务必保留

        :param head_middle_logs: 头部+中间段列表（backup_end_time 升序，非空）
        :param tail_log: 尾部段单条日志 dict（非 None）
        :return: 缺口列表；衔接正常返回 []，衔接不上返回 [missing_middle gap]（长度必为 0 或 1）

        边界 / 异常：
          - head_middle_logs 为空 -> 返回 []（跨段校验无意义，D4 分支由 _head_check_by_tail 兜底）
          - tail_log 为 None -> 返回 []（MISSING_TAIL 已由主编排提前拦截）
          - head_middle_logs[-1] 缺失 last_lsn / tail_log 缺失 first_lsn -> 视为衔接不上
            并返回 gap（不额外抛错，与段内容错策略保持一致）
        """
        if not head_middle_logs or tail_log is None:
            return []

        last_head_middle_log = head_middle_logs[-1]
        prev_last_lsn: str = str(last_head_middle_log.get("last_lsn", ""))
        next_first_lsn: str = str(tail_log.get("first_lsn", ""))

        if prev_last_lsn and next_first_lsn and prev_last_lsn == next_first_lsn:
            return []

        return [
            _build_gap(
                gap_type=GAP_TYPE_MISSING_MIDDLE,
                prev_file=last_head_middle_log.get("file_name", ""),
                prev_last_lsn=prev_last_lsn,
                next_file=tail_log.get("file_name", ""),
                next_first_lsn=next_first_lsn,
            )
        ]

    def _head_check_by_tail(self, tail_log: Dict[str, Any]) -> List[Dict[str, Any]]:
        """D4 特殊分支：头部+中间段为空、尾部段合法时，用尾部段做首份 LSN 判定。

        判定规则（对应需求 3.4 / D4 决策）：
          - full_last_lsn ∈ [tail.first_lsn, tail.last_lsn] -> 视为 OK，返回 []
          - 未落入 -> 返回 [missing_first gap]

        :param tail_log: `_query_tail_segment` 返回的唯一尾部日志 dict
        :return: 缺口列表（长度 0 或 1）

        边界 / 异常：
          - full_last_lsn 由 __init__ 保证非空，无需防御性判空
          - tail_log 缺失 first_lsn/last_lsn -> raise ValueError（Model 数据异常，fail-fast）
        """
        tail_first_lsn: str = str(tail_log.get("first_lsn", ""))
        tail_last_lsn: str = str(tail_log.get("last_lsn", ""))

        # 尾部日志的 first_lsn / last_lsn 缺失属于 SQLServerBinlogResult 上报数据异常，
        # 直接抛错让 DBA / 开发者显式感知（而非兜底返回 missing_first 误导排查方向）
        if not tail_first_lsn or not tail_last_lsn:
            raise ValueError(
                "tail_log missing first_lsn/last_lsn (backup_id={backup_id}, file_name={file_name})".format(
                    backup_id=tail_log.get("backup_id", ""),
                    file_name=tail_log.get("file_name", ""),
                )
            )

        # 区间判定：full_last_lsn 是否落入 [tail.first_lsn, tail.last_lsn]
        # LSN 为变长十进制数字串，必须走 _lsn_to_int 数值比较（见 _lsn_to_int / 阶段 A 说明）
        # 若 tail LSN 字段格式非法（非纯数字），fail-fast 抛错并携带上下文
        try:
            tail_first_lsn_int: int = self._lsn_to_int(tail_first_lsn)
            tail_last_lsn_int: int = self._lsn_to_int(tail_last_lsn)
        except ValueError as exc:
            raise ValueError(
                "tail_log has invalid LSN "
                "(backup_id={backup_id}, file_name={file_name}, first_lsn={first_lsn!r}, "
                "last_lsn={last_lsn!r}): {reason}".format(
                    backup_id=tail_log.get("backup_id", ""),
                    file_name=tail_log.get("file_name", ""),
                    first_lsn=tail_first_lsn,
                    last_lsn=tail_last_lsn,
                    reason=str(exc),
                )
            )
        full_last_lsn_int: int = self._lsn_to_int(self.full_last_lsn)
        if tail_first_lsn_int > full_last_lsn_int or tail_last_lsn_int < full_last_lsn_int:
            return [
                _build_gap(
                    gap_type=GAP_TYPE_MISSING_FIRST,
                    prev_file=self.full_file_name,
                    prev_last_lsn=self.full_last_lsn,
                    next_file=tail_log.get("file_name", ""),
                    next_first_lsn=tail_first_lsn,
                )
            ]

        return []

    # ------------------------------------------------------------------
    # 主编排 + 错误消息渲染
    # ------------------------------------------------------------------

    def inspect(self) -> LogBackupChainResult:
        """主入口：按状态优先级顺序判定 5 态之一，产出结构化结果。

        状态优先级（对应 D3 决策）：
          EMPTY > MISSING_TAIL > MISSING_HEAD > DISCONTINUOUS > OK

        执行流程：
          1. 查询尾部段（`_query_tail_segment`）；None -> 尾部缺失
          2. 查询头部+中间段（`_query_head_middle_segment`）
          3. 双段均空 -> EMPTY
          4. 尾部段缺失 -> MISSING_TAIL
          5. 头部+中间段非空 -> 调用 `_collect_head_and_middle_gaps` 收集段内缺口；
             5.1 再调用 `_collect_tail_join_gap` 校验"head_middle 最后一份"与
                 "tail 段"的 LSN 衔接（跨段衔接漏检是历史踩坑，务必保留此步）
             按缺口分型映射为 MISSING_HEAD / DISCONTINUOUS
          6. 头部+中间段为空、尾部段合法 -> 走 D4 特殊分支 `_head_check_by_tail`
          7. 全通过 -> OK；`backup_infos` = 头部+中间段 + 尾部段（按 backup_end_time 升序）

        :return: `LogBackupChainResult` 实例；status 必为 5 态之一

        边界 / 异常：
          - 非 OK 一律返回 `backup_infos=[]`（D5 决策）
          - OK 时 `error_message="" / gaps=[]`
        """
        # 阶段 1：尾部段查询
        tail_log: Optional[Dict[str, Any]] = self._query_tail_segment()

        # 阶段 2：头部 + 中间段查询
        head_middle_logs: List[Dict[str, Any]] = self._query_head_middle_segment()

        # 3. 双段均空 -> EMPTY
        if tail_log is None and not head_middle_logs:
            return self._make_result(
                status=LogBackupChainStatus.EMPTY,
                gaps=[],
            )

        # 4. 尾部段缺失 -> MISSING_TAIL（此时头部+中间段可能非空，但仍以尾部为准）
        if tail_log is None:
            # 从头部+中间段末尾取代表信息用于错误消息展示（若为空则用占位符）
            last_log: Dict[str, Any] = head_middle_logs[-1] if head_middle_logs else {}
            gap = _build_gap(
                gap_type=GAP_TYPE_MISSING_TAIL,
                prev_file=last_log.get("file_name", ""),
                prev_last_lsn=last_log.get("last_lsn", ""),
                next_file="",
                next_first_lsn="",
                extra={
                    "restore_time": str(self.restore_time),
                    "backup_end_time": str(last_log.get("backup_end_time", "")),
                },
            )
            return self._make_result(
                status=LogBackupChainStatus.MISSING_TAIL,
                gaps=[gap],
            )

        # 5/6. 尾部段合法，根据头部+中间段是否为空分两路
        head_gaps: List[Dict[str, Any]]
        if head_middle_logs:
            # 5. 头部+中间段非空 -> 走正常的首份 + 中间 LSN 判定
            head_gaps = self._collect_head_and_middle_gaps(head_middle_logs)
            # 5.1 追加跨段衔接校验：head_middle 最后一份 last_lsn 必须等于 tail first_lsn，
            # 否则 inspect() 会误判 OK，但 flow 执行期 RESTORE LOG 才爆（历史踩坑点）
            head_gaps.extend(self._collect_tail_join_gap(head_middle_logs, tail_log))
        else:
            # 6. 头部+中间段为空、尾部段合法 -> D4 特殊分支
            head_gaps = self._head_check_by_tail(tail_log)

        # 头部/中间缺口按分型映射为最终 status（首份优先）
        if any(g["type"] == GAP_TYPE_MISSING_FIRST for g in head_gaps):
            return self._make_result(
                status=LogBackupChainStatus.MISSING_HEAD,
                gaps=head_gaps,
            )
        if any(g["type"] == GAP_TYPE_MISSING_MIDDLE for g in head_gaps):
            return self._make_result(
                status=LogBackupChainStatus.DISCONTINUOUS,
                gaps=head_gaps,
            )

        # 7. 全通过 -> OK，拼装完整日志链
        # 需求 4.1 / 4.2：头部+中间段 + 尾部段 拼接；D4 场景下头部+中间段为空，仅返回 [tail]
        backup_infos: List[Dict[str, Any]] = list(head_middle_logs)
        backup_infos.append(tail_log)
        return LogBackupChainResult(
            status=LogBackupChainStatus.OK,
            db_name=self.db_name,
            backup_infos=backup_infos,
            error_message="",
            gaps=[],
        )

    def _make_result(
        self,
        status: str,
        gaps: List[Dict[str, Any]],
    ) -> LogBackupChainResult:
        """统一装配非 OK 态的 LogBackupChainResult（渲染错误消息 + 置空 backup_infos）。

        :param status: 非 OK 的 5 态之一
        :param gaps: 结构化缺口列表（EMPTY 态可传空）
        :return: 装配好的 LogBackupChainResult 实例

        边界：
          - 非 OK 一律 `backup_infos=[]`（D5 决策）
        """
        error_message: str = self._render_error_message(
            status=status,
            gaps=gaps,
        )
        return LogBackupChainResult(
            status=status,
            db_name=self.db_name,
            backup_infos=[],
            error_message=error_message,
            gaps=gaps,
        )

    def _render_error_message(
        self,
        status: str,
        gaps: List[Dict[str, Any]],
    ) -> str:
        """按状态渲染业务化中文错误消息，保持 DBA 视觉一致性（Header + 缺口明细 + Suggestion）。

        版式说明（对应需求 6.6）：
          - EMPTY：独立文案，明确"未查询到任何日志备份"
          - MISSING_TAIL / MISSING_HEAD / DISCONTINUOUS：三段式版式（Header + 分节明细 + 单一建议）

        :param status: 状态码，须为 LogBackupChainStatus 5 态之一
        :param gaps: 结构化缺口列表
        :return: 单条完整错误消息字符串（含 Header + 缺口 + Suggestion）

        边界 / 异常：
          - status == OK -> 返回空串（调用方通常不会到达此分支）
          - gaps 为空但 status 非 OK/EMPTY -> 仍能渲染 Header + Suggestion（防御性）
        """
        if status == LogBackupChainStatus.OK:
            return ""

        if status == LogBackupChainStatus.EMPTY:
            return _(
                "【集群: {cluster}】【数据库: {db_name}】在时间范围【{start_time} ~ {end_time}】内未查询到任何日志备份。\n"
                "  建议：请确认该数据库是否开启日志备份，或联系系统管理员排查备份上报链路\n"
            ).format(
                cluster=self.cluster_address,
                db_name=self.db_name,
                start_time=self.full_end_time_str,
                end_time=self.restore_time,
            )

        # 三段式版式：MISSING_TAIL / MISSING_HEAD / DISCONTINUOUS 共享同一 Header 结构
        first_gaps: List[Dict[str, Any]] = [g for g in gaps if g["type"] == GAP_TYPE_MISSING_FIRST]
        middle_gaps: List[Dict[str, Any]] = [g for g in gaps if g["type"] == GAP_TYPE_MISSING_MIDDLE]
        tail_gaps: List[Dict[str, Any]] = [g for g in gaps if g["type"] == GAP_TYPE_MISSING_TAIL]

        n_first: int = len(first_gaps)
        n_middle: int = len(middle_gaps)
        n_tail: int = len(tail_gaps)
        gap_count: int = n_first + n_middle + n_tail

        header = _(
            "【集群: {cluster}】【数据库: {db_name}】检测到日志备份缺失，共发现 {gap_count} 处缺口"
            "（首份:{n_first}/中间:{n_middle}/末份:{n_tail}）：\n"
        ).format(
            cluster=self.cluster_address,
            db_name=self.db_name,
            gap_count=gap_count,
            n_first=n_first,
            n_middle=n_middle,
            n_tail=n_tail,
        )

        first_template: str = _(
            "  【缺失类型：首份日志缺失】\n"
            "    · 全量备份文件：{prev_file}（结束 LSN: {prev_last_lsn}）\n"
            "    · 首份日志备份：{next_file}（起始 LSN: {next_first_lsn}）\n"
            "    · 缺口区间（LSN）：{prev_last_lsn} -> {next_first_lsn}\n"
        )
        middle_template: str = _(
            "  【缺失类型：中间日志缺失】\n"
            "    · 上一份日志备份：{prev_file}（结束 LSN: {prev_last_lsn}）\n"
            "    · 下一份日志备份：{next_file}（起始 LSN: {next_first_lsn}）\n"
            "    · 缺口区间（LSN）：{prev_last_lsn} -> {next_first_lsn}\n"
        )
        tail_template: str = _(
            "  【缺失类型：末份日志缺失】\n"
            "    · 末份日志备份：{prev_file}（结束 LSN: {prev_last_lsn}，结束时间: {backup_end_time}）\n"
            "    · 目标构造时点：{restore_time}\n"
            "    · 覆盖差距：末份日志结束时间早于 restore_time，日志链未覆盖到目标时点\n"
        )

        details: List[str] = []
        for g in first_gaps:
            details.append(first_template.format(**g))
        for g in middle_gaps:
            details.append(middle_template.format(**g))
        for g in tail_gaps:
            details.append(
                tail_template.format(
                    prev_file=g["prev_file"],
                    prev_last_lsn=g["prev_last_lsn"],
                    backup_end_time=g["extra"].get("backup_end_time", ""),
                    restore_time=g["extra"].get("restore_time", ""),
                )
            )

        suggestion = _("  建议：请联系系统管理员补齐上述区间内缺失的日志备份，或选择其他可用的回档时间点\n")
        return header + "".join(details) + suggestion
