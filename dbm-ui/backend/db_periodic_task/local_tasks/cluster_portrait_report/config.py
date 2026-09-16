# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 DispatchTask 的配置容器 —— 通用基类 + 各 db_type 专属子类。

模块职责：
    - 定义 :class:`PortraitReportConfigBase`：所有 db_type 画像共享的通用配置字段
      与 ``validate_raw`` 扩展校验（灰度限流 / 错峰 / 时间窗 / 域名黑名单）
    - 定义 :class:`MysqlPortraitReportConfig`：MySQL 家族画像的具体 task_key 绑定
    - 未来接入 Redis / MongoDB / SQLServer 画像时，**只需继承基类 + 声明 task_key**，
      无需重复通用字段与校验逻辑

设计要点：
    - 通用字段（``daily_shuffle_limit`` / ``dispatch_spread_window_seconds`` /
      ``report_window_days_back`` / ``ignore_cluster_domains``）与 db_type 无关，
      沉淀到基类；子类若需覆盖默认值可在字段级重新赋值；
    - :meth:`PortraitReportConfigBase.validate_raw` 追加子类字段校验，
      父类 :meth:`DispatchTaskConfig.validate_raw` 已覆盖公共字段；
    - 每个 db_type 一个 ``task_key``（管理端 ``DispatchTaskSettings`` 独立可调）。

边界：
    - 本模块无 IO / DB 访问，纯 dataclass 定义；
    - 修改字段名 / 移除字段是**破坏性变更**，必须同步迁移 DB 中已保存的 JSON 配置。
