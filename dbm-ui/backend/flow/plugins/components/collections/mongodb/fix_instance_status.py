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
import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.db_meta.enums.cluster_entry_type import ClusterEntryType
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models.instance import ProxyInstance, StorageInstance
from backend.flow.consts import InstanceStatus, MongoDBClusterRole
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.clb_manage import get_clb_by_ip
from backend.flow.utils.dns_manage import DnsManage

logger = logging.getLogger("json")


class ExecFixInstanceStatusOperation(BaseService):
    """
    FixInstanceStatus
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行创建名字服务功能的函数
        global_data 单据全局变量，格式字典
        kwargs 私有变量
        """
        kwargs = data.get_one_of_inputs("kwargs")
        instance = kwargs["trans_data_var"]["instance"]
        self.log_info(
            "fix instance status for instance {}:{}:{} role_type:{}".format(
                instance["ip"], instance["port"], instance["bk_cloud_id"], instance["role"]
            )
        )
        # 根据instance信息，获取instance的status
        fix_entry_list = fix_instance_cluster_entry(
            instance["ip"], instance["port"], instance["bk_cloud_id"], instance["role"]
        )
        data.outputs["fix_entry_list"] = [entry.__json__() for entry in fix_entry_list]

        if len(fix_entry_list) == 0:
            self.log_info(
                "no cluster entry to fix for instance {}:{}:{} role_type:{}".format(
                    instance["ip"], instance["port"], instance["bk_cloud_id"], instance["role"]
                )
            )
            return True

        all_success = True
        for fix_entry in fix_entry_list:
            self.log_info(
                f"instance {instance['ip']}:{instance['port']} cluster entry {fix_entry.cluster_entry_type} "
                f"entry:{fix_entry.entry} fix result:{fix_entry.result_code} message:{fix_entry.result_message}"
            )
            if fix_entry.result_code <= 0:
                all_success = False

        if all_success:
            self.log_info("all cluster entry fix success, try to update instance status to running")
            try:
                code, msg = fix_instance_meta_status(
                    instance["ip"], instance["port"], instance["bk_cloud_id"], instance["role"]
                )
                data.outputs["fix_instance_meta_status"] = {"result_code": code, "result_message": msg}
            except Exception as e:
                self.log_info("update instance status to normal failed, error:{}".format(e))
                all_success = False
                data.outputs["fix_instance_meta_status"] = {
                    "result_code": -1,
                    "result_message": "update instance status to normal failed, error:{}".format(e),
                }
        return all_success

    # 流程节点输入参数
    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class ExecFixInstanceStatusOperationComponent(Component):
    """
    ExecFixInstanceStatusOperation组件 从meta中获得相关ip的instance信息
    """

    name = __name__
    code = "fix_instance_status_operation"
    bound_service = ExecFixInstanceStatusOperation


@dataclass
class FixEntryInfo:
    cluster_entry_type: str = ""
    entry: str = ""
    result_code: int = 0
    result_message: str = ""

    def __json__(self):
        return {
            "cluster_entry_type": self.cluster_entry_type,
            "entry": self.entry,
            "result_code": self.result_code,
            "result_message": self.result_message,
        }


def fix_instance_meta_status(ip: str, port: int, bk_cloud_id: int, role_type: str) -> (bool, str):
    """
    修复实例的状态
    @param ip: 实例ip
    @param port: 实例port
    @param bk_cloud_id: 实例云区域id
    @param role_type: 实例角色类型，如: mongos, shard, config, mongos, shard, config
    @return: 是否修复成功
    """
    inst = (
        ProxyInstance.objects.get(machine__ip=ip, port=port, machine__bk_cloud_id=bk_cloud_id)
        if role_type == MongoDBClusterRole.Mongos.value
        else StorageInstance.objects.get(machine__ip=ip, port=port, machine__bk_cloud_id=bk_cloud_id)
    )
    if not inst:
        return False, "inst not found for {}:{}:{} role_type:{}".format(ip, port, bk_cloud_id, role_type)

    old_status = inst.status
    if old_status == InstanceStatus.RUNNING.value:
        return True, "instance status is already {}, no need to fix".format(old_status)
    inst.status = InstanceStatus.RUNNING.value
    inst.save()
    return True, "instance status from {} to {}".format(old_status, InstanceStatus.RUNNING.value)


