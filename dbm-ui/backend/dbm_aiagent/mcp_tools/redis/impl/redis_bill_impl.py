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
from itertools import chain

from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, Spec, StorageInstanceTuple
from backend.flow.consts import ClusterRoleEnum
from backend.ticket.builders.common.base import IpSource
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


def redis_cluster_cutoff(request, bk_biz_id, cluster_domain, cutoff_ips):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cutoff_role_list = []
    spec_info_list = []
    count = len(cutoff_ips)
    resource_spec = {}
    spec_id = ""
    # 校验
    cutoff_ip = cutoff_ips[0]
    if cluster_obj.proxyinstance_set.filter(machine__ip=cutoff_ip):
        cutoff_role = "proxy"
        for ip in cutoff_ips:
            ins = cluster_obj.proxyinstance_set.filter(machine__ip=ip).first()
            if not ins:
                return {"error": "{} 与 {}不是相同角色".format(ip, cutoff_ip)}
            cutoff_role_list.append({"bk_host_id": ins.machine.bk_host_id, "ip": ip, "spec_id": ins.machine.spec_id})
            spec_info = Spec.objects.get(spec_id=ins.machine.spec_id).get_spec_info()
            spec_info["count"] = count
            spec_info_list.append({"bk_host_id": ins.machine.bk_host_id, "ip": ip, "spec": spec_info})
            spec_id = ins.machine.spec_id
        resource_spec = {"new_proxy": {"count": count, "label_names": [], "labels": [], "spec_id": spec_id}}
    elif cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value).filter(
        machine__ip=cutoff_ip
    ):
        cutoff_role = "redis_master"
        for ip in cutoff_ips:
            ins = (
                cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value)
                .filter(machine__ip=ip)
                .first()
            )
            if not ins:
                return {"error": "{} 与 {}不是相同角色".format(ip, cutoff_ip)}
            cutoff_role_list.append({"bk_host_id": ins.machine.bk_host_id, "ip": ip, "spec_id": ins.machine.spec_id})
            spec_info = Spec.objects.get(spec_id=ins.machine.spec_id).get_spec_info()
            spec_info["count"] = count
            spec_info_list.append({"bk_host_id": ins.machine.bk_host_id, "ip": ip, "spec": spec_info})
            # 补充slave
            slave = StorageInstanceTuple.objects.get(ejector=ins).receiver
            # cutoff_role_list.append({
            #     "bk_host_id": slave.machine.bk_host_id,
            #     "ip": slave.machine.ip,
            #     "spec_id": slave.machine.spec_id
            # })
            spec_info = Spec.objects.get(spec_id=slave.machine.spec_id).get_spec_info()
            spec_info["count"] = count
            spec_info_list.append({"bk_host_id": slave.machine.bk_host_id, "ip": slave.machine.ip, "spec": spec_info})
            spec_id = ins.machine.spec_id
        resource_spec = {"backend_group": {"count": count, "label_names": [], "labels": [], "spec_id": spec_id}}
    elif cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.REDIS_SLAVE.value).filter(
        machine__ip=cutoff_ip
    ):
        cutoff_role = "redis_slave"
        resource_spec_map = defaultdict(dict)
        for ip in cutoff_ips:
            ins = (
                cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.REDIS_SLAVE.value)
                .filter(machine__ip=ip)
                .first()
            )
            if not ins:
                return {"error": "{} 与 {}不是相同角色".format(ip, cutoff_ip)}
            cutoff_role_list.append({"bk_host_id": ins.machine.bk_host_id, "ip": ip, "spec_id": ins.machine.spec_id})
            spec_info = Spec.objects.get(spec_id=ins.machine.spec_id).get_spec_info()
            spec_info["count"] = count
            spec_info_list.append({"bk_host_id": ins.machine.bk_host_id, "ip": ip, "spec": spec_info})
            resource_spec_map[f"redis_slave_{ip}"] = {
                "count": count,
                "label_names": [],
                "labels": [],
                "spec_id": ins.machine.spec_id,
            }
        resource_spec = dict(resource_spec_map)
    else:
        return {"error": "{} 不属于集群 {}".format(cutoff_ip, cluster_obj.immute_domain)}
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp {}-{} cutoff".format(cutoff_role, cutoff_ips),
        "ticket_type": TicketType.REDIS_CLUSTER_CUTOFF,
        "details": {
            "infos": [
                {
                    "bk_cloud_id": cluster_obj.bk_cloud_id,
                    "cluster_ids": [cluster_obj.id],
                    "switch_role": cutoff_role,
                    cutoff_role: cutoff_role_list,
                    # 页面展示
                    "old_nodes": {cutoff_role: spec_info_list},
                    "resource_spec": resource_spec,
                }
            ],
            "ip_source": "resource_pool",
        },
    }
    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_proxy_reduce(request, bk_biz_id, cluster_domain, proxy_change_count):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    cluster_proxy_count = cluster_obj.proxyinstance_set.count()
    count = cluster_proxy_count - proxy_change_count
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp proxy reduce ticket",
        "ticket_type": TicketType.REDIS_PROXY_SCALE_DOWN,
        "details": {
            "infos": [{"cluster_id": cluster_id, "online_switch_type": "user_confirm", "target_proxy_count": count}],
        },
    }
    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_proxy_reduce_by_ip(request, bk_biz_id, cluster_domain, reduce_ips):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    proxys = cluster_obj.proxyinstance_set.all()
    count = len(proxys) - len(reduce_ips)
    remark = r"mcp proxy {} reduce ticket".format(reduce_ips)
    if count < 2:
        return {"error": _("缩容后集群proxy小于2，不满足亲和度要求")}
    # 获取主机相关的数据
    proxy_reduced_hosts = []
    for proxy in proxys:
        machine = proxy.machine
        if machine.ip in reduce_ips:
            proxy_reduced_hosts.append(
                {
                    "ip": machine.ip,
                    "bk_biz_id": machine.bk_biz_id,
                    "bk_host_id": machine.bk_host_id,
                    "bk_cloud_id": machine.bk_cloud_id,
                }
            )
    # 检查是否存在传入的IP与集群对应不上的
    if len(reduce_ips) != len(proxy_reduced_hosts):
        for proxy in proxy_reduced_hosts:
            reduce_ips.remove(proxy["ip"])
        return {"error": _("存在不属于集群{}的proxy{}".format(cluster_domain, reduce_ips))}
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": remark,
        "ticket_type": TicketType.REDIS_PROXY_SCALE_DOWN,
        "details": {
            "infos": [
                {
                    "old_nodes": {"proxy_reduced_hosts": proxy_reduced_hosts},
                    "cluster_id": cluster_id,
                    "online_switch_type": "user_confirm",
                    "target_proxy_count": count,
                }
            ],
        },
    }
    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_proxy_increase(request, bk_biz_id, cluster_domain, proxy_change_count):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    proxys = cluster_obj.proxyinstance_set.all()
    # 获取spec_id
    spec_id = cluster_obj.proxyinstance_set.first().machine.spec_id
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp proxy increase ticket",
        "ticket_type": TicketType.REDIS_PROXY_SCALE_UP,
        "details": {
            "infos": [
                {
                    "bk_cloud_id": cluster_obj.bk_cloud_id,
                    "cluster_id": cluster_id,
                    "resource_spec": {"proxy": {"count": proxy_change_count, "spec_id": spec_id}},
                    # 用于前端展示的参数
                    "current_proxy_num": len(proxys),
                    "target_proxy_count": len(proxys) + proxy_change_count,
                }
            ],
            "ip_source": IpSource.RESOURCE_POOL.value,
            "shrink_type": "QUANTITY",
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_full_backup(request, bk_biz_id, cluster_domain, backup_type, target):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.REDIS_BACKUP,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp backup ticket",
        "details": {
            "rules": [
                {"backup_type": backup_type, "cluster_id": cluster_id, "domain": cluster_domain, "target": target}
            ]
        },
    }
    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_flush_db(request, bk_biz_id, cluster_domain, is_force, is_backup):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    cluster_type = cluster_obj.cluster_type
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.REDIS_PURGE,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis flushdb ticket",
        "details": {
            "rules": [
                {
                    "force": is_force,
                    "backup": is_backup,
                    "domain": cluster_domain,
                    "db_list": [],
                    "flushall": True,
                    "cluster_id": cluster_id,
                    "cluster_type": cluster_type,
                }
            ]
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_extract_key(request, bk_biz_id, cluster_domain, white_regex, black_regex):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.REDIS_KEYS_EXTRACT,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis extract key ticket",
        "details": {
            "rules": [
                {
                    "domain": cluster_domain,
                    "cluster_id": cluster_id,
                    "black_regex": black_regex,
                    "white_regex": white_regex,
                }
            ]
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_delete_key_by_regex(request, bk_biz_id, cluster_domain, white_regex, black_regex, delete_rate):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.REDIS_KEYS_DELETE,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis delete key ticket",
        "details": {
            "delete_type": "regex",
            "rules": [
                {
                    "domain": cluster_domain,
                    "delete_rate": delete_rate,
                    "cluster_id": cluster_id,
                    "black_regex": black_regex,
                    "white_regex": white_regex,
                }
            ],
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_reinstall_dbmon(request, bk_biz_id, cluster_domain):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.REDIS_CLUSTER_REINSTALL_DBMON,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis reinstall dbmon ticket",
        "details": {
            "is_stop": False,
            "bk_cloud_id": cluster_obj.bk_cloud_id,
            "restart_exporter": True,
            "cluster_ids": [cluster_id],
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_version_update_online(request, bk_biz_id, cluster_domain, node_type, target_version):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    # 为了前端展示获取
    current_versions = set()
    ips = set()
    if node_type == ClusterRoleEnum.BACKEND:
        update_instance = cluster_obj.storageinstance_set.all()
    else:
        update_instance = cluster_obj.proxyinstance_set.all()

    for ins in update_instance:
        current_versions.add(ins.version)
        ips.add(ins.machine.ip)
    current_versions = list(current_versions)

    target_versions = [{"ip": ip, "version": target_version} for ip in ips]

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis version update ticket",
        "ticket_type": TicketType.REDIS_VERSION_UPDATE_ONLINE,
        "details": {
            "infos": [
                {
                    "cluster_id": cluster_obj.id,
                    "current_versions": current_versions,
                    "node_type": node_type,
                    "slave_current_versions": [],
                    "target_versions": target_versions,
                }
            ],
            "update_type": "cluster",
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_load_modules(request, bk_biz_id, cluster_domain, modules):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.REDIS_CLUSTER_LOAD_MODULES,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis load modules ticket",
        "details": {
            "infos": [
                {"cluster_id": cluster_obj.id, "db_version": cluster_obj.major_version, "load_modules": modules}
            ],
            "bk_cloud_id": cluster_obj.bk_cloud_id,
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_hotkey_analysis(request, bk_biz_id, cluster_domain, analysis_time, ins):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)

    # 检查ins是否都属于这个集群
    errmsg = []
    cluster_ins = [
        "{}:{}".format(e.machine.ip, e.port)
        for e in chain(cluster_obj.storageinstance_set.all(), cluster_obj.proxyinstance_set.all())
    ]
    errmsg.extend(f"{i}不属于集群{cluster_domain}\n" for i in ins if i not in cluster_ins)
    if len(errmsg) != 0:
        return {"error": str(errmsg)}

    # 如果传参为空，则为所有proxy
    if len(ins) == 0:
        ins = ["{}:{}".format(e.machine.ip, e.port) for e in cluster_obj.proxyinstance_set.all()]

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis analysis hot key ticket",
        "ticket_type": TicketType.REDIS_HOT_KEY_ANALYSIS,
        "details": {
            "analysis_time": analysis_time,
            "bk_cloud_id": cluster_obj.bk_cloud_id,
            "infos": [
                {
                    "cluster_id": cluster_obj.id,
                    "cluster_type": "TwemproxyRedisInstance",
                    "immute_domain": cluster_domain,
                    "ins": ins,
                    # "record_id"
                }
            ],
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_memory_analysis(request, bk_biz_id, cluster_domain, ins):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)

    # 检查ins是否都属于这个集群
    errmsg = []
    cluster_ins = [
        "{}:{}".format(e.machine.ip, e.port)
        for e in chain(cluster_obj.storageinstance_set.all(), cluster_obj.proxyinstance_set.all())
    ]
    errmsg.extend(f"{i}不属于集群{cluster_domain}\n" for i in ins if i not in cluster_ins)
    if len(errmsg) != 0:
        return {"error": str(errmsg)}

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis memory analysis ticket",
        "ticket_type": TicketType.REDIS_KEYSTAT,
        "details": {
            "bk_cloud_id": cluster_obj.bk_cloud_id,
            "analysis_time": 0,
            "infos": [
                {
                    "ins": [{"addr": n} for n in ins],
                    "delimiter": "#@_-",
                    "cluster_id": cluster_obj.id,
                    "cluster_type": cluster_obj.cluster_type,
                    "immute_domain": cluster_obj.immute_domain,
                    "check_last_visit": True,
                }
            ],
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}
