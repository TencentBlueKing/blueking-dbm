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
import copy
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, Machine
from backend.flow.consts import (
    DEFAULT_PREDIXY_STANDALONE_SEG_TOTOL_NUM,
    DEFAULT_REDIS_START_PORT,
    ClusterStatus,
    DnsOpType,
)
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.redis.atom_jobs import ProxyBatchInstallAtomJob, RedisBatchInstallAtomJob
from backend.flow.plugins.components.collections.redis.dns_manage import RedisDnsManageComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.redis_update_version import RedisUpdateVersionComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext, DnsKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_util import add_summary_output_act, build_clb_polaris_apply_subs, check_domain

logger = logging.getLogger("flow")


class PredixyTendisPlusInsApplyFlow(object):
    """
    构建predixy+tendisplus主从模式集群申请流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def __pre_check(self, proxy_ips, master_ips, slave_ips, group_num, shard_num, servers, domain):
        """
        前置检查，检查传参
        """
        ips = proxy_ips + master_ips + slave_ips
        if len(set(ips)) != len(ips):
            raise Exception("have ip address has been used multiple times.")
        if len(master_ips) != len(slave_ips):
            raise Exception("master machine len != slave machine len.")
        if len(master_ips) != group_num:
            raise Exception("machine len != group_num.")
        # 主从模式：servers 只包含 master 节点（predixy 只路由到 master）
        if len(servers) != shard_num:
            raise Exception("servers len ({}) != shard_num ({}).".format(len(servers), shard_num))
        if shard_num % group_num != 0:
            raise Exception("shard_num ({}) % group_num ({}) != 0.".format(shard_num, group_num))
        if not check_domain(domain):
            raise Exception("domain[{}] is illegality.".format(domain))
        d = Cluster.objects.filter(immute_domain=domain).values("immute_domain")
        if len(d) != 0:
            raise Exception("domain [{}] is used.".format(domain))
        m = Machine.objects.filter(ip__in=ips).values("ip")
        if len(m) != 0:
            raise Exception("[{}] is used.".format(m))

    def cal_predixy_servers(self, ips, inst_num) -> list:
        """
        计算predixy的servers列表（仅master节点），每个实例分配等量的slot范围
        格式示例: ["x.x.x.1:30000 0-104999", "x.x.x.1:30001 105000-209999", ...]
        predixy配置格式为 "+ ip:port slot_start-slot_end"
        """
        MAX_SLOTS = DEFAULT_PREDIXY_STANDALONE_SEG_TOTOL_NUM
        total_inst = len(ips) * inst_num
        slots_per_inst = MAX_SLOTS // total_inst
        servers = []
        inst_idx = 0
        for ip in ips:
            for inst_no in range(0, inst_num):
                port = DEFAULT_REDIS_START_PORT + inst_no
                slot_start = inst_idx * slots_per_inst
                slot_end = (inst_idx + 1) * slots_per_inst - 1
                if inst_idx == total_inst - 1:
                    slot_end = MAX_SLOTS - 1
                servers.append("{}:{} {}-{}".format(ip, port, slot_start, slot_end))
                inst_idx += 1
        return servers

    def deploy_predixy_tendisplus_ins_flow(self):
        """
        部署predixy+tendisplus主从模式集群
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.is_update_trans_data = True
        act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]

        proxy_ips = [info["ip"] for info in self.data["nodes"]["proxy"]]
        master_ips = [info["master"]["ip"] for info in self.data["nodes"]["backend_group"]]
        slave_ips = [info["slave"]["ip"] for info in self.data["nodes"]["backend_group"]]

        # 每台机器需要部署的实例数量
        ins_num = self.data["shard_num"] // self.data["group_num"]
        ports = list(map(lambda i: i + DEFAULT_REDIS_START_PORT, range(ins_num)))
        # predixy的servers只指向master节点
        servers = self.cal_predixy_servers(master_ips, ins_num)

        self.__pre_check(
            proxy_ips,
            master_ips,
            slave_ips,
            self.data["group_num"],
            self.data["shard_num"],
            servers,
            self.data["domain_name"],
        )
        cluster_tpl = {
            "immute_domain": self.data["domain_name"],
            "cluster_type": self.data["cluster_type"],
            "db_version": self.data["db_version"],
            "bk_biz_id": self.data["bk_biz_id"],
            "bk_cloud_id": self.data["bk_cloud_id"],
            "created_by": self.data["created_by"],
            "cluster_name": self.data["cluster_name"],
        }

        # 步骤1：初始化配置
        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # 目前传参不允许传databases，默认databases为2（后续有可能放开）
        self.data["databases"] = 2
        # 步骤2：并行安装tendisplus主从实例（master + slave）
        params = {
            "instance_numb": ins_num,
            "ports": ports,
            "start_port": DEFAULT_REDIS_START_PORT,
            "requirepass": self.data["redis_pwd"],
            "databases": self.data["databases"],
            "maxmemory": self.data["maxmemory"],
        }
        sub_pipelines = []
        for ip in master_ips:
            act_kwargs.cluster = copy.deepcopy(cluster_tpl)

            params["ip"] = ip
            params["spec_id"] = int(self.data["resource_spec"]["master"]["id"])
            params["spec_config"] = self.data["resource_spec"]["master"]
            params["meta_role"] = InstanceRole.REDIS_MASTER.value
            sub_builder = RedisBatchInstallAtomJob(self.root_id, self.data, act_kwargs, params, to_install_dbmon=False)
            sub_pipelines.append(sub_builder)
        for ip in slave_ips:
            act_kwargs.cluster = copy.deepcopy(cluster_tpl)

            params["ip"] = ip
            params["spec_id"] = int(self.data["resource_spec"]["slave"]["id"])
            params["spec_config"] = self.data["resource_spec"]["slave"]
            params["meta_role"] = InstanceRole.REDIS_SLAVE.value
            sub_builder = RedisBatchInstallAtomJob(self.root_id, self.data, act_kwargs, params, to_install_dbmon=False)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 步骤3：建立主从关系（slaveof，非cluster meet）
        bacth_pairs = []
        act_kwargs.cluster = copy.deepcopy(cluster_tpl)
        common = {
            "master_start_port": DEFAULT_REDIS_START_PORT,
            "master_inst_num": ins_num,
            "master_auth": self.data["redis_pwd"],
            "slave_start_port": DEFAULT_REDIS_START_PORT,
            "slave_inst_num": ins_num,
            "slave_password": self.data["redis_pwd"],
        }
        for _index, master_ip in enumerate(master_ips):
            slave_ip = slave_ips[_index]
            bp = copy.deepcopy(common)
            bp["master_ip"] = master_ip
            bp["slave_ip"] = slave_ip
            bacth_pairs.append(bp)
        act_kwargs.cluster["bacth_pairs"] = bacth_pairs
        act_kwargs.exec_ip = master_ips[0]
        act_kwargs.get_redis_payload_func = RedisActPayload.get_slaveof_redis_payload.__name__
        redis_pipeline.add_act(
            act_name=_("建立主从关系"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 步骤4：写入主从复制元数据
        bacth_pairs = []
        for _index, master_ip in enumerate(master_ips):
            slave_ip = slave_ips[_index]
            bacth_pairs.append({"master_ip": master_ip, "slave_ip": slave_ip})
        act_kwargs.cluster = {
            "bacth_pairs": bacth_pairs,
            "created_by": self.data["created_by"],
            "start_port": DEFAULT_REDIS_START_PORT,
            "inst_num": ins_num,
            "meta_func_name": RedisDBMeta.replicaof.__name__,
        }
        redis_pipeline.add_act(
            act_name=_("redis建立主从 元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 步骤5：并行安装predixy代理
        sub_pipelines = []
        params = {
            "spec_id": int(self.data["resource_spec"]["proxy"]["id"]),
            "spec_config": self.data["resource_spec"]["proxy"],
            "redis_pwd": self.data["redis_pwd"],
            "proxy_pwd": self.data["proxy_pwd"],
            "proxy_admin_pwd": self.data["proxy_admin_pwd"],
            "proxy_port": self.data["proxy_port"],
            "databases": self.data["databases"],
            "servers": servers,
        }
        for ip in proxy_ips:
            act_kwargs.cluster = copy.deepcopy(cluster_tpl)

            params["ip"] = ip
            sub_builder = ProxyBatchInstallAtomJob(self.root_id, self.data, act_kwargs, params, to_install_dbmon=False)
            sub_pipelines.append(sub_builder)
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 步骤6：建立集群元数据（无storages，主从模式不需要）
        act_kwargs.cluster = {
            "new_proxy_ips": proxy_ips,
            "servers": servers,
            "proxy_port": self.data["proxy_port"],
            "bk_biz_id": self.data["bk_biz_id"],
            "bk_cloud_id": self.data["bk_cloud_id"],
            "cluster_type": self.data["cluster_type"],
            "cluster_name": self.data["cluster_name"],
            "cluster_alias": self.data["cluster_alias"],
            "db_version": self.data["db_version"],
            "immute_domain": self.data["domain_name"],
            "created_by": self.data["created_by"],
            "region": self.data.get("city_code"),
            "meta_func_name": RedisDBMeta.redis_segment_make_cluster.__name__,
            "disaster_tolerance_level": self.data.get("disaster_tolerance_level", AffinityEnum.CROS_SUBZONE),
            "zone_list": self.data.get("zone_list", []),
        }
        redis_pipeline.add_act(
            act_name=_("建立集群 元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 集群部署成功后，根据单据传参决定是否给集群构建创建clb / 北极星的子流程，与后面的注册域名等节点并行执行
        clb_polaris_subs = build_clb_polaris_apply_subs(
            root_id=self.root_id,
            data=self.data,
            bk_biz_id=self.data["bk_biz_id"],
            domain_name=self.data["domain_name"],
            creator=self.data["created_by"],
            apply_clb=self.data.get("apply_clb", False),
            apply_polaris=self.data.get("apply_polaris", False),
        )

        # 步骤7：并行回写配置
        acts_list = list(clb_polaris_subs)

        # 回写Redis配置（主从模式不设置cluster-enabled）
        act_kwargs.cluster = {
            "conf": {
                "databases": str(self.data["databases"]),
                "cluster-enabled": ClusterStatus.REDIS_CLUSTER_NO,
            },
            "db_version": self.data["db_version"],
            "domain_name": self.data["domain_name"],
        }
        act_kwargs.get_redis_payload_func = RedisActPayload.set_redis_config.__name__
        acts_list.append(
            {
                "act_name": _("回写集群配置[Redis]"),
                "act_component_code": RedisConfigComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )

        # 回写Predixy配置（使用文件一的predixy介质组件：独立admin密码）
        act_kwargs.cluster = {
            "conf": {
                "databases": str(self.data["databases"]),
                "port": str(self.data["proxy_port"]),
            },
            "pwd_conf": {
                "proxy_pwd": self.data["proxy_pwd"],
                "proxy_admin_pwd": self.data["proxy_admin_pwd"],
                "redis_pwd": self.data["redis_pwd"],
            },
            "domain_name": self.data["domain_name"],
        }
        act_kwargs.get_redis_payload_func = RedisActPayload.set_proxy_config.__name__
        acts_list.append(
            {
                "act_name": _("回写集群配置[Predixy]"),
                "act_component_code": RedisConfigComponent.code,
                "kwargs": asdict(act_kwargs),
            }
        )

        # 申请了clb时，主域名会由clb子流程绑定到clb ip（domain_bind_clb_ip），不再将主域名注册到proxy ip
        if not self.data.get("apply_clb", False):
            dns_kwargs = DnsKwargs(
                dns_op_type=DnsOpType.CREATE,
                add_domain_name=self.data["domain_name"],
                dns_op_exec_port=self.data["proxy_port"],
            )
            act_kwargs.exec_ip = proxy_ips
            acts_list.append(
                {
                    "act_name": _("proxy注册域名"),
                    "act_component_code": RedisDnsManageComponent.code,
                    "kwargs": {**asdict(act_kwargs), **asdict(dns_kwargs)},
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        # 步骤8：后置安装dbmon监控
        acts_list = []
        for ip in master_ips + slave_ips + proxy_ips:
            act_kwargs.exec_ip = ip
            act_kwargs.cluster = {"ip": ip}
            act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install_list_new.__name__
            acts_list.append(
                {
                    "act_name": _("{}-安装bkdbmon").format(ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=acts_list)

        # 步骤9：更新集群版本
        act_kwargs.cluster["update_all"] = True
        act_kwargs.cluster["domain_name"] = self.data["domain_name"]
        act_kwargs.cluster["bk_biz_id"] = self.data["bk_biz_id"]
        redis_pipeline.add_act(
            act_name=_("{}-更新版本").format(self.data["domain_name"]),
            act_component_code=RedisUpdateVersionComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 写入集群信息摘要(地区/域名/端口/CLB/北极星)，供前端"执行摘要"展示
        add_summary_output_act(
            redis_pipeline=redis_pipeline,
            bk_biz_id=self.data["bk_biz_id"],
            domain_name=self.data["domain_name"],
            region=self.data.get("city_code", ""),
            proxy_port=self.data["proxy_port"],
            apply_clb=self.data.get("apply_clb", False),
            apply_polaris=self.data.get("apply_polaris", False),
        )

        redis_pipeline.run_pipeline()
