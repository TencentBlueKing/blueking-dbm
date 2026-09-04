# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像报告生成 —— Celery worker 薄壳 + 分发器实例。

设计要点 / 怎么做：
  - 两段职责，同文件，边界清晰：
    1) `generate_cluster_portrait_report_batch`：Celery @app.task 薄壳，单集群画像生成；
    2) 模块级 `portrait_dispatcher`：ClusterPortraitDispatcher 实例，供 task.py 调用。
  - 通用调度骨架（dispatch 锁 / 错峰 / 防重锁 / apply_async）复用
    ClusterPortraitDispatcher，本文件不重复实现。
  - 时间窗：取调度日期的前一天整天（东八区 aware datetime），
    report_from=昨天00:00:00，report_to=昨天23:59:59。
  - 生成器选择：TenDBCluster 用 TendbClusterClusterPortraitGenerator（db_type 落 tendbcluster），
    其余（TenDBSingle/TenDBHA）用 MysqlClusterPortraitGenerator（db_type 落 mysql）。
"""
import logging
from datetime import date, datetime
from datetime import time as dt_time
from datetime import timedelta

from blueapps.core.celery.celery import app
from django.utils import timezone

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.cluster_portrait_report.dispatcher import ClusterPortraitDispatcher
from backend.db_report.portrait.generator import MysqlClusterPortraitGenerator, TendbClusterClusterPortraitGenerator

logger = logging.getLogger("root")

# ------------------------------ 常量 / 配置 ------------------------------

# TODO: 灰度阶段仅跑前 1000 个集群（约总量 20%），验证稳定后改为 0 开放全量
_PORTRAIT_LIMIT: int = 1000

# 画像覆盖的集群类型
_PORTRAIT_CLUSTER_TYPES = [
    ClusterType.TenDBSingle,
    ClusterType.TenDBHA,
    ClusterType.TenDBCluster,
]


# ------------------------------ Celery 薄壳 worker ------------------------------


# rate_limit：Celery 内建令牌桶，硬限当前 task 类型的消费速率（不影响其他 task）。
# 目标：把每 5 分钟画像 AI 请求量控制在 30-50 区间（对齐灰度期下游 AI SDK 的请求上限）。
#
# 作用域说明（重要）：
#   - rate_limit 是 per-worker-process 语义（每个 celery worker 进程一个独立令牌桶），
#     与 -P 并发模型（prefork / threads / gevent）以及 -c 并发数无关；
#   - 当前部署：K=8 个 worker 进程（每进程 -P threads -c 100），共 8 个令牌桶；
#   - 总速率 = 单 worker 速率 × K = 单 worker 速率 × 8。
#
# 取值推导（当前 K=8）：
#   - 单 worker "1/m" → 总 8/min = 40/5min，落在目标 [30, 50]/5min 区间中间偏低（保守灰度）；
#   - 1000 个 task 稳态跑完约需 1000 / 8 = 125 分钟 ≈ 2h05min，符合每日 1 桶的节奏；
#   - 若灰度稳定后想更贴近上界（50/5min），可改为 "75/h" 提升到 8×75/h = 600/h = 50/5min。
#
# 部署侧变化时的对齐规则：
#   - K 值变化 → 单 worker 速率按 f"{总目标每分钟 // K}/m" 反推，当前总目标 8/min；
#   - 例如：K=4 → "2/m"；K=1 → "8/m"；K=16 → "0.5/m" 无法整数表达，
#     此时改用小时粒度 "30/h"（16 × 30 = 480/h ≈ 40/5min）。
#
# 其他注意事项：
#   - 令牌桶按 task name 隔离，仅影响 generate_cluster_portrait_report_batch 自身；
#   - 等待令牌期间不计入软/硬超时（超时从执行开始才计时）；
#   - -P threads 模式下 rate_limit 仍在 worker 主循环判定，100 线程不会突破令牌桶速率；
#   - 等待令牌的 task 仅占用 worker 内存（不重回 broker 队列），
#     故不会触发 broker visibility_timeout 的重复投递问题；
#   - 回滚方式：删除 rate_limit 参数即可恢复无限速。
@app.task(rate_limit="1/m")
def generate_cluster_portrait_report_batch(cluster_id: int, lock_key: str, schedule_date_str: str) -> None:
    """集群画像报告 —— 单集群 Celery worker 任务（薄壳）。

    功能说明：
      - 由 dispatcher 按 Cluster.id 升序逐个投递；
      - 根据 cluster_type 选择对应生成器，调用 ``run()`` 生成画像报告；
      - 生成器内部已落 ClusterPortraitReport（init_record + fill_report_result），
        本 worker 不再落库；AI 异常 / 解析失败由生成器内部转 status 落库，不冒泡。

    :param cluster_id: 待生成画像的集群 id
    :param lock_key: 防重锁 key（按集群+日期）；不主动释放（25h TTL，次日换新 key）
    :param schedule_date_str: 调度日期 ISO 字符串（dispatch 时刻的 localdate），用于确定"昨天"
    :return: None
    边界：
      - 集群不存在 -> 记录 warning 跳过
      - 生成器 run 内部异常已兜底；ORM 等未兜底异常 -> 记录 exception，不上抛
    """
    logger.info("portrait batch start: cluster_id=%s lock_key=%s", cluster_id, lock_key)
    try:
        # 时间窗：调度日期的前一天整天（东八区 aware datetime）
        # 关于 23:59:59 的"漏 1 秒"说明（已知的可接受小瑕疵）：
        #   - report_to 使用 23:59:59 会丢失 23:59:59.000001~999999 这一秒内的微秒粒度数据；
        #   - 更严谨写法是"次日 00:00:00 左闭右开"，但本项目中 report_from / report_to
        #     仅通过 datetime2str 格式化后注入 LLM prompt 作为可读时间窗上下文
        #     （见 generator/base.py PROMPT_TEMPLATE），不参与任何 ORM/SQL/ES filter；
        #   - LLM 后续调用 MCP 工具查具体数据时，各工具自行传 start_time/end_time，与本值无过滤耦合；
        #   - 因此保留 23:59:59 更符合人类可读直觉（"昨天 00:00 到 23:59:59"），
        #     避免 LLM 看到"次日 00:00:00"时误判日期边界。
        schedule_date = date.fromisoformat(schedule_date_str)
        yesterday = schedule_date - timedelta(days=1)
        report_from = timezone.make_aware(datetime.combine(yesterday, dt_time(0, 0, 0)))
        report_to = timezone.make_aware(datetime.combine(yesterday, dt_time(23, 59, 59)))

        cluster = Cluster.objects.get(id=cluster_id)

        generator = (
            TendbClusterClusterPortraitGenerator()
            if cluster.cluster_type == ClusterType.TenDBCluster
            else MysqlClusterPortraitGenerator()
        )
        result = generator.run(
            cluster=cluster,
            report_from=report_from,
            report_to=report_to,
            dimensions=None,
            operator="system",
        )
        logger.info(
            "portrait batch done: cluster=%s status=%s record_id=%s score=%s",
            cluster.immute_domain,
            result.status,
            result.record_id,
            result.score,
        )
    except Cluster.DoesNotExist:
        logger.warning("portrait batch skip, cluster not found: cluster_id=%s", cluster_id)
    except Exception:  # noqa
        logger.exception("portrait batch failed: cluster_id=%s lock_key=%s", cluster_id, lock_key)


# ------------------------------ 模块级 dispatcher 实例 ------------------------------

# 集群画像 dispatcher（供 task.py 直接调用 dispatch()）
portrait_dispatcher: ClusterPortraitDispatcher = ClusterPortraitDispatcher(
    name="mysql",
    cluster_types=_PORTRAIT_CLUSTER_TYPES,
    worker_task=generate_cluster_portrait_report_batch,
    limit=_PORTRAIT_LIMIT,
)
