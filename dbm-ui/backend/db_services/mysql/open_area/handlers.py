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
import copy
import re
from collections import defaultdict
from typing import Any, Dict, List, Union

from django.utils.translation import ugettext as _

from backend.components import DBPrivManagerApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.dbpermission.constants import AccountType
from backend.db_services.mysql.open_area.models import TendbOpenAreaConfig
from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.flow.utils.mysql.db_table_filter.tools import contain_glob


class OpenAreaHandler:
    """封装开区的一些处理函数"""

    ALL_TABLE_FLAG = "*"

    @classmethod
    def validate_only_openarea(cls, bk_biz_id, config_name, config_id: int = -1) -> bool:
        """校验同一业务下的开区模板名称唯一"""
        config = TendbOpenAreaConfig.objects.filter(bk_biz_id=bk_biz_id, config_name=config_name)
        is_duplicated = config.exists() and (config.first().id != config_id)
        return not is_duplicated

    @classmethod
    def __check_db_list(cls, source_db, real_dbs):
        """检查库是否合法"""
        if source_db not in real_dbs:
            return _("源集群不存在库{}，请检查或修改开区模板".format(source_db))
        return ""

    @classmethod
    def __check_table_list(cls, real_tables, source_db, check_tables, check_type):
        """
        检查表是否合法,并根据模糊匹配解析具体表结构
        1. schema全选，传到flow为[]
        2. data全选，传到flow为["*"]
        3. 模糊匹配或者指定部分表，需要解析具体的表结构，并和集群表结构对比
        """
        if cls.ALL_TABLE_FLAG in check_tables and check_type == "data":
            return [cls.ALL_TABLE_FLAG], ""

        if cls.ALL_TABLE_FLAG in check_tables and check_type == "schema":
            return [], ""

        error_msg = ""
        match_tables = []
        if cls.ALL_TABLE_FLAG not in check_tables and check_tables:
            # 尝试精确匹配
            exact = [t for t in check_tables if not contain_glob(t)]
            not_exist_tables = set(exact) - set(real_tables[source_db])
            if not_exist_tables:
                error_msg = _("源集群库{}中不存在表{}，请检查或修改开区模板\n".format(source_db, not_exist_tables))
            match_tables.extend(exact)

            # 尝试模糊匹配
            fuzzy = [t.replace("*", "%").replace("%", ".*").replace("?", ".") for t in check_tables if contain_glob(t)]
            for pattern in fuzzy:
                re_pattern = re.compile(f"^{pattern}$")
                pattern_match = [t for t in real_tables[source_db] if re_pattern.match(t)]
                if not pattern_match:
                    error_msg += _("源集群库{}中不存在表匹配[{}]，请检查或修改开区模板".format(source_db, pattern))
                match_tables.extend(pattern_match)

        return match_tables, error_msg

    @classmethod
    def __get_openarea_execute_objects(cls, config, config_data, cluster_id__cluster):
        """获取开区执行数据结构体"""
        remote_handler = RemoteServiceHandler(bk_biz_id=config.bk_biz_id)
        openarea_results: List[Dict[str, Any]] = []

        # 实时查询集群的库表
        real_dbs = remote_handler.show_databases(cluster_ids=[config.source_cluster_id])[0]["databases"]
        cluster_db_infos = [{"cluster_id": config.source_cluster_id, "dbs": real_dbs}]
        real_tables = remote_handler.show_tables(cluster_db_infos)[0]["table_data"]

        # 获取基础执行结构体
        execute_objects_tpl = [
            {
                "source_db": config_rule["source_db"],
                "target_db": config_rule["target_db_pattern"],
                "schema_tblist": config_rule["schema_tblist"],
                "data_tblist": config_rule["data_tblist"],
                "authorize_ips": [],
            }
            for config_rule in config.config_rules
        ]
        # 校验每个开区执行结构，如果存在不合法的库表，则填充错误信息
        for info in execute_objects_tpl:
            # 校验库是否存在
            err_db_msg = cls.__check_db_list(info["source_db"], real_dbs)
            # 校验schema_tblist是否合法
            info["schema_tblist"], err_schema_tb_msg = cls.__check_table_list(
                real_tables, info["source_db"], info["schema_tblist"], "schema"
            )
            # 校验data_tblist是否合法
            info["data_tblist"], err_data_tb_msg = cls.__check_table_list(
                real_tables, info["source_db"], info["data_tblist"], "data"
            )
            err_msg_list = [err_db_msg, err_schema_tb_msg, err_data_tb_msg]
            info["error_msg"] = "\n".join([msg for msg in err_msg_list if msg])

        for data in config_data:
            # 获取开区执行数据
            execute_objects = copy.deepcopy(execute_objects_tpl)
            for info in execute_objects:
                try:
                    info["target_db"] = info["target_db"].format(**data["vars"])
                    info["authorize_ips"] = data.get("authorize_ips", [])
                except KeyError:
                    info["error_msg"] = info["error_msg"] + "\n" + _("范式{}渲染缺少变量".format(info["target_db"]))

            openarea_results.append(
                {
                    "cluster_id": data["cluster_id"],
                    "target_cluster_domain": cluster_id__cluster[data["cluster_id"]].immute_domain,
                    "execute_objects": execute_objects,
                }
            )

        return openarea_results

    @classmethod
    def __get_openarea_rules_set(cls, config, config_data, operator, cluster_id__cluster):
        """获取开区授权数据"""
        priv_ids = config.related_authorize
        # 如果没有授权ID，则直接返回为空
        if not priv_ids:
            return []

        account_type = (
            AccountType.TENDBCLUSTER if config.cluster_type == ClusterType.TenDBCluster else AccountType.MYSQL
        )
        authorize_rules = DBPrivManagerApi.list_account_rules(
            {"bk_biz_id": config.bk_biz_id, "ids": priv_ids, "cluster_type": account_type}
        )
        # 根据用户名和db将授权规则分批
        user__dbs_rules: Dict[str, List[str]] = defaultdict(list)
        user__privileges: Dict[str, List[Dict]] = defaultdict(list)
        for rule_data in authorize_rules["items"]:
            user = rule_data["account"]["user"]
            user__dbs_rules[user].extend([r["dbname"] for r in rule_data["rules"]])
            user__privileges[user].extend(
                [{"user": user, "access_db": r["dbname"], "priv": r["priv"]} for r in rule_data["rules"]]
            )
        # 根据当前的规则生成授权数据
        authorize_details: List[Dict[str, Any]] = [
            {
                "bk_biz_id": config.bk_biz_id,
                "operator": operator,
                "user": user,
                "source_ips": data["authorize_ips"],
                "target_instances": [cluster_id__cluster[data["cluster_id"]].immute_domain],
                "access_dbs": user__dbs_rules[user],
                "privileges": user__privileges[user],
                "account_rules": [
                    {"bk_biz_id": config.bk_biz_id, "dbname": dbname} for dbname in user__dbs_rules[user]
                ],
                "cluster_type": cluster_id__cluster[data["cluster_id"]].cluster_type,
            }
            for data in config_data
            if data.get("authorize_ips")
            for user in user__dbs_rules.keys()
        ]
        return authorize_details

    @classmethod
    def openarea_result_preview(
        cls, operator: str, config_id: int, config_data: List[Dict[str, Union[int, str, Dict]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        config = TendbOpenAreaConfig.objects.get(id=config_id)
        clusters = Cluster.objects.filter(id__in=[info["cluster_id"] for info in config_data])
        cluster_id__cluster = {cluster.id: cluster for cluster in clusters}
        # 获取开区执行数据
        openarea_results: List[Dict[str, Any]] = cls.__get_openarea_execute_objects(
            config, config_data, cluster_id__cluster
        )
        # 获取开区授权规则
        rules_set: List[Dict[str, Any]] = cls.__get_openarea_rules_set(
            config, config_data, operator, cluster_id__cluster
        )
        return {"config_data": openarea_results, "rules_set": rules_set, "config_id": config_id}
