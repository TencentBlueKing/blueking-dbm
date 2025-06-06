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
from typing import List, Optional

from backend.configuration.constants import DB_ADMIN_USER_MAP, DBPrivSecurityType, DBType
from backend.configuration.handlers.password import DBPasswordHandler
from backend.db_meta.enums import ClusterType, MachineType, TenDBClusterSpiderRole
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance


def admin_password(bk_cloud_id: int, ip: str, port_list: Optional[List[int]] = None) -> dict:
    """
    目前不能正常工作
    """
    m = Machine.objects.get(bk_cloud_id=bk_cloud_id, ip=ip)
    if m.cluster_type in [ClusterType.TenDBSingle, ClusterType.TenDBHA]:
        dbtype = DBType.MySQL
    elif m.cluster_type == ClusterType.TenDBCluster:
        dbtype = DBType.TenDBCluster
    else:
        raise Exception(f"not support cluster type: {m.cluster_type}")  # noqa

    # 密码服务要求一个叫做 role 的参数, 用来确定一个 AdminPasswordRole 类型
    # role 其实没有做精确要求
    # 中控: 常量 spider_ctl
    # spider: [spider_master, spider_slave, spider_mnt] 随意一个
    # 存储:
    # 如果是 TendbCluster, 可以是 [remote master, remote slave, remote repeater] 随便一个
    # 如果是 Tendbha, tendbsingle, 可以是 [master, slave] 随便一个
    ports_with_role = []
    if port_list:
        if m.machine_type in [MachineType.BACKEND, MachineType.SINGLE]:
            ports_with_role = [{"port": port, "role": "master"} for port in port_list]
        elif m.machine_type == MachineType.REMOTE:
            ports_with_role = [{"port": port, "role": "remote_master"} for port in port_list]
        elif m.machine_type == MachineType.SPIDER:
            # 需要区分 port 到底是 spider 还是 spider ctl
            for pwr in port_list:
                if ProxyInstance.objects.filter(machine__ip=ip, port=pwr).exists():
                    ports_with_role.append({"port": pwr, "role": "spider_master"})
                elif ProxyInstance.objects.filter(machine__ip=ip, port=pwr - 1000).exists():
                    ports_with_role.append({"port": pwr, "role": "spider_ctl"})
                else:
                    raise
        else:
            raise
    else:
        if m.machine_type in [MachineType.BACKEND, MachineType.SINGLE]:
            ports_with_role = [
                {"port": port, "role": "master"}
                for port in list(StorageInstance.objects.filter(machine__ip=ip).values_list("port", flat=True))
            ]
        elif m.machine_type == MachineType.REMOTE:
            ports_with_role = [
                {"port": port, "role": "remote_master"}
                for port in list(StorageInstance.objects.filter(machine__ip=ip).values_list("port", flat=True))
            ]
        elif m.machine_type == MachineType.SPIDER:
            for pi in ProxyInstance.objects.filter(machine__ip=ip):
                ports_with_role.append({"port": pi.port, "role": pi.tendbclusterspiderext.spider_role})
                if pi.tendbclusterspiderext.spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
                    ports_with_role.append({"port": pi.port + 1000, "role": "spider_ctl"})
        else:
            raise

    res = {}
    for pwr in ports_with_role:
        rp = DBPasswordHandler.query_admin_password(
            limit=1, offset=0, bk_biz_id=m.bk_biz_id, instances=["{}:{}".format(ip, pwr["port"])], db_type=dbtype
        )
        if rp["count"] == 0:
            np = DBPasswordHandler.get_random_password(DBPrivSecurityType.MYSQL_PASSWORD)
            rt = DBPasswordHandler.modify_admin_password(
                operator="admin",
                password=np,
                lock_hour=72,
                is_async=False,
                instance_list=[
                    {
                        "ip": ip,
                        "port": pwr["port"],
                        "bk_cloud_id": bk_cloud_id,
                        "cluster_type": m.cluster_type,
                        "role": pwr["role"],
                    }
                ],
            )
            if rt["fail"] is not None:
                raise
            else:
                res[pwr["port"]] = {
                    "username": DB_ADMIN_USER_MAP[dbtype],
                    "password": np,
                }
        else:
            res[pwr["port"]] = {"username": rp["results"][0]["username"], "password": rp["results"][0]["password"]}

    return res