def fix_instance_cluster_entry(ip: str, port: int, bk_cloud_id: int, role_type: str) -> list:
    """
    修复实例的集群entry.
    @param ip: 实例ip
    @param port: 实例port
    @param bk_cloud_id: 实例云区域id
    @param role_type: 实例角色类型，如: mongos, shard, config, mongos, shard, config
    @return: 是否找到，是否修复成功
    """
    is_proxy = role_type in [MongoDBClusterRole.Mongos.value]
    fix_entry_list = []
    if is_proxy:
        inst = ProxyInstance.objects.get(machine__ip=ip, port=port, machine__bk_cloud_id=bk_cloud_id)
        if not inst:
            raise Exception("inst not found for {}:{}:{} role_type:{}".format(ip, port, bk_cloud_id, role_type))

        bk_biz_id = inst.cluster.first().bk_biz_id
        for row in inst.bind_entry.all():
            match row.cluster_entry_type:
                case ClusterEntryType.DNS.value:
                    code, msg = fix_instance_dns_entry(
                        ip=ip, port=port, bk_cloud_id=bk_cloud_id, bk_biz_id=bk_biz_id, domain=row.entry
                    )
                    fix_entry_list.append(
                        FixEntryInfo(
                            cluster_entry_type=row.cluster_entry_type,
                            entry=row.entry,
                            result_code=code,
                            result_message=msg,
                        )
                    )

                case ClusterEntryType.CLB.value:
                    code, msg = fix_instance_clb_entry(
                        clb_ip=row.entry, bk_cloud_id=bk_cloud_id, rs_instance_list=["{}:{}".format(ip, port)]
                    )
                    fix_entry_list.append(
                        FixEntryInfo(
                            cluster_entry_type=row.cluster_entry_type,
                            entry=row.entry,
                            result_code=code,
                            result_message=msg,
                        )
                    )
                case _:
                    # other cluster entry type, do nothing
                    pass
    else:
        # storage instance, only fix dns entry for replica set cluster
        inst = StorageInstance.objects.get(machine__ip=ip, port=port, machine__bk_cloud_id=bk_cloud_id)
        if not inst:
            raise Exception("inst not found for {}:{}:{} role_type:{}".format(ip, port, bk_cloud_id, role_type))
        cluster_type = inst.cluster.first().cluster_type
        if cluster_type != ClusterType.MongoReplicaSet.value:
            # cluster type is not replica set, do nothing. return a fake entry
            fix_entry_list.append(
                FixEntryInfo(
                    cluster_entry_type="none",
                    entry="none dns entry",
                    result_code=1,
                    result_message="cluster type is not replica set, cluster_type:{}".format(cluster_type),
                )
            )
        else:
            bk_biz_id = inst.cluster.first().bk_biz_id
            for row in inst.bind_entry.all():
                if row.cluster_entry_type == ClusterEntryType.DNS.value:
                    domain = row.entry
                    code, msg = fix_instance_dns_entry(
                        ip=ip, port=port, bk_cloud_id=bk_cloud_id, bk_biz_id=bk_biz_id, domain=domain
                    )
                    fix_entry_list.append(
                        FixEntryInfo(
                            cluster_entry_type=row.cluster_entry_type,
                            entry=row.entry,
                            result_code=code,
                            result_message=msg,
                        )
                    )

    return fix_entry_list


def fix_instance_dns_entry(ip: str, port: int, bk_cloud_id: int, bk_biz_id: int, domain: str) -> (int, str):
    # fix_instance_dns_entry 修复实例的dns entry
    # return:
    # 1. 成功: 1
    # 2. 失败: 0
    # 3. 已存在: 2
    # 4. 其他: -1
    code_dict = {
        1: "success",
        0: "failed",
        2: "domain already exists",
        -1: "invalid parameters: domain:{} ip:{} port:{} bk_biz_id:{} bk_cloud_id:{}".format(
            domain, ip, port, bk_biz_id, bk_cloud_id
        ),
    }
    if not domain or not ip or not port or not bk_biz_id or bk_cloud_id is None:
        return -1, code_dict[-1]
    dns_manage = DnsManage(bk_cloud_id=bk_cloud_id, bk_biz_id=bk_biz_id)
    domain_list = dns_manage.get_domain(domain_name=domain)
    if not domain_list:
        domain_list = []

    for domain_row in domain_list:
        if domain_row["ip"] == ip and domain_row["port"] == port:
            return 2, code_dict[2]
    # create domain: register domain in dns service
    try:
        dns_manage.create_domain(instance_list=["{}#{}".format(ip, port)], add_domain_name=domain)
    except Exception as e:
        return 0, "create domain failed, error:{}".format(e)
    return 1, code_dict[1]


