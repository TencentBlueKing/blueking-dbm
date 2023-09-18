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
import base64
import copy
import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Union

from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext as _
from jinja2 import Environment

from backend import env
from backend.components import JobApi
from backend.components.bklog.client import BKLogApi
from backend.constants import DATETIME_PATTERN
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import StorageInstance
from backend.db_meta.models.cluster import Cluster
from backend.db_services.mysql.fixpoint_rollback.constants import BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS
from backend.exceptions import AppBaseException
from backend.flow.consts import SUCCESS_LIST, DBActuatorActionEnum, DBActuatorTypeEnum, InstanceStatus, JobStatusEnum
from backend.flow.utils.script_template import dba_toolkit_actuator_template, fast_execute_script_common_kwargs
from backend.utils.string import pascal_to_snake
from backend.utils.time import datetime2str, find_nearby_time, str2datetime


class FixPointRollbackHandler:
    """
    封装定点回档相关接口
    """

    def __init__(self, cluster_id: int):
        self.cluster = Cluster.objects.get(id=cluster_id)

    def _get_ip_list(self) -> List[Dict[str, Any]]:
        """
        获取集群的相关机器ip信息
        """
        storages: List[StorageInstance] = (
            self.cluster.storageinstance_set.select_related("machine")
            .filter(Q(instance_inner_role=InstanceInnerRole.SLAVE) | Q(instance_inner_role=InstanceInnerRole.MASTER))
            .filter(status=InstanceStatus.RUNNING.value)
        )
        ip_list: List[Dict[str, Any]] = [
            {"bk_cloud_id": storage.machine.bk_cloud_id, "ip": storage.machine.ip, "port": storage.port}
            for storage in storages
        ]
        return ip_list

    def _find_local_backup_script(self, port: int):
        """
        获取查询本地文件备份内容的脚本
        :param port: 进程的Port
        """
        payload = json.dumps(
            {
                "extend": {
                    "backup_dirs": ["/data/dbbak", "/data1/dbbak"],
                    "tgt_instance": {"port": port},
                }
            }
        )
        render_params = {
            "db_type": DBActuatorTypeEnum.MySQL.value,
            "action": DBActuatorActionEnum.GetBackupFile.value,
            "payload": f"'{payload}'",
        }
        jinja_env = Environment()
        template = jinja_env.from_string(dba_toolkit_actuator_template)
        return template.render(render_params).encode("utf-8")

    @staticmethod
    def _batch_make_job_requests(job_func: Callable, job_payloads: List[Dict]):
        """
        批量请求作业平台接口
        :param job_payloads: 请求参数
        """
        tasks = []
        with ThreadPoolExecutor(max_workers=min(len(job_payloads), settings.CONCURRENT_NUMBER)) as ex:
            for job_payload in job_payloads:
                tasks.append(ex.submit(job_func, job_payload))

        task_results = []
        for future in as_completed(tasks):
            task_results.append(future.result())

        return task_results

    @staticmethod
    def _format_job_backup_log(raw_backup_logs: List[str]) -> List[Dict[str, Any]]:
        """
        格式化本地备份记录日志
        :param raw_backup_logs: 原始日志信息
        """
        pattern = re.compile(r"^<ctx>(.*?)</ctx>$")
        backup_logs = []
        for raw_log in raw_backup_logs:
            backup_log_dict = json.loads(pattern.match(raw_log).group(1))["backups"]
            for backup_id, log in backup_log_dict.items():
                log["file_list"].append(log["index_file"].split("/")[-1])
                log["mysql_role"] = log.pop("db_role")

                # 过滤适用于定点回档的备份
                if str(log["data_schema_grant"]).lower() == "all" or (
                    "schema" in str(log["data_schema_grant"]).lower()
                    and "data" in str(log["data_schema_grant"]).lower()
                ):
                    backup_logs.append(log)

        return backup_logs

    def _get_log_from_bklog(self, collector, start_time, end_time, query_string="*") -> List[Dict]:
        """
        从日志平台获取对应采集项的日志
        @param collector: 采集项名称
        @param start_time: 开始时间
        @param end_time: 结束时间
        @param query_string: 过滤条件
        """
        resp = BKLogApi.esquery_search(
            {
                "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.{collector}",
                "start_time": start_time,
                "end_time": end_time,
                # 这里需要精确查询集群域名，所以可以通过log: "key: \"value\""的格式查询
                "query_string": query_string,
                "start": 0,
                "size": 1000,
                "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
            },
            use_admin=True,
        )
        backup_logs = []
        for hit in resp["hits"]["hits"]:
            raw_log = json.loads(hit["_source"]["log"])
            backup_logs.append({pascal_to_snake(key): value for key, value in raw_log.items()})

        return backup_logs

    @staticmethod
    def aggregate_backup_log_by_id(backup_logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        按照backup_id聚合备份记录
        :param backup_logs: 备份记录列表
        """
        backup_id__backup_logs_map = defaultdict(dict)
        for log in backup_logs:
            file_name, backup_id = log["file_name"], log["backup_id"]
            if not backup_id__backup_logs_map.get(backup_id):
                backup_id__backup_logs_map[backup_id].update(copy.deepcopy(log))
                backup_id__backup_logs_map[backup_id]["backup_time"] = log["consistent_backup_time"]
                backup_id__backup_logs_map[backup_id]["file_list"] = []
                backup_id__backup_logs_map[backup_id]["file_list_details"] = []

                # 丢弃一些聚合后无用字段
                delete_fields = ["consistent_backup_time", "file_name", "file_size", "task_id"]
                for field in delete_fields:
                    backup_id__backup_logs_map[backup_id].pop(field)

            backup_id__backup_logs_map[backup_id]["file_list"].append(file_name)
            backup_id__backup_logs_map[backup_id]["file_list_details"].append(
                {"file_name": file_name, "size": log["file_size"], "task_id": log["task_id"]}
            )

            if file_name.split(".")[-1] == "index":
                backup_id__backup_logs_map[log["backup_id"]]["index_file"] = file_name

        return list(backup_id__backup_logs_map.values())

    def query_backup_log_from_bklog(self, start_time: str, end_time: str) -> List[Dict]:
        """
        通过日志平台查询集群的时间范围内的备份记录
        :param start_time: 开始时间
        :param end_time: 结束时间
        """

        cluster_domain = self.cluster.immute_domain
        backup_logs = self._get_log_from_bklog(
            collector="mysql_backup_result",
            start_time=start_time,
            end_time=end_time,
            query_string=f'log: "cluster_address: \\"{cluster_domain}\\""',
        )
        return self.aggregate_backup_log_by_id(backup_logs)

    def query_binlog_from_bklog(self, start_time: datetime, end_time: datetime, host_ip: str = None) -> Dict:
        """
        通过日志平台查询集群的时间范围内的binlog记录
        :param start_time: 开始时间
        :param end_time: 结束时间
        :param host_ip: 过滤的主机IP
        """

        start_time, end_time = str2datetime(start_time), str2datetime(end_time)
        if not host_ip:
            host_ip = self.cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER).machine.ip

        binlogs = self._get_log_from_bklog(
            collector="mysql_binlog_result",
            # 时间范围前后放大20min，避免日志平台上传延迟
            start_time=datetime2str(start_time - timedelta(minutes=20)),
            end_time=datetime2str(end_time + timedelta(minutes=20)),
            query_string=f'log: "host: \\"{host_ip}\\""',
        )

        if not binlogs:
            raise AppBaseException(_("无法查找到在时间范围内{}-{}，主机{}的binlog日志").format(start_time, end_time, host_ip))

        # 根据stop_time和host进行过滤(字典外层参数cluster_domain,cluster_id,host,port都一样)
        binlog_record: Dict[str, Union[str, List]] = {
            "cluster_domain": binlogs[0]["cluster_domain"],
            "cluster_id": binlogs[0]["cluster_id"],
            "host": binlogs[0]["host"],
            "port": binlogs[0]["port"],
            "file_list_details": [],
        }
        collector_fields = ["file_mtime", "start_time", "stop_time", "size", "backup_taskid"]
        for log in binlogs:
            if str2datetime(log["stop_time"]) > end_time or str2datetime(log["stop_time"]) < start_time:
                continue

            detail = {field: log[field] for field in collector_fields}
            binlog_record["file_list_details"].append(detail)

        return binlog_record

    def execute_backup_log_script(self) -> List[int]:
        """
        通过下发脚本查询集群的备份记录
        """

        target_ip_infos = self._get_ip_list()
        execute_body: Dict[str, Any] = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": _("查询集群{}的备份日志").format(self.cluster.immute_domain),
            "script_content": str(
                base64.b64encode(self._find_local_backup_script(target_ip_infos[0]["port"])), "utf-8"
            ),
            "script_language": 1,
            "target_server": {
                "ip_list": [
                    {"bk_cloud_id": self.cluster.bk_cloud_id, "ip": ip_info["ip"]} for ip_info in target_ip_infos
                ]
            },
        }
        common_kwargs: Dict[str, str] = copy.deepcopy(fast_execute_script_common_kwargs)
        job_payloads = {**common_kwargs, **execute_body}
        job_result = JobApi.fast_execute_script(job_payloads, use_admin=True)

        return job_result["job_instance_id"]

    def query_backup_log_from_job(self, job_instance_id: int) -> Dict[str, Any]:
        """
        根据job_instance_id查询执行状态并在执行完成后返回结果
        :param job_instance_id: job执行的实例id列表
        """

        job_status_payload = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "job_instance_id": job_instance_id,
            "return_ip_result": True,
        }
        job_status = JobApi.get_job_instance_status(job_status_payload, use_admin=True)
        # 当任务没有准备好，则认为集群的备份信息任务还需要轮询
        if not job_status["finished"]:
            return {
                "backup_logs": [],
                "job_status": JobStatusEnum.get_choice_label(JobStatusEnum.RUNNING.value),
                "message": "job is running...",
            }

        # 如果任务执行失败，则认为当前备份查询失败
        if job_status["job_instance"]["status"] not in SUCCESS_LIST:
            return {
                "backup_logs": [],
                "job_status": JobStatusEnum.get_choice_label(job_status["job_instance"]["status"]),
                "message": _("作业【{}】执行失败，job_instance_id: {}").format(
                    job_status["job_instance"]["name"], job_status["job_instance"]["job_instance_id"]
                ),
            }

        job_log_payload = {
            "bk_biz_id": job_status["job_instance"]["bk_biz_id"],
            "job_instance_id": job_status["job_instance"]["job_instance_id"],
            "step_instance_id": job_status["step_instance_list"][0]["step_instance_id"],
            "ip_list": [
                {"bk_cloud_id": self.cluster.bk_cloud_id, "ip": ip_info["ip"]} for ip_info in self._get_ip_list()
            ],
        }
        job_log_results = JobApi.batch_get_job_instance_ip_log(job_log_payload, use_admin=True)
        local_backup_logs = []
        for job_log in job_log_results["script_task_logs"]:
            local_backup_logs.append(job_log["log_content"])

        return {
            "backup_logs": self._format_job_backup_log(local_backup_logs),
            "job_status": JobStatusEnum.get_choice_label(JobStatusEnum.SUCCESS.value),
            "message": "ok",
        }

    def query_latest_backup_log(self, rollback_time: datetime, job_instance_id: int = None) -> Dict[str, Any]:
        if job_instance_id:
            # 本地查询
            backup_logs = self.query_backup_log_from_job(job_instance_id)["backup_logs"]
        else:
            # 日志平台查询
            end_time = rollback_time
            start_time = end_time - timedelta(days=BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS)
            backup_logs = self.query_backup_log_from_bklog(
                start_time=datetime2str(start_time), end_time=datetime2str(end_time)
            )

        backup_logs.sort(key=lambda x: x["backup_time"])
        time_keys = [log["backup_time"] for log in backup_logs]
        try:
            latest_log = backup_logs[find_nearby_time(time_keys, rollback_time.strftime(DATETIME_PATTERN), 1)]
        except IndexError:
            raise AppBaseException(_("无法找到小于时间点{}附近的日志记录，请检查时间点的合法性或稍后重试").format(rollback_time))

        return latest_log