"""
from dataclasses import dataclass, field
from typing import ClassVar, List

from django.core.exceptions import ValidationError

from backend.db_periodic_task.dispatch.config import DispatchTaskConfig, IdempotenceMode

#: 默认单集群画像执行超时（秒）；对齐 AITaskConfig 的 540s AI 调用预算
#: 语义：一次 dispatch worker 从 reserved 到 finalize 的最长允许时长
_DEFAULT_PORTRAIT_EXECUTION_TIMEOUT_SECONDS: int = 540

#: 默认错峰窗口（秒）：暂时置 0 —— 关闭 producer 侧错峰，items 立即 ready
#: 历史值：50 * 60（对应旧 ClusterPortraitDispatcher 的 _DEFAULT_DISPATCH_WINDOW_SECONDS）
#: 语义：0 表示 ``ready_at=None``，全部 items 立即入队；>0 时用 ``spread(window)`` 均摊
_DEFAULT_DISPATCH_SPREAD_WINDOW_SECONDS: int = 0

#: 默认画像时间窗回溯天数；1 表示"昨天整天"（与旧实现一致）
#: 语义：report_from / report_to = schedule_date - N 天 的 00:00:00 ~ 23:59:59
_DEFAULT_REPORT_WINDOW_DAYS_BACK: int = 1


@dataclass
class PortraitReportConfigBase(DispatchTaskConfig):
    """集群画像任务的通用运行期配置基类（跨 db_type 复用）。

    职责：
        - 沉淀"画像语义"共用字段：灰度分桶、错峰窗口、时间窗回溯、域名黑名单
        - 沉淀通用校验：字段级非负 / >=1 / list[str] 约束
        - 提供画像专属的默认值：``execution_timeout_seconds=540``、``idempotence_mode=DEDUPE``

    使用方式：
        - 子类只需继承本类并声明 ``task_key: ClassVar[str] = "xxx.cluster_portrait"``；
          若需覆盖默认值可在字段级 override。

    线程安全：是（dataclass 一次构造后视为不可变）
    边界：
        - ``daily_shuffle_limit=0`` -> 不做灰度限流（当天全量画像）
        - ``dispatch_spread_window_seconds=0`` -> 所有 items 立即入队（不错峰）
        - ``report_window_days_back<1`` 会被 :meth:`validate_raw` 拦截
    """

    #: 去重语义：DEDUPE = 按 (task_key, work_item_id) 拦截重复入队
    #: 画像语义："同集群同调度日期"通过 work_item_id 中的日期后缀实现"每日仅一次"
    idempotence_mode: IdempotenceMode = IdempotenceMode.DEDUPE

    #: 单集群画像 dispatch 执行超时（秒）；覆盖父类 3600s 默认，向 AITask 540s 对齐
    execution_timeout_seconds: int = _DEFAULT_PORTRAIT_EXECUTION_TIMEOUT_SECONDS

    #: 灰度限流：0 表示不分桶全量画像；>0 时按 (id + 日序数) % ceil(total/limit) 分桶轮转
    #: 对应旧 ClusterPortraitDispatcher 的 _PORTRAIT_LIMIT，切换时保持默认 0 = 与线上一致
    daily_shuffle_limit: int = 0

    #: 错峰投递窗口（秒）：0 表示不错峰、items 立即入队
    #: 对应旧 calculate_countdown 的窗口时长；改用 ``spread(window)`` 均摊
    dispatch_spread_window_seconds: int = _DEFAULT_DISPATCH_SPREAD_WINDOW_SECONDS

    #: 画像时间窗回溯天数；1 = 昨天整天；必须 >= 1（画像不能覆盖未来时间）
    report_window_days_back: int = _DEFAULT_REPORT_WINDOW_DAYS_BACK

    #: 画像域名黑名单：命中的 immute_domain 直接跳过；用于临时排除某些异常集群
    ignore_cluster_domains: List[str] = field(default_factory=list)

    @classmethod
    def validate_raw(cls, raw: dict) -> None:
        """追加画像通用字段的合法性校验。

        功能说明：
            - 先调用父类校验（``queue_wait_ttl_seconds`` / ``execution_timeout_seconds``
              / ``max_requeue_attempts`` 等公共字段）；
            - 再对画像通用字段追加非负 / >=1 校验，并检查 ``ignore_cluster_domains``
              必须是 str 列表；命中任一异常统一 raise ``ValidationError``。

        :param raw: 待校验的原始 dict（来自 ``DispatchTaskSettings.config`` JSON 字段）
        :return: None（无异常即校验通过）

        边界 / 异常：
            - ``report_window_days_back < 1`` -> ``ValidationError``
            - ``dispatch_spread_window_seconds < 0`` -> ``ValidationError``
            - ``daily_shuffle_limit < 0`` -> ``ValidationError``
            - ``ignore_cluster_domains`` 非 list[str] -> ``ValidationError``
        """
        super().validate_raw(raw)
        config = cls.from_raw(raw)

        if config.report_window_days_back < 1:
            raise ValidationError({"config": "report_window_days_back must be at least 1"})
        if config.dispatch_spread_window_seconds < 0:
            raise ValidationError({"config": "dispatch_spread_window_seconds cannot be negative"})
        if config.daily_shuffle_limit < 0:
            raise ValidationError({"config": "daily_shuffle_limit cannot be negative"})

        # ignore_cluster_domains: 允许空列表；非空时逐项类型校验，避免 DB 落坏值
        domains = config.ignore_cluster_domains or []
        if not isinstance(domains, list) or any(not isinstance(item, str) for item in domains):
            raise ValidationError({"config": "ignore_cluster_domains must be a list of str"})


@dataclass
class MysqlPortraitReportConfig(PortraitReportConfigBase):
    """MySQL 家族（TenDBSingle / TenDBHA / TenDBCluster）集群画像的运行期配置。

    职责：
        - 通过 ``task_key`` 声明与 ``MysqlPortraitReportTask`` 的绑定关系
        - 复用 :class:`PortraitReportConfigBase` 的所有通用字段与校验

    使用方式：
        由 ``@register_dispatch_task(config_cls=MysqlPortraitReportConfig, ...)``
        绑定到 :class:`MysqlPortraitReportTask`。

    线程安全：是（继承自 dataclass 基类）
    边界：
        - 未来若 MySQL 画像有 db_type 专属字段，可在此追加；本类当前**只声明 task_key**。
    """

    #: 任务 key：管理端配置行主键；同一进程内唯一，不可与其他 DispatchTask 冲突
    task_key: ClassVar[str] = "mysql.cluster_portrait"


__all__ = (
    "PortraitReportConfigBase",
    "MysqlPortraitReportConfig",
)
