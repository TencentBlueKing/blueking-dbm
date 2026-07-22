# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

机器操作系统时区初始化 pipeline 组件"公共基类"模块（DB 引擎无关）。

模块职责：
    - 承载**所有变体共享**的机器 OS 时区初始化能力：
        * UTC 偏移解析（``±HH:00`` → POSIX ``Etc/GMT±N`` + ``date +%z`` 字面偏移）
        * 幂等 shell 脚本模板 :data:`init_os_timezone_script`（``timedatectl`` 唯一方案）
        * JobApi 下发通道（``fast_execute_script``，业务集作用域）
        * 统一 ``_execute`` 骨架：入参校验 → 解析时区源 → SYSTEM 短路 → 下发 Job
    - 通过**抽象钩子** :meth:`OsTimeZoneInitBase._resolve_time_zone` 把"目标时区从何而来"
      这一变化点开放给子类，实现"模板方法"模式；
    - 定位在 ``common`` 目录：**引擎无关 / 业务无关**，MySQL / SQLServer / Redis /
      "退回资源池重置"等场景均可复用。

数据源 / 调用通道：
    - 时区值来源：由子类 :meth:`_resolve_time_zone` 决定（可来自 dbconfig / 硬编码常量 /
      环境变量 / CMDB / 其他，本基类不假设）；
    - 执行通道：``JobApi.fast_execute_script``（``bk_scope_type=biz_set``，
      ``account_alias=DBA_ROOT_USER``）。

支持的时区值域：
    - ``SYSTEM``（大小写不敏感）：跟随操作系统，不下发 Job，直接短路成功；
    - ``±HH:00`` 整点偏移（``-12:00 ~ +12:00``）：映射为 POSIX ``Etc/GMT±N`` 后下发；
    - 其它值（``Asia/Shanghai`` 等 IANA 命名 / 带分钟位偏移等）→ 抛异常。

边界：
    - 子类若不覆盖 :meth:`_resolve_time_zone` 将直接抛 ``NotImplementedError``；
    - 组件内所有影响执行结果的异常均**主动抛出**，不做静默吞异常；
    - 本基类不修改任何 DB 实例内部参数，仅处理机器 OS 层时区。

历史沿革：
    - 本模块由 :mod:`backend.flow.plugins.components.collections.mysql.mysql_os_timezone_init`
      中的重头实现物理搬迁而来，通过"公共基类 + 钩子"消除了原 ``common → mysql`` 反向依赖，
      同时保证外部使用方（``MySQLInitOsTimeZoneComponent`` / ``MySQLInitOsTimeZoneKwargs``
      的 import 路径）**零变更**。
"""
import copy
import re
from typing import Any, Dict, List, NamedTuple, Pattern

from django.utils.translation import gettext_lazy as _
from jinja2.sandbox import SandboxedEnvironment as Environment

from backend import env
from backend.components import JobApi
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.script_template import fast_execute_script_common_kwargs
from backend.utils.string import base64_encode

# ---------------------------------------------------------------------------
# 模块级常量
# ---------------------------------------------------------------------------

#: 表示 "跟随操作系统" 语义的特殊时区值；比较时统一 upper() 做大小写不敏感匹配
_SYSTEM_TZ: str = "SYSTEM"

#: 严格匹配 ``±HH:00`` 形式的 UTC 偏移（本需求范围内 dbconfig 只会返回整点偏移）
#: - 分钟位必须为 ``:00``，不允许 ``:30`` / ``:45`` 等
#: - 小时位 1~2 位数字，越界校验交由 ``_MAX_OFFSET_HOUR`` 逻辑判定
_OFFSET_PATTERN: Pattern[str] = re.compile(r"^([+-])(\d{1,2}):00$")

#: 合法 UTC 整点偏移的绝对值上限（含），来源于业务约束 ``-12:00 ~ +12:00``
_MAX_OFFSET_HOUR: int = 12


class _ResolvedOffset(NamedTuple):
    """归一化偏移的两种表达（同源派生，一次校验、一次产出）。

    功能说明 / 怎么做：
        - 供 :meth:`OsTimeZoneInitBase._resolve_offset` 单次校验入参后，
          同时暴露 shell 侧需要的 POSIX 时区名与 ``date +%z`` 字面偏移；
        - 使用 ``NamedTuple`` 而非 ``tuple``，避免调用方按位置解包出错。

    :param posix_tz: POSIX ``Etc/GMT±N`` 时区名，供 ``timedatectl set-timezone`` 使用
    :param date_z: ``date +%z`` 输出格式（``±HHMM``），供 shell 幂等短路时的字面比较
    """

    posix_tz: str
    date_z: str


#: 修改操作系统时区的 shell 脚本模板（Jinja2 语法）
#: - 仅使用 ``timedatectl set-timezone`` 一种方案，**不做任何回退**
#: - 前置校验 ``/usr/share/zoneinfo/<time_zone>`` 与 ``timedatectl`` 命令必须存在
#: - ``set -euo pipefail`` 保证任一关键步骤失败即以非零码退出
#: - 幂等短路：当 ``date +%z`` 与渲染进来的 ``target_offset`` 完全一致（如均为 ``+0800``）时，
#:   跳过 ``timedatectl set-timezone``，避免对已在目标偏移下的机器做无意义写入
init_os_timezone_script: str = r"""#!/bin/bash
set -euo pipefail

