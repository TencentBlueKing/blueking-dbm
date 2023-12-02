"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import json
from collections import defaultdict
from typing import Any, Dict, List, Union

from django.forms import model_to_dict
from django.utils.translation import ugettext as _

from backend.components import DRSApi
from backend.components.mysql_partition.client import DBPartitionApi
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_services.partition.constants import QUERY_DATABASE_FIELD_TYPE, QUERY_UNIQUE_FIELDS_SQL
from backend.db_services.partition.exceptions import DBPartitionCreateException, DBPartitionInvalidFieldException
from backend.exceptions import ApiRequestError, ApiResultError
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket
from backend.utils.batch_request import request_multi_thread


class PartitionHandler(object):
    """分区管理视图的处理函数"""

    @staticmethod
    def format_err_execute_objects(config_data, message):
        config_data = config_data or {}
        err_execute_object = {
            "config_id": config_data.get("id"),
            "db_like": config_data.get("dblike"),
            "tblike": config_data.get("tblike"),
        }
        return [{"message": message, "execute_objects": [err_execute_object]}]

    @classmethod
    def get_dry_run_data(cls, data):
        params, res = data
        params = params["params"] if "params" in params else params
        config_id = params.get("config_id") or params.get("params", {}).get("config_id", 0)
        if res["result"]:
            config_data = [{**data, "message": ""} for data in res["data"]]
            return {config_id: config_data}
        else:
            cluster_type, bk_biz_id = params["cluster_type"], params["bk_biz_id"]
            query_params = {
                "ids": [config_id],
                "cluster_type": cluster_type,
                "bk_biz_id": bk_biz_id,
                "limit": 1,
                "offset": 0,
            }
            config_data = DBPartitionApi.query_conf(query_params)
            config_data = config_data["items"][0] if config_data["count"] else None
            return {config_id: cls.format_err_execute_objects(config_data, res["message"])}

    @classmethod
    def create_and_dry_run_partition(cls, create_data: Dict):
        """
        创建预执行分区策略
        @param create_data: 分区策略数据
        """

        # 创建分区策略
        try:
            partition = DBPartitionApi.create_conf(params=create_data)
        except (ApiRequestError, ApiResultError) as e:
            raise DBPartitionCreateException(_("分区管理创建失败，创建参数:{}, 错误信息: {}").format(create_data, e))

        # 判断是否需要执行分区
        partition_ids = partition["config_ids"]
        partition_dry_run_params: List[Dict] = [
            {"params": {**create_data, "config_id": partition_id}, "raw": True} for partition_id in partition_ids
        ]
        results = request_multi_thread(
            func=DBPartitionApi.dry_run,
            params_list=partition_dry_run_params,
            get_data=cls.get_dry_run_data,
            in_order=True,
        )

        config__id_result: Dict[str, Union[List, str]] = {}
        for res in results:
            config__id_result.update(res)

        return config__id_result

    @classmethod
    def execute_partition(
        cls,
        user: str,
        bk_biz_id: int,
        bk_cloud_id: int,
        cluster_id: int,
        immute_domain: str,
        partition_objects: Dict[str, Any],
    ):
        """
        执行分区策略
        @param user: 创建者
        @param bk_biz_id: 业务ID
        @param bk_cloud_id: 云区域ID
        @param cluster_id: 集群ID
        @param immute_domain: 集群域名
        @param partition_objects: 分区执行数据
        """
        # 获取分区单据的类型
        cluster = Cluster.objects.get(id=cluster_id)
        if cluster.cluster_type == ClusterType.TenDBCluster:
            partition_ticket_type = TicketType.TENDBCLUSTER_PARTITION
        else:
            partition_ticket_type = TicketType.MYSQL_PARTITION

        # 构造分区策略单据数据列表
        partition_data_list: List[Dict] = [
            {
                "config_id": config_id,
                "cluster_id": cluster_id,
                "bk_cloud_id": bk_cloud_id,
                "immute_domain": immute_domain,
                "partition_objects": partition_object,
            }
            for config_id, partition_object in partition_objects.items()
        ]

        # 循环执行分区单据，这里一个分区策略对应一个单据
        ticket_list: List[Dict] = []
        for partition_data in partition_data_list:
            # 创建分区单据
            ticket = Ticket.create_ticket(
                ticket_type=partition_ticket_type,
                creator=user,
                bk_biz_id=bk_biz_id,
                remark=_("分区单据执行"),
                details={"infos": [partition_data]},
                auto_execute=True,
            )
            ticket_list.append(model_to_dict(ticket))
            # 创建分区日志
            partition_log_data = {
                "cluster_type": cluster.cluster_type,
                "config_id": int(partition_data["config_id"]),
                "bk_biz_id": bk_biz_id,
                "cluster_id": cluster.id,
                "bk_cloud_id": bk_cloud_id,
                "ticket_id": ticket.id,
                "immute_domain": cluster.immute_domain,
                "time_zone": cluster.time_zone,
                "ticket_detail": json.dumps(ticket.details),
            }
            DBPartitionApi.create_log(partition_log_data)

        return ticket_list

    @classmethod
    def verify_partition_field(
        cls,
        bk_biz_id: int,
        cluster_id: int,
        dblikes: List[str],
        tblikes: List[str],
        partition_column: str,
        partition_column_type: str,
    ):
        """
        校验分区字段是否合理
        @param bk_biz_id: 业务ID
        @param cluster_id: 集群ID
        @param dblikes: 校验库名列表
        @param tblikes: 校验表面列表
        @param partition_column: 分区字段
        @param partition_column_type: 分区字段类型
        """

        def _verify_valid_index(_index_keys, _field):
            # 不属于主键部分
            primary_keys = _index_keys["primary"]
            if primary_keys and not (_field in primary_keys):
                return False

            # 不属于唯一键交集
            unique_keys_list = _index_keys["unique"]
            if unique_keys_list and not (_field in set(unique_keys_list[0]).intersection(*unique_keys_list[1:])):
                return False

            return True

        # 获取集群的DRS查询地址，格式化库表过滤条件
        cluster = Cluster.objects.get(id=cluster_id)
        address = ClusterHandler.get_exact_handler(bk_biz_id=bk_biz_id, cluster_id=cluster_id).get_remote_address()

        table_sts = "(" + " or ".join([f"table_name = '{table}'" for table in tblikes]) + ")"
        db_sts = "(" + " or ".join([f"table_schema like '{db}'" for db in dblikes]) + ")"
        unique_fields_sql = QUERY_UNIQUE_FIELDS_SQL.format(table_sts=table_sts, db_sts=db_sts)
        fields_type_sql = QUERY_DATABASE_FIELD_TYPE.format(table_sts=table_sts, db_sts=db_sts)

        # 查询涉及的所有库表索引信息和字段类型信息
        rpc_results = DRSApi.rpc(
            {"bk_cloud_id": cluster.bk_cloud_id, "addresses": [address], "cmds": [unique_fields_sql, fields_type_sql]}
        )
        cmd__data = {res["cmd"]: res["table_data"] for res in rpc_results[0]["cmd_results"]}
        index_data, field_type_data = cmd__data[unique_fields_sql], cmd__data[fields_type_sql]

        # 分区策略创建至少要保证能匹配存在的库表
        if not field_type_data:
            raise DBPartitionInvalidFieldException(_("【{}】【{}】当前库表模式匹配为空，请检查是否是合法库表").format(dblikes, tblikes))

        # 对字段索引的要求：
        # 1. 如果存在主键，则分区字段必须是主键的一部分
        # 2. 如果存在唯一键，则分区字段必须是所有唯一键的交集
        db_index_keys: Dict[str, Dict[str, Dict]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for inx in index_data:
            # DRS有些字段为大写，有些字段为小写，这里统一转为小写
            inx = {k.lower(): v for k, v in inx.items()}
            index_column_list = inx["column_list"].split(",")
            if inx["index_name"] == "PRIMARY":
                db_index_keys[inx["table_schema"]][inx["table_name"]]["primary"].extend(index_column_list)
            else:
                db_index_keys[inx["table_schema"]][inx["table_name"]]["unique"].append(index_column_list)

        for db, table_index_keys in db_index_keys.items():
            for table, index_keys in table_index_keys.items():
                if not _verify_valid_index(index_keys, partition_column):
                    raise DBPartitionInvalidFieldException(
                        _("【{}】【{}】分区字段{}不满足属于主键部分或唯一键交集的要求").format(db, table, partition_column)
                    )

        # 对字段类型的要求：分区字段对应的原表字段类型相同
        db_fields: Dict[str, Dict[str, Dict]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        for field in field_type_data:
            field = {k.lower(): v for k, v in field.items()}
            db_fields[field["table_schema"]][field["table_name"]][field["column_name"]] = field["column_type"]

        for db, table_fields in db_fields.items():
            for table, fields in table_fields.items():
                if partition_column not in fields or partition_column_type not in fields[partition_column]:
                    raise DBPartitionInvalidFieldException(
                        _("【{}】【{}】分区字段{}与该表对应的字段类型不匹配").format(db, table, partition_column)
                    )
