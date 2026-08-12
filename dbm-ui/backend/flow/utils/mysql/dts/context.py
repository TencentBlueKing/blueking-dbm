# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from backend.flow.utils.mysql.dts.constants import DtsRegisterMode

if TYPE_CHECKING:
    from backend.flow.utils.mysql.dts.migrate_plan import DtsMigratePlan


@dataclass
class DtsHostSpec:
    ip: str
    bk_cloud_id: int
    name: str | None = None


@dataclass
class MysqlDtsDeployContext:
    master_addr: str = ""
    deployed_master_nodes: list = field(default_factory=list)
    deployed_worker_nodes: list = field(default_factory=list)
    pkg_name: str = ""
    dts_version: str = ""


@dataclass
class MysqlDtsMigrateContext:
    master_addr: str = ""
    bk_cloud_id: int | None = None
    dts_cluster_id: int | None = None
    created_dts_info_ids: list[int] = field(default_factory=list)
    dts_user: str = ""
    dts_password: str = ""
    registered_source_names: list[str] = field(default_factory=list)
    # create_user 写入，供后续 drop_user 子流程使用（不含密码）
    grant_hosts: list[str] = field(default_factory=list)
    grant_targets: list[dict] = field(default_factory=list)
    # myloader 全量导入：source_name -> 落盘目录 / 备份摘要 / Worker 上二进制路径
    myloader_dirs: dict[str, str] = field(default_factory=dict)
    myloader_path: str = ""
    myloader_backup_by_source: dict[str, dict] = field(default_factory=dict)
    # create_task 写入的目标端连接点，供 start_task 日志直接使用（不再二次解析）
    target_host: str = ""
    target_port: int = 0
    target_cluster_type: str = ""


@dataclass
class MysqlDtsDeploySubflowInput:
    root_id: str
    bk_biz_id: int
    bk_cloud_id: int
    cluster_name: str
    master_hosts: list[DtsHostSpec]
    worker_hosts: list[DtsHostSpec]
    deploy_path: str = ""
    master_ha: bool = False
    dts_pkg_id: int | None = None
    register_mode: str = DtsRegisterMode.CREATE.value
    creator: str = ""


@dataclass
class MysqlDtsDeployMasterSubflowInput:
    root_id: str
    bk_biz_id: int
    bk_cloud_id: int
    cluster_name: str
    hosts: list[DtsHostSpec]
    deploy_path: str
    master_ha: bool = False
    dts_pkg_id: int | None = None


@dataclass
class MysqlDtsDeployWorkerSubflowInput:
    root_id: str
    bk_biz_id: int
    bk_cloud_id: int
    cluster_name: str
    hosts: list[DtsHostSpec]
    master_addr: str
    deploy_path: str
    dts_pkg_id: int | None = None
    register_mode: str = DtsRegisterMode.CREATE.value


@dataclass
class MysqlDtsDeployColocatedHostSubflowInput:
    root_id: str
    bk_biz_id: int
    bk_cloud_id: int
    cluster_name: str
    host: DtsHostSpec
    deploy_path: str
    master_ha: bool = False
    dts_pkg_id: int | None = None


@dataclass
class MysqlDtsAppendWorkerSubflowInput:
    root_id: str
    dts_cluster_id: int
    bk_biz_id: int
    bk_cloud_id: int
    master_addr: str
    deploy_path: str
    existing_worker_nodes: list[dict]
    new_worker_hosts: list[DtsHostSpec]
    dts_pkg_id: int | None = None
    register_mode: str = DtsRegisterMode.APPEND_WORKER.value
    creator: str = ""


@dataclass
class MysqlDtsCleanupSubflowInput:
    root_id: str
    dts_cluster_id: int
    bk_biz_id: int
    bk_cloud_id: int
    master_addr: str
    master_nodes: list[dict]
    worker_nodes: list[dict]
    deploy_path: str
    force_destroy: bool = False
    recycle_hosts: bool = True
    clean_data_dir: bool = True
    target_hosts: list[DtsHostSpec] | None = None
    creator: str = ""


@dataclass
class MysqlDtsMigrateSubflowInput:
    root_id: str
    bk_biz_id: int
    ticket_id: int
    migrate_plan: "DtsMigratePlan"
    creator: str = ""
    # 与外层 dts-task-clean 同源时可显式传入；未传则子流程内解析并生成
    dts_user: str = ""
    dts_password: str = ""
    grant_hosts: list[str] | None = None
    grant_targets: list | None = None


