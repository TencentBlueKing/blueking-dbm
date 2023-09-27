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
import logging
import traceback
from typing import List

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.redis.redis_context_dataclass as flow_context
from backend import env
from backend.components import JobApi
from backend.db_meta.api.cluster import nosqlcomm
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BaseService, BkJobService
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, RedisDataStructureContext
from backend.flow.utils.redis.redis_script_template import redis_fast_execute_script_common_kwargs
from backend.ticket.constants import TicketType

logger = logging.getLogger("json")


class ExecuteShellScriptService(BkJobService):
    """
    执行shell命令
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]

        exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"])
        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员"))
            return False
        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]
        self.log_info("{} exec {}".format(target_ip_info, node_name))

        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=exec_ips)

        # 脚本内容
        shell_command = kwargs["cluster"]["shell_command"]

        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": str(base64.b64encode(shell_command.encode("utf-8")), "utf-8"),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }

        self.log_info("[{}] ready start task with body {}".format(node_name, body))
        resp = JobApi.fast_execute_script({**redis_fast_execute_script_common_kwargs, **body}, raw=True)

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="exec_ips", key="exec_ips", type="list")]


class ExecuteShellScriptComponent(Component):
    name = __name__
    code = "shell_execute"
    bound_service = ExecuteShellScriptService


class GetDeleteKeysExeIpService(BkJobService):
    """
    获取字典中最大磁盘空间最大的机器
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        splice_payload_var = data.get_one_of_inputs("splice_payload_var")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        try:
            total_size = kwargs["cluster"]["total_size"]
            disk_used = getattr(trans_data, splice_payload_var)
            # {'1.1.1.1': {'data': '/dev/vdb        51474912 1187792  47649296   3% /data'}}
            disk_free_ip = ""
            for ip, disk_info in disk_used.items():
                info = disk_info["data"].split()
                disk_free = int(info[3])
                if disk_free > total_size * 3:
                    disk_free_ip = ip
                    break

            if disk_free_ip == "":
                raise ValueError(_("无符合要求机器"))

            setattr(trans_data, "disk_free_max_ip", disk_free_ip)
        except ValueError as e:
            self.log_error(_("获取最大磁盘空闲机器失败：{}").format(e))
            data.outputs.ext_result = False
            return False

        data.outputs["trans_data"] = trans_data
        data.outputs.ext_result = True
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="exec_ips", key="exec_ips", type="list")]


class GetDeleteKeysExeIpComponent(Component):
    name = __name__
    code = "get_delete_keys_exe_ip"
    bound_service = GetDeleteKeysExeIpService


