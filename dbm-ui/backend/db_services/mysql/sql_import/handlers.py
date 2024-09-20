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
import itertools
import os.path
import re
import tempfile
import time
from typing import Any, Dict, List, Optional, Union

import chardet
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.translation import ugettext as _

from backend.components.sql_import.client import SQLSimulationApi
from backend.configuration.constants import PLAT_BIZ_ID, BizSettingsEnum, DBType
from backend.configuration.models import BizSettings
from backend.core.storages.storage import get_storage
from backend.db_services.mysql.sql_import.constants import (
    BKREPO_SQLFILE_PATH,
    CACHE_SEMANTIC_DATA_FIELD,
    CACHE_SEMANTIC_TASK_FIELD,
    MAX_PREVIEW_SQL_FILE_SIZE,
    SQL_SEMANTIC_CHECK_DATA_EXPIRE_TIME,
)
from backend.db_services.mysql.sql_import.exceptions import SQLImportBaseException
from backend.db_services.taskflow.handlers import TaskFlowHandler
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.engine.controller.spider import SpiderController
from backend.flow.models import FlowNode, FlowTree
from backend.flow.plugins.components.collections.mysql.semantic_check import SemanticCheckComponent
from backend.ticket.constants import BAMBOO_STATE__TICKET_STATE_MAP, TicketFlowStatus
from backend.utils.basic import generate_root_id
from backend.utils.cache import cache, data_cache
from backend.utils.redis import RedisConn


