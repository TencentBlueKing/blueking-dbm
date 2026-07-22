# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

机器操作系统时区"重置为环境基线"pipeline 组件（用于机器退回资源池等收尾场景）。

业务场景：
    - **机器退回资源池** 时的收尾动作：机器即将脱离当前 DBM 业务归属、被资源池回收，
      需要把 OS 时区**统一还原为部署环境约定的基线时区**（由环境变量
      ``env.ENABLE_DB_MACHINE_TIMEZONE_RESET`` 指定，例如 ``+08:00``），避免脏状态
      污染下一个使用方；
    - 因为机器此时已脱离具体集群 / 模块 / 业务的语义，本组件**不查 dbconfig、不需要**
      ``bk_biz_id / db_module_id / cluster_type`` 等定位配置的字段；
    - 组件与 DB 引擎无关（MySQL / SQLServer / Redis 均可复用），因此归属通用 ``common`` 目录。

模块职责：
    - 提供一个"简化版"的机器 OS 时区初始化组件，目标时区**由部署环境变量决定**；
    - 通过继承公共基类 :class:`OsTimeZoneInitBase` 复用所有引擎无关能力
      （偏移解析 / shell 模板 / JobApi 下发 / ``_execute`` 骨架 / ``SYSTEM`` 短路），
      本模块仅实现"从何获取时区"这一变化点（读取
      ``env.ENABLE_DB_MACHINE_TIMEZONE_RESET``）。

与 :class:`MySQLInitOsTimeZoneComponent` 的关系：
    - 两者是**同级兄弟**，均继承自 :class:`OsTimeZoneInitBase`；
    - 唯一差异：:meth:`_resolve_time_zone` 钩子的实现——本组件读取部署环境变量，
      MySQL 变体从 dbconfig 读取；
    - **使用取舍**：常规部署 / 变更场景请使用 MySQL 变体（时区来自 dbconfig，可按业务模块
      灵活配置）；**仅当机器要脱离业务归属**（退回资源池、下架前收尾等）时使用本组件。

边界：
    - ``env.ENABLE_DB_MACHINE_TIMEZONE_RESET`` 必须落在 ``±00:00 ~ ±12:00`` 整点偏移范围内
      （或特殊值 ``SYSTEM``），否则会在基类 :meth:`OsTimeZoneInitBase._resolve_offset`
      阶段抛异常；
    - ``env.ENABLE_DB_MACHINE_TIMEZONE_RESET`` 为空 → :meth:`_resolve_time_zone` 原样返回
      空串，由基类 :meth:`_execute` 的**空值短路**分支处理：不下发 Job、直接短路成功，
      与 MySQL 变体（dbconfig 未配置时返回空）行为一致；调用方（flow 层）通常还会在
      挂节点前先做一次 env 空值判断，避免生成注定空跑的 act，属于**性能优化**而非必需；
    - 组件内所有影响执行结果的异常均**主动抛出**，不做静默吞异常；
    - 本组件不负责修改 DB 实例内部 ``default_time_zone`` 参数，仅处理机器 OS 层时区；
      对于退回资源池场景，实例通常已在前置步骤下线，无需关注实例层参数；
    - shell 幂等：基类模板会先检测机器当前时区，若与目标一致则直接跳过，无副作用。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from pipeline.component_framework.component import Component

from backend import env
from backend.flow.plugins.components.collections.common.os_timezone_init_base import OsTimeZoneInitBase
from backend.flow.utils.base.validate_handler import ValidateHandler, validate_int, validate_ip_in_list


@dataclass()
class OsTimeZoneResetKwargs(ValidateHandler):
    """``OsTimeZoneResetComponent`` 组件 kwargs 私有变量结构体。

    功能说明 / 怎么做：
        - 显式声明本组件从 pipeline ``kwargs`` 中期望读取的字段；
        - 继承 ``ValidateHandler``：实例化时按 ``field.metadata['validate']`` 逐字段校验类型，
          让 kwargs 契约从入口起就是**强类型**；
        - 目标时区**不通过 kwargs 传入**，而由组件侧 :meth:`OsTimeZoneReset._resolve_time_zone`
          从环境变量 ``env.ENABLE_DB_MACHINE_TIMEZONE_RESET`` 统一读取，
          避免"目标时区值"来源分散在多处；
        - 因此**无需** ``bk_biz_id`` / ``db_module_id`` / ``cluster_type`` 等仅用于定位
          dbconfig 配置的字段，只保留 Job 下发链路真正需要的 ``bk_cloud_id`` / ``exec_ip``。

    :param bk_cloud_id: 云区域 ID，必填
    :param exec_ip: 目标机器 IP 列表；每项须为合法 IPv4 字符串，必填

    使用示例::

        kwargs = OsTimeZoneResetKwargs(
            bk_cloud_id=0,
            exec_ip=["x.x.x.x", "xx.xx.xx.xx"],
        )

    边界 / 异常：
        - 任一字段类型不合法（如 ``bk_cloud_id`` 非 int、``exec_ip`` 含非 IPv4 元素）
          → ``ValidateHandler.__post_init__`` 抛 ``ValueError``
    """

    bk_cloud_id: int = field(metadata={"validate": validate_int})
    exec_ip: List[str] = field(metadata={"validate": validate_ip_in_list})


