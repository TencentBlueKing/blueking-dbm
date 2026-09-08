# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

------------------------------------------------------------------------------

mysql pt-table-sync 修复结果摘要组件（trans_data 展平版）。

模块职责：
  - 面向 pt-table-sync 数据修复子流程末尾节点：把 :class:`PtTableSyncContext.result`
    （结构：{slave_ip: [{db_name, table_name, status, reason, ...}, ...]}）按
    (集群, slave-ip, 库, 表) 四元组展平为一行行摘要，写入 FlowSummary.summary。

设计要点 / 数据源 / 调用通道：
  - 采用与 :class:`MysqlClusterApplySummaryComponent` 同款的\"继承 + 薄壳\"分层：
    :class:`PtTableSyncSummaryService` 继承 :class:`MysqlFlowOutputSummaryService`，
    `_execute` 只做一件事——从 trans_data 展平出 items → 塞回 kwargs
    → 回调 super()._execute()，preset 校验 / Flow 兜底 / 幂等落库全部沿用通用底座，
    避免逻辑重复。
  - 单据侧调用极简：仅传 `cluster_domain + slave_ip` 两个静态定位字段；
    业务字段（db_name / table_name / status / reason）从 trans_data 反查。

边界：
  - trans_data 无 result 或 result 中无对应 slave_ip -> items 为空，父类走 no-op 返回 True。
  - 单行缺 db_name / table_name / status -> log_warning 跳过该行，不阻断其他行。
  - kwargs 缺 cluster_domain / slave_ip -> log_error 返回 False（对齐父类"preset 非法"的显式失败语义）。
  - 无关联 Flow / 反查结果为空等其他兜底路径 -> 沿用父类行为，不重复实现。
