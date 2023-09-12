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
from typing import Any, Dict

from django.db import transaction

from backend.components import NameServiceApi
from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta import api
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.env import CLB_DOMAIN
from backend.flow.utils import dns_manage


@transaction.atomic
def tendis_add_clb_domain(immute_domain: str, bk_cloud_id: int, created_by: str):
    """ 增加CLB 域名 """
    cluster = Cluster.objects.get(bk_cloud_id=bk_cloud_id, immute_domain=immute_domain)
    clb = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB.value).first()
    ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.CLBDNS,
        entry="clb.{}".format(cluster.immute_domain),
        creator=created_by,
        forward_to_id=clb.id,
    )


@transaction.atomic
def tendis_bind_clb_domain(immute_domain: str, bk_cloud_id: int, created_by: str):
    """ 主域名直接指向CLB """
    cluster = Cluster.objects.get(bk_cloud_id=bk_cloud_id, immute_domain=immute_domain)
    immute_entry = cluster.clusterentry_set.filter(
        cluster_entry_type=ClusterEntryType.DNS.value, entry=cluster.immute_domain
    ).first()
    clb_entry = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB.value).first()
    immute_entry.forward_to_id = clb_entry.id
    immute_entry.creator = created_by
    immute_entry.save(update_fields=["forward_to_id", "creator"])


@transaction.atomic
def tendis_unbind_clb_domain(immute_domain: str, bk_cloud_id: int, created_by: str):
    """ 主域名解绑CLB """
    cluster = Cluster.objects.get(bk_cloud_id=bk_cloud_id, immute_domain=immute_domain)
    immute_entry = cluster.clusterentry_set.filter(
        cluster_entry_type=ClusterEntryType.DNS.value, entry=cluster.immute_domain
    ).first()
    immute_entry.forward_to_id = None
    immute_entry.creator = created_by
    immute_entry.save(update_fields=["forward_to_id", "creator"])


@transaction.atomic
def delete_clb(domain: str):
    """删除db中clb数据"""

    cluster = Cluster.objects.filter(immute_domain=domain).get()
    cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB).delete()


@transaction.atomic
def delete_clb_dns(domain: str):
    """删除db中clbDns"""

    cluster = Cluster.objects.filter(immute_domain=domain).get()
    cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLBDNS).delete()


def tendis_domain_bind_clb_status(immute_domain: str, bk_cloud_id: int) -> bool:
    """判断主域名是否绑定了clb ip"""

    cluster = Cluster.objects.get(bk_cloud_id=bk_cloud_id, immute_domain=immute_domain)
    immute_entry = cluster.clusterentry_set.filter(
        cluster_entry_type=ClusterEntryType.DNS.value, entry=cluster.immute_domain
    ).first()
    return immute_entry.forward_to_id is not None


def get_cluster_info(cluster_id: int) -> Dict[str, Any]:
    """获取集群信息"""

    # 获取集群信息
    result = api.cluster.nosqlcomm.other.get_cluster_detail(cluster_id=cluster_id)
    cluster = result[0]
    return cluster


def get_dns_status_by_domain(bk_biz_id: int, bk_cloud_id: int, domain: str) -> bool:
    """判断域名是否存在"""

    result = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).get_domain(get_domain_name=domain)
    return len(result) > 0


def get_dns_status_by_ip(bk_biz_id: int, bk_cloud_id: int, domain: str, ip: str) -> bool:
    """判断ip是否在域名映射中"""

    results = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).get_domain(get_domain_name=domain)
    for result in results:
        if result["ip"] == ip:
            return True
    return False


def response_ok() -> Dict[str, Any]:
    """成功返回"""

    return {"code": 0, "message": "ok"}


def response_fail(code: int, message: str) -> Dict[str, Any]:
    """失败返回"""

    return {"code": code, "message": message}


def create_lb_and_register_target(cluster_id: int) -> Dict[str, Any]:
    """创建clb并绑定后端主机"""

    # 获取信息
    cluster = get_cluster_info(cluster_id=cluster_id)
    immute_domain = cluster["immute_domain"]

    # 判断clb是否已经存在
    if ClusterEntryType.CLB.value in cluster["clusterentry_set"]:
        message = "clb of cluster:{} has existed".format(immute_domain)
        return response_fail(code=3, message=message)
    region = cluster["region"]
    ips = cluster["twemproxy_set"]
    bk_biz_id = cluster["bk_biz_id"]

    # 通过bk_biz_id获取manager，backupmanager，去除admin
    users = DBAdministrator().get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=DBType.Redis)
    users = [user for user in users if user != "admin"]
    manager = users[0]
    backupmanager = users[1] if len(users) > 1 else users[0]

    # 进行请求，得到返回结果
    output = NameServiceApi.clb_create_lb_and_register_target(
        {
            "region": region,
            "loadbalancername": immute_domain,
            "listenername": immute_domain,
            "manager": manager,
            "backupmanager": backupmanager,
            "protocol": "TCP",
            "ips": ips,
        },
        raw=True,
    )
    return output


