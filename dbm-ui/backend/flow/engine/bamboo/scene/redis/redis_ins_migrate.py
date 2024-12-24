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

import logging.config
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import DEFAULT_LAST_IO_SECOND_AGO, DEFAULT_MASTER_DIFF_TIME, DEPENDENCIES_PLUGINS, SyncType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import (
    RedisBatchInstallAtomJob,
    RedisBatchShutdownAtomJob,
    RedisClusterSwitchAtomJob,
    RedisMakeSyncAtomJob,
)
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.install_nodeman_plugin import (
    InstallNodemanPluginServiceComponent,
)
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs, InstallNodemanPluginKwargs
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")


class RedisSingleInsMigrateFlow(object):
    """
    redis集群选定实例迁移

    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def __pre_check(self) -> dict:
        """
        检查参数
        1、新机器端口是否冲突
        2、新机器主从是否一致
        3、新机器版本是否一致
        4、机器角色是否混用
        """
        machine_ports = defaultdict(list)
        src_master_list = defaultdict(list)
        machine_link = {}
        new_db_version = {}
        cluster_type_map = {}
        slave_ip_list = []
        master_ip_list = []
        machine_spec_dict = {}
        for info in self.data["infos"]:
            cluster = Cluster.objects.get(id=info["cluster_id"], bk_biz_id=self.data["bk_biz_id"])
            origin_db_version = cluster.major_version
            master = info["dest_master"]
            slave = info["dest_slave"]
            version = info.get("db_version") or origin_db_version
            src_master = info["src_master"]
            port = int(src_master.split(IP_PORT_DIVIDER)[1])

            if master in slave_ip_list:
                raise Exception(_("{} 不能既是master又是slave".format(master)))
            if slave in master_ip_list:
                raise Exception(_("{} 不能既是master又是slave".format(slave)))

            # 之前没遍历过这个ip
            if master not in new_db_version:
                new_db_version[master] = version
                machine_link[master] = slave
                master_ip_list.append(master)
                slave_ip_list.append(slave)
                machine_spec_dict[master] = info["resource_spec"]["master"]
                machine_spec_dict[slave] = info["resource_spec"]["slave"]
                cluster_type_map[master] = cluster.cluster_type

            else:
                if version != new_db_version[master]:
                    raise Exception(_("{}:db_version:{}不一致".format(master, version)))
                if port in machine_ports[master]:
                    raise Exception(_("{}:port:{}冲突".format(master, port)))
                if slave != machine_link[master]:
                    raise Exception(_("{}存在不同slave".format(master)))
                if cluster_type_map[master] != cluster.cluster_type:
                    raise Exception(_("{}存在不同cluster_type".format(master)))

            machine_ports[master].append(port)

            # 获取源实例的slave实例
            master_obj = cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value)[0]
            old_master_ip = master_obj.machine.ip
            if old_master_ip != src_master.split(IP_PORT_DIVIDER)[0]:
                raise Exception(_("{}和集群{}不匹配".format(master, cluster.immute_domain)))
            if master_obj.port != port:
                raise Exception(_("{}端口不匹配, 传参为{}, 实际端口为{}".format(cluster.immute_domain, master_obj.port, port)))

            old_slave_ip = master_obj.as_ejector.get().receiver.machine.ip

            # 默认主从实例的端口是一致的
            src_master_list[master].append(
                {
                    "old_master_ip": old_master_ip,
                    "old_slave_ip": old_slave_ip,
                    "port": port,
                    "cluster_id": info["cluster_id"],
                    "cluster_name": cluster.name,
                    "origin_db_version": origin_db_version,
                    "immute_domain": cluster.immute_domain,
                }
            )

        return {
            # 新机器主从机器对应关系
            "repl_dict": machine_link,
            # 新master机器对应的源实例相关信息列表
            "src_master_info": dict(src_master_list),
            # 新机器对应版本
            "new_db_version": new_db_version,
            # 新机器对应规格
            "machine_spec_dict": machine_spec_dict,
            "cluster_type_map": cluster_type_map,
        }

    def get_redis_install_sub_pipelines(self, act_kwargs, master_ip, slave_ip, spec_info, src_master_info) -> list:
        install_redis_sub_pipeline = []
        port = src_master_info["port"]
        act_kwargs.exec_ip = master_ip
        act_kwargs.cluster["immute_domain"] = src_master_info["immute_domain"]
        act_kwargs.cluster["origin_db_version"] = src_master_info["origin_db_version"]
        install_master_redis_params = {
            "meta_role": InstanceRole.REDIS_MASTER.value,
            "start_port": port,
            "ip": master_ip,
            "ports": [port],
            "instance_numb": 1,
            "spec_id": spec_info[master_ip]["id"],
            "spec_config": spec_info[master_ip],
            # 老实例的db版本，主要用来获取配置
            "origin_db_version": src_master_info["origin_db_version"],
        }
        install_redis_sub_pipeline.append(
            RedisBatchInstallAtomJob(
                self.root_id,
                self.data,
                act_kwargs,
                install_master_redis_params,
                to_install_dbmon=True,
                to_trans_files=False,
                to_install_puglins=False,
            )
        )

        act_kwargs.exec_ip = slave_ip
        install_slave_redis_params = {
            "meta_role": InstanceRole.REDIS_SLAVE.value,
            "start_port": port,
            "ip": slave_ip,
            "ports": [port],
            "instance_numb": 1,
            "spec_id": spec_info[slave_ip]["id"],
            "spec_config": spec_info[slave_ip],
            "origin_db_version": src_master_info["origin_db_version"],
        }
        install_redis_sub_pipeline.append(
            RedisBatchInstallAtomJob(
                self.root_id,
                self.data,
                act_kwargs,
                install_slave_redis_params,
                to_install_dbmon=True,
                to_trans_files=False,
                to_install_puglins=False,
            )
        )

        return install_redis_sub_pipeline

    def generate_sync_relation(self, act_kwargs, new_master_ip, new_slave_ip, src_master_list) -> list:
        """
        后面有空处理下，按照new_master-old_master来聚合port
        """
        sync_relations = []
        for src_master_info in src_master_list:
            port = src_master_info["port"]
            old_master_ip = src_master_info["old_master_ip"]
            old_slave_ip = src_master_info["old_slave_ip"]

            sync_relations.append(
                {
                    "sync_type": act_kwargs.cluster["sync_type"],
                    "origin_1": old_master_ip,
                    "origin_2": old_slave_ip,
                    "sync_dst1": new_master_ip,
                    "sync_dst2": new_slave_ip,
                    "ins_link": [{"origin_1": port, "origin_2": port, "sync_dst1": port, "sync_dst2": port}],
                }
            )

        return sync_relations

    def redis_single_ins_migrate_flow(self):
        # 检查参数
        # 初始化需要信息(slave_ins/domain_name)
        # 安装实例
        # 建立主从关系
        # 切换
        # 下架老实例
        # 更新dbmon
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        info = self.__pre_check()

        sub_pipelines = []
        for master_ip, slave_ip in info["repl_dict"].items():
            all_ip = [master_ip, slave_ip]
            db_version = info["new_db_version"][master_ip]
            src_master_list = info["src_master_info"][master_ip]

            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.is_update_trans_data = True
            act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]
            # 初始化配置
            act_kwargs.cluster["db_version"] = db_version
            act_kwargs.cluster["sync_type"] = SyncType.SYNC_MMS.value
            act_kwargs.cluster["bk_biz_id"] = self.data["bk_biz_id"]
            act_kwargs.cluster["bk_cloud_id"] = self.data["bk_cloud_id"]
            act_kwargs.cluster["cluster_type"] = info["cluster_type_map"][master_ip]
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            sub_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            # 下发介质包
            trans_files = GetFileList(db_type=DBType.Redis)
            act_kwargs.file_list = trans_files.redis_cluster_apply_backend(db_version)
            act_kwargs.exec_ip = all_ip
            sub_pipeline.add_act(
                act_name=_("Redis-{}-下发介质包").format(all_ip),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 初始化插件
            act_kwargs.get_redis_payload_func = RedisActPayload.get_sys_init_payload.__name__
            sub_pipeline.add_act(
                act_name=_("Redis-{}-初始化机器").format(all_ip),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            acts_list = []
            acts_list.append(
                {
                    "act_name": _("Redis-{}-安装backup-client工具").format(all_ip),
                    "act_component_code": DownloadBackupClientComponent.code,
                    "kwargs": asdict(
                        DownloadBackupClientKwargs(
                            bk_cloud_id=self.data["bk_cloud_id"],
                            bk_biz_id=int(self.data["bk_biz_id"]),
                            download_host_list=all_ip,
                        ),
                    ),
                }
            )
            for plugin_name in DEPENDENCIES_PLUGINS:
                acts_list.append(
                    {
                        "act_name": _("安装[{}]插件".format(plugin_name)),
                        "act_component_code": InstallNodemanPluginServiceComponent.code,
                        "kwargs": asdict(
                            InstallNodemanPluginKwargs(
                                bk_cloud_id=int(self.data["bk_cloud_id"]), ips=all_ip, plugin_name=plugin_name
                            )
                        ),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 密码可能不一致 ，需要能够按照端口安装Redis实例
            src_sub_pipelines = []
            for src_master_info in src_master_list:
                src_sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
                act_kwargs.cluster["cluster_name"] = src_master_info["cluster_name"]
                src_sub_pipeline.add_parallel_sub_pipeline(
                    self.get_redis_install_sub_pipelines(
                        act_kwargs, master_ip, slave_ip, info["machine_spec_dict"], src_master_info
                    )
                )

                # 建立同步
                port = src_master_info["port"]
                sync_params = {
                    "sync_type": act_kwargs.cluster["sync_type"],
                    "origin_1": src_master_info["old_master_ip"],
                    "origin_2": src_master_info["old_slave_ip"],
                    "sync_dst1": master_ip,
                    "sync_dst2": slave_ip,
                    "ins_link": [{"origin_1": port, "origin_2": port, "sync_dst1": port, "sync_dst2": port}],
                }
                src_sub_pipeline.add_sub_pipeline(
                    RedisMakeSyncAtomJob(self.root_id, self.data, act_kwargs, sync_params)
                )

                # 执行切换
                act_kwargs.cluster["cluster_id"] = src_master_info["cluster_id"]
                act_kwargs.cluster["switch_condition"] = {
                    "is_check_sync": True,  # 强制切换
                    "slave_master_diff_time": DEFAULT_MASTER_DIFF_TIME,
                    "last_io_second_ago": DEFAULT_LAST_IO_SECOND_AGO,
                    "can_write_before_switch": True,
                    "sync_type": act_kwargs.cluster["sync_type"],
                }
                sub_builder = RedisClusterSwitchAtomJob(self.root_id, self.data, act_kwargs, [sync_params])
                src_sub_pipeline.add_sub_pipeline(sub_flow=sub_builder)

                src_sub_pipeline.add_act(act_name=_("Redis-人工确认"), act_component_code=PauseComponent.code, kwargs={})

                # 下架老实例
                redis_shutdown_sub_pipelines = []
                old_ips = [src_master_info["old_master_ip"], src_master_info["old_slave_ip"]]
                for ip in old_ips:
                    params = {"ip": ip, "ports": [port], "ignore_ips": old_ips, "force_shutdown": True}
                    redis_shutdown_sub_pipelines.append(
                        RedisBatchShutdownAtomJob(self.root_id, self.data, act_kwargs, params)
                    )
                src_sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=redis_shutdown_sub_pipelines)

                src_sub_pipelines.append(
                    src_sub_pipeline.build_sub_process(sub_name=_("{}同步子流程").format(src_master_info["cluster_name"]))
                )
                sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=src_sub_pipelines)

                if src_master_info["origin_db_version"] != db_version:  # 更新元数据中集群版本
                    act_kwargs.cluster["cluster_ids"] = [src_master_info["cluster_id"]]
                    act_kwargs.cluster["db_version"] = db_version
                    act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_cluster_version_update.__name__
                    sub_pipeline.add_act(
                        act_name=_("Redis-元数据更新集群版本"),
                        act_component_code=RedisDBMetaComponent.code,
                        kwargs=asdict(act_kwargs),
                    )

                    # 更新dbconfig中版本信息
                    act_kwargs.cluster["cluster_domain"] = src_master_info["immute_domain"]
                    act_kwargs.cluster["current_version"] = db_version
                    act_kwargs.cluster["target_version"] = src_master_info["origin_db_version"]

                    act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_version_update_dbconfig.__name__
                    sub_pipeline.add_act(
                        act_name=_("{}-dbconfig更新版本").format(src_master_info["immute_domain"]),
                        act_component_code=RedisDBMetaComponent.code,
                        kwargs=asdict(act_kwargs),
                    )

                # 刷新dbmon
                acts_list = []
                for ip in [master_ip, slave_ip, src_master_info["old_master_ip"], src_master_info["old_slave_ip"]]:
                    act_kwargs.exec_ip = ip
                    act_kwargs.cluster["ip"] = ip
                    act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install_list_new.__name__
                    acts_list.append(
                        {
                            "act_name": _("{}-重装bkdbmon").format(ip),
                            "act_component_code": ExecuteDBActuatorScriptComponent.code,
                            "kwargs": asdict(act_kwargs),
                        }
                    )
                sub_pipeline.add_parallel_acts(acts_list)
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("主从实例迁移至{}").format(master_ip)))

        redis_pipeline.add_parallel_sub_pipeline(sub_pipelines)
        redis_pipeline.run_pipeline()
