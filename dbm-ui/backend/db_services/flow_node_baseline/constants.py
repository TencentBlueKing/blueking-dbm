# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

flow 节点耗时基线：常量与配置。

模块职责：
  - 集中定义所有"魔法数、阈值、正则、prompt 模板"，禁止在业务代码内散落硬编码
  - 为 NameCleaner / NameNormalizer / BaselineAggregator / FlowSampleCollector 提供统一常量入口
  - 每个常量都必须带类型注解与语义说明，便于运维/DBA review 与调整

变更约束：
  - 修改常量前需评估对存量基线的影响（如可靠性阈值调整会导致 is_reliable 大量翻转）
  - 新增正则清洗规则时，务必同步补充单元测试用例
"""
import re
from typing import List, Pattern, Tuple

from django.utils.translation import gettext_lazy as _

# =============================================================================
# 一、名称清洗（NameCleaner）用正则规则
# -----------------------------------------------------------------------------
# 设计约束：
#   - 只做"参数化"，不做"合并判断"（合并判断交给 LLM）
#   - 每条规则都是无损、可判定的字符串替换
#   - 顺序敏感：先替换更长/更精确的模式，再替换泛化模式
# =============================================================================

#: IPv4 正则；生产 name 里最常见的漂移来源
#: 边界放宽：使用负向断言 (?<![\d.]) / (?![\d.]) 替代 \b
#: 原因：中文/字母紧邻 IP 时 \b 依赖 \w 定义，某些上下文（如 "v1.1.1.1" / "实例1.1.1.1"）
#: 边界识别不稳定；负向断言只要求两侧不是"数字或点"，能覆盖中文/字母/冒号/方括号等所有场景
_IPV4_PATTERN: Pattern = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")

#: 端口号（形如 :48333、:20000）
#: 边界说明：右侧使用 (?!\d) 而非 \b
#: 原因：Python3 默认 re.UNICODE 模式下，中文字符属于 \w，导致 "48322是否" 中的
#: "2" 和 "是" 之间不是 \b，\b 边界会失效；改用 (?!\d) 只要求右侧不是数字，
#: 覆盖中文/字母/标点/空白/字符串结尾等所有停止场景
_COLON_PORT_PATTERN: Pattern = re.compile(r":\d{2,5}(?!\d)")

#: 中括号包裹的端口（形如 [30000]、[20000]）；生产 Redis 类 name 常见
_BRACKET_PORT_PATTERN: Pattern = re.compile(r"\[\d{2,5}\]")

#: 引号包裹的 IP（形如 'X.X.X.X'）；已被 IPv4 规则处理过 IP 后仍需保留引号形态
_QUOTED_IP_PATTERN: Pattern = re.compile(r"'\s*<IP>\s*'")

#: IP 列表折叠：把连续 ≥2 个 <IP> 或 <IP>:<PORT> 单元（以常见分隔符相连）压成 <IP_LIST>
#: 覆盖场景：
#:   - "<IP>,<IP>,<IP>"                       → "<IP_LIST>"
#:   - "<IP>:<PORT>,<IP>:<PORT>"              → "<IP_LIST>"
#:   - "<IP>、<IP>、<IP>"                     → "<IP_LIST>"（中文顿号）
#:   - "<IP>; <IP>； <IP>"                    → "<IP_LIST>"（含中英文分号 + 空格）
#: 单元定义：一个 <IP> 或 <IP>:<PORT>；后可跟 :<PORT> 是可选的
#: 分隔符定义：英文逗号 / 中文逗号 / 英文分号 / 中文分号 / 顿号 / 空白（含中文空格 \u3000）
#: 匹配前提：至少 2 个单元连续出现，避免把单个 <IP> 也误折叠导致丢失信息
#: 依据：编排层常见拼接方式（Python join / Golang strings.Join）产出的多实例 name
_IP_LIST_UNIT: str = r"<IP>(?::<PORT>)?"
_IP_LIST_SEP: str = r"(?:\s|,|，|;|；|、|\u3000)+"
_IP_LIST_PATTERN: Pattern = re.compile(rf"{_IP_LIST_UNIT}(?:{_IP_LIST_SEP}{_IP_LIST_UNIT})+")

#: dbm 集群/实例域名：以 `.db` 结尾的多段域名，形如：
#:   - spider.xxx.db / gamedb.xxx.db                （2 段前缀）
#:   - test2016db.1.jtest.db                        （3 段前缀，含数字段）
#:   - node1.cluster.biz.dbm.db                     （4 段前缀）
#: 段构成：字母/数字/下划线/连字符 组合；总段数 ≥ 2 且以 `.db` 结束
#: 依据：dbm 集群域名规范（backend/db_meta 域名生成规则），末段固定为 `db`
#: 边界说明：使用显式字符集 [A-Za-z0-9_.-] 的负向断言，不用 \w
#: 原因：Python3 默认 re.UNICODE 下中文属于 \w，"集群test..." 中"群"和"t"之间
#: 不是 \b，\w 类边界会失效；显式字符集只匹配 ASCII 域名字符，中文自然不在其中
_CLUSTER_DOMAIN_PATTERN: Pattern = re.compile(r"(?<![A-Za-z0-9_.-])(?:[A-Za-z0-9_-]+\.){2,}db(?![A-Za-z0-9_.-])")

#: hex/hash 长串（≥16 位十六进制字符）；如 UUID / MD5 / commit hash
#: 边界说明：使用 (?<![0-9a-fA-F]) / (?![0-9a-fA-F]) 而非 \b
#: 原因：同 _COLON_PORT_PATTERN，Python3 Unicode 下中文属于 \w，"任务abc123..."
#: 中文和 hex 之间不是 \b；显式字符集断言只要求两侧不是 hex 字符
_HEX_HASH_PATTERN: Pattern = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{16,}(?![0-9a-fA-F])")

#: ISO 时间戳（形如 2026-07-03 11:15:16 或 2026-07-03T11:15:16）
_ISO_TIMESTAMP_PATTERN: Pattern = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")

#: 通用清洗规则表：(pattern, placeholder)；按顺序应用
#: 顺序说明：
#:   1. 先替换集群域名 → <DOMAIN>（域名结构最独特，先吃掉避免被 IP 规则拆错）
#:   2. 再替换 IP → <IP>（避免后续规则误伤）
#:   3. 再替换端口（避免和 IP 里的数字混淆）
#:   4. 再替换 hex / 时间戳这类独立 token
#:   5. 清理 <IP> 外层引号，避免出现 '<IP>' 的多余引号形态
#:   6. 最后折叠 <IP>/<IP>:<PORT> 列表为 <IP_LIST>
#:      —— 必须放在最后：等前面把单值都替换成占位符后，再对占位符做长度归一
NAME_CLEAN_RULES: List[Tuple[Pattern, str]] = [
    (_CLUSTER_DOMAIN_PATTERN, "<DOMAIN>"),
    (_IPV4_PATTERN, "<IP>"),
    (_COLON_PORT_PATTERN, ":<PORT>"),
    (_BRACKET_PORT_PATTERN, "[<PORT>]"),
    (_HEX_HASH_PATTERN, "<HASH>"),
    (_ISO_TIMESTAMP_PATTERN, "<TS>"),
    (_QUOTED_IP_PATTERN, "<IP>"),
    (_IP_LIST_PATTERN, "<IP_LIST>"),
]

#: name 清洗前的最大处理长度；超长部分先截断，避免 LLM prompt 膨胀
#: 单位：字符；生产实测最长 name < 100 字符，200 是安全上限
MAX_NAME_LENGTH_FOR_NORMALIZE: int = 200


# =============================================================================
# 二、name 归一化（NameNormalizer）行为阈值
# -----------------------------------------------------------------------------
# LLM 服务不可用时的降级行为与恢复手册（重要，运维必读）：
#
#   1. 单次调用失败（超时 / 解析失败）：
#      - 走 LLM_FALLBACK 分支：normalized_name = cleaned_name，needs_review=True
#      - 结果写入 FlowNodeNameAlias，供后续同 cleaned_name 直接命中缓存
#      - 影响范围：仅当条样本对应的 (tt, code, cleaned_name)
#
#   2. LLM 服务整体不可用（长时间维护 / AgentHandler 故障）：
#      - 每个"新出现的 cleaned_name"都会各成一类（normalized_name = cleaned_name）
#      - 基线桶（(tt, bk_biz_id, code, normalized_name)）膨胀，P95/P99 稳定性下降
#      - 已归一化过的旧样本不受影响（alias 表命中即返回，不触发 LLM）
#      - CATEGORIES_WARN_THRESHOLD / CATEGORIES_HARD_LIMIT 是最后一道安全网：
#        超阈值会打告警日志、触发熔断，避免无声膨胀
#
#   3. LLM 服务恢复后的处理策略：
#      - **重跑 rebuild / repair 不会自动纠正**：alias 表命中缓存直接返回旧的
#        LLM_FALLBACK 记录，不会重新触发 LLM。
#      - 正确恢复步骤（DBA 手动介入）：
#        step1. 定位受影响记录：
#               FlowNodeNameAlias.objects.filter(
#                   match_source='llm_fallback', manual_locked=False
#               )
#        step2. 清理这些记录（或按 tt/code 精细化清理）
#        step3. 触发 rebuild（全量）或 repair（业务级）重新归一化
#      - 若无法清理，DBA 也可对受影响记录逐条设置 manual_locked=True + 修正
#        normalized_name，走人工审阅通道兜底
#
#   4. 关于"主动关闭 LLM"开关的说明：
#      - 当前**不提供** DISABLE_LLM_NORMALIZE 之类的运维开关；理由：
#        a) 主动关闭 LLM 与"LLM 全局不可用"效果一致，均触发上述 (2) 的桶膨胀
#        b) 需要主动关闭的场景（LLM 长时维护），直接停用 flow_node_baseline
#           相关定时任务即可，避免污染 alias 表
#        c) manual_locked=True + 修正 normalized_name 已是 DBA 的强兜底通道
# =============================================================================

#: 单个 (ticket_type, code) 下已有 normalized_name 集合的**告警阈值**
#: 业务预期：受 flow 编排代码控制，同一 (tt, code) 的语义类别数应 ≤ 此值
#: 超过时打 warning 日志，提示可能是清洗规则漏了参数或 LLM 误判导致新桶爆炸
#: 依据：dbm 单个组件动作词表实测在 3~15 之间，30 是"合理上限的 2 倍余量"，
#:      为大型编排单据（如 MYSQL_HA_APPLY 等）预留缓冲，避免误报
CATEGORIES_WARN_THRESHOLD: int = 30

#: 单个 (ticket_type, code) 下已有 normalized_name 集合的**熔断上限**
#: 超过此值时抛 ValueError，避免把超大 prompt 丢给 LLM 导致成本 / 延迟失控
#: 触发熔断后需人工介入排查：清洗规则遗漏 / LLM 误判 / flow 编排异常膨胀
#: 依据：LLM prompt 稳态在 2K token 以内；100 条候选 × 平均 40 tokens 已达 4K 边界
CATEGORIES_HARD_LIMIT: int = 100

#: LLM 判定合并的最低置信度门槛：
#:   - confidence >= 此值：采纳合并（needs_review=False）
#:   - confidence <  此值：**拒绝合并**，走"新类别"路径（不再走"合并 + needs_review"）
#: 变更依据：
#:   - 旧策略 "合并 + needs_review" 会污染基线；一旦被合并到错误的 normalized_name，
#:     后续同 cleaned_name 会命中 alias 缓存持续吃错映射，纠正成本高
#:   - 拒绝合并只是多一个类别，最坏情况是 CATEGORIES_WARN_THRESHOLD 触发告警
#:     由 DBA 通过 manual_locked 人工介入，代价远小于污染基线
#: 阈值取 0.8：多次实测 confidence 分布，>=0.8 的判定错误率显著下降
LLM_LOW_CONFIDENCE_THRESHOLD: float = 0.8

#: 单次归一化处理的 LLM 调用超时（秒）；超时降级为"新类别"路径
#: 依据：AgentHandler 默认 30s；这里保守取 20s，留 10s 给上层重试
LLM_CALL_TIMEOUT_SECONDS: int = 20

#: LLM 调用失败重试次数（不含首次调用）
#: 失败超过此次数后，走 LLM_FALLBACK 路径，normalized_name = cleaned_name
LLM_CALL_RETRY_TIMES: int = 1


# =============================================================================
# 三、基线聚合（BaselineAggregator）阈值
# =============================================================================

#: 判定基线可靠所需的最小样本数
#: 依据：统计学上 P95/P99 在 n<30 时抖动剧烈，30 是经验下限
BASELINE_MIN_RELIABLE_SAMPLES: int = 30

#: 分布形态判定阈值：stddev / mean 比值
#: - <= 0.5   → NARROW_UNIMODAL（窄单峰，均值高度可信）
#: - <= 2.0   → WIDE_UNIMODAL  （宽单峰，均值可参考）
#: - >  2.0   → HEAVY_TAILED   （重尾，均值失真，只信分位数）
DIST_NARROW_UNIMODAL_CV: float = 0.5
DIST_WIDE_UNIMODAL_CV: float = 2.0

#: 单条样本耗时上限（秒）；超过视为异常样本，不入基线
#: 依据：生产实测 p99 最大 ~2000s，取 24h 作为宽松上限，可容纳超长回档流程与合法长任务
SAMPLE_MAX_DURATION_SECONDS: int = 24 * 3600

#: 单条样本耗时下限（秒）；< SAMPLE_MIN_DURATION_SECONDS 视为时钟回拨或异常样本，进 reject 表
#: 依据：采集器对真实 delta 使用 math.ceil 向上取整，任何 > 0 的耗时最小都会被拉齐为 1 秒；
#:      因此正常样本恒 >= 1，只有 delta < 0（updated_at 早于 started_at，即时钟回拨）
#:      或 delta == 0 但被判定为异常场景，才会 < 1 命中下界过滤。
#: 说明：亚秒级真实节点（如 sqlserver_add_job_user 通常 0.2~0.6s）经 ceil 后 = 1s，正常入基线。
SAMPLE_MIN_DURATION_SECONDS: int = 1


# =============================================================================
# 四、样本采集（FlowSampleCollector）参数
# =============================================================================

#: FlowTree 迭代 chunk_size；平衡内存与 DB 往返次数
FLOW_TREE_ITER_CHUNK_SIZE: int = 100

#: FlowNode 迭代 chunk_size；单个 flow 下节点数一般 <200，500 已足够
FLOW_NODE_ITER_CHUNK_SIZE: int = 500

#: 存量任务默认按天切片处理，避免单次 SQL 拉取过大
STOCK_TASK_SLICE_DAYS: int = 1

#: 每日增量任务的默认回溯窗口（天）——首次运行且无水位时使用
INCREMENTAL_DEFAULT_LOOKBACK_DAYS: int = 1

#: 存量任务默认回溯天数（当 command 未指定 --since 时使用）
STOCK_DEFAULT_LOOKBACK_DAYS: int = 365

#: 组件 code 黑名单：这些是"人工暂停/等待确认"类节点，天然会有超长耗时（等 DBA/业务确认）。
#: 命中黑名单的节点：既不参与基线聚合，也不写入 reject 表（不属于"异常"，无需排查）。
#: - pause                        : 通用人工暂停节点
#: - pause_with_ticket_lock_check : 带单据锁校验的人工暂停节点
#: - sidecar_check_cluster_alarm_for_ai : 单据值守不做处理
#: - mysql_dts_poll_confirm_alive : DTS 确认节点（待办 + 存活轮询，等人确认）
EXCLUDED_COMPONENT_CODES: frozenset = frozenset(
    {
        "pause",
        "pause_with_ticket_lock_check",
        "sidecar_check_cluster_alarm_for_ai",
        "mysql_dts_poll_confirm_alive",
    }
)

#: reject 样本批量落库的批大小；每积累这么多条 reject 记录就 flush 一次。
#: 依据：平衡内存占用与单次 INSERT 效率；单条 reject 记录约 <1KB，500 条约 500KB 可控。
REJECT_SAMPLE_FLUSH_BATCH_SIZE: int = 500


# =============================================================================
# 五、LLM prompt 模板
# -----------------------------------------------------------------------------
# 设计约束：
#   - prompt 里必须明确"输出 JSON 结构"与"判断准则"，减少解析失败
#   - 使用 {existing_categories} / {cleaned_name} 等占位符，由 NameNormalizer 填充
#   - 保持 prompt 尽可能短，避免 token 消耗
# =============================================================================

#: LLM 语义匹配 prompt 模板
#: 输入：ticket_type / component_code / cleaned_name(新) / existing_categories(已有归一化 name 列表)
#: 输出：严格 JSON，字段 matched / matched_name / reasoning / confidence
#:
#: 设计原则（重要）：
#:   - 归一化的目的是"耗时基线聚合"，而非"字面语义相似"
#:   - 只有【动词一致 且 宾语核心词一致 且 耗时特征相同】才允许合并
#:   - 该组件 code 的语义域已由外部 (ticket_type, component_code) 限定，
#:     LLM 只需在此域内判断；不需要泛化到跨组件的"意图相似"
#:   - 合并错误（假阳）会污染 P95/P99；拆分保守（假阴）只是多几个类别，代价小
LLM_NAME_MATCH_PROMPT = _(
    """你是 DBM 系统的运维专家，正在为流程节点耗时统计做名称归一化。

