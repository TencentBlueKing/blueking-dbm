# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

MySQL 机器操作系统时区初始化 pipeline 组件（"从 dbconfig 读取时区"变体）。

模块职责：
    - 定义 MySQL 语义下的时区初始化组件：目标时区来自 DBM 配置中心的
      模块级（``LevelName.MODULE``）``deploy_info.system_time_zone`` 字段；
    - 每次调用仅处理**单一模块**，不再接受集群条目列表，也不做多集群 / 多层一致性校验；
    - 通过继承 :class:`OsTimeZoneInitBase` 复用所有引擎无关能力
      （偏移解析 / shell 模板 / JobApi 下发 / SYSTEM 短路 / ``_execute`` 骨架），
      本模块仅实现"从何获取时区"这一变化点（子类钩子 :meth:`OsTimeZoneInitBase._resolve_time_zone`）。

数据源 / 调用通道：
    - 配置来源：:func:`get_system_time_zone_in_bk_config`
      （``level_name=MODULE`` / ``conf_file=deploy_info`` / ``conf_type=deploy``）
    - 执行通道：由基类统一走 ``JobApi.fast_execute_script``（``bk_scope_type=biz_set``）

边界：
    - 仅支持 ``system_time_zone ∈ {SYSTEM, ±00:00 ~ ±12:00 的整点偏移}``；
    - 不支持 ``Asia/Shanghai`` 等 IANA 命名时区（由基类偏移解析统一拒绝）；
    - 组件内所有影响执行结果的异常均**主动抛出**，不做静默吞异常；
    - 本组件不负责修改 MySQL 实例内部 ``default_time_zone`` 参数，仅处理机器 OS 层时区。

"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.common.os_timezone_init_base import OsTimeZoneInitBase
from backend.flow.utils.base.validate_handler import (
    ValidateHandler,
    validate_int,
    validate_ip_in_list,
    validate_string,
)
from backend.flow.utils.mysql.mysql_bk_config import get_system_time_zone_in_bk_config


@dataclass()
class MySQLInitOsTimeZoneKwargs(ValidateHandler):
    """``MySQLInitOsTimeZoneComponent`` 组件 kwargs 私有变量结构体。

    功能说明 / 怎么做：
        - 显式声明本组件从 pipeline ``kwargs`` 中期望读取的字段；
        - 继承 ``ValidateHandler``：实例化时按 ``field.metadata['validate']`` 逐字段校验类型，
          让 kwargs 契约从入口起就是**强类型**；
        - 作为组件入参契约挂在 ``MySQLInitOsTimeZoneComponent.kwargs`` 上，
          调用方需 ``asdict(...)`` 转 dict 后再挂到 pipeline ``kwargs`` 上下文；
        - 组件仅处理**单一模块**：顶层直接携带 ``db_module_id`` / ``cluster_type`` 两个标量字段。

    :param bk_cloud_id: 云区域 ID，必填
    :param exec_ip: 目标机器 IP 列表；每项须为合法 IPv4 字符串，必填
    :param bk_biz_id: 业务 ID，必填
    :param db_module_id: 集群所属 DB 模块 ID（dbconfig ``level_value``），必填
    :param cluster_type: dbconfig ``namespace``（如 ``tendbha`` / ``tendbcluster`` /
                        ``tendbsingle``），必填

    使用示例::

        kwargs = MySQLInitOsTimeZoneKwargs(
            bk_cloud_id=0,
            exec_ip=["x.x.x.x", "xx.xx.xx.xx"],
            bk_biz_id=100,
            db_module_id=12,
            cluster_type="tendbha",
        )

    边界 / 异常：
        - 任一字段类型不合法（如 ``bk_cloud_id`` 非 int、``exec_ip`` 含非 IPv4 元素、
          ``db_module_id`` 非 int、``cluster_type`` 非 str）
          → ``ValidateHandler.__post_init__`` 抛 ``ValueError``
    """

    bk_cloud_id: int = field(metadata={"validate": validate_int})
    exec_ip: List[str] = field(metadata={"validate": validate_ip_in_list})
    bk_biz_id: int = field(metadata={"validate": validate_int})
    db_module_id: int = field(metadata={"validate": validate_int})
    cluster_type: str = field(metadata={"validate": validate_string})


