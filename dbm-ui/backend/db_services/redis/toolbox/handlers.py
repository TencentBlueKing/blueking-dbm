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
import itertools
import json
from collections import defaultdict
from typing import Any, Dict, List

from django.db import connection
from django.utils.translation import gettext as _

from backend import env
from backend.components import CCApi, DRSApi, JobApi
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.enums.comm import RedisVerUpdateNodeType
from backend.db_meta.exceptions import InstanceNotExistException
from backend.db_meta.models import AppCache, Cluster, ProxyInstance, StorageInstance
from backend.db_services.dbbase.cluster.handlers import ClusterServiceHandler
from backend.db_services.ipchooser.handlers.host_handler import HostHandler
from backend.db_services.ipchooser.handlers.topo_handler import TopoHandler
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.db_services.redis.constants import TCP_ESTABLISHED_CODE, TCP_LISTEN_CODE
from backend.db_services.redis.redis_modules.models import TbRedisModuleSupport
from backend.db_services.redis.redis_modules.models.redis_module_support import ClusterRedisModuleAssociate
from backend.db_services.redis.resources.constants import SQL_QUERY_COUNT_INSTANCES, SQL_QUERY_INSTANCES
from backend.db_services.redis.resources.redis_cluster.query import RedisListRetrieveResource
from backend.exceptions import ApiResultError, ValidationError
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis import redis_util
from backend.flow.utils.redis.redis_proxy_util import (
    get_cluster_proxy_version,
    get_cluster_proxy_version_for_upgrade,
    get_cluster_redis_version,
    get_cluster_remote_address,
    get_cluster_storage_versions_for_upgrade,
)
from backend.utils.basic import dictfetchall
from backend.utils.string import base64_encode