@dataclass
class MysqlDtsTaskCleanSubflowInput:
    """成功路径可扩展清理子流程入参（节点 dts-task-clean）。

    含 drop 临时账号，以及本单维度 delete_task → delete_source（与账号 DROP 并行）。
    仅挂成功路径总流程末尾，终止路径不调用。

    名称来源（建流期为主）：
      - task_names / source_names 由 migrate_plan.task_specs 枚举组装（见 build_ticket_dts_clean_names）
      - 语义与 MysqlDtsInfo.dts_task_id / dts_source_names 对齐；不在 clean 内对 Master list 全量
    """

    root_id: str
    bk_biz_id: int
    dts_user: str
    grant_hosts: list[str]
    grant_targets: list[dict]  # [{"bk_cloud_id": int, "address": "ip:port", ...}, ...]
    ignore_errors: bool = True  # 仅作用于 drop_user；delete_task_source 在 task_clean 内强制 False
    creator: str = ""
    master_addr: str = ""
    bk_cloud_id: int = 0
    task_names: list[str] | None = None
    source_names: list[str] | None = None


@dataclass
class MysqlDtsDeleteTaskSourceSubflowInput:
    """本单维度删除 DTS task/source 子流程入参（成功路径 dts-task-clean 并行支路）。"""

    root_id: str
    bk_biz_id: int
    master_addr: str
    task_names: list[str]
    source_names: list[str]
    bk_cloud_id: int = 0
    ignore_errors: bool = False  # 成功路径默认不吞错；与 drop_user 尽力清理分离
    creator: str = ""


@dataclass
class MysqlDtsDropUserSubflowInput:
    """删除 DTS 迁移临时账号子流程入参。

    调用时机由业务侧决定（成功路径 dts-task-clean / 终止信号同步 DROP 等），本子流程只负责执行 DROP。
    """

    root_id: str
    bk_biz_id: int
    dts_user: str
    grant_hosts: list[str]
    grant_targets: list[dict]  # [{"bk_cloud_id": int, "address": "ip:port", ...}, ...]
    ignore_errors: bool = True  # 用户不存在等视为可忽略，默认尽力清理
    creator: str = ""


@dataclass
class MysqlDtsWaitCatchupSubflowInput:
    """追平轮询子流程入参：连续 N 次 SBM==0 且同 binlog 文件后通过。"""

    root_id: str
    bk_biz_id: int
    master_addr: str
    task_name: str
    bk_cloud_id: int = 0
    source_name_list: list[str] | None = None
    poll_interval: int | None = None
    required_consecutive: int | None = None
    max_fail_streak: int | None = None
    creator: str = ""


@dataclass
class MysqlDtsCutoverSubflowInput:
    """安全切换子流程入参（Pause → actuator cutover → 写元数据）。"""

    root_id: str
    bk_biz_id: int
    ticket_id: int
    master_addr: str
    task_name: str
    deploy_path: str
    dts_cluster_id: int
    creator: str = ""


@dataclass
class MysqlDtsChecksumSubflowInput:
    """DTS 模式数据校验子流程入参（关联 MYSQL_CHECKSUM 单据）。"""

    root_id: str
    bk_biz_id: int
    ticket_id: int
    creator: str = ""


@dataclass
class HostDeployPlan:
    colocated_hosts: list[DtsHostSpec] = field(default_factory=list)
    master_only_hosts: list[DtsHostSpec] = field(default_factory=list)
    worker_only_hosts: list[DtsHostSpec] = field(default_factory=list)


@dataclass
class MysqlDtsReinstallSubflowInput:
    """重装子流程入参：stop → transfile → symlink bin + start → verify → update version。"""

    root_id: str
    dts_cluster_id: int
    bk_biz_id: int
    bk_cloud_id: int
    master_addr: str
    master_nodes: list[dict]
    worker_nodes: list[dict]
    deploy_path: str
    force_reinstall: bool = False
    dts_pkg_id: int | None = None
    creator: str = ""


@dataclass
class MysqlDtsTransData:
    deploy_context: MysqlDtsDeployContext = field(default_factory=MysqlDtsDeployContext)
    migrate_context: MysqlDtsMigrateContext = field(default_factory=MysqlDtsMigrateContext)
    extra: dict[str, Any] = field(default_factory=dict)
    # dts-cutover PrintOutputCtx → write_payload_var 写入，供 cutover_meta 落库
    cutover_position: dict = field(default_factory=dict)

    @staticmethod
    def get_cutover_position_var_name() -> str:
        return "cutover_position"