TZ_NAME="{{ time_zone }}"
TARGET_OFFSET="{{ target_offset }}"
ZONEINFO_PATH="/usr/share/zoneinfo/${TZ_NAME}"

echo "[timezone-init] target timezone: ${TZ_NAME}"
echo "[timezone-init] target offset:   ${TARGET_OFFSET}"
echo "[timezone-init] current date before change: $(date)"

# Idempotent short-circuit: read current UTC offset (e.g. +0800 / -0500) and
# compare literally with the target offset.
# - `date +%z` on GNU coreutils is stable as +/-HHMM (4 digits); an empty
#   string is treated as "unknown" and falls back to timedatectl.
CURRENT_OFFSET="$(date +%z 2>/dev/null || true)"
echo "[timezone-init] current offset:  ${CURRENT_OFFSET}"

if [ -n "${CURRENT_OFFSET}" ] && [ "${CURRENT_OFFSET}" = "${TARGET_OFFSET}" ]; then
    echo "[timezone-init] current offset already equals target offset (${TARGET_OFFSET}), skip timedatectl set-timezone"
    echo "[timezone-init] timedatectl status (unchanged):"
    timedatectl status || true
    echo "[timezone-init] current date after change: $(date)"
    echo "[timezone-init] set timezone to ${TZ_NAME} successfully (skipped, already in target offset)"
    exit 0
fi

if [ ! -f "${ZONEINFO_PATH}" ]; then
    echo "[timezone-init][ERROR] zoneinfo file not found: ${ZONEINFO_PATH}" >&2
    exit 1
fi

if ! command -v timedatectl >/dev/null 2>&1; then
    echo "[timezone-init][ERROR] 'timedatectl' command not available on this host" >&2
    exit 1
fi

echo "[timezone-init] timedatectl status before change:"
timedatectl status || true

timedatectl set-timezone "${TZ_NAME}"

echo "[timezone-init] timedatectl status after change:"
timedatectl status