class MySQLInitOsTimeZone(OsTimeZoneInitBase):
    """MySQL 机器操作系统时区初始化 Service（"从 dbconfig 读取时区"变体）。

    职责：
        - 覆盖基类抽象钩子 :meth:`_resolve_time_zone`：从 DBM 配置中心（模块级
          ``deploy_info``）读取指定模块的 ``system_time_zone`` 作为目标时区；
        - 其余能力（``_execute`` 骨架、偏移解析、shell 模板渲染、JobApi 下发、
          ``SYSTEM`` 短路）全部复用 :class:`OsTimeZoneInitBase` 基类实现。

    使用方式：
        - 通过 ``kwargs`` 传入：
            * ``bk_cloud_id``  云区域 ID
            * ``exec_ip``      目标机器 IP（字符串或列表）
            * ``bk_biz_id``    业务 ID
            * ``db_module_id`` 集群所属 DB 模块 ID（dbconfig ``level_value``）
            * ``cluster_type`` dbconfig ``namespace``（如 ``tendbha`` / ``tendbcluster``）

    边界：
        - 参数缺失 → 由基类 :meth:`OsTimeZoneInitBase._execute` 通用校验捕获后抛异常；
        - ``db_module_id`` / ``cluster_type`` / ``bk_biz_id`` 三个 MySQL 变体特有的
          必填字段由本类 :meth:`_resolve_time_zone` 单独校验；
        - dbconfig 字段缺失 / API 异常 → 记录 ``db_module_id / cluster_type`` 上下文后 re-raise；
        - 仅支持 ``SYSTEM`` 与 ``±00:00 ~ ±12:00`` 整点偏移；
        - 组件不修改实例内部 ``default_time_zone``。
    """

    #: 日志前缀：兼容原实现，保持既有日志检索关键字不变
    LOG_PREFIX: str = "[timezone-init]"

    #: JobApi task_name：兼容原实现，保持作业平台侧任务名不变
    JOB_TASK_NAME: str = "DBM-Init-Mysql-Os-Timezone"

    def _resolve_time_zone(self, kwargs: Dict[str, Any]) -> str:
        """[钩子实现] 从 DBM 配置中心读取目标 OS 时区。

        功能说明 / 怎么做：
            - 依据 kwargs 携带的 ``bk_biz_id`` / ``db_module_id`` / ``cluster_type``
              定位到 DBM 配置中心的 **模块级** ``deploy_info`` 配置文件，读取
              ``system_time_zone`` 字段并原样返回；
            - 本方法只负责"取值"，不做偏移语法校验（由基类 :meth:`_resolve_offset` 统一承担），
              也不处理 ``SYSTEM`` 短路（由基类 :meth:`_execute` 统一承担）；
            - MySQL 变体特有的三个必填字段（``bk_biz_id`` / ``db_module_id`` / ``cluster_type``）
              在此单独校验，缺失即终止流程。

        :param kwargs: 组件入参原始 dict
        :return: str，``SYSTEM``（大小写不敏感）或 ``±HH:00`` 形式的整点偏移
        边界 / 异常：
            - MySQL 变体特有字段缺失 → raise Exception（携带中文错误信息）
            - dbconfig API 抛异常 → 记录 ``db_module_id / cluster_type`` 上下文后 re-raise
        """
        # MySQL 变体特有的三个必填字段校验（基类只校验 bk_cloud_id / exec_ip 通用字段）
        bk_biz_id = kwargs.get("bk_biz_id")
        db_module_id = kwargs.get("db_module_id")
        cluster_type = kwargs.get("cluster_type")

        missing_fields: List[str] = []
        if not bk_biz_id:
            missing_fields.append("bk_biz_id")
        if db_module_id is None:
            missing_fields.append("db_module_id")
        if not cluster_type:
            missing_fields.append("cluster_type")
        if missing_fields:
            err_msg = _("MySQL-OS-时区初始化组件缺失必填参数：{fields}").format(fields=", ".join(missing_fields))
            self.log_error(str(err_msg))
            raise Exception(err_msg)

        # 下游 API 抛异常（包括字段缺失）时记录 db_module_id / cluster_type 上下文后 re-raise
        try:
            system_time_zone: str = get_system_time_zone_in_bk_config(
                bk_biz_id=bk_biz_id,
                db_module_id=db_module_id,
                cluster_type=cluster_type,
            )
        except Exception as e:
            self.log_error(
                _(
                    "{prefix} 获取 deploy_info.set_os_timezone 失败，"
                    "db_module_id={db_module_id}, cluster_type={cluster_type}, error={error}"
                ).format(
                    prefix=self.LOG_PREFIX,
                    db_module_id=db_module_id,
                    cluster_type=cluster_type,
                    error=e,
                )
            )
            raise
        self.log_info(
            _("{prefix} db_module_id={db_module_id}, cluster_type={cluster_type}, " "system_time_zone={tz}").format(
                prefix=self.LOG_PREFIX,
                db_module_id=db_module_id,
                cluster_type=cluster_type,
                tz=system_time_zone,
            )
        )
        return system_time_zone


class MySQLInitOsTimeZoneComponent(Component):
    """MySQL 机器操作系统时区初始化组件。

    :name: 组件模块名
    :code: 组件唯一编码 ``mysql_init_os_timezone``（保持原值以兼容既有 pipeline 存量）
    :bound_service: 绑定的 Service 实现 :class:`MySQLInitOsTimeZone`
    :kwargs: 组件入参契约结构体 :class:`MySQLInitOsTimeZoneKwargs`，仅用于向调用方声明字段结构，
             ``_execute`` 内部仍以 dict 形式读取 ``kwargs``
    """

    name = __name__
    code = "mysql_init_os_timezone"
    bound_service = MySQLInitOsTimeZone
    kwargs = MySQLInitOsTimeZoneKwargs
