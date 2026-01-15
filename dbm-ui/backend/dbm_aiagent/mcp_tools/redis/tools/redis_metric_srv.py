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
import datetime
import logging

from backend import env
from backend.components.bkmonitorv3.client import BKMonitorV3Api
from backend.db_services.redis.capacity_evaluate_service.util import is_dev, logger_debug

from .redis_meta_srv import RedisMetaService

logger = logging.getLogger("root")
# UNIFY_QUERY_PARAMS is used to query prometheus
UNIFY_QUERY_PARAMS = {
    "bk_biz_id": 0,
    "query_configs": [
        {
            "data_source_label": "prometheus",
            "data_type_label": "time_series",
            "promql": "",  # we will set promql in exec_promql_instant
            "interval": 60,
            "alias": "a",
        }
    ],
    "expression": "a",
    "alias": "a",
    "start_time": 1697100405,  # we will set start_time in exec_promql_instant
    "end_time": 1697101305,  # we will set end_time in exec_promql_instant
    "slimit": 500,
    "down_sample_range": "1s",
    # 取最新的几个周期，可以加速查询（如果指标数据不连续，则查不出数据）
    "type": "instant",
}


class RedisMetricService:
    """redis metric service"""

    redis_meta_srv: RedisMetaService

    debug_info: dict = {}

    def __init__(self, immute_domain: str):
        self.redis_meta_srv = RedisMetaService(immute_domain)

    def generate_used_capacity_info(self, bk_biz_id: int):
        """fetch used capacity from tsdb, if there are missing instances, return error info"""
        query_errors = []
        if self.redis_meta_srv.is_memory_redis():
            used_capacity_sql = (
                "avg by (cluster_domain,instance,instance_role)"
                "(bkmonitor:exporter_dbm_redis_exporter:__default__:redis_memory_used_bytes"
                "{bk_target_ip =~ _instance_address_str_})"
            )
        else:
            used_capacity_sql = (
                "avg by (cluster_domain,instance,instance_role)"
                "(bkmonitor:exporter_dbm_redis_exporter:__default__:redis_rocksdb_datadir_size_kb"
                "{bk_target_ip =~ _instance_address_str_} * 1024) "
            )

        used_capacity_sql = self.replace_instance_address_str(
            used_capacity_sql, self.redis_meta_srv.get_master_ip_list()
        )
        logger.info(f"generate_used_capacity_info sql: {used_capacity_sql}")
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(minutes=5)
        tsdb_result = self.exec_promql_instant(used_capacity_sql, bk_biz_id, start_time, end_time)
        query_result = self.tsdb_result_to_map(tsdb_result, "instance")
        logger.info(f"generate_used_capacity_info query_result: {query_result}")

        # test, set query_result
        if is_dev():
            logger_debug("is_dev, set query_result for test")
            for shard in self.redis_meta_srv.shard_list:
                first_member = shard["members"][0]
                instance = first_member["ip"] + "-" + str(first_member["port"])
                query_result[instance] = 1024 * 1024 * 1024

        miss_instances = []
        total_result = 0  # total of query result
        max_result = 0  # max of query result
        count = 0

        if len(self.redis_meta_srv.shard_list) == 0:
            query_errors.append("shard_list is empty")
            return query_errors

        for shard in self.redis_meta_srv.shard_list:
            first_member = shard["members"][0]
            instance = first_member["ip"] + "-" + str(first_member["port"])
            if instance not in query_result:
                miss_instances.append(instance)
                continue
            v = query_result[instance]
            total_result += v / 1024 / 1024
            if v > max_result:
                max_result = v
            count += 1

        if len(miss_instances) > 0:
            query_errors.append(f"miss_instances: {miss_instances}")
        return query_errors

    def replace_instance_address_str(self, sql: str, ip_list: list):
        """build sql"""
        ip_list = list(set(ip_list))
        instance_address_str = "'^(" + "|".join(list(set(ip_list))) + ")$'"
        sql = sql.replace("_instance_address_str_", instance_address_str)
        return sql

    def tsdb_result_to_map(self, tsdb_result: dict, key_name: str):
        """
        convert tsdb result to map
        """
        result = {}
        for item in tsdb_result["series"]:
            result[item["dimensions"][key_name]] = item["datapoints"][0][0]
        return result

    def exec_promql_instant(self, promql: str, bk_biz_id: int, start_time, end_time):
        """
        execute promql
        """
        params = copy.deepcopy(UNIFY_QUERY_PARAMS)
        params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
        params["start_time"] = int(start_time.timestamp())
        params["end_time"] = int(end_time.timestamp())
        params["query_configs"][0]["promql"] = promql
        try:
            out = BKMonitorV3Api.unify_query(params, use_admin=True)
            return out
        except Exception:
            return None
