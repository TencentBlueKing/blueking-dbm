"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import Dict, List, Optional

from django.utils.translation import gettext as _

from backend.db_services.sqlserver.rollback.handlers import SQLServerRollbackHandler
from backend.db_services.sqlserver.rollback.log_backup_chain import LogBackupChainStatus
from backend.flow.engine.bamboo.scene.sqlserver.validate.exception import DuplicateDStClusterException
from backend.flow.engine.validate.base_validate import validator_log_format
from backend.flow.engine.validate.sqlserver_base_validate import SqlserverBaseValidator
from backend.utils.time import str2datetime


class SqlserverDBConstructValidator(SqlserverBaseValidator):
    """
    SqlserverDataConstruct类对应的validate类
    判断传入flow的data参数合法性
    """

    def run_check_for_info(self, info: dict, index: int, is_check_src_and_dst_cluster: bool = False) -> list:
        """
        @param info
        @param index
        @param is_check_is_all_in_group: 判断同组共享的集群信息，是否全部传入
        """
        row_key = info.get("row_key", "")
        error_msgs = []

        # 检查传入的源集群是否存在
        log_format_tag = self.create_log_tag(field="src_cluster", index=index, row_key=row_key)
        error_msg = self.pre_check_cluster_exist([info["src_cluster"]], **log_format_tag)
        if error_msg:
            error_msgs.append(error_msg)

        # 检查传入的目标集群是否存在
        log_format_tag = self.create_log_tag(field="dst_cluster", index=index, row_key=row_key)
        error_msg = self.pre_check_cluster_exist([info["dst_cluster"]], **log_format_tag)
        if error_msg:
            error_msgs.append(error_msg)

        # 定点构造场景：源集群与目标集群不能一致（本地回档场景由子类关闭该开关）
        # 通过 int 转换消除前端可能下发字符串/数字混用带来的误判
        if is_check_src_and_dst_cluster:
            log_format_tag = self.create_log_tag(field="dst_cluster", index=index, row_key=row_key)
            error_msg = self.pre_check_src_dst_cluster_not_same(
                src_cluster_id=info["src_cluster"],
                dst_cluster_id=info["dst_cluster"],
                **log_format_tag,
            )
            if error_msg:
                error_msgs.append(error_msg)

        # 检查 rename_infos 中每个 db_name 是否都在备份记录 backup_db_list 中
        log_format_tag = self.create_log_tag(field="rename_infos", index=index, row_key=row_key)
        error_msg = self.pre_check_dbs_in_backup_list(
            rename_infos=info["rename_infos"],
            restore_backup_file=info["restore_backup_file"],
            **log_format_tag,
        )
        if error_msg:
            error_msgs.append(error_msg)

        # 定点构造场景下，日志备份连续性校验；提交时 fail-fast，避免执行阶段才发现缺失
        # 数据构造分两类：只回档全量（无 restore_time）/ 定点构造（有 restore_time）
        # 仅后者需要日志备份，故用 restore_time 是否为空作为触发开关，与 flow 侧一致
        restore_time_str: str = info.get("restore_time", "") or ""
        if restore_time_str:
            # 前置守卫：restore_time 时间窗口合法性校验；不通过则跳过后续日志链校验（无意义）
            # 单据提交到 flow 执行时间跨度可能较大，flow 侧也会调用同一底层能力兜住越界场景
            log_format_tag = self.create_log_tag(field="restore_time", index=index, row_key=row_key)
            error_msg = self.pre_check_restore_time_range(
                restore_time_str=restore_time_str,
                **log_format_tag,
            )
            if error_msg:
                error_msgs.append(error_msg)
                return error_msgs

            log_format_tag = self.create_log_tag(
                field="restore_backup_file",
                index=index,
                row_key=row_key,
            )
            # 在调用点完成"从单据挖 logs"的解构；handler 校验方法只关心 logs 本身
            restore_backup_file: Dict = info.get("restore_backup_file") or {}
            logs: List[Dict] = restore_backup_file.get("logs") or []

            # 定点构造只校验本行 rename_infos 声明的库：从 rename_infos 提取 db_name
            # 去重成 db_list（与 pre_check_dbs_in_backup_list 取值口径一致），
            # 只保留这些库的全量备份记录做日志链校验，避免对无关库（如 master）误报
            rename_infos: List[Dict] = info.get("rename_infos") or []
            db_list: List[str] = list({item.get("db_name") for item in rename_infos if item.get("db_name")})

            error_msg = self.pre_check_log_backup_continuity(
                src_cluster_id=info["src_cluster"],
                logs=logs,
                restore_time_str=restore_time_str,
                db_list=db_list,
                **log_format_tag,
            )
            if error_msg:
                error_msgs.append(error_msg)

        return error_msgs

    def __call__(self):
        """
        发起校验, 实例函数化
        校验项：
          1) 源集群 src_cluster 必须存在
          2) 目标集群 dst_cluster 必须存在
          3) rename_infos 中每个元素的 db_name 必须存在于 restore_backup_file.backup_db_list 中
          4) 定点构造场景下，src_cluster 与 dst_cluster 不允许一致（本地回档场景由子类关闭）
          5) 聚合：目标集群 dst_cluster 不允许在多条 info 中重复
          6) 定点构造场景下，rename_infos 对应每个 DB 的日志备份必须连续覆盖到 restore_time
        """
        # 阶段1 检测每个行的数据合法性
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.run_check_for_info(info=info, index=index, is_check_src_and_dst_cluster=True)
        if error_msgs:
            return error_msgs

        # 聚合查询，目标集群重复则异常
        err = self.pre_check_duplicate_cluster_ids("dst_cluster")
        if err:
            # 必须用 message= 关键字传入，触发 MESSAGE_TPL.format(**context) 拼上前缀；
            # 若用位置参数，AppBaseException 会走 except 分支把 str 原样赋值，MESSAGE_TPL 前缀会丢失
            raise DuplicateDStClusterException(message=err)

        return None

    @classmethod
    @validator_log_format
    def pre_check_src_dst_cluster_not_same(cls, src_cluster_id, dst_cluster_id) -> str:
        """校验源集群与目标集群不能是同一个集群。

        设计要点 / 怎么做：
          - 适用场景：定点构造（跨集群构造），业务上明确要求 src != dst，防止误覆盖源库
          - 本地回档场景（SqlserverDBRollbackInLocalValidator）不调用该方法
          - 比较前统一 int 化，避免前端下发 str / int 混用导致的类型差异误判
          - 错误消息经 validator_log_format 装饰器统一装配 field/index/row_key

        :param src_cluster_id: 源集群 ID（int 或可转 int 的字符串）
        :param dst_cluster_id: 目标集群 ID（int 或可转 int 的字符串）
        :return: 错误消息字符串；为空表示校验通过

        边界 / 异常：
          - src_cluster_id 或 dst_cluster_id 无法转为 int -> 判定为非法输入，返回错误
          - src_cluster_id == dst_cluster_id -> 返回错误消息
          - 集群是否存在由 pre_check_cluster_exist 负责，此处不重复校验
        """
        error_msg: str = ""

        # 前端可能下发 str/int 混用，先做类型归一化后再比较；转换失败按非法输入处理
        try:
            src_id_normalized: int = int(src_cluster_id)
            dst_id_normalized: int = int(dst_cluster_id)
        except (TypeError, ValueError):
            error_msg += _("src_cluster[{src}] 或 dst_cluster[{dst}] 非合法的集群 ID \n").format(
                src=src_cluster_id, dst=dst_cluster_id
            )
            return error_msg

        if src_id_normalized == dst_id_normalized:
            error_msg += _("src_cluster[{src}] 与 dst_cluster[{dst}] 不能是同一个集群 \n").format(
                src=src_cluster_id, dst=dst_cluster_id
            )

        return error_msg

    @classmethod
    @validator_log_format
    def pre_check_dbs_in_backup_list(cls, rename_infos: List[Dict], restore_backup_file: Dict) -> str:
        """
        校验 rename_infos 中每个待构造 DB 是否都存在于备份记录 restore_backup_file 的 backup_db_list 中。

        设计要点 / 怎么做：
          - 数据源：单据参数 restore_backup_file["backup_db_list"]（由查询备份记录时装配，见
            backend/db_services/sqlserver/rollback/handlers.py）
          - 匹配规则：db_name 精确匹配（大小写敏感，与 SQLServer 现网命名习惯一致）
          - 该方法为数据构造场景专属，故与 validator 类同文件放置，不下沉基类
          - 不修改入参，仅收集错误消息返回给 validator_log_format 装饰器统一格式化

        :param rename_infos: 构造重命名信息列表，每个元素至少包含 db_name(源库名) 字段
        :param restore_backup_file: 备份记录 dict，需包含 backup_db_list(List[str])
        :return: 错误消息字符串，为空表示校验通过

        边界 / 异常：
          - rename_infos 与 restore_backup_file 同时为空 -> 视为非法（无源无目标），返回错误
          - rename_infos 为空、restore_backup_file 非空 -> 直接返回 ""（无需构造，认为合法，交给上层业务判断）
          - restore_backup_file 缺失或 backup_db_list 缺失（但 rename_infos 非空）-> 视为无有效备份，所有 db_name 都报错
          - 单个 rename_info 缺失 db_name 字段 -> 记录错误（结构异常）
        """
        error_msg: str = ""

        # 同时为空视为非法输入：既没有待构造的 DB，又没有备份记录，无法完成任何有效校验
        if not rename_infos and not restore_backup_file:
            error_msg += _("rename_infos 与 restore_backup_file 均为空 \n")
            return error_msg

        if not rename_infos:
            return error_msg

        # 从备份记录中提取库列表，缺失时置空 -> 所有 db_name 都会被判定为不在备份中
        backup_db_list: List[str] = []
        if restore_backup_file:
            backup_db_list = restore_backup_file.get("backup_db_list") or []

        # 使用 set 加速查找；每次调用重建，避免持有跨请求状态
        backup_db_set: set = set(backup_db_list)

        for idx, info in enumerate(rename_infos):
            db_name = info.get("db_name")
            if not db_name:
                error_msg += _("rename_infos[{idx}] 缺少 'db_name' 字段 \n").format(idx=idx)
                continue
            if db_name not in backup_db_set:
                error_msg += _(
                    "rename_infos[{idx}] 中的 db_name[{db_name}] 不在备份记录 "
                    "restore_backup_file.backup_db_list{backup_db_list} 中 \n"
                ).format(idx=idx, db_name=db_name, backup_db_list=backup_db_list)

        return error_msg

    @classmethod
    @validator_log_format
    def pre_check_restore_time_range(cls, restore_time_str: str) -> str:
        """校验 restore_time 时间窗口合法性（薄壳，委托 SQLServerRollbackHandler 单一实现）。

        设计要点 / 怎么做：
          - 底层实现下沉到 SQLServerRollbackHandler.check_restore_time_range（静态方法），
            与 flow 执行期共用单一事实源；单据提交 -> flow 执行时间跨度大，两处都校验
            确保时间窗口越界能被完整拦截
          - 本方法仅负责"接入 validator_log_format 装饰器契约"（field / index / row_key
            装配），不再持有业务判定逻辑

        :param restore_time_str: 目标构造时点字符串（ISO 格式，由单据下发）
        :return: 错误消息字符串；为空表示校验通过

        边界 / 异常：
          - 完整边界详见 SQLServerRollbackHandler.check_restore_time_range
        """
        return SQLServerRollbackHandler.check_restore_time_range(restore_time_str=restore_time_str)

    @classmethod
    @validator_log_format
    def pre_check_log_backup_continuity(
        cls,
        src_cluster_id: int,
        logs: List[Dict],
        restore_time_str: str,
        db_list: Optional[List[str]] = None,
    ) -> str:
        """校验一批全量备份记录对应的日志备份是否连续覆盖到 restore_time。

        设计要点 / 怎么做：
          - 复用 flow 执行期同一底层能力（SQLServerRollbackHandler.check_log_backup_chain_batch），
            提交阶段 fail-fast + 执行阶段兜底，共用单一事实源
          - 接口最小化：仅接收 logs 列表本身，与单据外层结构（restore_backup_file dict）解耦；
            "从单据里挖 logs" 的解构动作放在调用点
          - 定点构造只关心本次 rename_infos 声明的库：db_list 非空时，按
            `log["dbname"] ∈ db_list` 过滤 logs，避免对无关库（如 master）做无意义校验/误报；
            db_list 为空（非定点构造历史调用方）则保持原行为——不过滤整个 logs
          - 校验阶段仅抽取 handler 所需的"最小字段子集"（不组装下载/恢复路径），
            与 flow 里 _get_full_backup_infos 的完整装配解耦；不引入 target_db_name 等
            flow 执行期专属字段
          - handler 侧返回 `List[LogBackupChainResult]`（结构化），本方法遍历后仅收集
            status != OK 的 error_message 拼接为字符串返回（保持装饰器契约）
          - 该方法为数据构造场景专属，故与 validator 类同文件放置，不下沉基类

        :param src_cluster_id: 源集群 ID，用于定位 binlog 查询上下文
        :param logs: 全量备份记录列表，每条至少包含
            dbname / backup_end_time / cluster_domain / last_lsn / file_name
        :param restore_time_str: 目标构造时点字符串（ISO 格式，由单据下发，例如 "2024-01-01 12:00:00"）
        :param db_list: 本次定点构造需要校验的库名列表（来自 rename_infos 的 db_name 去重集合）；
            非空时按 dbname 过滤 logs，只校验这些库；缺省 None 表示不过滤（兼容历史调用方）
        :return: 错误消息字符串；为空表示所有 DB 的日志备份均连续可用

        边界 / 异常：
          - logs 为空 -> 返回错误消息（定点构造强依赖全量备份记录，此处 fail-fast，
            避免 flow 执行期才暴露）
          - db_list 非空但过滤后无匹配记录 -> 返回错误消息（说明 rename_infos 声明的库
            在 logs 里找不到对应全量备份，装配层接口契约被破坏）
          - handler 返回多条非 OK 结果 -> 换行拼接后一并输出
        """
        # 定点构造场景强依赖全量备份记录：logs 为空意味着无从做全量回档，直接报错
        if not logs:
            return _("restore_backup_file.logs 为空，无法在定点构造场景下进行日志备份连续性校验")

        # db_list 非空 -> 只保留 dbname 在 db_list 内的记录，避免对无关库（如 master）误报
        # 用 set 加速成员判定；db_list 缺省为 None 时跳过过滤，保持历史调用方原行为
        filtered_logs: List[Dict] = logs
        if db_list:
            db_set: set = set(db_list)
            filtered_logs = [file_info for file_info in logs if file_info.get("dbname") in db_set]

        # 过滤后无匹配 -> 装配层契约异常（rename_infos 声明的库在 logs 里找不到全量备份）
        if db_list and not filtered_logs:
            return _("rename_infos 声明的库{db_list}在 restore_backup_file.logs 中找不到对应全量备份记录，" "无法完成日志备份连续性校验").format(
                db_list=list(db_list)
            )

        # 直接以每条 log 作为校验单元；仅保留连续性校验必需字段
        # 与 flow._get_full_backup_infos 的关键区别：不组装 bak_file/target_path/target_db_name 等执行期路径
        full_restore_infos: List[Dict] = [
            {
                "db_name": file_info["dbname"],
                "backup_full_end_time": file_info["backup_end_time"],
                "cluster_address": file_info["cluster_domain"],
                "full_last_lsn": file_info["last_lsn"],
                "full_file_name": file_info["file_name"],
            }
            for file_info in filtered_logs
        ]

        # 委托 handler 做真正的连续性判断（内部会调 LogBackupChainInspector 完成 6 态判定）
        results = SQLServerRollbackHandler(cluster_id=src_cluster_id).check_log_backup_chain_batch(
            full_restore_infos=full_restore_infos,
            restore_time=str2datetime(restore_time_str),
        )

        # 仅收集 status != OK 的错误消息拼接为字符串（保持 validator_log_format 装饰器返回契约）
        err_messages: List[str] = [
            result.error_message
            for result in results
            if result.status != LogBackupChainStatus.OK and result.error_message
        ]
        return "\n".join(err_messages)