echo "[timezone-init] current date after change: $(date)"
echo "[timezone-init] set timezone to ${TZ_NAME} successfully"
"""


class OsTimeZoneInitBase(BkJobService):
    """机器操作系统时区初始化 Service 公共基类（引擎无关）。

    职责：
        - 承载所有变体共享的能力：偏移解析、shell 模板、JobApi 下发、``_execute`` 骨架、
          SYSTEM 短路；
        - 通过抽象钩子 :meth:`_resolve_time_zone` 把"目标时区从何而来"这一变化点开放给子类。

    使用方式（模板方法模式）：
        - 子类必须实现 :meth:`_resolve_time_zone`：返回 ``SYSTEM`` 或 ``±HH:00`` 形式字符串；
        - 子类**可选覆盖** :attr:`LOG_PREFIX` / :attr:`JOB_TASK_NAME` 以携带业务语义化标识；
        - 子类**通常无需**覆盖 :meth:`_execute` / :meth:`_resolve_offset` / :meth:`_dispatch_job`。

    子类扩展示例::

        class MyTimeZoneInit(OsTimeZoneInitBase):
            LOG_PREFIX = "[timezone-init-mycase]"
            JOB_TASK_NAME = "DBM-Init-MyCase-Os-Timezone"

            def _resolve_time_zone(self, kwargs):
                return "+08:00"  # 或 "SYSTEM" 触发短路

    边界：
        - 子类若不实现 :meth:`_resolve_time_zone` → 抛 ``NotImplementedError``；
        - 时区值不合法（非 ``SYSTEM``、非 ``±HH:00``、越界等）→ 由 :meth:`_resolve_offset` 抛异常；
        - JobApi 异常 → 由 :meth:`_dispatch_job` 向上传播；
        - 子类应保证 :meth:`_resolve_time_zone` 抛出的业务异常已携带足够上下文。
    """

    #: 日志行统一前缀；子类覆盖以携带业务语义（如 ``[os-timezone-reset]``）
    LOG_PREFIX: str = "[timezone-init]"

    #: JobApi ``task_name`` 字段值，用于在作业平台侧标识本次任务；子类可覆盖
    JOB_TASK_NAME: str = "DBM-Init-Os-Timezone"

    # ------------------------------------------------------------------
    # 抽象钩子：子类必须实现
    # ------------------------------------------------------------------

    def _resolve_time_zone(self, kwargs: Dict[str, Any]) -> str:
        """[抽象钩子] 根据 pipeline ``kwargs`` 决定目标时区字符串。

        功能说明 / 怎么做：
            - 变化点：不同子类的"时区来源"不同——可能来自 dbconfig（按业务模块）、
              硬编码常量（退回资源池）、环境变量、CMDB 主机属性等；
            - 本方法**只负责产出时区字符串**，不负责下发 Job，也不做偏移语法校验
              （偏移语法校验统一由 :meth:`_resolve_offset` 承担，避免多处校验分裂）。

        :param kwargs: 组件入参原始 dict（``data.get_one_of_inputs("kwargs")`` 的结果）
        :return: str，``SYSTEM``（大小写不敏感）或 ``±HH:00`` 形式的整点偏移
        边界 / 异常：
            - 子类未实现 → raise ``NotImplementedError``
            - 子类实现内部若查询失败 / 字段缺失 → 应主动抛异常，携带定位上下文
        """
        raise NotImplementedError(_("OsTimeZoneInitBase 子类必须实现 _resolve_time_zone(kwargs) -> str"))

    # ------------------------------------------------------------------
    # 模板方法：统一 _execute 骨架，子类通常无需覆盖
    # ------------------------------------------------------------------

    def _execute(self, data, parent_data) -> bool:
        """组件主流程入口（模板方法）。

        流程步骤：
            1. 从 ``data`` 中提取 pipeline ``kwargs``；
            2. 通用入参校验：``bk_cloud_id`` / ``exec_ip`` 必填；
            3. 调用子类钩子 :meth:`_resolve_time_zone` 获取目标时区字符串；
            4. 若为**空值**（``None`` / 空串 / 纯空白）则视为"未指定目标时区"，
               短路返回、不下发 Job；
            5. 若为 ``SYSTEM`` 则短路返回、不下发 Job；
            6. 否则解析偏移 → 复用 :meth:`_dispatch_job` 下发 Job。

        :param data: pipeline 框架注入的输入数据容器
        :param parent_data: 父流程数据容器（本组件未使用）
        :return: bool，True 表示组件成功（含 SYSTEM / 空值短路场景）；失败一律抛异常，不返回 False
        边界 / 异常：
            - 缺参 → raise Exception（携带中文错误信息）
            - 时区值为空 → 短路返回 True，不下发 Job，不抛异常
            - 时区值非法（非空、非 SYSTEM、非 ±HH:00）→ 由 :meth:`_resolve_offset` 抛 Exception
            - JobApi 异常 → 由 :meth:`_dispatch_job` 向上传播
        """
        kwargs: Dict[str, Any] = data.get_one_of_inputs("kwargs") or {}

        # ---- 步骤 A：通用入参校验（bk_cloud_id / exec_ip 是所有变体共同的最小契约） ----
        bk_cloud_id = kwargs.get("bk_cloud_id")
        exec_ip = kwargs.get("exec_ip")

        missing_fields: List[str] = []
        if bk_cloud_id is None:
            missing_fields.append("bk_cloud_id")
        if not exec_ip:
            missing_fields.append("exec_ip")
        if missing_fields:
            err_msg = _("OS-时区初始化组件缺失必填参数：{fields}").format(fields=", ".join(missing_fields))
            self.log_error(str(err_msg))
            raise Exception(err_msg)

        # ---- 步骤 B：调用子类钩子获取目标时区（变化点） ----
        system_time_zone: str = self._resolve_time_zone(kwargs)
        self.log_info(
            _("{prefix} 解析得到目标时区: system_time_zone={tz}").format(prefix=self.LOG_PREFIX, tz=system_time_zone)
        )

        # ---- 步骤 C：空值短路，不下发 Job ----
        # 子类钩子可能因 dbconfig 未配置 / 字段为空等原因返回空值（None / 空串 / 纯空白），
        # 此时视为"未指定目标时区"，保持机器现有时区不变，直接短路成功，不下发 Job
        if system_time_zone is None or not str(system_time_zone).strip():
            self.log_info(
                _("{prefix} 目标时区为空（system_time_zone={tz!r}），" "视为未指定目标时区，跳过 OS 时区修改，不下发 Job").format(
                    prefix=self.LOG_PREFIX, tz=system_time_zone
                )
            )
            # ext_result 设置为 bool 类型，就不需要巡检结果
            data.outputs.ext_result = True
            return True

        # ---- 步骤 D：SYSTEM 短路，不下发 Job ----
        if system_time_zone.strip().upper() == _SYSTEM_TZ:
            self.log_info(
                _("{prefix} 目标时区跟随操作系统（system_time_zone=SYSTEM），" "跳过 OS 时区修改，不下发 Job").format(prefix=self.LOG_PREFIX)
            )
            # ext_result 设置为 bool 类型，就不需要巡检结果
            data.outputs.ext_result = True
            return True

        # ---- 步骤 D：映射到 POSIX 时区名并下发 Job ----
        # 一次校验 + 一次产出：posix_tz 供 timedatectl 使用；date_z 供 shell 幂等短路时字面比较
        resolved: _ResolvedOffset = self._resolve_offset(system_time_zone)
        self.log_info(
            _("{prefix} 最终目标 OS 时区（POSIX 名）: {posix_tz}，" "目标偏移（date +%z 格式）: {date_z}").format(
                prefix=self.LOG_PREFIX, posix_tz=resolved.posix_tz, date_z=resolved.date_z
            )
        )

        return self._dispatch_job(
            kwargs=kwargs,
            bk_cloud_id=bk_cloud_id,
            time_zone=resolved.posix_tz,
            target_offset=resolved.date_z,
            data=data,
        )

    # ------------------------------------------------------------------
    # 私有工具方法
    # ------------------------------------------------------------------

    def _resolve_offset(self, offset: str) -> _ResolvedOffset:
        """把 ``±HH:00`` UTC 偏移解析为 POSIX 时区名 + ``date +%z`` 字面偏移。

        设计要点 / 怎么做：
            - 本方法**仅接受**形如 ``±HH:00`` 的整点偏移字符串；``SYSTEM`` 已在
              :meth:`_execute` 上游做了短路处理，不会进入本方法，因此这里将
              ``SYSTEM`` 视为**非法值**并抛异常，避免语义混淆；
            - 单次匹配 ``_OFFSET_PATTERN``、单次越界校验，同时产出两种业务表达，
              避免两个下游用途各自校验、错误消息分裂：
                * POSIX ``Etc/GMT±N`` 名：符号与 UTC 偏移**相反**（POSIX 历史约定）：
                  ``+08:00`` → ``Etc/GMT-8``；``-05:00`` → ``Etc/GMT+5``；``+00:00`` → ``Etc/GMT0``
                * ``date +%z`` 字面偏移：GNU coreutils 输出 4 位数字 ``±HHMM``，
                  与 UTC 偏移**同号**：``+08:00`` → ``+0800``；``-05:00`` → ``-0500``
            - 本项目业务范围内分钟位固定 ``00``，因此 ``date +%z`` 后两位恒为 ``00``。

        :param offset: 形如 ``+08:00`` / ``-05:00`` 的整点偏移字符串
        :return: :class:`_ResolvedOffset`，含 ``posix_tz`` 与 ``date_z`` 两个字段

        边界 / 异常：
            - 格式不匹配 ``^([+-])(\\d{1,2}):00$``（含 ``SYSTEM`` / IANA 命名时区 /
              带分钟位的偏移等）→ raise Exception
            - 小时绝对值 > ``_MAX_OFFSET_HOUR`` → raise Exception
        """
        m = _OFFSET_PATTERN.match(offset or "")
        if not m:
            err_msg = _("非法的 system_time_zone 值 '{value}'：仅允许形如 '±HH:00' 的整点偏移（-12:00 ~ +12:00）").format(value=offset)
            self.log_error(str(err_msg))
            raise Exception(err_msg)

        sign: str = m.group(1)
        hour: int = int(m.group(2))
        if hour > _MAX_OFFSET_HOUR:
            err_msg = _("system_time_zone '{value}' 越界，允许范围为 -{max}:00 ~ +{max}:00").format(
                value=offset, max=_MAX_OFFSET_HOUR
            )
            self.log_error(str(err_msg))
            raise Exception(err_msg)

        # 1) POSIX 时区名：符号反转；小时为 0 时统一为 "Etc/GMT0"（无正负号）
        if hour == 0:
            posix_tz: str = "Etc/GMT0"
        else:
            posix_sign: str = "-" if sign == "+" else "+"
            posix_tz = f"Etc/GMT{posix_sign}{hour}"

        # 2) date +%z 字面偏移：与 UTC 偏移同号，4 位数字（分钟位固定 00）
        date_z: str = f"{sign}{hour:02d}00"

        return _ResolvedOffset(posix_tz=posix_tz, date_z=date_z)

    def _dispatch_job(
        self,
        kwargs: Dict[str, Any],
        bk_cloud_id: Any,
        time_zone: str,
        target_offset: str,
        data: Any,
    ) -> bool:
        """渲染 shell 脚本并通过 JobApi 下发到目标机器。

        :param kwargs: 组件入参原始 dict（用于 splice_exec_ips_list 与 target_server 组装）
        :param bk_cloud_id: 云区域 ID
        :param time_zone: 已映射的 POSIX 时区名（``Etc/GMT±N``）
        :param target_offset: ``date +%z`` 字面格式的目标偏移（``±HHMM``），用于 shell 幂等短路
        :param data: pipeline 框架 data 容器；成功后写入 ``ext_result`` / ``exec_ips``
        :return: True
        边界 / 异常：
            - 由 ``JobApi.fast_execute_script`` 抛出的异常将直接向上传播（不吞异常）
        """
        jinja_env = Environment()
        template = jinja_env.from_string(init_os_timezone_script)
        script_content = template.render(time_zone=time_zone, target_offset=target_offset)

        exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"])
        target_ip_info = [{"bk_cloud_id": bk_cloud_id, "ip": ip} for ip in exec_ips]
        body = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": self.JOB_TASK_NAME,
            "script_content": base64_encode(script_content),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }

        common_kwargs = copy.deepcopy(fast_execute_script_common_kwargs)
        common_kwargs["account_alias"] = DBA_ROOT_USER

        resp = JobApi.fast_execute_script({**common_kwargs, **body}, raw=True)
        self.log_info(f"fast execute script response: {resp}")
        self.log_info(f"job url: {self.__url__(resp['data']['job_instance_id'])}")

        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True