class ToolboxHandler(ClusterServiceHandler):
    """redis工具箱查询接口封装"""

    def __init__(self, bk_biz_id: int):
        super().__init__(bk_biz_id)

    def query_cluster_ips(
        self, limit=None, offset=None, cluster_id=None, ip=None, role=None, status=None, cluster_status=None
    ):
        """聚合查询集群下的主机 TODO:"""

        limit_sql = ""
        if limit and limit > 0:
            # 强制格式化为int，避免sql注入
            limit_sql = " LIMIT {}".format(int(limit))

        offset_sql = ""
        if offset:
            offset_sql = " OFFSET {}".format(int(offset))

        where_sql = "WHERE i.bk_biz_id = %s "
        where_values = [self.bk_biz_id]

        if cluster_id:
            placeholder = ",".join(["%s"] * len(cluster_id))
            where_sql += f"AND c.cluster_id IN ({placeholder})"
            where_values.extend(cluster_id)

        if ip:
            ip_conditions = " OR ".join(["m.ip LIKE %s" for _ in ip])
            where_sql += f" AND ({ip_conditions})"
            where_ip_values = [f"%{single_ip}%" for single_ip in ip]
            where_values.extend(where_ip_values)

        if status:
            where_sql += "AND i.status = %s "
            where_values.append(status)
            # placeholders = ",".join(["%s"] * len(status))
            # where_sql += "AND i.status IN (" + placeholders + ") "
            # where_values.extend(status)

        if cluster_status:
            where_sql += "AND cluster.status = %s "
            where_values.append(cluster_status)

        if role:
            placeholder = ", ".join(["%s"] * len(role))
            having_sql = f"HAVING role IN ({placeholder}) "
            where_values.extend(role)
        else:
            having_sql = ""

        # union查询需要两份参数
        where_values = where_values * 2
        sql_count = SQL_QUERY_COUNT_INSTANCES.format(where=where_sql, having=having_sql)
        sql = SQL_QUERY_INSTANCES.format(where=where_sql, having=having_sql, limit=limit_sql, offset=offset_sql)

        with connection.cursor() as cursor:
            cursor.execute(sql_count, where_values)
            total_count = cursor.fetchone()[0]
            cursor.execute(sql, where_values)

        ips = dictfetchall(cursor)
        bk_host_ids = [ip["bk_host_id"] for ip in ips]

        if not bk_host_ids:
            return {"count": 0, "results": ips}

        # 查询主机信息
        host_id_info_map = {host["host_id"]: host for host in HostHandler.check([], [], [], bk_host_ids)}

        # 查询主从状态对
        master_slave_map = RedisListRetrieveResource.query_master_slave_map(
            [i["ip"] for i in ips if i["role"] == InstanceRole.REDIS_MASTER]
        )
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        # 补充主机、规格和主从关系信息、补充云区域信息
        for item in ips:
            item["host_info"] = host_id_info_map.get(item["bk_host_id"])
            item["spec_config"] = json.loads(item["spec_config"])
            item["bk_cloud_name"] = cloud_info[str(item["bk_cloud_id"])]["bk_cloud_name"]
            item.update(master_slave_map.get(item["ip"], {}))

        response = {"count": total_count, "results": ips}
        return response

    @classmethod
    def get_online_cluster_versions(cls, cluster_id: int, node_type: str):
        """根据cluster id获取集群现存版本"""
        if node_type == RedisVerUpdateNodeType.Backend.value:
            return [get_cluster_redis_version(cluster_id)]
        else:
            return get_cluster_proxy_version(cluster_id)

    @classmethod
    def get_update_cluster_versions(cls, cluster_id: int, node_type: str):
        """根据cluster类型获取版本信息"""
        if node_type == RedisVerUpdateNodeType.Backend.value:
            return get_cluster_storage_versions_for_upgrade(cluster_id)
        else:
            return get_cluster_proxy_version_for_upgrade(cluster_id)

    @classmethod
    def list_cluster_big_version(cls, cluster_id: int):
        """查询集群可更新的大版本"""
        return redis_util.get_cluster_update_version(cluster_id)

    @classmethod
    def webconsole_rpc(cls, cluster_id: int, cmd: str, db_num: int = 0, raw: bool = True, **kwargs):
        """
        执行webconsole命令，只支持select语句
        @param cluster_id: 集群ID
        @param cmd: 执行命令
        @param db_num: 数据库编号
        @param raw: 源字符返回
        """
        cluster = Cluster.objects.get(id=cluster_id)
        # 获取访问密码
        password = PayloadHandler.redis_get_cluster_password(cluster=cluster)["redis_proxy_password"]
        # 获取rpc结果
        try:
            remote_address = get_cluster_remote_address(cluster_id=cluster.id)
            rpc_results = DRSApi.redis_rpc(
                {
                    "bk_cloud_id": cluster.bk_cloud_id,
                    "addresses": [remote_address],
                    "command": cmd,
                    "db_num": db_num,
                    "raw": raw,
                    "password": password,
                    # redis这里的client_type固定为webconsole，drs会发起redis-cli进行执行
                    "client_type": "webconsole",
                }
            )
        except (ApiResultError, InstanceNotExistException) as err:
            return {"query": "", "error_msg": err.message}

        return {"query": rpc_results[0]["result"], "error_msg": ""}

    @classmethod
    def get_cluster_module_info(cls, cluster_id: int, version: str):
        """
        获取集群module信息
        """
        # 获取版本支持的module名称列表
        support_modules = TbRedisModuleSupport.objects.filter(major_version=version).values_list(
            "module_name", flat=True
        )
        # 获取集群已安装的module名称列表
        cluster_module_associate = ClusterRedisModuleAssociate.objects.filter(cluster_id=cluster_id).first()
        cluster_modules = getattr(cluster_module_associate, "module_names", [])
        # 字典输出集群是否安装的module列表
        results = {item: (item in cluster_modules) for item in support_modules}
        return {"results": results}

    @classmethod
    def execute_cluster_net_tcp_cmd(cls, cluster_ids: List[int]):
        """
        执行集群net tcp命令
        """

        def get_execute_cluster_hosts(cluster):
            cluster_type = cluster.cluster_type
            host_ids = []
            # 有可能连后端Master/slave, 也有可能连接Proxy的
            if cluster_type in [ClusterType.TendisPredixyRedisCluster, ClusterType.TendisPredixyTendisplusCluster]:
                host_ids = list(cluster.storageinstance_set.values_list("machine__bk_host_id", flat=True))
                host_ids.extend(list(cluster.proxyinstance_set.values_list("machine__bk_host_id", flat=True)))
            # 只连接Proxy的
            elif cluster_type in [ClusterType.TendisTwemproxyRedisInstance, ClusterType.TwemproxyTendisSSDInstance]:
                host_ids = list(cluster.proxyinstance_set.values_list("machine__bk_host_id", flat=True))
            # 只连接后端Master节点的
            elif cluster_type in [ClusterType.TendisRedisInstance]:
                host_ids = [
                    inst.machine.bk_host_id
                    for inst in cluster.storageinstance_set.all()
                    if inst.instance_role == InstanceRole.REDIS_MASTER
                ]
            return host_ids

        # 获取集群的所有可执行的节点
        clusters = Cluster.objects.filter(id__in=cluster_ids).prefetch_related(
            "storageinstance_set__machine", "proxyinstance_set__machine"
        )
        execute_host_ids = list(itertools.chain(*[get_execute_cluster_hosts(cluster) for cluster in clusters]))

        # 目前暂定执行的上限为1w台机器，超过就报错
        if len(execute_host_ids) > 10000:
            raise ValidationError(_("执行主机数量过多:{}，请不要超过10000台").format(len(execute_host_ids)))

        # 执行job脚本
        #  /proc/net/tcp 分析前30000行，job的log日志返回有大小限制
        cmds = """head -n 30000 /proc/net/tcp;"""
        body = {
            "account_alias": DBA_ROOT_USER,
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": _("查询集群接入层tcp的连接信息"),
            "script_content": base64_encode(cmds),
            "script_language": 1,
            "target_server": {"host_id_list": execute_host_ids},
        }
        resp = JobApi.fast_execute_script(body)
        return resp

    @classmethod
    def get_cluster_proc_net_tcp(cls, job_instance_id: int):
        """
        通过作用平台查询集群proc/net/tcp信息执行信息
        """
        payload = {"bk_biz_id": env.JOB_BLUEKING_BIZ_ID, "job_instance_id": job_instance_id, "return_ip_result": True}
        resp = JobApi.get_job_instance_status(payload)

        # job 未完成
        if not resp["finished"]:
            return {"finished": False, "data": []}

        ip_result_list = resp["step_instance_list"][0]["step_ip_result_list"]

        # 执行完成直接获取主机执行的日志，不用判断是否有报错
        step_instance_id = resp["step_instance_list"][0]["step_instance_id"]
        bk_host_ids = [result["bk_host_id"] for result in resp["step_instance_list"][0]["step_ip_result_list"]]
        resp = JobApi.batch_get_job_instance_ip_log(
            {
                "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
                "job_instance_id": job_instance_id,
                "step_instance_id": step_instance_id,
                "host_id_list": bk_host_ids,
            }
        )
        script_task_logs = resp["script_task_logs"] or []

        # 保持兼容性，对于没有查到日志的主机填空
        log_host_ids = [log["host_id"] for log in script_task_logs]
        add_empty_task_logs = [
            {"host_id": res["bk_host_id"], "log_content": "", "bk_cloud_id": res["bk_cloud_id"], "ip": res["ip"]}
            for res in ip_result_list
            if res["bk_host_id"] not in log_host_ids
        ]
        script_task_logs.extend(add_empty_task_logs)

        # 解析主机生成的tcp报告
        tcp_data_report = cls.__generate_net_tcp_report(script_task_logs)
        return {"finished": True, "data": tcp_data_report}

    @classmethod
    def __generate_net_tcp_report(cls, log_infos: List):
        """
        解析每个主机生成的tcp报告，汇聚成集群来源报告
        """

        def __format_cc_info():
            if not remote_ip__report_map:
                return {}

            # 查询remote cc信息
            remote_ips = list(remote_ip__report_map.keys())
            search_rules = [
                {"field": "bk_host_innerip", "operator": "in", "value": remote_ips},
                {"field": "bk_cloud_id", "operator": "equal", "value": bk_cloud_id},
            ]
            resp = CCApi.list_hosts_without_biz(
                {
                    "fields": ["bk_host_id", "bk_host_innerip", "operator", "bk_bak_operator"],
                    "host_property_filter": {"condition": "AND", "rules": search_rules},
                }
            )

            cc_map = defaultdict(dict)
            # 补充主备负责人信息
            for host in resp["info"]:
                cc_map[host["bk_host_innerip"]].update(operator=host["operator"], bak_operator=host["bk_bak_operator"])

            # 查询主机与业务的映射关系
            remote_host_ids = [info["bk_host_id"] for info in resp["info"]]
            resp = CCApi.find_host_biz_relations({"bk_host_id": remote_host_ids})
            biz__host_ids = defaultdict(list)
            for host in resp:
                biz__host_ids[host["bk_biz_id"]].append(host["bk_host_id"])

            # 查询主机的业务模块信息
            app_dict = AppCache.get_appcache("appcache_dict")
            for bk_biz_id, bk_host_ids in biz__host_ids.items():
                app = app_dict[str(bk_biz_id)]
                filter_conditions = {"bk_host_id": bk_host_ids}
                topos = TopoHandler.query_host_topo_infos(int(bk_biz_id), filter_conditions, 0, len(bk_host_ids))

                for topo in topos["hosts_topo_info"]:
                    topo["topo"] = [f"{app['bk_biz_name']}/{info}" for info in topo["topo"]]
                    cc_map[topo["ip"]].update(topo=topo["topo"])

            return cc_map

        bk_cloud_id = log_infos[0]["bk_cloud_id"]

        # 获取主机和tcp解析信息的映射，并收集错误主机
        host_id__tcp_info_map: Dict[int, Dict] = {}
        host_id__ip_map: Dict[int, str] = {}
        success_hosts: List = []
        err_hosts: List = []

        for info in log_infos:
            try:
                parse_info, is_success = cls.__parse_proc_net_tcp(info["log_content"])
            except (Exception, IndexError):
                parse_info, is_success = {}, False
            host_id__tcp_info_map[info["host_id"]] = parse_info
            host_id__ip_map[info["host_id"]] = info["ip"]

            if not is_success:
                err_hosts.append(info["host_id"])
            else:
                success_hosts.append(info["host_id"])

        # 获取执行主机关联的实例信息
        fields = ["cluster__immute_domain", "machine__bk_host_id", "machine__ip", "port"]
        host_ids = host_id__tcp_info_map.keys()
        instances = (
            StorageInstance.objects.filter(machine__bk_host_id__in=host_ids)
            .values(*fields)
            .union(ProxyInstance.objects.filter(machine__bk_host_id__in=host_ids).values(*fields))
        )

        # 生成汇总报告，按照remote ip + domain进行聚合
        host_id__domain_map: Dict[int, str] = {}
        remote_ip__report_map: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: defaultdict(lambda: {"all_connections": 0, "establish": 0})
        )
        for inst in instances:
            host_id, port, domain = inst["machine__bk_host_id"], inst["port"], inst["cluster__immute_domain"]
            host_id__domain_map[host_id] = domain
            tcp_infos = host_id__tcp_info_map.get(host_id, {}).get(port, [])
            # 统计总连接数、建立连接数、连接集群
            for tcp_info in tcp_infos:
                ip = tcp_info["remote_host"]
                remote_ip__report_map[ip][domain]["all_connections"] += 1
                remote_ip__report_map[ip][domain]["establish"] += tcp_info["st"] == TCP_ESTABLISHED_CODE

        # 生成tcp链接报告
        cluster_domain__tcp_report: Dict[str, Any] = defaultdict(lambda: {"success": [], "error": [], "report": []})
        cc_map = __format_cc_info()
        for remote_ip, domain_map in remote_ip__report_map.items():
            for domain, tcp_info in domain_map.items():
                data = {"remote_ip": remote_ip, "cluster_domain": domain, **tcp_info, **cc_map.get(remote_ip)}
                cluster_domain__tcp_report[domain]["report"].append(data)

        # 统计集群正确和错误主机信息
        for host in err_hosts:
            domain = host_id__domain_map[host]
            cluster_domain__tcp_report[domain]["error"].append(host_id__ip_map[host])
        for host in success_hosts:
            domain = host_id__domain_map[host]
            cluster_domain__tcp_report[domain]["success"].append(host_id__ip_map[host])

        # 补充连接数为0的集群报告
        tcp_report = [{"cluster_domain": domain, **report} for domain, report in cluster_domain__tcp_report.items()]
        return tcp_report

    @staticmethod
    def __parse_proc_net_tcp(proc_net_tcp_content: str):
        """
        解析proc/net/tcp文件
        参考：https://guanjunjian.github.io/2017/11/09/study-8-proc-net-tcp-analysis/
        返回聚合后的端口与tpc信息的映射
        """

        def parse_hex_addr(hex_ip_port):
            hex_ip, hex_port = hex_ip_port.split(":")
            if len(hex_ip) != 8:
                return "", 0
            # 将小端序转为大端序，解析16进制
            ip = f"{int(hex_ip[6:8], 16)}.{int(hex_ip[4:6], 16)}.{int(hex_ip[2:4], 16)}.{int(hex_ip[:2], 16)}"
            port = int(hex_port, 16)
            return ip, port

        proc_net_tcp_lines = proc_net_tcp_content.strip("\n").split("\n")
        # 如果第一行的头不为sl，说明解析错误
        if not proc_net_tcp_lines or proc_net_tcp_lines[0].split()[0] != "sl":
            return {}, False

        # 解析每行的tcp字符
        net_tcp_list: List = []
        for line in proc_net_tcp_lines[1:]:
            line = line.split()
            local_host, local_port = parse_hex_addr(line[1])
            remote_host, remote_port = parse_hex_addr(line[2])
            sl, st = line[0], int(line[3], 16)
            tcp_info = {
                "sl": sl,
                "st": st,
                "established": st == TCP_ESTABLISHED_CODE,
                "local_host": local_host,
                "local_port": local_port,
                "remote_host": remote_host,
                "remote_port": remote_port,
            }
            net_tcp_list.append(tcp_info)

        # 遍历net_tcp_list，找到所有监听端口的tcp链接
        # 1. 跳过 local_ip == "127.0.0.1"的情况
        # 2. 如果是监听端口，记录本机的IP到 localIpList，并生成一个report[local_port] = []
        local_ip_list: List[str] = []
        tcp_report: Dict[int, List] = {}
        for tcp_info in net_tcp_list:
            if tcp_info["local_host"] == "127.0.0.1":
                continue
            if tcp_info["st"] == TCP_LISTEN_CODE:
                local_ip_list.append(tcp_info["local_host"])
                tcp_report[tcp_info["local_port"]] = []

        # 再次遍历net_tcp_list，将tcp信息聚合到report中
        # 跳过LocalHost == "127.0.0.1"的情况， 跳过remote_ip in local_ip_list的情况
        for tcp_info in net_tcp_list:
            if tcp_info["local_host"] == "127.0.0.1" or tcp_info["remote_host"] in local_ip_list:
                continue
            if tcp_info["local_port"] not in tcp_report:
                continue
            tcp_report[tcp_info["local_port"]].append(tcp_info)

        return tcp_report, True
