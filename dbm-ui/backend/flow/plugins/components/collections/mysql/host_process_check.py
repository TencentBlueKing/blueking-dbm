# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

MySQL 主机进程存活检查 bamboo 原子节点。

模块职责：
  - 承载"revoke 流程 → MySQL 主机进程存活检查"的采集环节：
    渲染 shell → 交给 :class:`ExecuteShellScriptService` 下发 → 父类完成 Job 轮询与 <ctx> 提取
    → 把 <ctx> JSON 写入 ``trans_data.<write_payload_var>`` 供下游节点读取
  - 与项目内其它 `xxx_ExecuteShellScriptService` 保持一致：均通过 `kwargs["cluster"]["shell_command"]`
    注入脚本；均通过 `write_payload_var` + `trans_data` 传递 <ctx> JSON

设计要点：
  - **薄封装**：只重写 `_execute`（渲染脚本 + 兜底 trans_data）；Job 下发 / 轮询 / <ctx> 正则提取 /
    结果写 trans_data 全部复用父类，杜绝重复实现
  - **仅采集不判定**：本节点仅负责采集 `<ctx>` JSON 落到 `trans_data`；是否 `passed / MYSQL_STILL_ALIVE`
    的语义判定由下游专用决策节点承担，本节点只在 Job 层面反馈"脚本下发成功/失败"
  - **`write_payload_var` 契约**：**要求上层建节点时显式传入**（如
    ``write_payload_var="mysql_process_check_ctx"``），符合父类既有约定
  - **`trans_data` 兜底**：上层若未准备 `trans_data`，子类 `_execute` 里注入
    ``types.SimpleNamespace()`` 占位，避免父类 `setattr` 时抛异常
