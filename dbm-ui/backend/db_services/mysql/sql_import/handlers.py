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
from typing import Any, Dict, List, Optional, Union

from django.core.cache import cache
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.translation import ugettext as _

from backend.components.sql_import.client import SQLSimulationApi
from backend.configuration.constants import PLAT_BIZ_ID, DBType
from backend.core.storages.storage import get_storage
from backend.db_services.mysql.sql_import.constants import (
    BKREPO_SQLFILE_PATH,
    CACHE_SEMANTIC_AUTO_COMMIT_FIELD,
    CACHE_SEMANTIC_SKIP_PAUSE_FILED,
    CACHE_SEMANTIC_TASK_FIELD,
    SQL_SEMANTIC_CHECK_DATA_EXPIRE_TIME,
    SQLImportMode,
)
from backend.db_services.mysql.sql_import.exceptions import SQLImportBaseException
from backend.db_services.taskflow.handlers import TaskFlowHandler
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.engine import BambooEngine
from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.engine.controller.spider import SpiderController
from backend.flow.models import FlowNode, FlowTree
from backend.flow.plugins.components.collections.mysql.semantic_check import SemanticCheckComponent
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

    def grammar_check(self, sql_content: str = None, sql_files: List[InMemoryUploadedFile] = None) -> Optional[Dict]:
        """
        sql 语法检查
        @param sql_content: sql内容
        @param sql_files: sql文件
        """

        sql_file_info_list = self._upload_sql_file(sql_content, sql_files)
        file_name_list = [os.path.split(sql_file_info["sql_path"])[1] for sql_file_info in sql_file_info_list]
        dir_name = os.path.split(sql_file_info_list[0]["sql_path"])[0]

        # 获取检查信息
        check_info = SQLSimulationApi.grammar_check(
            params={"path": dir_name, "files": file_name_list, "cluster_type": self.cluster_type}
        )

        # 填充sql内容。TODO：如果sql内容过大需要进行压缩吗？
        for sql_file_info in sql_file_info_list:
            sql_path = sql_file_info["sql_path"]
            file_name = os.path.split(sql_path)[1]
            check_info[file_name].update(
                content=sql_file_info["sql_content"], sql_path=sql_path, raw_file_name=sql_file_info["raw_file_name"]
            )

        return check_info

    def semantic_check(
        self,
        charset: str,
        path: str,
        cluster_ids: List[int],
        execute_sql_files: List[str],
        execute_db_infos: List[Dict[str, List]],
        highrisk_warnings: Dict,
        ticket_type: str,
        ticket_mode: Dict,
        import_mode: SQLImportMode,
        backup: List[Dict],
    ) -> Dict:
        """
        sql 模拟执行(sql 语义检查)
        @param charset: 字符集
        @param path: sql文件路径
        @param cluster_ids: 集群列表
        @param execute_sql_files: 待执行的sql文件名
        @param execute_db_infos: 待执行的db匹配模式
        @param highrisk_warnings: 高危信息
        @param ticket_type: 单据类型
        @param ticket_mode: sql导入单据的触发类型
        @param import_mode: sql文件导入类型
        @param backup: 备份信息（和备份单据一样）
        """

        # 语义检查参数准备
        execute_objects: List[Dict[str, Union[str, List]]] = []
        for sql_file in execute_sql_files:
            execute_objects.extend([{"sql_file": sql_file, **db_info} for db_info in execute_db_infos])

        # 异步执行语义检查
        root_id = f"{datetime.date.today()}{uuid.uuid1().hex[:6]}".replace("-", "")
        ticket_data = {
            "created_by": self.context["user"],
            "bk_biz_id": self.bk_biz_id,
            "ticket_type": ticket_type,
            "charset": charset,
            "path": path,
            "cluster_ids": cluster_ids,
            "execute_objects": execute_objects,
            "highrisk_warnings": highrisk_warnings,
            "ticket_mode": ticket_mode,
            "import_mode": import_mode,
            "backup": backup,
        }
        try:
            if self.cluster_type == DBType.MySQL:
                MySQLController(root_id=root_id, ticket_data=ticket_data).mysql_sql_semantic_check_scene()
            elif self.cluster_type == DBType.TenDBCluster:
                SpiderController(root_id=root_id, ticket_data=ticket_data).spider_semantic_check_scene()
        except Exception as e:  # pylint: disable=broad-except
            raise SQLImportBaseException(_("模拟流程构建失败，错误信息: {}").format(e))

        # 获取语义执行的node id
        tree = FlowTree.objects.get(root_id=root_id)
        node_id = self.get_node_id_by_component(tree=tree.tree, component_code=SemanticCheckComponent.code)

        # 缓存用户的语义检查，并删除过期的数据。注：django的cache不支持redis命令，这里只能使用原生redis客户端进行操作
        now = int(time.time())
        key = CACHE_SEMANTIC_TASK_FIELD.format(user=self.context["user"], cluster_type=self.cluster_type)
        RedisConn.zadd(key, {root_id: now})
        RedisConn.set(root_id, StateType.CREATED)

        expired_task_ids = RedisConn.zrangebyscore(key, "-inf", now - SQL_SEMANTIC_CHECK_DATA_EXPIRE_TIME)
        self.delete_user_semantic_tasks(task_ids=expired_task_ids)

        return {"root_id": root_id, "node_id": node_id}

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
            return {"sql_files": "", "import_mode": "", "sql_data_ready": False}

        import_mode = details["import_mode"]
        details["execute_sql_files"] = [detail.pop("sql_file") for detail in details["execute_objects"]]
        details["execute_db_infos"] = details.pop("execute_objects")
        return {"semantic_data": details, "import_mode": import_mode, "sql_data_ready": True}

    def deploy_user_config(self, root_id: str, is_auto_commit: bool, is_skip_pause: bool) -> None:
        """
        更改用户配置(是否自动提交，是否跳过确认)
        @param root_id: 语义任务执行ID
        @param is_auto_commit: 是否自动提交
        @param is_skip_pause: 是否跳过暂停
        """

        # auto_commit的配置
        auto_commit_key = CACHE_SEMANTIC_AUTO_COMMIT_FIELD.format(bk_biz_id=self.bk_biz_id, root_id=root_id)
        cache.set(auto_commit_key, is_auto_commit, SQL_SEMANTIC_CHECK_DATA_EXPIRE_TIME)

        # skip_pause的配置
        skip_pause_key = CACHE_SEMANTIC_SKIP_PAUSE_FILED.format(bk_biz_id=self.bk_biz_id, root_id=root_id)
        cache.set(skip_pause_key, is_skip_pause, SQL_SEMANTIC_CHECK_DATA_EXPIRE_TIME)

    def query_user_config(self, root_id: str) -> Dict:
        """
        查询用户配置
        @param root_id: 语义任务执行ID
        """

        auto_commit_key = CACHE_SEMANTIC_AUTO_COMMIT_FIELD.format(bk_biz_id=self.bk_biz_id, root_id=root_id)
        skip_pause_key = CACHE_SEMANTIC_SKIP_PAUSE_FILED.format(bk_biz_id=self.bk_biz_id, root_id=root_id)
        is_auto_commit = cache.get(auto_commit_key)
        is_skip_pause = cache.get(skip_pause_key)
        return {"is_auto_commit": is_auto_commit, "is_skip_pause": is_skip_pause}

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
                "node_id": self.get_node_id_by_component(tree.tree, code),
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

    def get_node_id_by_component(self, tree: Dict, component_code: str) -> str:
        """
        根据component获取node id
        :param tree: 流程树对象
        :param component_code: 组件code名称
        """

        activities: Dict = tree["activities"]
        for node_id, activity in activities.items():
            if activity.get("component") and activity["component"]["code"] == component_code:
                return node_id

            if activity.get("pipeline"):
                node_id = self.get_node_id_by_component(activity["pipeline"], component_code)
                if node_id:
                    return node_id

        return ""
