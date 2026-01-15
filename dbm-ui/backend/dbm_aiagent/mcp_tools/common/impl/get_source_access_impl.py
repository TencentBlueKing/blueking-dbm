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
from collections import defaultdict
from typing import Any, Dict, List

from backend.components import CCApi
from backend.db_meta.models import AppCache, ProxyInstance, StorageInstance
from backend.db_services.dbbase.constants import TCP_ESTABLISHED_CODE, TCP_LISTEN_CODE
from backend.db_services.ipchooser.handlers.topo_handler import TopoHandler
from backend.utils.batch_request import batch_request


def parse_proc_net_tcp(proc_net_tcp_content: str):
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


def format_cc_info(bk_cloud_id: int, remote_ip__report_map: dict):
    if not remote_ip__report_map:
        return {}

    # 查询remote cc信息
    remote_ips = list(remote_ip__report_map.keys())
    params = {
        "fields": ["bk_host_id", "bk_host_innerip", "operator", "bk_bak_operator"],
        "host_property_filter": {
            "condition": "AND",
            "rules": [
                {"field": "bk_host_innerip", "operator": "in", "value": remote_ips},
                {"field": "bk_cloud_id", "operator": "equal", "value": bk_cloud_id},
            ],
        },
    }
    hosts = batch_request(CCApi.list_hosts_without_biz, params, get_data=lambda x: x["info"], use_admin=True)

    if not hosts:
        return {}

    cc_map = defaultdict(dict)
    # 补充主备负责人信息
    for host in hosts:
        cc_map[host["bk_host_innerip"]].update(operator=host["operator"], bak_operator=host["bk_bak_operator"])

    # 查询主机与业务的映射关系，这里要分批请求
    remote_host_ids = [host["bk_host_id"] for host in hosts]
    resp = CCApi.batch_find_host_biz_relations({"bk_host_id": remote_host_ids})
    biz__host_ids = defaultdict(list)
    for host in resp:
        biz__host_ids[host["bk_biz_id"]].append(host["bk_host_id"])

    # 查询主机的业务模块信息
    app_dict = AppCache.get_appcache("appcache_dict")
    for bk_biz_id, bk_host_ids in biz__host_ids.items():
        app = app_dict.get(str(bk_biz_id), "unknown")
        # 分批请求cc的拓扑信息
        batch = 500
        for i in range(0, len(bk_host_ids), batch):
            filter_conditions = {"bk_host_id": bk_host_ids[i : i + batch]}
            topos = TopoHandler.query_host_topo_infos(int(bk_biz_id), filter_conditions, 0, batch)
            for topo in topos["hosts_topo_info"]:
                topo["topo"] = [f"{app['bk_biz_name']}/{info}" for info in topo["topo"]]
                cc_map[topo["ip"]].update(topo=topo["topo"])

    return cc_map


def generate_cluster_query_report(
    job_log_resp,
    cluster_domain,
    cluster_all_ip: List,
):
    bk_cloud_id = job_log_resp[0]["bk_cloud_id"]
    # 获取主机和tcp解析信息的映射，并收集错误主机
    host_id__tcp_info_map: Dict[int, Dict] = {}
    host_id__ip_map: Dict[int, str] = {}
    success_hosts: List = []
    err_hosts: List = []

    for info in job_log_resp:
        try:
            parse_info, is_success = parse_proc_net_tcp(info["log_content"])
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
            # 跳过集群内部IP
            if ip in cluster_all_ip:
                continue
            remote_ip__report_map[ip][domain]["all_connections"] += 1
            remote_ip__report_map[ip][domain]["establish"] += tcp_info["st"] == TCP_ESTABLISHED_CODE  # 生成tcp链接报告
    cluster_domain__tcp_report: Dict[str, Any] = defaultdict(lambda: {"success": [], "error": [], "report": []})
    cc_map = format_cc_info(bk_cloud_id, remote_ip__report_map)
    for remote_ip, domain_map in remote_ip__report_map.items():
        for domain, tcp_info in domain_map.items():
            # 主从多实例，可能会统计到其他实例的信息
            if domain == cluster_domain:
                data = {"remote_ip": remote_ip, "cluster_domain": domain, **tcp_info, **cc_map.get(remote_ip, {})}
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
