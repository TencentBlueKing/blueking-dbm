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
from collections import defaultdict
from typing import Any, Dict, List, Union

from django.utils.translation import ugettext as _

from backend.components import DRSApi
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.models import Cluster
from backend.db_services.mysql.constants import QUERY_SCHEMA_DBS_SQL, QUERY_SCHEMA_TABLES_SQL, QUERY_TABLES_FROM_DB_SQL
from backend.db_services.mysql.remote_service.exceptions import RemoteServiceBaseException
from backend.db_services.mysql.sqlparse.exceptions import SQLParseBaseException
from backend.db_services.mysql.sqlparse.handlers import SQLParseHandler
from backend.db_services.partition.constants import QUERY_DATABASE_FIELD_TYPE
from backend.flow.consts import SYSTEM_DBS


class RemoteServiceHandler:
    def __init__(self, bk_biz_id: int):
        self.bk_biz_id = bk_biz_id

    @classmethod
    def _format_db_tb_name(cls, _data_names):
        _copied_data = copy.deepcopy(_data_names)
        for index in range(len(_copied_data)):
            # mysql模糊匹配单个字符，用_，原本字符串里带的_，要\_转义，如果是*，则转为%表示like % --> 永真
            _copied_data[index] = (
                _copied_data[index].replace("_", "\_").replace("?", "_").replace("*", "%")
            )  # noqa: W605
        return _copied_data

    @classmethod
    def _get_db_tb_sts(cls, _data_names, key, default):
        _data_names = cls._format_db_tb_name(_data_names)
        _sts = "(" + " or ".join([f"{key} like '{name}'" for name in _data_names]) + ")"
        _sts = f"({default})" if _sts == "()" else _sts
        return _sts

    @classmethod
    def _get_db_table_list(cls, _bk_cloud_id, _address, _cmds, key):
        _rpc_results = DRSApi.rpc({"bk_cloud_id": _bk_cloud_id, "addresses": [_address], "cmds": _cmds})

        if _rpc_results[0]["error_msg"]:
            raise RemoteServiceBaseException(_("DRS调用失败，错误信息: {}").format(_rpc_results[0]["error_msg"]))

        _cmd__datalist = {
            _result["cmd"]: [data[key] for data in _result["table_data"]] for _result in _rpc_results[0]["cmd_results"]
        }
        return _cmd__datalist

    def _get_cluster_address(self, cluster_id__role_map, cluster_id):
        cluster_handler = ClusterHandler.get_exact_handler(bk_biz_id=self.bk_biz_id, cluster_id=cluster_id)
        if cluster_id__role_map.get(cluster_id):
            return cluster_handler, cluster_handler.get_remote_address(cluster_id__role_map[cluster_id])

        return cluster_handler, cluster_handler.get_remote_address()

    def show_databases(
        self, cluster_ids: List[int], cluster_id__role_map: Dict[int, str] = None
    ) -> List[Dict[str, Union[int, List[str]]]]:
        """
        批量查询集群的数据库列表
        @param cluster_ids: 集群ID列表
        @param cluster_id__role_map: (可选)集群ID和对应查询库表角色的映射表
        """

        # 如果集群列表为空，则提前返回
        if not cluster_ids:
            return []

        cluster_id__role_map = cluster_id__role_map or {}
        cloud_addresses = defaultdict(list)
        cluster_databases = []
        address_cluster_id_map = defaultdict(dict)
        cluster_ids = list(set(cluster_ids))

        # 查询各个集群可执行的实例地址
        for cluster_id in cluster_ids:
            cluster_handler, address = self._get_cluster_address(cluster_id__role_map, cluster_id)
            bk_cloud_id = cluster_handler.cluster.bk_cloud_id
            cloud_addresses[bk_cloud_id].append(address)
            address_cluster_id_map[bk_cloud_id][address] = cluster_id

        # 批量查询实例地址对应的数据库列表
        for bk_cloud_id in cloud_addresses.keys():
            rpc_results = DRSApi.rpc(
                {"bk_cloud_id": bk_cloud_id, "addresses": cloud_addresses[bk_cloud_id], "cmds": ["show databases"]}
            )

            if rpc_results[0]["error_msg"]:
                raise RemoteServiceBaseException(_("DRS调用失败，错误信息: {}").format(rpc_results[0]["error_msg"]))

            for rpc_result in rpc_results:
                cmd_results = rpc_result["cmd_results"] or [{}]
                cluster_databases.append(
                    {
                        "cluster_id": address_cluster_id_map[bk_cloud_id][rpc_result["address"]],
                        "databases": [
                            data["Database"]
                            for data in cmd_results[0].get("table_data", [])
                            if data["Database"] not in SYSTEM_DBS
                        ],
                        "system_databases": SYSTEM_DBS,
                    }
                )
        return cluster_databases

    def show_tables(
        self, cluster_db_infos: List[Dict], cluster_id__role_map: Dict[int, str] = None
    ) -> List[Dict[str, Union[str, List]]]:
        """
        批量查询集群的数据库列表
        @param cluster_db_infos: 集群DB信息
        @param cluster_id__role_map: (可选)集群ID和对应查询库表角色的映射表
        """
        cluster_id__role_map = cluster_id__role_map or {}

        cluster_table_infos: List[Dict[str, Union[str, List]]] = []
        for info in cluster_db_infos:
            cluster_handler, address = self._get_cluster_address(cluster_id__role_map, info["cluster_id"])

            # 构造数据表查询语句
            db_sts = " or ".join([f"table_schema='{db}'" for db in info["dbs"]])
            query_table_sql = QUERY_TABLES_FROM_DB_SQL.format(db_sts=db_sts)

            # 执行DRS，并聚合库所包含的表数据
            bk_cloud_id = cluster_handler.cluster.bk_cloud_id
            rpc_results = DRSApi.rpc({"bk_cloud_id": bk_cloud_id, "addresses": [address], "cmds": [query_table_sql]})

            if rpc_results[0]["error_msg"]:
                raise RemoteServiceBaseException(_("DRS调用失败，错误信息: {}").format(rpc_results[0]["error_msg"]))

            table_data = rpc_results[0]["cmd_results"][0]["table_data"]
            aggregate_table_data: Dict[str, List[str]] = {db: [] for db in info["dbs"]}
            for data in table_data:
                aggregate_table_data[data["table_schema"]].append(data["table_name"])

            cluster_table_infos.append({"cluster_id": cluster_handler.cluster_id, "table_data": aggregate_table_data})

        return cluster_table_infos

    def check_cluster_database(self, check_infos: List[Dict[str, Any]]) -> List[Dict[str, Dict]]:
        """
        批量校验集群下的DB是否存在
        @param check_infos: 校验库表的信息
        """

        cluster_id__check_info = {info["cluster_id"]: info for info in check_infos}
        cluster_database_infos = self.show_databases(cluster_ids=list(cluster_id__check_info.keys()))

        for db_info in cluster_database_infos:
            check_info = {
                db_name: (db_name in db_info["databases"])
                for db_name in cluster_id__check_info[db_info["cluster_id"]]["db_names"]
            }
            cluster_id__check_info[db_info["cluster_id"]].update(check_info=check_info)

        return list(cluster_id__check_info.values())

    def show_database_with_pattern(self, cluster_id: int, dbs: list, ignore_dbs: list) -> list:
        """
        根据库正则查询单个集群的库信息
        @param cluster_id: 集群id，
        @param dbs: 库正则列表
        @param ignore_dbs: 忽略库正则
        """
        sys_db_list = "(" + ",".join([f"'{db}'" for db in SYSTEM_DBS]) + ")"
        cluster_handler, address = self._get_cluster_address({}, cluster_id)

        # 构造查询库的sql语句
        db_sts = self._get_db_tb_sts(dbs, "SCHEMA_NAME", 1)
        ignore_sts = self._get_db_tb_sts(ignore_dbs, "SCHEMA_NAME", 0)
        query_schema_dbs_sql = QUERY_SCHEMA_DBS_SQL.format(db_sts=db_sts, sys_db_list=sys_db_list)
        query_ignore_schema_dbs_sql = QUERY_SCHEMA_DBS_SQL.format(db_sts=ignore_sts, sys_db_list=sys_db_list)

        # 查询库
        query_dbs_list = self._get_db_table_list(
            _bk_cloud_id=cluster_handler.cluster.bk_cloud_id,
            _address=address,
            _cmds=[query_schema_dbs_sql, query_ignore_schema_dbs_sql],
            key="SCHEMA_NAME",
        )
        databases = set(query_dbs_list[query_schema_dbs_sql]) - set(query_dbs_list[query_ignore_schema_dbs_sql])

        return list(databases)

    def show_table_with_pattern(self, cluster_id: int, dbs: list, tables: list, ignore_tables: list) -> list:
        """
        根据表正则查询单个集群的表信息
        @param cluster_id: 集群id，
        @param dbs: 库列表
        @param tables: 表正则列表
        @param ignore_tables: 忽略表正则列表
        """
        cluster_handler, address = self._get_cluster_address({}, cluster_id)

        # 构造查询表的sql语句
        db_list = "(" + ",".join([f"'{db}'" for db in dbs]) + ")"
        table_sts = self._get_db_tb_sts(tables, "TABLE_NAME", 1)
        ignore_table_sts = self._get_db_tb_sts(ignore_tables, "TABLE_NAME", 0)
        query_schema_tables_sql = QUERY_SCHEMA_TABLES_SQL.format(db_list=db_list, table_sts=table_sts)
        query_ignore_schema_tables_sql = QUERY_SCHEMA_TABLES_SQL.format(db_list=db_list, table_sts=ignore_table_sts)

        # 查询表
        query_tbs_list = self._get_db_table_list(
            _bk_cloud_id=cluster_handler.cluster.bk_cloud_id,
            _address=address,
            _cmds=[query_schema_tables_sql, query_ignore_schema_tables_sql],
            key="TABLE_NAME",
        )
        tables = set(query_tbs_list[query_schema_tables_sql]) - set(query_tbs_list[query_ignore_schema_tables_sql])

        return list(tables)

    def check_flashback_database(self, flashback_infos: List[Dict[str, Any]]):
        """
        批量校验闪回库表是否存在
        @param flashback_infos: 闪回信息
        [
            {
                "cluster_id": 17,
                "databases": "db%",
                "databases_ignore": "tb%",
                "tables": "db1",
                "tables_ignore": "tb1",
            }
        ]
        """

        for info in flashback_infos:
            databases = self.show_database_with_pattern(
                info["cluster_id"], info["databases"], info["databases_ignore"]
            )
            if not databases:
                info.update(message=_("不存在可用于闪回的库"))
                continue

            tables = self.show_table_with_pattern(info["cluster_id"], databases, info["tables"], info["tables_ignore"])
            if not tables:
                info.update(message=_("不存在可用于闪回的表"))
                continue

            info.update(message="")

        return flashback_infos

    def show_databases_with_db_patterns(
        self, cluster_db_infos: List[Dict], cluster_id__role_map: Dict[int, str] = None
    ) -> List[Dict[str, List[str]]]:
        """
        批量查询集群的数据库列表
        @param cluster_db_infos: 集群db查询信息
        info格式：{"cluster_id": 3, "dbs": ["db%"], "ignore_dbs": ["db1"]}
        @param cluster_id__role_map: (可选)集群ID和对应查询库表角色的映射表
        """

        cluster_databases_infos: List[Dict[str, List[str]]] = []
        for info in cluster_db_infos:
            databases = self.show_database_with_pattern(info["cluster_id"], info["dbs"], info["ignore_dbs"])
            cluster_databases_infos.append({"cluster_id": info["cluster_id"], "databases": databases})
        return cluster_databases_infos

    def webconsole_rpc(self, cluster_id: int, cmd: str, **kwargs):
        """
        执行webconsole命令，只支持select语句
        @param cluster_id: 集群ID
        @param cmd: 执行命令
        """

        # 校验select语句
        try:
            SQLParseHandler().parse_select_statement(cmd)
        except SQLParseBaseException as e:
            return {"query": [], "error_msg": e.message}

        # 获取远程执行地址
        cluster = Cluster.objects.get(id=cluster_id)
        bk_cloud_id = cluster.bk_cloud_id
        __, remote_address = self._get_cluster_address(cluster_id__role_map={}, cluster_id=cluster.id)

        # 获取rpc结果
        rpc_results = DRSApi.webconsole_rpc({"bk_cloud_id": bk_cloud_id, "addresses": [remote_address], "cmds": [cmd]})
        if rpc_results[0]["error_msg"]:
            return {"query": [], "error_msg": rpc_results[0]["error_msg"]}

        return {"query": rpc_results[0]["cmd_results"][0]["table_data"], "error_msg": ""}

    def validate_table_fields(self, info, input_fild_names):
        """
        校验库表中字段是否存在
        @param info:
        @param input_fild_names: csv头部并计算列数信息
        """
        bk_biz_id = self.bk_biz_id
        cluster_id = info["cluster_id"]

        # 获取集群的DRS查询地址，格式化库表过滤条件
        cluster = Cluster.objects.get(id=cluster_id)
        address = ClusterHandler.get_exact_handler(bk_biz_id=bk_biz_id, cluster_id=cluster_id).get_remote_address()

        table_sts = "(" + " or ".join([f"table_name = '{table}'" for table in info["tables"]]) + ")"
        db_sts = "(" + " or ".join([f"table_schema like '{db}'" for db in info["databases"]]) + ")"
        fields_type_sql = QUERY_DATABASE_FIELD_TYPE.format(table_sts=table_sts, db_sts=db_sts)

        # 查询涉及的所有库表索引信息和字段类型信息
        rpc_results = DRSApi.rpc(
            {"bk_cloud_id": cluster.bk_cloud_id, "addresses": [address], "cmds": [fields_type_sql]}
        )
        if rpc_results[0]["cmd_results"] is None:
            raise RemoteServiceBaseException(_("字段信息查询错误：{}").format(rpc_results[0]["error_msg"]))

        db_table_fields: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for table_data in rpc_results[0]["cmd_results"][0]["table_data"]:
            db_table_fields[table_data["table_schema"]][table_data["table_name"]].append(table_data["column_name"])

        for db_name, table_info in db_table_fields.items():
            for table_name, fild_names in table_info.items():
                no_file_name = set(input_fild_names).difference(set(fild_names))
                if no_file_name:
                    raise RemoteServiceBaseException(
                        _("数据库【{}】表【{}】中不存在字段{}".format(db_name, table_name, no_file_name))
                    )