def add_clb_info_to_meta(output: Dict[str, Any], cluster_id: int, creator: str) -> Dict[str, Any]:
    """clb信息写入meta"""

    # 获取信息
    cluster = get_cluster_info(cluster_id=cluster_id)

    # 进行判断请求结果,请求结果正确，写入数据库
    if output["code"] == 0 and ClusterEntryType.CLB.value not in cluster["clusterentry_set"]:
        clb_ip = output["data"]["loadbalancerip"]
        try:
            api.entry.clb.create(
                [
                    {
                        "domain": cluster["immute_domain"],
                        "clb_ip": clb_ip,
                        "clb_id": output["data"]["loadbalancerid"],
                        "clb_listener_id": output["data"]["listenerid"],
                        "clb_region": cluster["region"],
                    }
                ],
                creator,
            )
        except Exception as e:
            message = "add clb info to meta fail, error:{}".format(str(e))
            return response_fail(code=3, message=message)
    return response_ok()


def delete_clb_info_from_meta(output: Dict[str, Any], cluster_id: int) -> Dict[str, Any]:
    """在meta中删除clb信息"""

    # 获取信息
    cluster = get_cluster_info(cluster_id=cluster_id)
    # 进行判断请求结果，如果为0操作删除db数据
    if output["code"] == 0 and ClusterEntryType.CLB.value in cluster["clusterentry_set"]:
        loadbalancerid = cluster["clusterentry_set"]["clb"][0]["clb_id"]
        try:
            delete_clb(cluster["immute_domain"])
        except Exception as e:
            message = "delete clb:{} info in db fail, error:{}".format(loadbalancerid, str(e))
            return response_fail(code=1, message=message)
    return response_ok()


def add_clb_domain_to_dns(cluster_id: int, creator: str) -> Dict[str, Any]:
    """添加clb域名到dns"""

    # 获取信息
    cluster = get_cluster_info(cluster_id=cluster_id)
    immute_domain = cluster["immute_domain"]
    port = cluster["twemproxy_ports"][0]
    bk_cloud_id = cluster["bk_cloud_id"]
    bk_biz_id = cluster["bk_biz_id"]
    clb_ip = cluster["clusterentry_set"]["clb"][0]["clb_ip"]
    # 添加clb域名以及dns
    if CLB_DOMAIN:
        # 添加clb域名dns
        if not get_dns_status_by_domain(
            bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id, domain="clb.{}".format(immute_domain)
        ):
            result = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).create_domain(
                instance_list=["{}#{}".format(clb_ip, str(port))], add_domain_name="clb.{}".format(immute_domain)
            )
            if not result:
                return {"code": 3, "message": "add clb domain to dns fail"}
        try:
            if ClusterEntryType.CLBDNS.value not in cluster["clusterentry_set"]:
                tendis_add_clb_domain(immute_domain=immute_domain, bk_cloud_id=bk_cloud_id, created_by=creator)
        except Exception as e:
            message = "cluster:{} add clb domain fail, error:{}".format(immute_domain, str(e))
            return response_fail(code=3, message=message)
    return response_ok()


def delete_clb_domain_from_dns(cluster_id: int) -> Dict[str, Any]:
    """从dns中删除clb域名"""

    cluster = get_cluster_info(cluster_id=cluster_id)
    clb_dns = cluster["clusterentry_set"]["clbDns"]
    immute_domain = cluster["immute_domain"]
    clb_ip = cluster["clusterentry_set"]["clb"][0]["clb_ip"]
    port = cluster["twemproxy_ports"][0]
    bk_cloud_id = cluster["bk_cloud_id"]
    bk_biz_id = cluster["bk_biz_id"]
    # 如果存在clb域名指向clb ip，则删除
    if clb_dns:
        # 删除dns：clb域名绑定clb ip
        if get_dns_status_by_domain(
            bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id, domain="clb.{}".format(immute_domain)
        ):
            result = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).remove_domain_ip(
                domain="clb.{}".format(immute_domain), del_instance_list=["{}#{}".format(clb_ip, str(port))]
            )
            if not result:
                message = "delete clb.{} dns info fail".format(immute_domain)
                return response_fail(code=1, message=message)
        # 删除元数据clbDns信息
        try:
            delete_clb_dns(domain=immute_domain)
        except Exception as e:
            message = "delete clb domain of cluster:{} fail, error:{}".format(immute_domain, str(e))
            return response_fail(code=1, message=message)
    return response_ok()