"""

import logging
from typing import Any, Dict, List, Optional

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.mysql.flow_output_summary import MysqlFlowOutputSummaryService

logger = logging.getLogger("flow")

#: 本组件固定服务的预设 key；对齐 flow_output_presets.PtTableSyncSummarySerializer。
#: 调用方无需感知，Service 强制注入到 kwargs["preset"]。
_FIXED_PRESET_KEY: str = "pt_table_sync"


class PtTableSyncSummaryService(MysqlFlowOutputSummaryService):
    """mysql pt-table-sync 数据修复摘要 Service（trans_data 展平装配）。

    功能说明：
      - 从 kwargs 读取集群/节点定位信息（`cluster_domain` + `slave_ip`），
        从 :class:`PtTableSyncContext.result` 读取当前 slave 的修复结果列表，
        按 (集群, ip, 库, 表) 四元组展平为对齐
        :class:`PtTableSyncSummarySerializer` 契约的 items 后回调
        :meth:`MysqlFlowOutputSummaryService._execute` 完成落库。
      - 调用方**不再传业务字段**（db_name / table_name / status / reason），
        全部由 Service 从 trans_data 展平产生。

    输入参数（即 kwargs 字段结构）：
      - cluster_domain (str, 必填, 非空): 集群主域名，前端展示第一列
      - slave_ip (str, 必填, 非空): 修复目标 slave IP；用于从 trans_data.result 取子列表
      - global_data (dict, 可选): 由 pipeline 框架传入，用于激活国际化

    输出：
      - 返回 bool；行为语义与父类一致：
          * True: 写入成功 / no-op（trans_data 无结果、无关联 Flow 等）
          * False: 定位字段缺失 / 父类落库失败

    边界 / 异常：
      - kwargs.cluster_domain / kwargs.slave_ip 缺失 -> log_error 返回 False。
      - trans_data 无 result 属性或 result 中无对应 slave_ip -> items 为空，
        父类走\"items 为空 no-op\"路径返回 True。
      - 单行缺 db_name / table_name / status -> log_warning 跳过该行，
        不中止其他行，也不阻断整体写入。
      - 无关联 Flow 的临时 pipeline -> 沿用父类 Flow 兜底逻辑，不重复实现。
    """

    #: 必需的静态定位字段清单
    _REQUIRED_KWARGS: List[str] = ["cluster_domain", "slave_ip"]

    def _execute(self, data, parent_data) -> bool:
        kwargs: Dict[str, Any] = data.get_one_of_inputs("kwargs") or {}

        # 1) 静态入参校验：定位字段缺失直接失败，避免展平出无主键的脏行
        for key in self._REQUIRED_KWARGS:
            if not kwargs.get(key):
                self.log_error(_("pt-table-sync 摘要写入缺少必填 kwargs 字段: {}").format(key))
                return False
        cluster_domain: str = kwargs["cluster_domain"]
        slave_ip: str = kwargs["slave_ip"]

        # 2) 从 trans_data 展平 items；无结果时 items=[]，交给父类走 no-op 分支
        trans_data = data.get_one_of_inputs("trans_data")
        items: List[Dict[str, Any]] = self._build_items_from_trans_data(trans_data, cluster_domain, slave_ip)

        # 3) 将装配好的 items 与固定 preset 塞回 kwargs，交给父类完成 preset 校验 / Flow 兜底 / 落库
        kwargs["preset"] = _FIXED_PRESET_KEY
        kwargs["items"] = items
        data.inputs.kwargs = kwargs
        return super()._execute(data, parent_data)

    def _build_items_from_trans_data(
        self,
        trans_data: Any,
        cluster_domain: str,
        slave_ip: str,
    ) -> List[Dict[str, Any]]:
        """按 trans_data.result[slave_ip] 展平为 :class:`PtTableSyncSummarySerializer` 契约的 items。

        功能说明 / 怎么做：
          - 从 trans_data.result 中取当前 slave_ip 对应的修复结果列表；
          - 逐行装配 `(cluster_domain, ip, db_name.table_name, status, reason)`；
          - unique_key 按预设 Serializer 约定拼接 `"{domain}|{ip}|{db}|{table}"` 作为主键单字段，
            走 FlowOutputHandler.insert_data 主键合并分支实现同 (集群, ip, 库, 表) 的"后写覆盖前写"幂等；
          - 缺关键字段的行跳过并 log_warning，避免脏行触发预设 Serializer 校验失败牵连整体写入。

        :param trans_data: pipeline 运行期上下文对象；期望是 :class:`PtTableSyncContext`
        :param cluster_domain: 集群主域名，摘要第一列
        :param slave_ip: 修复目标 slave IP，摘要第二列 & unique_key 组成部分
        :return: 已对齐预设 Serializer 字段契约的 items 列表；长度 ≤ 原始 rows 长度
                 （无结果 / 脏行会被过滤掉）

        边界 / 异常：
          - trans_data 无 result 属性或 result 不含 slave_ip -> 返回 []，父类走 no-op；
          - rows 单行缺 db_name / table_name / status -> log_warning 跳过；
          - reason 缺失 -> 填空串，符合预设 Serializer 的 allow_blank 契约。
        """
        result_map: Optional[Dict[str, List[Dict[str, Any]]]] = getattr(trans_data, "result", None)
        if not result_map or slave_ip not in result_map:
            self.log_info(_("trans_data.result 无 slave_ip=[{}] 的修复结果，跳过摘要写入").format(slave_ip))
            return []

        rows: List[Dict[str, Any]] = result_map.get(slave_ip) or []
        if not rows:
            return []

        items: List[Dict[str, Any]] = []
        for row in rows:
            row = row or {}
            db_name: str = row.get("db_name") or ""
            table_name: str = row.get("table_name") or ""
            status: str = row.get("status") or ""
            if not db_name or not table_name or not status:
                # 脏行不产出，避免触发预设 Serializer allow_blank=False 校验失败牵连整体
                self.log_warning(_("pt-table-sync 修复结果单行缺关键字段, 跳过: row={}").format(row))
                continue
            items.append(
                {
                    "cluster_domain": cluster_domain,
                    "ip": slave_ip,
                    "db_name_table_name": f"{db_name}.{table_name}",
                    "status": status,
                    "reason": row.get("reason") or "",
                    # unique_key：与预设 Serializer 约定的四元组拼接串，作为主键做同行覆盖合并
                    "unique_key": f"{cluster_domain}|{slave_ip}|{db_name}|{table_name}",
                }
            )
        return items


class PtTableSyncSummaryComponent(Component):
    """pt-table-sync 修复结果摘要组件（薄壳）。

    使用方式（在 pt-table-sync 修复子流程里，紧跟 PtTableSyncComponent 之后添加）：
      slave_sync_sub_pipeline.add_act(
          act_name=_("写入数据修复摘要"),
          act_component_code=PtTableSyncSummaryComponent.code,
          kwargs={
              "cluster_domain": cluster.immute_domain,
              "slave_ip": slave["ip"],
          },
      )

    边界 / 备注：
      - 本组件强制走 preset="pt_table_sync"（对齐 PtTableSyncSummarySerializer）；
        单据侧无需感知 preset 短名。
      - trans_data 必须使用 :class:`PtTableSyncContext`（其 result 字段承载 db-actuator 输出）。
    """

    name = __name__
    code = "mysql_pt_table_sync_summary"
    bound_service = PtTableSyncSummaryService