class SQLHandler(object):
    """
    封装sql导入相关处理操作
    """

    def __init__(self, bk_biz_id: int, context: Dict = None, cluster_type: str = ""):
        """
        @param bk_biz_id: 业务ID
        @param context: 上下文数据
        @param cluster_type: 集群类型
        """

        self.bk_biz_id = bk_biz_id
        self.context = context
        self.cluster_type = cluster_type

    @staticmethod
    def upload_sql_file(
        bkrepo_path, sql_content: str = None, sql_file_list: List[InMemoryUploadedFile] = None
    ) -> List[Dict[str, Any]]:
        """
        - 将sql文本或者sql文件上传到制品库
        @param bkrepo_path: sql 路径
        @param sql_content: sql 语句内容
        @param sql_file_list: sql 语句文件
        """
        storage = get_storage(file_overwrite=False)

        # 如果上传的是sql内容, 则创建一个sql文件
        if sql_content:
            sql_file = tempfile.NamedTemporaryFile(suffix=".sql")
            content_byte = str.encode(sql_content, encoding="utf-8")
            sql_file.write(content_byte)
            sql_file.size = len(content_byte)
            sql_file.seek(0)
            sql_file_list = [sql_file]

        sql_file_info_list: List[Dict[str, Any]] = []
        for sql_file in sql_file_list:
            sql_file_info: Dict[str, Any] = {}
            with sql_file as file:
                # TODO: 是否需要考虑windows机器的路径分隔
                sql_path = storage.save(name=os.path.join(bkrepo_path, file.name.split("/")[-1]), content=file)

                # 恢复文件指针为文件头，否则会无法读取内容 TODO：如果sql内容过大需要进行内容读取吗？
                file.seek(0)
                # 超过最大预览限制，则不支持预览
                if file.size > MAX_PREVIEW_SQL_FILE_SIZE:
                    sql_content = _("当前SQL文件过大，暂不提供内容预览...")
                else:
                    content_bytes = file.read()
                    # chardet.detect预测性非100%，这里非强制UnicodeDecodeError，选择replace模式忽略
                    encoding = chardet.detect(content_bytes[:100])["encoding"]
                    sql_content = content_bytes.decode(encoding=encoding, errors="replace")

                sql_file_info.update(sql_path=sql_path, sql_content=sql_content, raw_file_name=file.name)

            sql_file_info_list.append(sql_file_info)

        return sql_file_info_list

    def grammar_check(
        self,
        sql_content: str = None,
        sql_filenames: List[str] = None,
        sql_files: List[InMemoryUploadedFile] = None,
        versions: list = None,
    ) -> Optional[Dict]:
        """
        sql 语法检查
        @param sql_content: sql内容
        @param sql_filenames: sql文件名(在制品库的路径，说明已经在制品库上传好了。目前是适配sql执行插件形式.)
        @param sql_files: sql文件
        @param versions 版本列表
        """
        if sql_filenames:
            sql_file_info_list = [{"sql_path": filename} for filename in sql_filenames]
        else:
            upload_sql_path = BKREPO_SQLFILE_PATH.format(biz=self.bk_biz_id)
            sql_file_info_list = self.upload_sql_file(upload_sql_path, sql_content, sql_files)

        file_name_list = [os.path.split(sql_file_info["sql_path"])[1] for sql_file_info in sql_file_info_list]
        dir_name = os.path.split(sql_file_info_list[0]["sql_path"])[0]

        # 获取检查信息
        versions = versions or []
        check_info = SQLSimulationApi.grammar_check(
            params={"path": dir_name, "files": file_name_list, "cluster_type": self.cluster_type, "versions": versions}
        )

        # 填充sql内容。
        # TODO: 业务配置忽略语法检查，暂时加到BizSettings，后续删除该逻辑
        skip_check = BizSettings.get_setting_value(self.bk_biz_id, BizSettingsEnum.SKIP_GRAMMAR_CHECK, default=False)
        for sql_file_info in sql_file_info_list:
            sql_path = sql_file_info["sql_path"]
            file_name = os.path.split(sql_path)[1]
            check_info[file_name].update(
                content=sql_file_info.get("sql_content"),
                sql_path=sql_path,
                raw_file_name=sql_file_info.get("raw_file_name"),
                skip_check=skip_check,
            )

        return check_info

    def semantic_check(
        self,
        charset: str,
        cluster_ids: List[int],
        execute_objects: List[Dict[str, Union[int, List[str]]]],
        ticket_type: str,
        ticket_mode: Dict,
        backup: List[Dict],
        is_auto_commit: bool = True,
        remark: str = "",
    ) -> Dict:
        """
        sql 模拟执行(sql 语义检查)
        @param charset: 字符集
        @param cluster_ids: 集群列表
        @param execute_objects: 执行的结构体
        @param ticket_type: 单据类型
        @param ticket_mode: sql导入单据的触发类型
        @param backup: 备份信息（和备份单据一样）
        @param is_auto_commit: 是否自动提单
        @param remark: 提单备注
        """

        # 语义检查参数准备
        for index, execute in enumerate(execute_objects):
            execute["line_id"] = index

        # 异步执行语义检查
        root_id = generate_root_id()
        ticket_data = {
            "created_by": self.context["user"],
            "bk_biz_id": self.bk_biz_id,
            "ticket_type": ticket_type,
            "charset": charset,
            "path": BKREPO_SQLFILE_PATH.format(biz=self.bk_biz_id),
            "cluster_ids": cluster_ids,
            "execute_objects": execute_objects,
            "ticket_mode": ticket_mode,
            "backup": backup,
            "is_auto_commit": is_auto_commit,
            "remark": remark,
        }
        try:
            if self.cluster_type == DBType.MySQL:
                MySQLController(root_id=root_id, ticket_data=ticket_data).mysql_sql_semantic_check_scene()
            elif self.cluster_type == DBType.TenDBCluster:
                SpiderController(root_id=root_id, ticket_data=ticket_data).spider_semantic_check_scene()
        except Exception as e:  # pylint: disable=broad-except
            raise SQLImportBaseException(_("模拟流程构建失败，错误信息: {}").format(e))

        # 缓存用户的语义检查，并删除过期的数据。注：django的cache不支持redis命令，这里只能使用原生redis客户端进行操作
        now = int(time.time())
        key = CACHE_SEMANTIC_TASK_FIELD.format(user=self.context["user"], cluster_type=self.cluster_type)
        RedisConn.zadd(key, {root_id: now})
        RedisConn.set(root_id, StateType.CREATED)
        expired_task_ids = RedisConn.zrangebyscore(key, "-inf", now - SQL_SEMANTIC_CHECK_DATA_EXPIRE_TIME)
        self.delete_user_semantic_tasks(task_ids=expired_task_ids)
        # 缓存语义数据, 60s过期
        data_cache(key=CACHE_SEMANTIC_DATA_FIELD.format(root_id=root_id), data=ticket_data, cache_time=60)

        return {"root_id": root_id}

    def delete_user_semantic_tasks(self, task_ids: List[int]) -> None:
        """
        删除用户的语义执行任务
        @param task_ids: 待删除的语义任务ID
        """

        key = CACHE_SEMANTIC_TASK_FIELD.format(user=self.context["user"], cluster_type=self.cluster_type)
        if task_ids:
            RedisConn.zrem(key, *task_ids)
            RedisConn.delete(*task_ids)

    def revoke_semantic_check(self, root_id: str) -> Dict:
        """
        撤销语义检查流程
        @param root_id: 语义检查的任务ID
        """

        revoke_info = TaskFlowHandler(root_id=root_id).revoke_pipeline()
        return {"result": revoke_info.result, "message": revoke_info.message, "data": revoke_info.data}

    def query_semantic_data(self, root_id: str) -> Dict:
        """
        根据语义执行id查询语义执行的数据
        @param root_id: 语义任务执行ID
        """
        first_act_node_id = FlowNode.objects.filter(root_id=root_id).first().node_id
        try:
            details = BambooEngine(root_id=root_id).get_node_input_data(node_id=first_act_node_id).data["global_data"]
        except KeyError:
            details = cache.get(CACHE_SEMANTIC_DATA_FIELD.format(root_id=root_id))

        if not details:
            return {}

        execute_sql_files = list(itertools.chain(*[detail["sql_files"] for detail in details["execute_objects"]]))
        details["execute_sql_files"] = list(set(execute_sql_files))
        return details

    def _get_user_semantic_tasks(self, cluster_type, code) -> List[Dict]:
        # 获取缓存的任务ID
        key = CACHE_SEMANTIC_TASK_FIELD.format(user=self.context["user"], cluster_type=cluster_type)
        task_ids = RedisConn.zrange(key, 0, -1)
        task_ids__status_map = dict(zip(task_ids, RedisConn.mget(task_ids)))

        # 获取用户的语义执行列表信息
        flow_tree_list = FlowTree.objects.filter(root_id__in=task_ids)
        semantic_info_list = [
            {
                "bk_biz_id": tree.bk_biz_id,
                "root_id": tree.root_id,
                "created_at": tree.created_at,
                "status": tree.status,
                "is_alter": task_ids__status_map[tree.root_id] != tree.status,
            }
            for tree in flow_tree_list
            if self.bk_biz_id in [tree.bk_biz_id, PLAT_BIZ_ID]
        ]

        # 更新root_id对应的状态
        task_ids__status_map = {info["root_id"]: info["status"] for info in semantic_info_list}
        if task_ids__status_map:
            RedisConn.mset(task_ids__status_map)

        return semantic_info_list

    def get_user_semantic_tasks(self) -> List[Dict]:
        """
        获取用户的语义检查执行信息列表
        """

        semantic_info_list: List[Dict] = []
        if not self.cluster_type or self.cluster_type == DBType.MySQL:
            semantic_info_list.extend(self._get_user_semantic_tasks(DBType.MySQL, SemanticCheckComponent.code))

        if not self.cluster_type or self.cluster_type == DBType.TenDBCluster:
            semantic_info_list.extend(self._get_user_semantic_tasks(DBType.TenDBCluster, SemanticCheckComponent.code))

        return semantic_info_list

    @classmethod
    def parse_semantic_check_logs(cls, root_id: str, logs: List[Dict], sql_files: List[str]) -> List[Dict]:
        """
        解析语义检查的执行日志，根据sql文件返回结构化的执行结果日志
        :param root_id: 流程id
        :param logs: 语义执行日志(node_log)
        :param sql_files: sql文件名列表
        """

        # 定义匹配日志的开始和结束正则
        start_patterns = re.compile(r".*\[start]-(.*\.sql)")
        end_patterns = re.compile(r".*\[end]-(.*\.sql)")

        current_sql_filename: str = ""
        current_sql_logs: List[Dict] = []
        parsed_sql_logs_results: List[Dict] = []

        # 解析sql语义执行日志
        for log in logs:
            message = log["message"]
            is_start_match = start_patterns.match(message)
            is_end_match = end_patterns.match(message)
            # 忽略结果日志之前的日志
            if not current_sql_filename and not is_start_match:
                continue
            # 如果当前存在sql名，但匹配到了start，说明当前sql文件非预期结束
            if current_sql_filename and is_start_match:
                status = TicketFlowStatus.FAILED
                parsed_sql_logs_results.append(
                    {"filename": current_sql_filename, "match_logs": current_sql_logs, "status": status}
                )
                current_sql_filename, current_sql_logs = "", []
            # 获取当前的sql名
            if not current_sql_filename:
                current_sql_filename = start_patterns.match(message).groups()[0]
            # 加入当前的匹配日志
            current_sql_logs.append(log)
            # 如果匹配到结束节点，则完成当前sql日志的结果匹配，生成一条匹配记录
            if is_end_match:
                end_filename = end_patterns.match(message).groups()[0]
                status = (
                    TicketFlowStatus.SUCCEEDED if current_sql_filename == end_filename else TicketFlowStatus.FAILED
                )
                parsed_sql_logs_results.append(
                    {"filename": current_sql_filename, "match_logs": current_sql_logs, "status": status}
                )
                # 清空current_sql_filename, current_sql_logs
                current_sql_filename, current_sql_logs = "", []

        # 如果匹配完成后current_sql_filename仍然有值，说明解析未完成，要根据flow的状态进行判断
        if current_sql_filename:
            flow_status = FlowTree.objects.get(root_id=root_id).status
            sql_exec_status = BAMBOO_STATE__TICKET_STATE_MAP.get(flow_status, TicketFlowStatus.RUNNING)
            parsed_sql_logs_results.append(
                {"filename": current_sql_filename, "match_logs": current_sql_logs, "status": sql_exec_status}
            )

        # 对于不出现在匹配结果的sql文件，说明是待执行状态
        parsed_filenames = [item["filename"] for item in parsed_sql_logs_results]
        not_parser_files = [
            {"filename": filename, "match_logs": [], "status": TicketFlowStatus.PENDING}
            for filename in sql_files
            if filename not in parsed_filenames
        ]
        parsed_sql_logs_results.extend(not_parser_files)

        return parsed_sql_logs_results

    def get_semantic_check_result_logs(self, root_id: str, node_id: str) -> List[Dict]:
        """
        获取语义执行的结果日志 TODO: 该函数被替换为get_semantic_execute_result，暂无解析日志需求
        :param root_id: 语义执行的root id
        :param node_id: 语义执行的node id
        """
        taskflow_handler = TaskFlowHandler(root_id)
        # 获取节点执行日志，如果流程还未启动则直接返回空
        semantic_data = self.query_semantic_data(root_id)

        # 获取语义执行的version id
        versions = taskflow_handler.get_node_histories(node_id)
        version_id = versions[0]["version"]
        if not version_id:
            return []

        # 获取语法检查结果日志
        logs = taskflow_handler.get_version_logs(node_id, version_id)
        # 解析日志，获得结构化数据
        semantic_data = semantic_data["semantic_data"]
        parsed_sql_logs_results = self.parse_semantic_check_logs(root_id, logs, semantic_data["execute_sql_files"])
        return parsed_sql_logs_results

    def get_semantic_execute_result(self, root_id: str) -> List[Dict]:
        """
        获取语义执行的结果
        :param root_id: 语义执行的root id
        """
        flow_tree = FlowTree.objects.get(root_id=root_id).tree
        taskflow_handler = TaskFlowHandler(root_id)

        # 获取语义执行的版本ID
        node_id = taskflow_handler.get_node_id_by_component(flow_tree, component_code=SemanticCheckComponent.code)[0]
        version_id = FlowNode.objects.get(node_id=node_id).version_id
        # 没有version id，证明没有执行到此步骤，直接返回空
        if not version_id:
            return []

        # 查询执行结果
        results = SQLSimulationApi.query_semantic_result(params={"root_id": root_id, "version_id": version_id})

        # 拼接执行的变更DB
        node_data = BambooEngine(root_id=root_id).get_node_input_data(node_id).data["global_data"]
        execute_objects = node_data["execute_objects"]
        line_id__execute = {obj["line_id"]: obj for obj in execute_objects}
        for data in results:
            execute = line_id__execute[data["line_id"]]
            data.update(dbnames=execute["dbnames"], ignore_dbnames=execute["ignore_dbnames"])

        return results