class OsTimeZoneReset(OsTimeZoneInitBase):
    """机器操作系统时区"重置为环境基线"Service（退回资源池等收尾场景）。

    业务场景：
        - **机器退回资源池** 时的收尾动作：机器即将脱离当前 DBM 业务归属，
          需要把 OS 时区还原为部署环境约定的基线时区，避免脏状态污染下一个使用方。

    职责：
        - 覆盖基类抽象钩子 :meth:`_resolve_time_zone`：从环境变量
          ``env.ENABLE_DB_MACHINE_TIMEZONE_RESET`` 读取目标时区值，
          不依赖 dbconfig / 集群元数据 / 业务上下文；
        - 其余能力（``_execute`` 骨架、偏移解析、shell 模板渲染、JobApi 下发）
          全部复用 :class:`OsTimeZoneInitBase` 基类实现。

    差异化点（与 :class:`MySQLInitOsTimeZone` 的对比）：
        - 目标时区**来自部署环境变量**，不再从 dbconfig 读取
          （机器已脱离业务归属，dbconfig 查询无意义）；
        - kwargs 仅需 ``bk_cloud_id`` / ``exec_ip`` 两个字段，无需 MySQL 变体那 3 个
          用于定位 dbconfig 配置的额外字段。

    扩展方式：
        - 若需要"多个固定偏移基线共存"（同环境下不同业务线不同时区），
          可再次继承本类并覆盖 :meth:`_resolve_time_zone`，改为读取更细粒度的配置源；
        - 单一环境基线场景下无需扩展。

    边界：
        - ``env.ENABLE_DB_MACHINE_TIMEZONE_RESET`` 必须匹配基类 ``_OFFSET_PATTERN`` 的
          ``±HH:00`` 格式（或特殊值 ``SYSTEM``），否则在基类 :meth:`_resolve_offset`
          阶段抛异常；
        - ``env.ENABLE_DB_MACHINE_TIMEZONE_RESET`` 为空 → :meth:`_resolve_time_zone`
          原样返回空串，由基类 :meth:`_execute` 空值短路分支处理（不下发 Job、
          直接短路成功），组件层不抛异常；调用方（flow 层）通常还会在挂节点前
          先做一次 env 空值短路，避免生成注定空跑的 act，属于**性能优化**而非必需；
        - 参数缺失 → 由基类 :meth:`OsTimeZoneInitBase._execute` 通用校验捕获后抛异常；
        - 组件不负责挂载到具体子流程，也不修改实例内部 ``default_time_zone``；
        - shell 幂等：机器当前时区若已与目标一致则基类模板会直接跳过，无副作用。
    """

    #: 日志前缀：与业务动作对齐，便于作业日志检索
    LOG_PREFIX: str = "[os-timezone-reset]"

    #: JobApi task_name：作业平台侧任务名，与业务动作对齐
    JOB_TASK_NAME: str = "DBM-Reset-Os-Timezone"

    def _resolve_time_zone(self, kwargs: Dict[str, Any]) -> str:
        """[钩子实现] 从环境变量读取目标时区值。

        功能说明 / 怎么做：
            - 读取 ``env.ENABLE_DB_MACHINE_TIMEZONE_RESET``（模块加载时即从进程环境
              一次性解析，运行期为字符串常量），作为 OS 时区重置的目标基线值；
            - **本方法只负责"取值"，不负责"取空后怎么办"**：空值语义（未指定目标时区）
              由基类 :meth:`OsTimeZoneInitBase._execute` 的空值短路分支统一处理
              （不下发 Job、直接短路成功），与 MySQL 变体（dbconfig 未配置时返回空）
              行为一致；
            - 非空值的格式合法性（``SYSTEM`` / ``±HH:00``）同样由基类
              :meth:`_resolve_offset` 统一校验，本方法不做前置校验，避免多处分裂。

        :param kwargs: 组件入参原始 dict（本方法未使用；基类已在 :meth:`_execute`
                       中完成 ``bk_cloud_id`` / ``exec_ip`` 的通用校验）
        :return: str，环境变量原始值；可能为空串（触发基类空值短路）、
                 ``SYSTEM``（触发基类 SYSTEM 短路）或 ``±HH:00``（触发下发 Job）

        边界 / 异常：
            - 空串 → 交由基类空值短路处理，本方法不抛异常；
            - 非空但格式非法（既非 ``SYSTEM`` 亦非 ``±HH:00`` / 超出 ``-12:00 ~ +12:00``）
              → 由基类 :meth:`_resolve_offset` 阶段抛异常，本方法不做前置校验
        """
        return env.ENABLE_DB_MACHINE_TIMEZONE_RESET


class OsTimeZoneResetComponent(Component):
    """机器操作系统时区"重置为环境基线"组件（退回资源池等收尾场景）。

    :name: 组件模块名
    :code: 组件唯一编码 ``os_timezone_reset``
    :bound_service: 绑定的 Service 实现 :class:`OsTimeZoneReset`
    :kwargs: 组件入参契约结构体 :class:`OsTimeZoneResetKwargs`，仅用于向调用方
             声明字段结构，``_execute`` 内部仍以 dict 形式读取 ``kwargs``
    """

    name = __name__
    code = "os_timezone_reset"
    bound_service = OsTimeZoneReset
    kwargs = OsTimeZoneResetKwargs
