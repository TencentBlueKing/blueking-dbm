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
import json
import logging
from datetime import datetime, timedelta
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend import env
from backend.components import JobApi
from backend.components.mysql_backup.client import RedisBackupApi
from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.redis.redis_script_template import redis_fast_execute_script_common_kwargs
from backend.utils.string import base64_encode

logger = logging.getLogger("json")


def get_last_n_days_backup_records(n_days: int, bk_cloud_id: 0, server_ip: str) -> list:
    """逐天获取最近n天的备份记录"""
    records_unique = set()
    records_ret = []
    now = datetime.now()
    for i in range(n_days):
        start_date = (now - timedelta(days=i + 1)).strftime("%Y-%m-%d %H:%M:%S")
        end_date = (now - timedelta(days=i)).strftime("%Y-%m-%d %H:%M:%S")
        query_param = {
            "bk_cloud_id": bk_cloud_id,
            "source_ip": server_ip,
            "begin_date": start_date,
            "end_date": end_date,
            "filename": "",
        }
        query_result = RedisBackupApi.query(query_param)
        for record in query_result:
            if record["task_id"] in records_unique:
                continue
            records_unique.add(record["task_id"])
            records_ret.append(record)
    return records_ret


class GetOldBackupRecordsAndSave(BkJobService):
    """
    获取ip最近N天的备份记录,并保存到本地
    kwargs:{
        "node_id": "xxx",
        "root_id": "xxx",
        "node_name": "xxx",
        "exec_ip": "xxx",
        "cluster": {
            "ndays": 7,
            "bk_cloud_id": 0,
            "server_ip": "xxx",
            "save_file": "xxx"
        }
    }
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]

        exec_ip = kwargs["exec_ip"]
        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": exec_ip}]
        self.log_info("{} exec {}".format(target_ip_info, node_name))

        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=exec_ip)

        # 查询历史备份记录
        ndays = kwargs["cluster"].get("ndays", 7) + 1
        bk_cloud_id = kwargs["cluster"].get("bk_cloud_id", DEFAULT_BK_CLOUD_ID)
        server_ip = kwargs["cluster"]["server_ip"]
        save_file = kwargs["cluster"]["save_file"]
        self.log_info(f"start get last {ndays} days old backup records of {server_ip}")

        query_result = get_last_n_days_backup_records(ndays, bk_cloud_id, server_ip)
        encode_str = base64_encode(json.dumps(query_result))

        self.log_info(f"success get last {ndays} days old backup records of {server_ip}")

        # 脚本内容
        shell_command = f"""
cat > {save_file} << EOF
{encode_str}
EOF
    """

        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": base64_encode(shell_command),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }

        self.log_info("[{}] ready start task with body {}".format(node_name, body))
        resp = JobApi.fast_execute_script({**redis_fast_execute_script_common_kwargs, **body}, raw=True)

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ip
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="exec_ips", key="exec_ips", type="list")]


class GetOldBackupRecordsAndSaveComponent(Component):
    name = __name__
    code = "get_old_backup_records_and_save_to_local"
    bound_service = GetOldBackupRecordsAndSave
