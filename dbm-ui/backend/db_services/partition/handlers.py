"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from collections import defaultdict
from typing import Any, Dict, List, Union

from django.core.exceptions import ObjectDoesNotExist
from django.forms import model_to_dict
from django.http.response import HttpResponse
from django.utils.translation import gettext as _

from backend.components import CCApi, DRSApi
from backend.components.mysql_partition.client import DBPartitionApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.api.cluster.base.handler import ClusterHandler
from backend.db_meta.enums import ClusterType
from backend.db_meta.enums.instance_inner_role import InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.db_report.models.mysql_partiton_resuly import MysqlPartitionResult
from backend.db_services.partition.constants import (
    QUERY_DATABASE_FIELD_TYPE,
    QUERY_PARTITION_FIELD_TYPE,
    QUERY_UNIQUE_FIELDS_SQL,
    Query_partition_info_SQL,
    Query_shard_info_SQL,
    Query_Tables_info_SQL,
)
from backend.db_services.partition.exceptions import (
    DBPartitionCreateException,
    DBPartitionInternalServerError,
    DBPartitionInvalidFieldException,
    DBPartitionV2DRSAPIException,
    DBPartitionV2ShardInfoException,
)
from backend.exceptions import ApiRequestError, ApiResultError
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket
from backend.utils.batch_request import request_multi_thread
from backend.utils.excel import ExcelHandler


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
    def create_and_dry_run_partition(cls, user: str, create_data: Dict):
        """
        创建预执行分区策略
        @param user: 操作者
        @param create_data: 分区策略数据
        """
        # 针对直接调用接口做规则检查
        # 不符合规则的抛出异常，配置不会写入分区配置表
        cls.verify_partition_field(
            bk_biz_id=create_data["bk_biz_id"],
            cluster_id=create_data["cluster_id"],
            dblikes=create_data["dblikes"],
            tblikes=create_data["tblikes"],
            partition_column=create_data["partition_column"],
            partition_column_type=create_data["partition_column_type"],
        )
        # 创建分区策略
        cluster = Cluster.objects.get(id=create_data["cluster_id"])
        create_data["bk_cloud_id"] = cluster.bk_cloud_id

        try:
            partition = DBPartitionApi.create_conf(params=create_data)
        except (ApiRequestError, ApiResultError) as e:
            raise DBPartitionCreateException(_("分区管理创建失败，创建参数:{}, 错误信息: {}").format(create_data, e))

        # 如果不需要分区执行的数据，则默认直接返回分区创建数据
        # need_dry_run = create_data.pop("need_dry_run", True)
        create_data.pop("need_dry_run", True)
        # 默认创建分区配置就立即初始化 此处用编码为True
        need_dry_run = True
        if not need_dry_run:
            return partition

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

        # 创建分区配置立即初始化，硬编码为True
        create_data["auto_commit"] = True
        # 如果不需要创建分区单据，则返回分区执行数据
        if not create_data["auto_commit"]:
            return config__id_result

        # 创建分区初始化单据(可能创建多个单据，一个单据对应一个分区策略)
        ticket_list = cls.execute_partition(user, create_data["cluster_id"], config__id_result)
        return ticket_list

    @classmethod
    def execute_partition(cls, user: str, cluster_id: int, partition_objects: Dict[str, Any]):
        """
        执行分区策略
        @param user: 创建者
        @param cluster_id: 集群ID
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
                "bk_cloud_id": cluster.bk_cloud_id,
                "immute_domain": cluster.immute_domain,
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
                bk_biz_id=cluster.bk_biz_id,
                remark=_("分区单据执行"),
                details={"infos": [partition_data]},
                auto_execute=True,
            )
            ticket_list.append(model_to_dict(ticket))

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
        if rpc_results[0]["cmd_results"] is None:
            raise DBPartitionInternalServerError(_("字段信息查询错误：{}").format(rpc_results[0]["error_msg"]))

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

        # 如果表没有主键 or 唯一键，需要提示用户分区执行会锁表
        if not index_data:
            return _("表没有主键或者唯一键，将表改造为分区表的过程中会锁表，会阻塞查询、删除、修改、添加、表结构变更等语句")

    @classmethod
    def query_log_v2(cls, config_id: int = None, **kwargs):
        """
        查询分区v2执行日志
        @param config_id: 配置id
        @return: 分区执行日志
        根据分区配置id获取执行最近一条执行日志
        """

        if not config_id:
            raise DBPartitionInternalServerError(_("config_id不能为空"))

        # tb_mysql_partition_result 中不直接存 cluster_id，这里按 config_id 维度查询最近一条记录，
        log_obj = MysqlPartitionResult.objects.filter(config_id=config_id).order_by("-create_time").first()

        if not log_obj:
            return {"message": _("未查询到分区执行日志")}

        # 将模型对象转换为字典返回，便于前端直接展示字段
        log_data = model_to_dict(log_obj)
        return log_data

    @classmethod
    def query_status_v2(cls, config_id: int = None, **kwargs):
        """
        查询分区v2执行状态
        @param config_id: 配置id
        @return: 分区执行状态
        根据分区配置id获取执行最近一条执行日志
        """

        if not config_id:
            raise DBPartitionInternalServerError(_("config_id不能为空"))

        # tb_mysql_partition_result 中不直接存 cluster_id，这里按 config_id 维度查询最近一条记录
        log_obj = (
            MysqlPartitionResult.objects.filter(config_id=config_id)
            .only("status", "create_time")
            .order_by("-create_time")
            .first()
        )

        if not log_obj:
            return {"message": _("未查询到分区执行日志")}

        # 将模型对象转换为字典返回，便于前端直接展示字段
        log_data = model_to_dict(log_obj)
        return log_data

    @classmethod
    def query_conf_by_status(cls, bk_biz_id: int, cluster_type: str, status: str, limit: int = 10, offset: int = 0):
        """
        根据执行状态过滤分区配置
        @param bk_biz_id: 业务ID
        @param cluster_type: 集群类型
        @param status: 执行状态过滤值（如 SUCCEEDED / FAILED / WARNING）
        @param limit: 分页大小
        @param offset: 分页偏移
        """

        # log_obj = MysqlPartitionResult.objects.filter().only("status", "create_time").order_by("-create_time").first()

        partition_data = DBPartitionApi.query_conf_v2(
            params={"bk_biz_id": bk_biz_id, "cluster_type": cluster_type, "limit": 0, "offset": 0}
        )

        status_upper = status.upper()
        filtered = []
        for item in partition_data.get("items", []):
            log_detail = cls.query_status_v2(config_id=item["id"]) or {}
            item_status = (log_detail.get("status") or "WARNING").upper()
            if item_status == status_upper:
                item["status"] = item_status
                item["execute_time"] = log_detail.get("create_time") or ""
                filtered.append(item)

        total = len(filtered)
        paged = filtered[offset : offset + limit] if limit else filtered
        return {"count": total, "results": paged}

    @classmethod
    def create_and_run_partition_v2(cls, user: str, create_data: Dict):
        """
        创建并执行分区策略v2
        @param user: 操作者
        @param create_data: 分区策略数据
        """
        # 针对直接调用接口做规则检查
        # 不符合规则的抛出异常，配置不会写入分区配置表
        cls.verify_partition_field(
            bk_biz_id=create_data["bk_biz_id"],
            cluster_id=create_data["cluster_id"],
            dblikes=create_data["dblikes"],
            tblikes=create_data["tblikes"],
            partition_column=create_data["partition_column"],
            partition_column_type=create_data["partition_column_type"],
        )
        # 创建分区策略
        cluster = Cluster.objects.get(id=create_data["cluster_id"])
        create_data["bk_cloud_id"] = cluster.bk_cloud_id

        try:
            resp = DBPartitionApi.create_conf_v2(params=create_data, raw=True)
        except (ApiRequestError, ApiResultError) as e:
            raise DBPartitionCreateException(_("分区管理创建失败，创建参数:{}, 错误信息: {}").format(create_data, e))

        if resp["code"] != 0:
            raise DBPartitionInternalServerError(_("分区配置创建失败：{}").format(resp["message"]))

        # 配置创建成功后立即执行
        partition_items = resp["data"]["items"]

        for partition_item in partition_items:
            partition_item["config_id"] = partition_item.pop("id")

        partition_execute_objects = {
            "bk_biz_id": create_data["bk_biz_id"],
            "partition_infos": [
                {
                    "cluster_id": create_data["cluster_id"],
                    "configs": partition_items,
                    "force": False,
                }
            ],
        }
        return cls.execute_partition_v2(user, **partition_execute_objects)

    @classmethod
    def execute_partition_v2(cls, user: str, **partition_objects: Dict[str, Any]):
        """
        执行分区策略
        @param user: 创建者
        @param cluster_id: 集群ID
        @param partition_objects: 分区信息列表
        """

        ticket_list: List[Dict] = []
        for info in partition_objects["partition_infos"]:
            cluster_id = info["cluster_id"]
            configs = info["configs"]
            # 获取分区单据的类型
            cluster = Cluster.objects.get(id=cluster_id)
            if cluster.cluster_type == ClusterType.TenDBCluster:
                partition_ticket_type = TicketType.TENDBCLUSTER_PARTITION_V2
            else:
                partition_ticket_type = TicketType.MYSQL_PARTITION_V2

            partition_data = {
                "cluster_type": cluster.cluster_type,
                "cluster_id": cluster_id,
                "configs": configs,
                "force": info.get("force", False),
            }
            ticket = Ticket.create_ticket(
                ticket_type=partition_ticket_type,
                creator=user,
                bk_biz_id=cluster.bk_biz_id,
                remark=_("分区v2单据执行"),
                details=partition_data,
                auto_execute=True,
            )
            ticket_list.append(model_to_dict(ticket))

        return ticket_list

    @classmethod
    def query_field_type_v2(
        cls, bk_biz_id: int, cluster_id: int, dblikes: List[str], tblikes: List[str], partition_column: str
    ):
        """
        查询分区字段类型
        @param bk_biz_id: 业务ID
        @param cluster_id: 集群ID
        @param dblikes: 校验库名列表
        @param tblikes: 校验表面列表
        @param partition_column: 分区字段
        """
        # 获取集群的DRS查询地址，格式化库表过滤条件
        cluster = Cluster.objects.get(id=cluster_id)
        address = ClusterHandler.get_exact_handler(bk_biz_id=bk_biz_id, cluster_id=cluster_id).get_remote_address()

        # 库名支持模糊匹配，表名需要是实际表名
        table_sts = "(" + " or ".join([f"table_name = '{table}'" for table in tblikes]) + ")"
        db_sts = "(" + " or ".join([f"table_schema like '{db}'" for db in dblikes]) + ")"
        field_sts = "column_name = '{}'".format(partition_column)
        fields_type_sql = QUERY_PARTITION_FIELD_TYPE.format(table_sts=table_sts, db_sts=db_sts, field_sts=field_sts)

        # 查询涉及的所有库表索引信息和字段类型信息
        rpc_results = DRSApi.rpc(
            {"bk_cloud_id": cluster.bk_cloud_id, "addresses": [address], "cmds": [fields_type_sql]}
        )
        # 结构与内容健壮性校验，保证后续取值一定安全且有意义
        if not rpc_results or not isinstance(rpc_results, list):
            raise DBPartitionInternalServerError(_("字段信息查询错误：DRS 返回为空"))

        first_result = rpc_results[0]
        cmd_results = first_result.get("cmd_results")
        if not cmd_results:
            raise DBPartitionInternalServerError(_("字段信息查询错误：{}").format(first_result.get("error_msg") or _("结果集为空")))

        first_cmd = cmd_results[0]
        table_data = first_cmd.get("table_data") or []
        if not table_data:
            # DRS 调用成功但没有返回任何行，认为分区字段不存在或不合法
            raise DBPartitionInvalidFieldException(_("分区字段【{}】不存在或库表信息错误，请检查库表/字段配置是否正确").format(partition_column))

        # table_data 可能包含多个表的同名字段，这里对每一行做字段完整性校验
        required_keys = ["column_name", "data_type", "table_name", "table_schema"]
        checked_rows: List[Dict[str, Any]] = []
        for row in table_data:
            # 校验必须字段是否存在且有值
            missing_keys = [k for k in required_keys if not row.get(k)]
            if missing_keys:
                raise DBPartitionInternalServerError(_("字段信息查询错误：返回结果缺少字段 {}").format(",".join(missing_keys)))
            checked_rows.append(row)
        # 1. 校验字段类型是否合法：仅允许 int/bigint/datetime/timestamp
        allow_types = {"int", "bigint", "datetime", "timestamp"}
        invalid_type_rows = [r for r in checked_rows if str(r["data_type"]).lower() not in allow_types]
        if invalid_type_rows:
            detail_str = "; ".join(
                f"{r['table_schema']}.{r['table_name']}.{r['column_name']}({r['data_type']})"
                for r in invalid_type_rows
            )
            raise DBPartitionInvalidFieldException(
                _("分区字段类型仅支持 int/bigint/datetime/timestamp，实际结果：{}").format(detail_str)
            )

        # 2. 聚合校验：所有行的 column_name 和 data_type 必须一致
        # 其实 int 和 bigint 可以互转，但这里不校验，仍然当做错误报出来，用户单独处理
        first_col = checked_rows[0]["column_name"]
        first_type = str(checked_rows[0]["data_type"]).lower()
        has_inconsistent = any(
            r["column_name"] != first_col or str(r["data_type"]).lower() != first_type for r in checked_rows
        )
        if has_inconsistent:
            # 将所有查询到的库表+字段类型返回到错误信息中，便于前端展示
            all_rows_str = "; ".join(
                f"{r['table_schema']}.{r['table_name']}.{r['column_name']}({r['data_type']})" for r in checked_rows
            )
            raise DBPartitionInvalidFieldException(_("分区字段查询结果不一致，所有库表的字段名与类型必须一致，实际结果：{}").format(all_rows_str))

        # 校验通过后，仅返回公共的 data_type 字段值
        return first_type

    @classmethod
    def save_and_execute_v2(cls, user: str, partition_object: Dict[str, Any]):
        """
        保存并执行分区策略
        @param user: 创建者
        @param partition_info: 分区信息
        先更新分区配置
        再执行分区策略
        """

        try:
            resp = DBPartitionApi.update_conf_v2(params=partition_object, raw=True)
        except (ApiRequestError, ApiResultError) as e:
            raise DBPartitionInternalServerError(_("分区配置更新失败：{}").format(e))

        if resp["code"] != 0:
            raise DBPartitionInternalServerError(_("分区配置更新失败：{}").format(resp["message"]))
            # 配置创建成功后立即执行

        partition_items = resp["data"]["items"]
        for partition_item in partition_items:
            partition_item["config_id"] = partition_item.pop("id")

        partition_execute_object = {
            "bk_biz_id": partition_object["bk_biz_id"],
            "partition_infos": [
                {
                    "cluster_id": partition_object["cluster_id"],
                    "configs": partition_items,
                    "force": partition_object.get("force", False),
                }
            ],
        }

        return cls.execute_partition_v2(user, **partition_execute_object)

    @classmethod
    def check_partition_info(cls, cluster_id: int, config_id: int):
        """
        针对已有的分区配置，检查表的分区执行情况
        @param cluster_id: 集群id
        @param config_id: 配置id
        @return: 分区执行情况
        """
        # 先查询集群地址
        try:
            cluster = Cluster.objects.get(id=cluster_id)
        except Cluster.DoesNotExist:
            raise DBPartitionInternalServerError(_("集群不存在：{}").format(cluster_id))

        if cluster.cluster_type == ClusterType.TenDBCluster:
            address = cluster.tendbcluster_ctl_primary_address()
        elif cluster.cluster_type == ClusterType.TenDBHA:
            address = cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER).ip_port
        elif cluster.cluster_type == ClusterType.TenDBSingle:
            address = cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.ORPHAN).ip_port
        else:
            raise DBPartitionInternalServerError(_("集群类型不支持：{}").format(cluster.cluster_type))

        # 获取分区配置
        partition_confs = cls._get_partition_conf_by_config_id(cluster_id, config_id, cluster.cluster_type)
        partition_conf = partition_confs["configs"][0]
        dblike = partition_conf["dblike"]
        tblike = partition_conf["tblike"]
        # partition_column = partition_conf["partition_column"]
        # partition_column_type = partition_conf["partition_column_type"]
        # partition_time_interval = partition_conf["partition_time_interval"]
        # partition_type = partition_conf["partition_type"]
        # expire_time = partition_conf["expire_time"]

        table_info = cls._check_table_info(address, cluster.bk_cloud_id, cluster.cluster_type, dblike, tblike)
        return table_info

    @classmethod
    def _get_partition_conf_by_config_id(cls, cluster_id: int, config_id: int, cluster_type: str):
        """
        根据配置id获取分区配置
        @param cluster_id: 集群id
        @param config_id: 配置id
        @param cluster_type: 集群类型
        @return: 分区配置
        """
        params = {
            "name": "get_conf_by_id",
            "cluster_type": cluster_type,
            "query_args": {"cluster_id": cluster_id, "config_id": config_id},
        }
        try:
            partition_conf = DBPartitionApi.partition_conf_query(params=params, raw=True)
        except Exception as e:
            raise DBPartitionInternalServerError(_("分区配置查询错误：{}").format(e))
        if partition_conf["code"] != 0:
            raise DBPartitionInternalServerError(_("分区配置查询错误：{}").format(partition_conf["message"]))
        partition_conf = partition_conf["data"]
        return partition_conf

    @classmethod
    def _check_table_info(cls, address: str, bk_cloud_id: int, cluster_type: str, dblike: str, tblike: str):
        """
        检查表信息
        @param address: 地址
        @param bk_cloud_id: 云区域id
        @param cluster_type: 集群类型
        @param dblike: 库名
        @param tblike: 表名
        @return: 表信息
        """

        if cluster_type == ClusterType.TenDBCluster:
            table_info = cls._check_tendbcluster_table_info(address, bk_cloud_id, dblike, tblike)
        else:
            pass
        return table_info

    @classmethod
    def _get_is_partitiond_query_sql(cls, dblike: str, tblike: str):
        """
        获取查询语句
        @param dblike: 库名
        @param tblike: 表名
        @return: 查询语句
        """
        # 判断 dblike 和 tblike 是否包含通配符 '%'
        db_like_has_wildcard = "%" in dblike
        tb_like_has_wildcard = "%" in tblike

        if db_like_has_wildcard and tb_like_has_wildcard:
            condition_sts = "TABLE_SCHEMA LIKE '{}' AND TABLE_NAME LIKE '{}'".format(dblike, tblike)
            query_sql = Query_Tables_info_SQL.format(condition_sts=condition_sts)
        elif db_like_has_wildcard and not tb_like_has_wildcard:
            condition_sts = "TABLE_SCHEMA LIKE '{}' AND TABLE_NAME = '{}'".format(dblike, tblike)
            query_sql = Query_Tables_info_SQL.format(condition_sts=condition_sts)
        elif not db_like_has_wildcard and tb_like_has_wildcard:
            condition_sts = "TABLE_SCHEMA = '{}' AND TABLE_NAME LIKE '{}'".format(dblike, tblike)
            query_sql = Query_Tables_info_SQL.format(condition_sts=condition_sts)
        else:
            condition_sts = "TABLE_SCHEMA = '{}' AND TABLE_NAME = '{}'".format(dblike, tblike)
            query_sql = Query_Tables_info_SQL.format(condition_sts=condition_sts)
        return query_sql

    @classmethod
    def _check_tendbcluster_table_info(cls, address: str, bk_cloud_id: int, dblike: str, tblike: str) -> List:
        """
        查询tendbcluster表信息
        @param address: 地址
        @param bk_cloud_id: 云区域id
        @param query_sql: 查询语句
        @return: 表信息
        返回列表，列表中每个元素是一个元祖，是排序后的表信息，元祖中第一个元素是分片id，第二个元素是表信息
        表信息是一个字典，字典中包含以下键：
        - db_address: 分片数据库地址
        - shard_id: 分片id
        - create_options: 创建选项
        - table_schema: 表schema
        - table_name: 表名
        - partition_name: 分区名称
        - partition_description: 分区描述
        """
        # 先查询shard信息
        try:
            shard_infos = DRSApi.short_rpc(
                {
                    "addresses": [address],
                    "cmds": [Query_shard_info_SQL],
                    "force": False,
                    "bk_cloud_id": bk_cloud_id,
                }
            )
        except Exception as e:
            raise DBPartitionV2DRSAPIException(message=_("DRS API 调用异常：{}").format(e))

        if shard_infos[0]["cmd_results"] is None:
            raise DBPartitionV2ShardInfoException(message=_("分片信息查询错误：{}").format(shard_infos[0]["error_msg"]))

        shard_info_list = shard_infos[0]["cmd_results"][0]["table_data"]
        table_infos = {}

        for shard_info in shard_info_list:
            db_address = "{}{}{}".format(shard_info["Host"], IP_PORT_DIVIDER, shard_info["Port"])
            shard_id = shard_info["Server_name"].split("SPT")[1]
            new_dblike = "{}_{}".format(dblike, shard_id)
            partitiond_query_sql = cls._get_is_partitiond_query_sql(new_dblike, tblike)
            partition_info_query_sql = Query_partition_info_SQL.format(dbname=new_dblike, tb=tblike)

            try:
                res = DRSApi.short_rpc(
                    {
                        "addresses": [db_address],
                        "cmds": [partitiond_query_sql, partition_info_query_sql],
                        "force": False,
                        "bk_cloud_id": bk_cloud_id,
                    }
                )
            except Exception as e:
                table_infos[shard_info["Server_name"].split("SPT")[1]] = {"Exception": e}
                continue

            if res[0]["cmd_results"] is None:
                table_infos[shard_info["Server_name"].split("SPT")[1]] = {"error": res[0]["error_msg"]}
                continue

            partitiond_query_result = res[0]["cmd_results"][0]["table_data"][0]
            partition_info_result = res[0]["cmd_results"][1]["table_data"]
            table_infos[shard_info["Server_name"].split("SPT")[1]] = {
                "db_address": db_address,
                "shard_id": shard_id,
                "create_options": partitiond_query_result["CREATE_OPTIONS"],
                "table_schema": partitiond_query_result["TABLE_SCHEMA"],
                "table_name": partitiond_query_result["TABLE_NAME"],
                "partition_name": [info["PARTITION_NAME"] for info in partition_info_result],
                "partition_description": [info["PARTITION_DESCRIPTION"] for info in partition_info_result],
            }
        # 对table_infos的键做int转换后排序，避免'10'比'2'小的问题
        # 排序后返回一个列表，列表中每个元素是一个元组，元组中第一个元素是键，第二个元素是值
        sorted_table_infos = sorted(table_infos.items(), key=lambda x: int(x[0]))

        return sorted_table_infos

    @classmethod
    def import_from_excel(cls, excel_file) -> dict:
        """
        从Excel文件导入分区策略

        Args:
            excel_file: Excel文件对象

        Returns:
            dict: 导入结果
        """
        try:
            # 使用ExcelHandler解析Excel文件，表头在第2行（索引为1）
            excel_data = ExcelHandler.paser(excel_file, header_row=1)

            if not excel_data:
                return {
                    "success_count": 0,
                    "failed_count": 0,
                    "failed_items": [{"row": 0, "error": _("Excel文件为空或没有数据行")}],
                }

            # 检查必要的列是否存在
            required_columns = [_("集群"), _("DB名"), _("表名"), _("分区字段"), _("分区字段类型"), _("分区间隔（天）"), _("数据过期时间（天）")]
            first_row = excel_data[0] if excel_data else {}
            missing_columns = [col for col in required_columns if col not in first_row]
            if missing_columns:
                return {
                    "success_count": 0,
                    "failed_count": len(excel_data),
                    "failed_items": [{"row": 0, "error": _("Excel文件缺少必要列: {}").format(", ".join(missing_columns))}],
                }

            success_count = 0
            failed_count = 0
            failed_items = []

            # 处理数据行
            for row_num, row_data in enumerate(excel_data, start=3):  # 从第3行开始（Excel行号）
                try:
                    # 验证集群是否存在
                    cluster = Cluster.objects.get(name=row_data[_("集群")])
                    # 构建分区策略参数
                    partition_data = {
                        "cluster_id": cluster.id,
                        "bk_biz_id": cluster.bk_biz_id,
                        "dblikes": [row_data.get(_("DB名"), "")],
                        "tblikes": [row_data[_("表名")]],
                        "partition_column": row_data[_("分区字段")],
                        "partition_column_type": row_data[_("分区字段类型")],
                        "partition_time_interval": int(row_data[_("分区间隔（天）")]),
                        "expire_time": int(row_data.get(_("数据过期时间（天）"), 720)),
                    }

                    # 调用API创建分区策略
                    result = DBPartitionApi.create_conf(params=partition_data)

                    if result.get("code") == 0:
                        success_count += 1
                    else:
                        failed_count += 1
                        failed_items.append({"row": row_num, "error": result.get("message", _("未知错误"))})
                except ObjectDoesNotExist:
                    failed_count += 1
                    failed_items.append({"row": row_num, "error": _("集群 {} 不存在").format(row_data[_("集群")])})
                except Exception as e:
                    failed_count += 1
                    failed_items.append({"row": row_num, "error": str(e)})

            return {"success_count": success_count, "failed_count": failed_count, "failed_items": failed_items}
        except Exception as e:
            return {
                "success_count": 0,
                "failed_count": 0,
                "failed_items": [{"row": 0, "error": _("Excel文件解析失败: {}").format(str(e))}],
            }

    @classmethod
    def export_partitions(
        cls, export_type: str, bk_biz_id: int, selected_ids: List[int] = None, cluster_type: str = None
    ) -> HttpResponse:
        """
        导出分区策略数据

        Args:
            export_type: 导出类型，all-所有策略，selected-已选策略
            selected_ids: 已选策略ID列表
            cluster_type: 集群类型
            bk_biz_id: 业务ID

        Returns:
            Dict: 导出结果，包含文件内容和文件名
        """
        # 获取分区策略数据
        if export_type == "all":
            # 获取所有策略
            partition_data = DBPartitionApi.query_conf(
                params={"bk_biz_id": bk_biz_id, "cluster_type": cluster_type, "limit": 20, "offset": 0}
            )
        else:
            # 获取指定策略
            partition_data = DBPartitionApi.query_conf(
                params={
                    "bk_biz_id": bk_biz_id,
                    "cluster_type": cluster_type,
                    "ids": selected_ids,
                    "limit": 20,
                    "offset": 0,
                }
            )

        partitions = partition_data.get("items", [])

        # 准备数据字典列表
        data_dict_list = []
        for partition in partitions:
            data_dict_list.append(
                {
                    _("策略ID"): partition.get("id", ""),
                    _("集群"): partition.get("immute_domain", ""),
                    _("DB名"): partition.get("dblike", ""),
                    _("表名"): partition.get("tblike", ""),
                    _("分区字段"): partition.get("partition_column", ""),
                    _("分区间隔（天）"): partition.get("partition_time_interval", ""),
                    _("数据过期时间（天）"): partition.get("expire_time", ""),
                }
            )

        # 设置表头
        headers = [
            {"id": _("策略ID"), "name": _("策略ID")},
            {"id": _("集群"), "name": _("集群")},
            {"id": _("DB名"), "name": _("DB名")},
            {"id": _("表名"), "name": _("表名")},
            {"id": _("分区字段"), "name": _("分区字段")},
            {"id": _("分区间隔（天）"), "name": _("分区间隔（天）")},
            {"id": _("数据过期时间（天）"), "name": _("数据过期时间（天）")},
        ]

        # 使用ExcelHandler序列化数据
        workbook = ExcelHandler.serialize(
            data_dict__list=data_dict_list, headers=headers, match_header=True, sheet_name=_("分区策略列表")
        )

        # 获取业务信息
        biz_infos = CCApi.search_business(
            {
                "fields": ["bk_biz_id", "bk_biz_name"],
                "biz_property_filter": {
                    "condition": "AND",
                    "rules": [{"field": "bk_biz_id", "operator": "equal", "value": bk_biz_id}],
                },
            },
            use_admin=True,
        ).get("info", [])
        # 生成文件名
        from datetime import datetime

        try:
            biz_name = biz_infos[0].get("bk_biz_name", _("未知业务"))
        except (IndexError, AttributeError):
            biz_name = _("未知业务")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = f"{timestamp}_{biz_name}({bk_biz_id})mysql_partition.xlsx"

        return ExcelHandler.response(workbook, file_name)

    @classmethod
    def batch_dry_run(cls, partition_list: List[Dict]) -> Dict:
        """
        批量分区策略预执行

        Args:
            partition_list: 分区策略参数列表

        Returns:
            Dict: 批量预执行结果
        """
        results = []

        for index, partition_data in enumerate(partition_list):
            try:
                # 验证集群是否存在
                cluster = Cluster.objects.get(id=partition_data["cluster_id"])

                # 构建完整的预执行参数
                partition_data.update(
                    immute_domain=cluster.immute_domain,
                    bk_cloud_id=cluster.bk_cloud_id,
                    cluster_type=cluster.cluster_type,
                    bk_biz_id=cluster.bk_biz_id,
                )

                # 调用API进行预执行
                result = DBPartitionApi.dry_run(params=partition_data, raw=True)

                # 添加索引信息便于追踪
                result["index"] = index
                results.append(result)

            except ObjectDoesNotExist:
                results.append(
                    {
                        "index": index,
                        "code": -1,
                        "message": _("集群ID {} 不存在").format(partition_data["cluster_id"]),
                        "data": None,
                    }
                )
            except Exception as e:
                results.append({"index": index, "code": -1, "message": _("预执行失败: {}").format(str(e)), "data": None})

        return {"results": results}
