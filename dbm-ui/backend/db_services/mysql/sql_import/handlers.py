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
import datetime
import os.path
import tempfile
import time
import uuid
from typing import Any, Dict, List, Optional

from django.core.cache import cache
from django.core.files.uploadedfile import InMemoryUploadedFile

from backend.components.sql_import.client import SQLImportApi
from backend.configuration.constants import PLAT_BIZ_ID
from backend.core.storages.storage import get_storage
from backend.db_services.mysql.sql_import.constants import (
    BKREPO_SQLFILE_PATH,
    CACHE_SEMANTIC_AUTO_COMMIT_FIELD,
    CACHE_SEMANTIC_SKIP_PAUSE_FILED,
    CACHE_SEMANTIC_TASK_FIELD,
    SQL_SEMANTIC_CHECK_DATA_EXPIRE_TIME,
)
from backend.db_services.mysql.sql_import.dataclass import SemanticOperateMeta, SQLExecuteMeta, SQLMeta
from backend.db_services.taskflow.handlers import TaskFlowHandler
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.models import FlowNode, FlowTree
from backend.flow.plugins.components.collections.mysql.semantic_check import SemanticCheckComponent
from backend.utils.redis import RedisConn


class SQLHandler(object):
    """
    封装sql导入相关处理操作
    """

    def __init__(self, bk_biz_id: int, context: Dict = None):
        """
        :param bk_biz_id: 业务ID
        :param context: 上下文数据
        """

        self.bk_biz_id = bk_biz_id
        self.context = context

    def _upload_sql_file(
        self, sql_content: str = None, sql_file_list: List[InMemoryUploadedFile] = None
    ) -> List[Dict[str, Any]]:
        """
        - 将sql文本或者sql文件上传到制品库
        :param sql_content: sql 语句内容
        :param sql_file: sql 语句文件
        """

        storage = get_storage(file_overwrite=False)

        # 如果上传的是sql内容, 则创建一个sql文件
        if sql_content:
            sql_file = tempfile.NamedTemporaryFile(suffix=".sql")
            sql_file.write(str.encode(sql_content, encoding="utf-8"))
            sql_file.seek(0)
            sql_file_list = [sql_file]

        sql_file_info_list: List[Dict[str, Any]] = []
        for sql_file in sql_file_list:
            sql_file_info: Dict[str, Any] = {}
            with sql_file as file:
                # TODO: 是否需要考虑windows机器的路径分隔
                sql_path = storage.save(name=os.path.join(BKREPO_SQLFILE_PATH, file.name.split("/")[-1]), content=file)

                # 恢复文件指针为文件头，否则会无法读取内容
                file.seek(0)
                sql_file_info.update(
                    sql_path=sql_path, sql_content=file.read().decode("utf-8"), raw_file_name=file.name
                )

            sql_file_info_list.append(sql_file_info)

        return sql_file_info_list

    def grammar_check(self, sql: SQLMeta) -> Optional[Dict]:
        """
        sql 语法检查
        :param sql: sql元数据
        """

        sql_file_info_list = self._upload_sql_file(sql.sql_content, sql.sql_files)
        file_name_list = [os.path.split(sql_file_info["sql_path"])[1] for sql_file_info in sql_file_info_list]
        dir_name = os.path.split(sql_file_info_list[0]["sql_path"])[0]

        # 获取检查信息
        check_info = SQLImportApi.grammar_check(params={"path": dir_name, "files": file_name_list})

        # 填充sql内容。TODO：如果sql内容过大需要进行压缩吗？
        for sql_file_info in sql_file_info_list:
            sql_path = sql_file_info["sql_path"]
            file_name = os.path.split(sql_path)[1]
            check_info[file_name].update(
                content=sql_file_info["sql_content"], sql_path=sql_path, raw_file_name=sql_file_info["raw_file_name"]
            )

        return check_info

    def semantic_check(self, sql_execute: SQLExecuteMeta) -> Dict:
        """
        sql 模拟执行(sql 语义检查)
        :param sql_execute: sql执行元数据
        """

        # 语义检查参数准备
        root_id = f"{datetime.date.today()}{uuid.uuid1().hex[:6]}".replace("-", "")
        sql_execute.created_by = self.context["user"]
        sql_execute.bk_biz_id = self.bk_biz_id
        sql_execute.execute_objects = []
        for sql_file in sql_execute.execute_sql_files:
            sql_execute.execute_objects.extend(
                [{"sql_file": sql_file, **db_info} for db_info in sql_execute.execute_db_infos]
            )

        # 异步执行语义检查
        MySQLController(root_id=root_id, ticket_data=sql_execute.to_dict()).mysql_sql_semantic_check_scene()

        # 获取语义执行的node id
        tree = FlowTree.objects.get(root_id=root_id)
        node_id = self._get_node_id_by_component(tree, SemanticCheckComponent.code)

        # 缓存用户的语义检查，并删除过期的数据, django的cache不支持redis命令，这里只能使用原生redis客户端进行操作
        now = int(time.time())
        key = CACHE_SEMANTIC_TASK_FIELD.format(user=sql_execute.created_by)
        expired_task_ids = RedisConn.zrangebyscore(key, "-inf", now - SQL_SEMANTIC_CHECK_DATA_EXPIRE_TIME)
        self.delete_user_semantic_tasks(semantic=SemanticOperateMeta(task_ids=expired_task_ids))
        RedisConn.zadd(key, {root_id: now})
        RedisConn.set(root_id, StateType.CREATED)

        return {"root_id": root_id, "node_id": node_id}

    def delete_user_semantic_tasks(self, semantic: SemanticOperateMeta) -> None:
        """
        删除用户的语义执行任务
        :param semantic: 语义检查相关操作的元数据
        """

        key = CACHE_SEMANTIC_TASK_FIELD.format(user=self.context["user"])
        if semantic.task_ids:
            RedisConn.zrem(key, *semantic.task_ids)
            RedisConn.delete(*semantic.task_ids)

    def revoke_semantic_check(self, semantic: SemanticOperateMeta) -> Dict:
        """
        撤销语义检查流程
        :param semantic: 语义检查相关操作的元数据
        """

        root_id = semantic.root_id
        revoke_info = TaskFlowHandler(root_id=root_id).revoke_pipeline()
        return {"result": revoke_info.result, "message": revoke_info.message, "data": revoke_info.data}

    def query_semantic_data(self, semantic: SemanticOperateMeta) -> Dict:
        """
        根据语义执行id查询语义执行的数据
        :param semantic: 语义检查相关操作的元数据
        """

        root_id = semantic.root_id
        first_act_node_id = FlowNode.objects.filter(root_id=root_id).first().node_id

        try:
            details = BambooEngine(root_id=root_id).get_node_input_data(node_id=first_act_node_id).data["global_data"]
        except KeyError:
            return {"sql_files": "", "import_mode": "", "sql_data_ready": False}

        import_mode = details["import_mode"]
        return {"semantic_data": details, "import_mode": import_mode, "sql_data_ready": True}

    def deploy_user_config(self, semantic: SemanticOperateMeta) -> None:
        """
        更改用户配置(是否自动提交，是否跳过确认)
        :param semantic: 语义检查相关操作的元数据
        """

        # auto_commit的配置
        auto_commit_key = CACHE_SEMANTIC_AUTO_COMMIT_FIELD.format(bk_biz_id=self.bk_biz_id, root_id=semantic.root_id)
        cache.set(auto_commit_key, semantic.is_auto_commit, SQL_SEMANTIC_CHECK_DATA_EXPIRE_TIME)

        # skip_pause的配置
        skip_pause_key = CACHE_SEMANTIC_SKIP_PAUSE_FILED.format(bk_biz_id=self.bk_biz_id, root_id=semantic.root_id)
        cache.set(skip_pause_key, semantic.is_skip_pause, SQL_SEMANTIC_CHECK_DATA_EXPIRE_TIME)

    def query_user_config(self, semantic: SemanticOperateMeta) -> Dict:
        """
        查询用户配置
        :param semantic: 语义检查相关操作的元数据
        """

        auto_commit_key = CACHE_SEMANTIC_AUTO_COMMIT_FIELD.format(bk_biz_id=self.bk_biz_id, root_id=semantic.root_id)
        skip_pause_key = CACHE_SEMANTIC_SKIP_PAUSE_FILED.format(bk_biz_id=self.bk_biz_id, root_id=semantic.root_id)

        is_auto_commit = cache.get(auto_commit_key)
        is_skip_pause = cache.get(skip_pause_key)
        return {"is_auto_commit": is_auto_commit, "is_skip_pause": is_skip_pause}

    def get_user_semantic_tasks(self, semantic: SemanticOperateMeta) -> List[Dict]:
        """
        获取用户的语义检查执行信息列表
        :param semantic: 语义检查相关操作的元数据
        """

        key = CACHE_SEMANTIC_TASK_FIELD.format(user=self.context["user"])
        task_ids = RedisConn.zrange(key, 0, -1)
        task_ids__status_map = dict(zip(task_ids, RedisConn.mget(task_ids)))

        # 获取用户的语义执行列表信息
        flow_tree_list = FlowTree.objects.filter(root_id__in=task_ids)
        semantic_info_list = [
            {
                "bk_biz_id": tree.bk_biz_id,
                "root_id": tree.root_id,
                "node_id": self._get_node_id_by_component(tree, SemanticCheckComponent.code),
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

    def _get_node_id_by_component(self, tree: FlowTree, component_code: str) -> str:
        """
        根据component获取node id
        :param tree: 流程树对象
        :param component_code: 组件code名称
        """

        activities: Dict = tree.tree["activities"]
        for node_id, activity in activities.items():
            if activity["component"]["code"] == component_code:
                return node_id