class RedisDataStructurePrecheckService(BaseService):
    """
    redis 数据构造 磁盘前置检查
    """

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        splice_payload_var = data.get_one_of_inputs("splice_payload_var")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        # 打印信息
        self.log_info(" RedisDataStructurePrecheckService start")
        self.log_info("kwargs: {}".format(kwargs))

        try:
            # 临时机器磁盘空间是否足够
            if not self.check_src_redis_host_disk(trans_data, kwargs):
                return False

        except Exception as e:
            traceback.print_exc()
            self.log_error("redis datastructure precheck failed:{}".format(e))
            return False
        self.log_info("redis datastructure precheck success")
        data.outputs["trans_data"] = trans_data

        return True

    @staticmethod
    def decode_slave_host_disk_info(disk_line: str) -> dict:
        """
        解析slave磁盘信息
        如: /dev/vdb       103080888 1788160  96033464   2% /data
        """
        l01 = disk_line.split()
        ret = {}
        ret["filesystem"] = l01[0]
        ret["total"] = int(l01[1]) * 1024
        ret["used"] = int(l01[2]) * 1024
        ret["avail"] = int(l01[3]) * 1024
        ret["used_ratio"] = int(l01[4].replace("%", ""))
        ret["mount_on"] = l01[5]
        return ret

    def log_disk_error(self, exec_ip, disk_info):
        error_message = _("源Redis服务器：{} {} 磁盘使用率：{}% > 85%").format(
            exec_ip["ip"], disk_info["filesystem"], disk_info["used_ratio"]
        )
        self.log_error(error_message)
        return False

    def check_disk_usage(self, disk_info, exec_ip, data_size):
        if disk_info["used_ratio"] > 85:
            return self.log_disk_error(exec_ip, disk_info)
        if (disk_info["used"] + data_size) / disk_info["total"] > 0.9:
            error_message = _("源Redis服务器：{} 磁盘使用情况：{}+Redis数据大小：{} 将会 >=90%").format(
                exec_ip, disk_info["used"], data_size
            )
            self.log_error(error_message)
            return False
        return True

    def check_src_redis_host_disk(self, trans_data: RedisDataStructureContext, kwargs: dict) -> bool:
        """
        检查临时redis 机器磁盘空间是否足够
        """

        disk_used = trans_data.disk_used
        is_same, backup_dir = self.check_backup_dir(disk_used)
        if is_same:
            self.log_info(_("所有临时Redis服务器的备份目录都相同：{}").format(backup_dir))
        else:
            self.log_error(_("备份目录的值不一致：{}").format(backup_dir))
            return False

        # # 当所有机器的备份目录一样时，对backup_dir赋值
        trans_data.backup_dir = backup_dir
        self.log_info(_("检查源Redis服务器磁盘使用情况：{}").format(disk_used))
        self.log_info("check_src_redis_host_disk  disk_used:{}".format(disk_used))

        exec_ip = kwargs["exec_ip"]
        cluster = kwargs["cluster"]
        # 检查备份目录
        redis_backup_dir_data = disk_used.get(exec_ip)["redis_backup_dir_data"]
        cluster["backup_dir"] = disk_used.get(exec_ip)["backup_dir"]
        disk_info = self.decode_slave_host_disk_info(redis_backup_dir_data)
        if not self.check_disk_usage(disk_info, exec_ip, cluster["multi_total_size"]):
            return False

        # 检查数据目录
        redis_data_dir_data = disk_used.get(exec_ip)["redis_data_dir_data"]
        data_disk_info = self.decode_slave_host_disk_info(redis_data_dir_data)
        if not self.check_disk_usage(data_disk_info, exec_ip, cluster["multi_total_size"]):
            return False

        self.log_info(_("redis 临时机器:{} 磁盘空间检查通过").format(kwargs["exec_ip"]))
        return True

    @staticmethod
    def check_backup_dir(disk_used):
        """
        检查是否所有机器的 backup_dir 都一致
        """
        backup_dirs = set()

        for server in disk_used.values():
            backup_dirs.add(server["backup_dir"])

        if len(backup_dirs) == 1:
            backup_dir_value = backup_dirs.pop()
            return True, backup_dir_value
        else:
            return False, backup_dirs


class RedisDataStructurePrecheckComponent(Component):
    name = __name__
    code = "redis_dataStructure_precheck"
    bound_service = RedisDataStructurePrecheckService
class ExecuteShellReloadMetaService(BkJobService):
    """
    执行shell命令
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]

        cluster_meta = nosqlcomm.other.get_cluster_detail(cluster_id=kwargs["cluster"]["cluster_id"])[0]
        exec_ips = cluster_meta["twemproxy_ips_set"]
        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员"))
            return False
        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]
        self.log_info("{} exec {}".format(target_ip_info, node_name))

        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=exec_ips)

        # 脚本内容
        shell_command = kwargs["cluster"]["shell_command"]

        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": str(base64.b64encode(shell_command.encode("utf-8")), "utf-8"),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }

        self.log_info("[{}] ready start task with body {}".format(node_name, body))
        resp = JobApi.fast_execute_script({**redis_fast_execute_script_common_kwargs, **body}, raw=True)

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="exec_ips", key="exec_ips", type="list")]


class ExecuteShellReloadMetaComponent(Component):
    name = __name__
    code = "shell_exec_reload_meta"
    bound_service = ExecuteShellReloadMetaService