CLB_API_MAX_RETRIES = 3
CLB_API_RETRY_INTERVAL = 2


def _fetch_clb_rs_set(clb_manage) -> Tuple[Optional[set], str]:
    try:
        ok, res = clb_manage.get_clb_rs_with_response()
    except Exception as e:
        return None, "error:{}".format(e)
    if not ok:
        return None, "response:{}".format(res)
    data = res.get("data") if isinstance(res, dict) else None
    if not isinstance(data, dict):
        return None, "invalid response:{}".format(res)
    ips = data.get("ips")
    if ips is None:
        return set(), ""
    if not isinstance(ips, list):
        return None, "invalid response:{}".format(res)
    return {str(rs) for rs in ips if rs}, ""


def _fetch_clb_rs_set_with_retry(clb_manage) -> Tuple[Optional[set], str]:
    last_err = ""
    for attempt in range(1, CLB_API_MAX_RETRIES + 1):
        clb_rs_set, err_msg = _fetch_clb_rs_set(clb_manage)
        if clb_rs_set is not None:
            return clb_rs_set, ""
        last_err = err_msg
        if attempt < CLB_API_MAX_RETRIES:
            time.sleep(CLB_API_RETRY_INTERVAL)
    return None, last_err


def fix_instance_clb_entry(clb_ip: str, bk_cloud_id: int, rs_instance_list: list) -> Tuple[int, str]:
    # fix_instance_clb_entry 修复实例的clb entry
    # return:
    # 1. 成功: 1
    # 2. 失败: 0
    # 3. 已存在: 2
    # 4. 其他: -1
    code_dict = {1: "success", 0: "failed", 2: "clb rs already exists", -1: "invalid parameters"}
    if not clb_ip or not rs_instance_list or bk_cloud_id is None:
        return -1, code_dict[-1]

    clb_manage = get_clb_by_ip(clb_ip=clb_ip)
    if not clb_manage:
        return 0, "clb_obj not found for clb_ip:{} bk_cloud_id:{}".format(clb_ip, bk_cloud_id)

    clb_rs_set, err_msg = _fetch_clb_rs_set_with_retry(clb_manage)
    if clb_rs_set is None:
        return 0, "get clb rs failed, {}".format(err_msg)

    missing_rs_list = [rs for rs in rs_instance_list if rs not in clb_rs_set]
    if not missing_rs_list:
        return 2, code_dict[2]

    add_err = ""
    add_ok = False
    for attempt in range(1, CLB_API_MAX_RETRIES + 1):
        try:
            ok, res = clb_manage.add_clb_rs_with_response(instance_list=missing_rs_list)
        except Exception as e:
            add_err = "error:{}".format(e)
        else:
            if ok:
                add_ok = True
                break
            add_err = "response:{}".format(res)

        if attempt < CLB_API_MAX_RETRIES:
            time.sleep(CLB_API_RETRY_INTERVAL)
            # 重试前查一次 CLB，避免上一次请求实际已生效但响应超时导致重复添加失败
            retry_rs_set, _err = _fetch_clb_rs_set(clb_manage)
            if retry_rs_set is not None:
                missing_rs_list = [rs for rs in missing_rs_list if rs not in retry_rs_set]
                if not missing_rs_list:
                    return 1, code_dict[1]

    if not add_ok:
        return 0, "add clb rs failed, {}".format(add_err)

    verify_err = ""
    for _attempt in range(1, CLB_API_MAX_RETRIES + 1):
        time.sleep(CLB_API_RETRY_INTERVAL)
        after_clb_rs_set, err_msg = _fetch_clb_rs_set(clb_manage)
        if after_clb_rs_set is None:
            verify_err = "verify clb rs failed, {}".format(err_msg)
            continue
        still_missing = [rs for rs in missing_rs_list if rs not in after_clb_rs_set]
        if not still_missing:
            return 1, code_dict[1]
        verify_err = "clb rs not found after add, missing:{}".format(still_missing)

    return 0, verify_err
