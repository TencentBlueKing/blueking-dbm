# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 - 维度注册表运维命令。

模块职责：
    - 面向运维 / DBA 的**只读 + 启停**工具；不做维度的新增写入
    - 维度的新增与元数据同步已由 SDK 自动懒注册接管（见 :func:`backend.db_report.portrait.ingest_summary`）

支持的子操作（通过位置参数 ``action`` 控制）：
    - list    ：列出维度（可按 db_type 过滤）
    - enable  ：启用维度（enabled=True）—— 仅影响 Agent 读侧，不影响 SDK 写入
    - disable ：禁用维度（enabled=False）—— 同上

使用示例::

    # 列出所有维度
    python manage.py sync_portrait_dimensions list

    # 只列 mysql 维度
    python manage.py sync_portrait_dimensions list --db-type mysql

    # 禁用某维度（Agent 不再分析；巡检 task 依然可以上报）
    python manage.py sync_portrait_dimensions disable --db-type mysql --code slow_query

    # 启用某维度
    python manage.py sync_portrait_dimensions enable --db-type mysql --code slow_query

边界：
    - 目标维度不存在（enable / disable） -> CommandError
    - db_type 非法                        -> CommandError
"""
import logging
from typing import Any, Dict, Optional

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_report.models.portrait_dimension_registry import PortraitDimensionRegistry

logger = logging.getLogger("root")

#: 支持的子操作
_ACTION_LIST: str = "list"
_ACTION_ENABLE: str = "enable"
_ACTION_DISABLE: str = "disable"

_ALL_ACTIONS: tuple = (_ACTION_LIST, _ACTION_ENABLE, _ACTION_DISABLE)


class Command(BaseCommand):
    """集群画像维度注册表运维命令。

    职责：
        - 提供 list / enable / disable 三种操作，供运维 / DBA 管理维度启停
        - **不提供 upsert**：维度的新增与元数据同步由 SDK 首次上报时自动完成

    边界：
        - db_type 不在 DBType 枚举内         -> CommandError
        - enable / disable 目标维度不存在    -> CommandError
    """

    help = _("集群画像 - 维度注册表运维命令（list / enable / disable）")

    def add_arguments(self, parser: CommandParser) -> None:
        """定义 CLI 参数。

        :param parser: Django CommandParser
        """
        parser.add_argument(
            "action",
            type=str,
            choices=_ALL_ACTIONS,
            help=_("子操作：list / enable / disable"),
        )
        parser.add_argument(
            "--db-type",
            dest="db_type",
            type=str,
            default="",
            help=_("数据库类型（取值同 DBType 枚举，如 mysql/redis/sqlserver）；list 时可选，其它 action 必填"),
        )
        parser.add_argument(
            "--code",
            dest="code",
            type=str,
            default="",
            help=_("维度短码；enable / disable 时必填"),
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """命令入口：按 action 分发到对应处理方法。"""
        action: str = options["action"]

        try:
            if action == _ACTION_LIST:
                self._handle_list(options)
            elif action == _ACTION_ENABLE:
                self._handle_switch(options, enabled=True)
            elif action == _ACTION_DISABLE:
                self._handle_switch(options, enabled=False)
            else:
                # 由 argparse choices 保证不会走到这里，防御性兜底
                raise CommandError(_("未知 action：{action}").format(action=action))
        except CommandError:
            raise
        except Exception as err:
            logger.exception("[sync_portrait_dimensions] action=%s failed", action)
            raise CommandError(_("执行失败：{err}").format(err=err))

    # ------------------------------------------------------------------
    # 子操作
    # ------------------------------------------------------------------

    def _handle_switch(self, options: Dict[str, Any], enabled: bool) -> None:
        """enable / disable：切换维度 enabled 状态。

        :param options: argparse 解析出的选项 dict
        :param enabled: True 表示启用，False 表示禁用
        :raises CommandError: 目标维度不存在
        """
        db_type: str = self._require_db_type(options)
        code: str = self._require_code(options)

        obj: Optional[PortraitDimensionRegistry] = PortraitDimensionRegistry.objects.filter(
            db_type=db_type, code=code
        ).first()
        if obj is None:
            raise CommandError(_("目标维度不存在：db_type={db_type} code={code}").format(db_type=db_type, code=code))

        if obj.enabled == enabled:
            self.stdout.write(f"[switch][no-change] db_type={db_type} code={code} enabled={enabled}")
            return

        obj.enabled = enabled
        obj.save(update_fields=["enabled", "update_at"])
        self.stdout.write(self.style.SUCCESS(f"[switch][ok] db_type={db_type} code={code} enabled={enabled}"))

    def _handle_list(self, options: Dict[str, Any]) -> None:
        """list：列出维度；--db-type 可选过滤。"""
        db_type: str = (options.get("db_type") or "").strip()

        qs = PortraitDimensionRegistry.objects.all()
        if db_type:
            self._check_db_type(db_type)
            qs = qs.filter(db_type=db_type)
        qs = qs.order_by("db_type", "code")

        if not qs.exists():
            self.stdout.write("no dimension registered")
            return

        self.stdout.write(f"{'db_type':<16}{'code':<32}{'enabled':<10}{'name'}")
        self.stdout.write("-" * 100)
        for obj in qs:
            self.stdout.write(f"{obj.db_type:<16}{obj.code:<32}{str(obj.enabled):<10}{obj.name}")
        self.stdout.write("-" * 100)
        self.stdout.write(self.style.SUCCESS(f"total={qs.count()}"))

    # ------------------------------------------------------------------
    # 私有辅助 - 参数校验
    # ------------------------------------------------------------------

    def _require_db_type(self, options: Dict[str, Any]) -> str:
        """从 options 中取 --db-type 并校验合法性；缺失或非法直接 CommandError。"""
        db_type: str = (options.get("db_type") or "").strip()
        if not db_type:
            raise CommandError(_("--db-type 必填"))
        self._check_db_type(db_type)
        return db_type

    def _require_code(self, options: Dict[str, Any]) -> str:
        """从 options 中取 --code；缺失直接 CommandError。"""
        code: str = (options.get("code") or "").strip()
        if not code:
            raise CommandError(_("--code 必填"))
        return code

    def _check_db_type(self, db_type: str) -> None:
        """校验 db_type 必须落在 DBType 枚举内。"""
        valid_values: set = {choice[0] for choice in DBType.get_choices()}
        if db_type not in valid_values:
            raise CommandError(
                _("非法 db_type={db_type}，允许值：{allow}").format(db_type=db_type, allow=sorted(valid_values))
            )
