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
import re
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, List

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum, RedisCapacityUpdateType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.name_service.name_service import ExecNameServiceOperationComponent
from backend.flow.plugins.components.collections.redis.redis_apply_summary import RedisApplySummaryComponent
from backend.flow.utils.name_service.name_service_dataclass import ActKwargs as NsActKwargs
from backend.flow.utils.name_service.name_service_dataclass import TransDataKwargs as NsTransDataKwargs


def build_clb_polaris_apply_subs(
    root_id: str,
    data: dict,
    bk_biz_id: int,
    domain_name: str,
    creator: str,
    apply_clb: bool = False,
    apply_polaris: bool = False,
) -> List:
    """
    redis集群部署成功后，根据单据传参决定是否构建创建CLB / 北极星(Polaris) 的子流程。
    该函数需要在"建立集群 元数据"活动节点之后调用，因为创建CLB/Polaris依赖集群及其proxy已经落库。
    返回的子流程(SubProcess)可以直接放入acts_list，与"注册域名"等节点一起通过add_parallel_acts并行执行，
    从而缩短集群部署总耗时。
    @param root_id: 当前flow的root_id
    @param data: 当前flow的全局参数(即self.data)
    @param bk_biz_id: 业务id
    @param domain_name: 集群主域名，集群刚创建，此时ticket/flow上下文中还没有cluster_id，
                         需要通过bk_biz_id+domain_name在节点执行态实时解析出cluster_id
    @param creator: 单据创建人
    @param apply_clb: 是否需要给集群创建clb，默认False
    @param apply_polaris: 是否需要给集群创建北极星，默认False
    @return: 子流程(SubProcess)列表，不需要创建clb/北极星时返回空列表
    """
    sub_processes = []
    if not apply_clb and not apply_polaris:
        return sub_processes

    if apply_clb:
        clb_sub_pipeline = SubBuilder(root_id=root_id, data=data)
        ns_kwargs = NsActKwargs()
        ns_kwargs.bk_biz_id = bk_biz_id
        ns_kwargs.domain_name = domain_name
        ns_kwargs.creator = creator
        ns_kwargs.set_trans_data_dataclass = NsTransDataKwargs.__name__

        ns_kwargs.name_service_operation_type = "create_clb"
        clb_sub_pipeline.add_act(
            act_name=_("创建clb"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(ns_kwargs),
        )
        ns_kwargs.name_service_operation_type = "add_clb_info_to_meta"
        clb_sub_pipeline.add_act(
            act_name=_("clb信息写入meta"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(ns_kwargs),
        )
        ns_kwargs.name_service_operation_type = "add_clb_domain_to_dns"
        clb_sub_pipeline.add_act(
            act_name=_("clb域名添加到dns，clb域名信息写入meta"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(ns_kwargs),
        )
        # 将集群主域名指向clb ip，使集群访问流量经过clb；与"创建clb"串成一条子流程
        ns_kwargs.name_service_operation_type = "domain_bind_clb_ip"
        clb_sub_pipeline.add_act(
            act_name=_("主域名绑定clb ip"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(ns_kwargs),
        )
        sub_processes.append(clb_sub_pipeline.build_sub_process(sub_name=_("创建clb")))

    if apply_polaris:
        polaris_sub_pipeline = SubBuilder(root_id=root_id, data=data)
        ns_kwargs = NsActKwargs()
        ns_kwargs.bk_biz_id = bk_biz_id
        ns_kwargs.domain_name = domain_name
        ns_kwargs.creator = creator
        ns_kwargs.set_trans_data_dataclass = NsTransDataKwargs.__name__

        ns_kwargs.name_service_operation_type = "create_polaris"
        polaris_sub_pipeline.add_act(
            act_name=_("创建polaris"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(ns_kwargs),
        )
        ns_kwargs.name_service_operation_type = "add_polaris_info_to_meta"
        polaris_sub_pipeline.add_act(
            act_name=_("polaris信息写入meta"),
            act_component_code=ExecNameServiceOperationComponent.code,
            kwargs=asdict(ns_kwargs),
        )
        sub_processes.append(polaris_sub_pipeline.build_sub_process(sub_name=_("创建北极星")))

    return sub_processes


def add_summary_output_act(
    redis_pipeline,
    bk_biz_id: int,
    domain_name: str,
    region: str,
    proxy_port: int,
    apply_clb: bool = False,
    apply_polaris: bool = False,
):
    """
    redis集群部署成功后，将集群关键信息(地区/域名/端口/CLB/北极星)写入FlowSummary，供前端"执行摘要"展示。
    该函数需要在"建立集群 元数据"以及"add_clb_polaris_apply_acts"(如果有)之后调用，
    这样才能查询到完整的CLB/北极星信息。
    @param redis_pipeline: 当前redis部署流程的Builder实例，节点会直接追加到该流程中
    @param bk_biz_id: 业务id
    @param domain_name: 集群主域名
    @param region: 地区(城市代码)
    @param proxy_port: 集群端口
    @param apply_clb: 单据是否创建了clb
    @param apply_polaris: 单据是否创建了北极星
    """
    item = {
        "bk_biz_id": bk_biz_id,
        "domain_name": domain_name,
        "region": region,
        "proxy_port": proxy_port,
        "apply_clb": apply_clb,
        "apply_polaris": apply_polaris,
    }
    redis_pipeline.add_act(
        act_name=_("{}-写入集群信息摘要").format(domain_name),
        act_component_code=RedisApplySummaryComponent.code,
        kwargs={"items": [item]},
    )


def add_batch_summary_output_act(redis_pipeline, items: List[Dict], component_code=None):
    """
    批量将多个集群关键信息(地区/域名/端口/CLB/北极星)一次性写入FlowSummary，供前端"执行摘要"展示。
    适用于一个流程需要一次性部署多个集群/实例的场景(如redis主从实例批量部署)，
    只会追加一个流程节点，最终合并到同一张摘要表(table_name)的values数组里，不会产生多条摘要记录。
    该函数需要在各集群"建立集群 元数据"以及"add_clb_polaris_apply_acts"(如果有)之后调用。
    @param redis_pipeline: 当前redis部署流程的Builder/SubBuilder实例，节点会直接追加到该流程中
    @param items: 摘要信息列表，每项需包含 bk_biz_id/domain_name/region/proxy_port，
                  可选 apply_clb/apply_polaris(默认False)
    @param component_code: 摘要组件code，默认使用集群部署的 RedisApplySummaryComponent（含CLB/北极星），
                           主从实例部署应传入 RedisInsApplySummaryComponent.code（不含CLB/北极星）
    """
    if not items:
        return
    if component_code is None:
        component_code = RedisApplySummaryComponent.code
    redis_pipeline.add_act(
        act_name=_("批量写入集群信息摘要"),
        act_component_code=component_code,
        kwargs={"items": items},
    )


def domain_without_port(domain):
    end_port_reg = re.compile(r"(\:\d+$)|(#\d+$)")
    if end_port_reg.search(domain):
        return end_port_reg.sub("", domain)
    return domain


def check_domain(domain):
    match = re.search(r"^[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62}){2,8}\.*(#(\d+))?$", domain)
    if match:
        return True
    return False


def convert_version_to_uint(version):
    version = version.strip()
    if not version:
        return 0, None
    list01 = version.split(".")
    billion = ""
    thousand = ""
    single = ""
    if len(list01) == 0:
        err = ValueError(f"version:{version} format not correct")
        return 0, err
    billion = list01[0]
    thousand = list01[1] if len(list01) >= 2 else ""
    single = list01[2] if len(list01) >= 3 else ""
    total = 0
    if billion:
        try:
            b = int(billion)
            total += b * 1000000
        except ValueError as e:
            err = ValueError(f"convertVersionToUint int() fail, err:{e}, billion:{billion}, version:{version}")
            return 0, err
    if thousand:
        try:
            t = int(thousand)
            total += t * 1000
        except ValueError as e:
            err = ValueError(f"convertVersionToUint int() fail, err:{e}, thousand:{thousand}, version:{version}")
            return 0, err
    if single:
        try:
            s = int(single)
            total += s
        except ValueError as e:
            err = ValueError(f"convertVersionToUint int() fail, err:{e}, single:{single}, version:{version}")
            return 0, err
    return total, None


# redis-6.2.7.tar.gz => (6002007, 0, None)
# redis-2.8.17-rocksdb-v1.3.10.tar.gz => (2008017, 1003010, None)
def version_parse(version):
    reg01 = re.compile(r"[\d+.]+")
    rets = reg01.findall(version)
    if len(rets) == 0:
        err = ValueError(f"TendisVersionParse version:{version} format not correct")
        return 0, 0, err
    base_version = 0
    sub_version = 0
    if len(rets) >= 1:
        base_version, err = convert_version_to_uint(rets[0])
        if err:
            return 0, 0, err
    if len(rets) >= 2:
        sub_version, err = convert_version_to_uint(rets[1])
        if err:
            return 0, 0, err
    return base_version, sub_version, None


# 判断两个版本是否相等
def version_equal(version1, version2):
    base_version1, sub_version1, err = version_parse(version1)
    if err:
        return False, err
    base_version2, sub_version2, err = version_parse(version2)
    if err:
        return False, err
    return base_version1 == base_version2 and sub_version1 == sub_version2, None


def _version_compare(version1, version2):
    """
    比较两个版本，返回比较结果
    返回值: -1 (version1 < version2), 0 (version1 == version2), 1 (version1 > version2), None (解析错误)
    """
    if version1 is None or version2 is None:
        return None

    base_version1, sub_version1, err = version_parse(version1)
    if err:
        return None
    base_version2, sub_version2, err = version_parse(version2)
    if err:
        return None

    if base_version1 > base_version2:
        return 1
    elif base_version1 < base_version2:
        return -1
    else:  # base_version1 == base_version2
        if sub_version1 > sub_version2:
            return 1
        elif sub_version1 < sub_version2:
            return -1
        else:
            return 0


def version_gt(version1, version2):
    """
    判断版本1是否大于版本2
    """
    result = _version_compare(version1, version2)
    return result is not None and result > 0


def version_eq(version1, version2):
    result = _version_compare(version1, version2)
    return result is not None and result == 0


def version_ge(version1, version2):
    return version_eq(version1, version2) or version_gt(version1, version2)


# 根据db_version 获取 redis 最新 Package
def get_latest_redis_package_by_version(db_version):
    pkg_type = MediumEnum.Redis
    if db_version.startswith("TendisSSD"):
        pkg_type = MediumEnum.TendisSsd
    if db_version.startswith("Tendisplus"):
        pkg_type = MediumEnum.TendisPlus
    redis_pkg = Package.get_latest_package(version=db_version, pkg_type=pkg_type, db_type=DBType.Redis)
    return redis_pkg


def humanbytes(B):
    """
    将字节数转换为更易读的的字符串
    如: 11111111111 -> 10.35 GB
    如: 891743743 -> 850.43 MB
    """
    # 定义不同单位的字节数
    KB = float(1024)
    MB = float(KB**2)
    GB = float(KB**3)
    TB = float(KB**4)
    PB = float(KB**5)

    # 根据字节数选择合适的单位
    if B < KB:
        return f"{B:.0f} {'Bytes' if B == 1 else 'Byte'}"
    elif KB <= B < MB:
        return f"{B / KB:.2f} KB"
    elif MB <= B < GB:
        return f"{B / MB:.2f} MB"
    elif GB <= B < TB:
        return f"{B / GB:.2f} GB"
    elif TB <= B < PB:
        return f"{B / TB:.2f} TB"
    elif B >= PB:
        return f"{B / PB:.2f} PB"


UNITS = {None: 1, "B": 1, "KB": 2**10, "MB": 2**20, "GB": 2**30, "TB": 2**40, "PB": 2**50}


def parse_human_size(size):
    """
    解析人类可读的字符串为字节数
    如: 100GB -> 107374182400
    如: 11.1 MB -> 11639193
    """
    if isinstance(size, int):
        return size
    m = re.match(r"^(\d+(?:\.\d+)?)\s*([KMGTP]?B)?$", size.upper())
    if m:
        number, unit = m.groups()
        return int(float(number) * UNITS[unit])
    raise ValueError("Invalid human size")


def decode_info_cmd(info_str: str) -> Dict:
    """
    将info命令返回的 used_memory:12241256\r\nused_memory_human:11.67M
    接些成字典:{
        "used_memory":"12241256",
        "used_memory_human":"11.67M"
    }
    """
    info_ret: Dict[str, dict] = {}
    info_list: List = info_str.split("\n")
    for info_item in info_list:
        info_item = info_item.strip()
        if info_item.startswith("#"):
            continue
        if len(info_item) == 0:
            continue
        tmp_list = info_item.split(IP_PORT_DIVIDER, 1)
        if len(tmp_list) < 2:
            continue
        tmp_list[0] = tmp_list[0].strip()
        tmp_list[1] = tmp_list[1].strip()
        info_ret[tmp_list[0]] = tmp_list[1]
    return info_ret


def get_tendisplus_shutdown_hosts(cluster_id, target_group_num: int, update_mode: str):
    """
    获取tendisplus缩容时需要下架的hosts
    """
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_masters = cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value)
    master_ips = set()
    slave_ips = set()
    master_slave_dict = {}
    for master_obj in cluster_masters:
        master_ips.add(master_obj.machine.ip)
        if master_obj.as_ejector and master_obj.as_ejector.first():
            my_slave_obj = master_obj.as_ejector.get().receiver
            slave_ips.add(my_slave_obj.machine.ip)
            master_slave_dict[master_obj.machine.ip] = my_slave_obj.machine.ip

    # 如果是替换变更，则需要回收所有机器
    if update_mode == RedisCapacityUpdateType.ALL_MACHINES_REPLACE:
        return list(master_ips), list(slave_ips)

    current_group_num = len(master_ips)
    # 如果是扩容，没有需要下架的机器
    if current_group_num <= target_group_num:
        return [], []

    contraction_group = current_group_num - target_group_num
    shutdown_master_hosts = []
    shutdown_slave_hosts = []
    for master_ip in list(master_ips):
        if contraction_group <= 0:
            break
        contraction_group -= 1
        shutdown_master_hosts.append(master_ip)
        shutdown_slave_hosts.append(master_slave_dict[master_ip])
    return shutdown_master_hosts, shutdown_slave_hosts


def get_migrate_shutdown_hosts(src_ins_list: list, bk_biz_id: int):
    """
    获取迁移单据时需要下架的机器
    """
    ips = set()
    migrate_ports = defaultdict(set)
    shutdown_hosts = []
    shutdown_hosts_info = []
    for ins in src_ins_list:
        ip = ins.split(IP_PORT_DIVIDER)[0]
        port = int(ins.split(IP_PORT_DIVIDER)[1])

        ips.add(ip)
        migrate_ports[ip].add(port)

    # 查询出ips对应的所有实例
    if len(ips) != 0:
        storages = StorageInstance.find_storage_instance_by_ip(list(ips)).filter(bk_biz_id=bk_biz_id)

    exist_ports = defaultdict(set)
    # 遍历实例，确认端口，如果端口都没了，就是要下架的机器
    for s in storages:
        ip = s.machine.ip
        port = s.port
        exist_ports[ip].add(port)

    for ip in list(ips):
        if ip not in exist_ports:
            raise Exception(_("有ip[{}]不在元数据中".format(ip)))
        # 如果迁移端口不在已有端口中，报错
        if len(migrate_ports[ip] - exist_ports[ip]) > 0:
            raise Exception(_("{}有迁移端口{}不在元数据中".format(ip, migrate_ports[ip] - exist_ports[ip])))
        if len(exist_ports[ip] - migrate_ports[ip]) == 0:
            shutdown_hosts.append(ip)
    # 如果有需要下架的机器
    if len(shutdown_hosts) != 0:
        storages = StorageInstance.find_storage_instance_by_ip(list(shutdown_hosts)).filter(bk_biz_id=bk_biz_id)
        for s in storages:
            m_desc = s.machine.simple_desc
            shutdown_hosts_info.append({"bk_host_id": m_desc["bk_host_id"], "ip": m_desc["ip"]})
    return shutdown_hosts_info


def get_cluster_capacity_shutdown_host(bk_biz_id, cluster_id, target_group_num: int, update_mode: str):
    """
    重构后的后端容量变更获取下架机器统一函数。
     返回:
    - err_msg 错误信息
    - "old_machine_info": {
                        "master": [{"ip", "bk_biz_id", "bk_host_id", "bk_cloud_id"}],
                        "slave":  [{"ip", "bk_biz_id", "bk_host_id", "bk_cloud_id"}]
                     } 下架机器的信息
    """
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_masters = cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value)

    master_ips = set()
    slave_ips = set()
    master_slave_dict = {}
    for master_obj in cluster_masters:
        master_ips.add(master_obj.machine.ip)
        if master_obj.as_ejector and master_obj.as_ejector.first():
            my_slave_obj = master_obj.as_ejector.get().receiver
            slave_ips.add(my_slave_obj.machine.ip)
            master_slave_dict[master_obj.machine.ip] = my_slave_obj.machine.ip

    current_group_num = len(master_ips)
    # 如果是扩容，没有需要下架的机器
    if current_group_num <= target_group_num:
        err_msg = _("slot 扩容时不需要获取下架机器。 当前机器组数[{}], 目标机器组数[{}]", len(cluster_masters), target_group_num)
        return err_msg, {}

    contraction_group = current_group_num - target_group_num
    shutdown_master_hosts = []
    shutdown_slave_hosts = []

    # 整机替换方式扩缩容(总分片数不变，机器数变少 or 机型变)
    # 扩缩容这里不再做隐式版本升级，如果有版本升级需求，需要走版本升级单显式去升级
    if update_mode == RedisCapacityUpdateType.ALL_MACHINES_REPLACE:
        shutdown_master_hosts = master_ips
    elif update_mode == RedisCapacityUpdateType.SLOT_MIGRATE:
        for master_ip in list(master_ips):
            if contraction_group <= 0:
                break
            contraction_group -= 1
            shutdown_master_hosts.append(master_ip)
    else:
        # 有可能是本地扩容，机器数变多
        return _("{}变更类型不支持获取下架机器"), {}
    for master_ip in shutdown_master_hosts:
        shutdown_slave_hosts.append(master_slave_dict[master_ip])

    shutdown_master_info = []
    shutdown_slave_info = []
    storages = StorageInstance.find_storage_instance_by_ip(list(shutdown_master_hosts)).filter(bk_biz_id=bk_biz_id)
    for s in storages:
        m_desc = s.machine.simple_desc
        shutdown_master_info.append(
            {
                "bk_host_id": m_desc["bk_host_id"],
                "ip": m_desc["ip"],
                "bk_biz_id": m_desc["bk_biz_id"],
                "bk_cloud_id": m_desc["bk_cloud_id"],
            }
        )
    storages = StorageInstance.find_storage_instance_by_ip(list(shutdown_slave_info)).filter(bk_biz_id=bk_biz_id)
    for s in storages:
        m_desc = s.machine.simple_desc
        shutdown_slave_info.append(
            {
                "bk_host_id": m_desc["bk_host_id"],
                "ip": m_desc["ip"],
                "bk_biz_id": m_desc["bk_biz_id"],
                "bk_cloud_id": m_desc["bk_cloud_id"],
            }
        )
    return "", {"master": shutdown_master_info, "slave": shutdown_slave_info}
