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
# redis相关单据上下文
import json
from dataclasses import dataclass, field
from typing import Any, Optional

from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta.enums.cluster_type import ClusterType
from backend.flow.consts import DEFAULT_REDIS_START_PORT, DEFAULT_TWEMPROXY_SEG_TOTOL_NUM


@dataclass()
class DnsKwargs:
    """
    定义dns管理的活动节点专属参数
    """

    dns_op_type: Optional[Any]  # 操作的域名方式
    delete_cluster_id: int = None  # 操作的集群，回收集群时需要
    add_domain_name: str = None  # 如果添加域名时,添加域名名称
    dns_op_exec_port: int = None  # 如果做添加或者更新域名管理，执行实例的port


@dataclass()
class ActKwargs:
    """
    定义活动节点的私有变量dataclass类
    """

    exec_ip: Optional[Any] = None  # 表示执行的ip，多个ip传入list类型，当个ip传入str类型，空则传入None
    set_trans_data_dataclass: str = None  # 加载到上下文的dataclass类的名称
    get_trans_data_ip_var: str = None  # 表示在上下文获取ip信息的变量名称。空则传入None
    get_redis_payload_func: str = None  # 上下文中RedisActPayload类的获取参数方法名称。空则传入None
    file_list: list = field(default_factory=list)  # 传入文件传输节点的文件名称列表，默认空字典
    is_update_trans_data: bool = False  # 表示是否合并上下文内容到单据cluster信息中，False表示不合并
    cluster: dict = field(default_factory=dict)  # 表示单据执行的集群信息，比如集群名称，集群域名等
    extend_attr: list = field(default_factory=list)  # 表示单据执行的额外参数
    meta_func_name: str = None  # 元数据dbmeta的方法名称，空则传入None
    meta_read_flag: bool = False  # 元数据dbmetea操作类型是是否是读
    ip_index: int = None  # 遍历ip列表时的下标索引
    write_op: str = None
    bk_cloud_id: int = DEFAULT_BK_CLOUD_ID  # 云区域id，默认为直连区域


@dataclass()
class CommonContext:
    """
    通用上下文
    """

    tendis_backup_info: list = None  # 执行备份后的信息
    redis_act_payload: Optional[Any] = None  # 代表获取payload参数的类


@dataclass()
class RedisDeleteKeyContext:
    redis_act_payload: Optional[Any] = None  # 代表获取payload参数的类
    disk_used: dict = field(default_factory=dict)
    disk_free_max_ip: str = None

    @staticmethod
    def get_disk_free_max_ip_name() -> str:
        return "disk_free_max_ip"


@dataclass()
class ProxyScaleContext:
    """
    proxy扩缩容上下文
    """

    new_proxy_ips: list = None  # 代表在资源池分配的proxy列表
    servers: list = None  # proxy分片规则数组
    redis_act_payload: Optional[Any] = None  # 代表获取payload参数的类


@dataclass()
class RedisDtsContext:
    """
    redis dts上下文
    """

    bk_biz_id: str = None  # 代表业务id
    bk_cloud_id: int = None  # 代表云区域id
    dts_bill_type: str = None  # 代表dts单据类型
    dts_copy_type: str = None  # 代表dts数据复制类型
    src_cluster_id: str = None  # 代表源集群id
    src_cluster_addr: str = None  # 代表源集群地址
    src_cluster_password: str = None  # 代表源集群密码
    src_cluster_type: str = None  # 代表源集群类型
    src_cluster_region: str = None  # 代表源集群所在区域
    src_cluster_running_master: dict = None  # 代表源集群一个正在运行的master
    src_redis_password: str = None  # 代表源redis密码
    src_slave_instances: list = None  # 代表源redis slave实例列表
    src_slave_hosts: list = None  # 代表源redis slave host列表
    src_proxy_instances: list = None  # 代表源redis proxy实例列表
    src_proxy_config: str = None  # 代表源redis proxy配置

    dst_cluster_id: str = None  # 代表目标集群id
    dst_cluster_addr: str = None  # 代表目标集群地址
    dst_cluster_password: str = None  # 代表目标集群密码
    dst_redis_password: str = None  # 代表目的redis密码
    dst_cluster_type: str = None  # 代表目标集群类型
    dst_proxy_config: str = None  # 代表目标redis proxy配置

    key_white_regex: str = None  # 代表key白名单正则
    key_black_regex: str = None  # 代表key黑名单正则
    disk_used: dict = field(default_factory=dict)

    job_id: int = None  # 代表dts job id,对应表tb_tendis_dts_job
    task_ids: list = None  # 代表dts task id列表,对应表tb_tendis_dts_task

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


@dataclass
class RedisDataStructureContext:
    """
    redis 数据构造，上下文dataclass类
    """

    tendis_backup_info: list = None  # 执行备份后的信息
    new_master_ips: list = None  # 代表在资源池分配到的master列表
    shard_num: int = None  # 集群分片数
    inst_num: int = None  # 集群单机实例个数
    servers: list = None  # proxy分片规则数组
    new_install_proxy_exec_ip: str = None  # 选取其中一台master作为部署 Proxy 的 IP
    start_port: int = None
    cluster_id: str = None
    redis_act_payload: Optional[Any] = None  # 代表获取payload参数的类

    def cal_twemproxy_serveres(self, name) -> list:
        """
        计算twemproxy的servers 列表
        - redisip:redisport:1 admin beginSeg-endSeg 1
        "servers": ["1.1.1.1:30000  xxx 0-219999 1","1.1.1.1:30001  xxx 220000-419999 1"]
        """
        shard_num = self.shard_num
        redis_list = self.new_master_ips
        name = name

        inst_num = self.inst_num
        seg_num = DEFAULT_TWEMPROXY_SEG_TOTOL_NUM // shard_num
        seg_no = 0

        #  计算分片
        servers = []
        for ip in redis_list:
            for inst_no in range(0, inst_num):
                port = DEFAULT_REDIS_START_PORT + inst_no
                begin_seg = seg_no * seg_num
                end_seg = seg_num * (seg_no + 1) - 1
                if inst_no == inst_num - 1 and end_seg != DEFAULT_TWEMPROXY_SEG_TOTOL_NUM:
                    end_seg = DEFAULT_TWEMPROXY_SEG_TOTOL_NUM - 1
                seg_no = seg_no + 1
                servers.append("{}:{} {} {}-{} {}".format(ip, port, name, begin_seg, end_seg, 1))
        return servers

    @staticmethod
    def get_redis_master_var_name() -> str:
        return "new_master_ips"

    @staticmethod
    def get_proxy_exec_ip_var_name() -> str:
        return "new_install_proxy_exec_ip"