上下文：
- 单据类型：{ticket_type}
- 组件代码：{component_code}

已有的归一化名称（每个代表一个独立的运维动作）：
{existing_categories}

新出现的节点名称（已做过 IP / 端口 / 域名 / 哈希等参数化处理）：
"{cleaned_name}"

请判断上述新名称是否与已有的某个名称在【耗时基线聚合意义上是同一个动作】。
注意：这里判断的不是"字面语义相似"，而是"是否应聚合到同一个耗时分布"。

判断准则（严格遵循，任一不满足即视为不匹配）：

1. 动词一致
   - 动词不同一律不合并。
   - 例：'安装MySQL实例' vs '卸载MySQL实例' —— 不合并。
   - 例：'启动backup jobs' vs '禁用backup jobs' —— 不合并。

2. 宾语核心词一致（仅参数化差异可以忽略）
   - 宾语指向的"操作对象类型"必须一致；对象体量 / 内容不同一律不合并。
   - ✅ 可合并：'安装Sqlserver实例:<IP>' 与 '安装Sqlserver实例' —— 仅参数差异。
   - ✅ 可合并：'恢复全量备份数据[<IP>]' 与 '恢复全量备份数据[<IP>:<PORT>]' —— 仅参数差异。
   - ❌ 不合并：'下发db-actuator介质' 与 '下发SQL文件'
        —— 前者是几十 MB 的固定执行器二进制，后者是用户 SQL 文本（可能几百 MB 至 GB），
           传输体量与耗时特征差异巨大。
   - ❌ 不合并：'下发执行器' 与 '下发SQL文件' —— 传输对象类型不同。
   - ❌ 不合并：'初始化配置' 与 '初始化数据库' —— 对象类型不同，耗时量级不同。
   - ❌ 不合并：'克隆Users' / '克隆Jobs' / '克隆LinkServer' —— 各自是独立对象类型。