def deregister_target_and_delete_lb(cluster_id: int) -> Dict[str, Any]:
    """解绑后端主机并删除clb"""

    # 获取集群信息
    cluster = get_cluster_info(cluster_id=cluster_id)
    immute_domain = cluster["immute_domain"]

    # 判断clb是否存在
    if ClusterEntryType.CLB.value not in cluster["clusterentry_set"]:
        return {"code": 3, "message": "clb of cluster:%s does not exist, can not delete clb" % immute_domain}
    region = cluster["clusterentry_set"]["clb"][0]["clb_region"]
    loadbalancerid = cluster["clusterentry_set"]["clb"][0]["clb_id"]
    listenerid = cluster["clusterentry_set"]["clb"][0]["listener_id"]

    # 进行请求，得到返回结果
    output = NameServiceApi.clb_deregister_target_and_del_lb(
        {
            "region": region,
            "loadbalancerid": loadbalancerid,
            "listenerid": listenerid,
        },
        raw=True,
    )
    return output


def immute_domain_clb_ip(cluster_id: int, creator: str, bind: bool) -> Dict[str, Any]:
    """主域名指向clb ip或者解绑"""

    # 获取集群信息
    cluster = get_cluster_info(cluster_id=cluster_id)
    immute_domain = cluster["immute_domain"]
    bk_cloud_id = cluster["bk_cloud_id"]
    bk_biz_id = cluster["bk_biz_id"]
    clb_ip = cluster["clusterentry_set"]["clb"][0]["clb_ip"]
    port = cluster["twemproxy_ports"][0]
    proxy_ips = cluster["twemproxy_ips_set"]
    clb_ip_port = "{}#{}".format(clb_ip, str(port))
    if ClusterEntryType.CLB.value not in cluster["clusterentry_set"]:
        message = "clb of cluster:{} does not exist, can not bind or unbind clb ip".format(immute_domain)
        return response_fail(code=3, message=message)
    if bind:
        if not tendis_domain_bind_clb_status(immute_domain=immute_domain, bk_cloud_id=bk_cloud_id):
            # 添加dns：主域名指向clb ip
            dns_status_result = get_dns_status_by_ip(
                bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id, domain=immute_domain, ip=clb_ip
            )
            if not dns_status_result:
                create_dns_result = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).create_domain(
                    instance_list=[clb_ip_port], add_domain_name=immute_domain
                )
                if not create_dns_result:
                    message = "add immute domain with clb ip to dns fail"
                    return response_fail(code=3, message=message)

            # 删除老的dns：主域名指向proxy
            delete_dns_list = []
            # 判断ip是否在dns中存在
            for ip in proxy_ips:
                dns_status_result = get_dns_status_by_ip(
                    bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id, domain=immute_domain, ip=ip
                )
                if dns_status_result:
                    delete_dns_list.append("{}#{}".format(ip, str(port)))
            if delete_dns_list:
                dns_remove_status = dns_manage.DnsManage(
                    bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id
                ).remove_domain_ip(domain=immute_domain, del_instance_list=delete_dns_list)
                if not dns_remove_status:
                    message = "delete immute domain with proxy ip from dns fail"
                    return response_fail(code=3, message=message)
            # 修改元数据
            try:
                tendis_bind_clb_domain(immute_domain=immute_domain, bk_cloud_id=bk_cloud_id, created_by=creator)
            except Exception as e:
                message = "change meta data about immute domain bind clb ip fail, error:{}".format(str(e))
                return response_fail(code=3, message=message)
            return response_ok()
        message = "immute domain has bound clb ip"
        return response_fail(code=3, message=message)
    # 主域名解绑clb ip
    if tendis_domain_bind_clb_status(immute_domain=immute_domain, bk_cloud_id=bk_cloud_id):
        # 添加dns：主域名指向proxy
        add_dns_list = []
        for ip in proxy_ips:
            dns_status_result = get_dns_status_by_ip(
                bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id, domain=immute_domain, ip=ip
            )
            if not dns_status_result:
                add_dns_list.append("{}#{}".format(ip, str(port)))
        if add_dns_list:
            dns_create_result = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).create_domain(
                instance_list=add_dns_list, add_domain_name=immute_domain
            )
            if not dns_create_result:
                message = "add immute domain with proxy ip from dns fail"
                return response_fail(code=3, message=message)

        # 删除老的dns：主域名指向clb ip
        dns_status_result = get_dns_status_by_ip(
            bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id, domain=immute_domain, ip=clb_ip
        )
        if dns_status_result:
            dns_remove_status = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).remove_domain_ip(
                immute_domain, [clb_ip_port]
            )
            if not dns_remove_status:
                message = "delete immute domain with clb ip from dns fail"
                return response_fail(code=3, message=message)
        # 修改元数据
        try:
            tendis_unbind_clb_domain(immute_domain=immute_domain, bk_cloud_id=bk_cloud_id, created_by=creator)
        except Exception as e:
            message = "change meta data about immute domain bind clb ip fail, error:{}".format(str(e))
            return response_fail(code=3, message=message)
        return response_ok()
    return response_ok()