"""

import logging
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.mysql.revoke.base.mysql_process_check_script import (
    build_mysql_process_check_script,
)
from backend.flow.plugins.components.collections.common.exec_shell_script import ExecuteShellScriptService

logger = logging.getLogger("flow")


class MySQLHostProcessCheckService(ExecuteShellScriptService):
    """MySQL 主机进程存活检查 bamboo 原子节点（薄封装版）。

    职责：
      - 渲染 shell 脚本并注入到 ``kwargs["cluster"]["shell_command"]``
      - 复用 :class:`ExecuteShellScriptService` 完成 Job 下发 / 轮询 / <ctx> JSON 提取
        以及"把 <ctx> JSON 写入 ``trans_data.<write_payload_var>``"
      - **不做判定**：`passed / MYSQL_STILL_ALIVE / CHECK_ERROR` 的语义判定由下游决策节点承担

    kwargs 契约（上层建节点时必须传入）：
      - ``root_id``            (str, 必填)  bamboo root pipeline id
      - ``node_id``            (str, 必填)  bamboo 节点 id
      - ``node_name``          (str, 必填)  bamboo 节点名，用于 Job 任务命名
      - ``bk_cloud_id``        (int, 必填)  目标主机云区域 id（组内所有 IP 共享同一云区域）
      - ``exec_ip``            (List[str], 必填)  目标主机 IP 列表；**必须是 list**，
        单机也用 ``["1.1.1.1"]``。组内多机时一次 Job 下发所有 IP，
        配合 ``write_op=APPEND`` 将每台机器的 <ctx> 汇聚为 ``{ip: <ctx>}`` 结构写入
        ``trans_data.<write_payload_var>``
      - ``expected_proc_names``(Optional[List[str]])     进程名白名单；不传走默认

    额外要求（上层建节点时显式传入，符合父类既有契约）：
      - ``inputs.write_payload_var``  (str, 必填)  例如 ``"mysql_process_check_ctx"``；
        父类 :meth:`BkJobService._schedule` 会把 <ctx> JSON ``setattr`` 到
        ``trans_data.<write_payload_var>``

    输出（下游读取入口）：
      - ``trans_data.<write_payload_var>``  <ctx> JSON dict（父类写入）；下游节点自行调用
        :meth:`HostRevokeChecker.parse_process_check_result` 做判定
      - ``data.outputs.exec_ips`` / ``data.outputs.ext_result`` 等由父类写入

    边界：
      - kwargs 关键字段缺失 / 脚本渲染失败 -> 记 error 日志并返回 False，bamboo 节点失败
      - 未传 ``write_payload_var`` -> 记 error 日志并返回 False，bamboo 节点失败
      - Job 下发失败 / 超时 / <ctx> 提取失败 -> 父类返回 False，bamboo 节点失败
    """

    def _execute(self, data, parent_data) -> bool:
        """渲染脚本 → 注入 kwargs → 兜底 trans_data → 交父类下发。

        怎么做：
          - 从 ``kwargs["expected_proc_names"]`` 取进程名白名单（可选）
          - 调 :func:`build_mysql_process_check_script` 渲染脚本
          - 塞进 ``kwargs["cluster"]["shell_command"]`` 供父类读取
          - 强制 ``account_alias = DBA_ROOT_USER``（父类 body 组装时会带上）
          - 若上层未准备 ``trans_data``，注入 :class:`SimpleNamespace` 占位

        :param data: bamboo 节点数据对象
        :param parent_data: bamboo 父节点数据对象（本节点不使用）
        :return: True 进入 schedule 阶段；False 表示 execute 阶段直接失败
        边界：
          - ``kwargs["exec_ip"]`` 缺失 / 脚本渲染 ValueError -> 记 error 并返回 False
          - 未传 ``inputs.write_payload_var`` -> 记 error 并返回 False（父类契约要求）
        """
        kwargs: Dict[str, Any] = data.get_one_of_inputs("kwargs") or {}
        node_name: str = kwargs.get("node_name") or self.__class__.__name__

        # 1) 必备参数校验（父类 `_execute` 也会读，这里提前校验以给出更明确的日志）
        exec_ip: Any = kwargs.get("exec_ip")
        if not isinstance(exec_ip, list) or not exec_ip:
            self.log_error(
                _("[{}] kwargs.exec_ip 必须为非空 list（单机场景也需传 ['x.x.x.x']），实际={}").format(
                    node_name, type(exec_ip).__name__
                )
            )
            return False
        # 元素类型校验：list 内必须全部是非空 str（父类 splice_exec_ips_list 支持 dict 但本节点收敛为 str）
        for item in exec_ip:
            if not isinstance(item, str) or not item:
                self.log_error(_("[{}] kwargs.exec_ip 列表元素必须为非空 str，实际含 {}").format(node_name, item))
                return False

        # 2) 显式检查 write_payload_var（父类契约：无此变量则拿不到 <ctx> JSON）
        write_payload_var: Optional[str] = data.get_one_of_inputs("write_payload_var")
        if not write_payload_var:
            self.log_error(
                _("[{}] 缺少 inputs.write_payload_var；请在建节点时显式传入，例如 'mysql_process_check_ctx'").format(node_name)
            )
            return False

        # 3) 渲染脚本
        expected_proc_names: Optional[List[str]] = kwargs.get("expected_proc_names")
        try:
            script_content: str = build_mysql_process_check_script(expected_proc_names=expected_proc_names)
        except ValueError as err:
            self.log_error(_("[{}] 脚本渲染失败: {}").format(node_name, err))
            return False

        # 4) 注入到父类约定的位置：kwargs["cluster"]["shell_command"]
        cluster_kwargs: Dict[str, Any] = kwargs.setdefault("cluster", {})
        cluster_kwargs["shell_command"] = script_content

        # 5) 强制以 root 身份执行（`ss -Hlntp` 需要 root 才能看到所有进程的 users:() 段）
        kwargs.setdefault("account_alias", DBA_ROOT_USER)

        # 6) 兜底 trans_data：父类 `_schedule` 需要 setattr(trans_data, write_payload_var, ...)，
        #    若上层未准备则注入 SimpleNamespace 占位；REWRITE 模式只写不读，此占位足够
        if data.get_one_of_inputs("trans_data") is None:
            data.inputs.trans_data = SimpleNamespace()

        self.log_info(
            _("[{node}] 开始下发 MySQL 主机进程存活检查脚本；ips={ips}, write_payload_var={var}").format(
                node=node_name, ips=exec_ip, var=write_payload_var
            )
        )

        # 7) 交给父类完成 body 组装 + Job 下发；_schedule 完全复用父类实现
        return super()._execute(data, parent_data)


class MySQLHostProcessCheckComponent(Component):
    """revoke 流程 · MySQL 主机进程存活检查 bamboo 组件。

    上层建节点示例（多 IP 场景，APPEND 汇聚为 {ip: <ctx>}）：
      act.component.inputs.kwargs = Var(type=Var.PLAIN, value={
          "root_id": root_id,
          "node_id": node_id,
          "node_name": "MySQL主机进程存活检查",
          "bk_cloud_id": bk_cloud_id,
          "exec_ip": ["1.1.1.1", "2.2.2.2"],   # 必须为 list，单机也用 ["1.1.1.1"]
          # 可选：进程名白名单
          "expected_proc_names": ["mysqld", "mysql-proxy", "mariadbd"],
          # 关键：APPEND 模式将每台机器的 <ctx> 汇聚到 trans_data.<write_payload_var>
          # 结构为 {ip: <ctx_dict>}；不传则走 REWRITE，多 IP 会互相覆盖
          "write_op": WriteContextOpType.APPEND.value,
      })
      # 必填：父类契约，指定 <ctx> JSON 写入 trans_data 的属性名
      act.component.inputs.write_payload_var = Var(type=Var.PLAIN, value="host_process_check__grp0")

    下游节点读取姿势：
      ctx_dict = getattr(trans_data, "host_process_check__grp0", None) or {}  # {ip: <ctx>}
      for ip, ctx_json in ctx_dict.items():
          result = HostRevokeChecker.parse_process_check_result(script_output_json=ctx_json, ip=ip)
    """

    name = __name__
    code = "mysql_host_process_check"
    bound_service = MySQLHostProcessCheckService