3. 耗时特征需可预期地相近
   - 若两个动作在物理执行上（IO 量、锁范围、外部依赖）显著不同，即使字面接近也不合并。
   - 有任何"体量 / 数据源 / 目标不同"的合理怀疑，一律不合并。

4. 边界原则
   - 拿不准 → matched=false（保守拆分）。
   - 合并错的代价 >> 拆分错的代价。
   - 只有对合并有 ≥0.8 的把握，才输出 matched=true 且 confidence≥0.8。

请**只输出**严格的 JSON，不要输出任何额外文字或代码块标记：
{{"matched": true 或 false, "matched_name": "已有名称原文" 或 null, "reasoning": "简短理由（不超过 60 字）", "confidence": 0.0 到 1.0 的浮点数}}
"""
)

#: LLM 返回 JSON 提取正则；容忍 LLM 输出前后有解释性文字或 markdown 代码块
LLM_JSON_EXTRACT_PATTERN: Pattern = re.compile(
    r"\{[^{}]*\"matched\"[^{}]*\}",
    re.DOTALL,
)


# =============================================================================
# 六、其它常量
# =============================================================================

#: 全局基线的 bk_biz_id 占位值；查询兜底时使用
GLOBAL_BASELINE_BK_BIZ_ID: int = 0

#: 首次出现且未匹配到已有类别时，match_source 记为此值
#: 与 NameMatchSource.FIRST_SEEN 保持一致（避免循环 import 常量在此重复定义）
DEFAULT_MATCH_SOURCE_FIRST_SEEN: str = "first_seen"
