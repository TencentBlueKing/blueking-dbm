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
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, Machine
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

# {
#     "bk_biz_id": 10,
#     "bk_cloud_id": 0,
#     "uid": "2022051612120001",
#     "created_by":"admin",
#     "ticket_type":"REDIS_SINGLE_INS_MIGRATE",
#     "infos":[
#         {
#           "src_cluster":[
#               {
#                   "cluster_id": "257",
#                   "master_ins": "1.1.1.1:30005",
#                   "slave_ins":"1.1.1.2:30005"
#               },{
#                   "cluster_id": "258",
#                   "master_ins": "1.1.1.1:30006",
#                   "slave_ins":"1.1.1.2:30006"
#               }
#           ],
#           "db_version":"Redis-6",
#           "dest_master": "2.2.2.1",
#           "dest_slave": "2.2.2.2",
#           "resource_spec":{
#                       ....
#           }
#         },
#         {
#           "src_cluster":[
#               {
#                   "cluster_id": "259",
#                   "master_ins": "1.1.1.1:30007",
#                   "slave_ins":"1.1.1.2:30007"
#               }
#           ],
#           "db_version":"Redis-6",
#           "dest_master": "2.2.2.3",
#           "dest_slave": "2.2.2.4",
#           "resource_spec":{
#               ...
#           }
#         }
#     ]
# }


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

    def __pre_check(self, info) -> dict:
        """
        参数检查：
            1、端口是否有冲突
            2、cluster_type是否一致
            3、传参和实际ip是否一致
            4、检查是否与目标端IP端口冲突
        数据整理：
            1、安装端口list
            2、部署版本
            3、源实例版本、映射 关系
        """
        # TODO 目前是从资源池获取，先判断目标IP是否被使用。 后续视情况是否改成机器合并场景
        m = Machine.objects.filter(ip__in=[info["dest_master"], info["dest_slave"]]).values("ip")
        if len(m) != 0:
            raise Exception("[{}] is used.".format(m))

        target_cluster_type = ""
        src_ports = []
        src_master_list = []
        old_master_slave = {}
        src_ips = set()

        for ins in info["src_cluster"]:
            cluster_id = ins["cluster_id"]
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=self.data["bk_biz_id"])
            cluster_type = cluster.cluster_type
            master_obj = cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value)[0]
            meta_old_master_ip = master_obj.machine.ip
            meta_old_slave_ip = master_obj.as_ejector.get().receiver.machine.ip
            meta_port = master_obj.port

            if target_cluster_type != "" and target_cluster_type != cluster_type:
                raise Exception(_("源端实例类型不一致，请先统一类型后再迁移"))

            old_master_ins = ins["master_ins"]
            old_slave_ins = ins["slave_ins"]
            if old_master_ins.split(IP_PORT_DIVIDER)[0] != meta_old_master_ip:
                raise Exception(_("源端实例IP{}与集群{}元数据{}不一致，不支持迁移", old_master_ins, cluster_id, meta_old_master_ip))
            if old_slave_ins.split(IP_PORT_DIVIDER)[0] != meta_old_slave_ip:
                raise Exception(_("源端实例IP{}与集群{}元数据{}不一致，不支持迁移", old_slave_ins, cluster_id, meta_old_slave_ip))

            port = int(old_master_ins.split(IP_PORT_DIVIDER)[1])
            if port != meta_port:
                raise Exception(_("源端实例port{}与集群{}元数据{}不一致，不支持迁移", port, cluster_id, meta_port))
            if port in src_ports:
                raise Exception(_("源端实例端口{}冲突，不支持迁移", port))

            if meta_old_master_ip in old_master_slave:
                if old_master_slave[meta_old_master_ip] != meta_old_slave_ip:
                    raise Exception(_("{}存在不同slave".format(meta_old_master_ip)))
            else:
                old_master_slave[meta_old_master_ip] = meta_old_slave_ip

            src_ports.append(port)
            target_cluster_type = cluster.cluster_type

            # 默认主从实例的端口是一致的
            src_master_list.append(
                {
                    "old_master_ip": meta_old_master_ip,
                    "old_slave_ip": meta_old_slave_ip,
                    "port": port,
                    "cluster_id": cluster_id,
                    "cluster_name": cluster.name,
                    "origin_db_version": cluster.major_version,
                    "immute_domain": cluster.immute_domain,
                }
            )
            src_ips.add(meta_old_master_ip)
            src_ips.add(meta_old_slave_ip)

        return {
            "src_ips": list(src_ips),
            "src_master_list": src_master_list,
            "cluster_type": target_cluster_type,
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
            "spec_id": spec_info["id"],
            "spec_config": spec_info,
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
            "spec_id": spec_info["id"],
            "spec_config": spec_info,
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
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        # 单行记录，目标机器是同一台机器的迁移
        sub_pipelines = []
        for info in self.data["infos"]:
            """
            0、初始化配置，下发介质
            1、安装实例
            2、主从复制
            3、切换
            4、下架
            """
            migrate_data = self.__pre_check(info)
            dest_master_ip = info["dest_master"]
            dest_slave_ip = info["dest_slave"]
            dest_ips = [dest_master_ip, dest_slave_ip]
            db_version = info["db_version"]
            cluster_type = migrate_data["cluster_type"]
            src_master_list = migrate_data["src_master_list"]

            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.is_update_trans_data = True
            act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]
            # 初始化配置
            act_kwargs.cluster["db_version"] = db_version
            act_kwargs.cluster["sync_type"] = SyncType.SYNC_MMS.value
            act_kwargs.cluster["bk_biz_id"] = self.data["bk_biz_id"]
            act_kwargs.cluster["bk_cloud_id"] = self.data["bk_cloud_id"]
            act_kwargs.cluster["cluster_type"] = cluster_type

            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

            sub_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            # 下发介质包
            trans_files = GetFileList(db_type=DBType.Redis)
            act_kwargs.file_list = trans_files.redis_cluster_apply_backend(db_version)
            act_kwargs.exec_ip = dest_ips
            sub_pipeline.add_act(
                act_name=_("Redis-{}-下发介质包").format(dest_ips),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 初始化插件
            act_kwargs.get_redis_payload_func = RedisActPayload.get_sys_init_payload.__name__
            sub_pipeline.add_act(
                act_name=_("Redis-{}-初始化机器").format(dest_ips),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            acts_list = []
            acts_list.append(
                {
                    "act_name": _("Redis-{}-安装backup-client工具").format(dest_ips),
                    "act_component_code": DownloadBackupClientComponent.code,
                    "kwargs": asdict(
                        DownloadBackupClientKwargs(
                            bk_cloud_id=self.data["bk_cloud_id"],
                            bk_biz_id=int(self.data["bk_biz_id"]),
                            download_host_list=dest_ips,
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
                                bk_cloud_id=int(self.data["bk_cloud_id"]), ips=dest_ips, plugin_name=plugin_name
                            )
                        ),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 密码可能不一致 ，按照端口安装Redis实例
            src_sub_pipelines = []
            for src_master_info in src_master_list:
                src_sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
                act_kwargs.cluster["cluster_name"] = src_master_info["cluster_name"]
                src_sub_pipeline.add_parallel_sub_pipeline(
                    self.get_redis_install_sub_pipelines(
                        act_kwargs, dest_master_ip, dest_slave_ip, info["resource_spec"], src_master_info
                    )
                )

                # 建立同步
                port = src_master_info["port"]
                sync_params = {
                    "sync_type": act_kwargs.cluster["sync_type"],
                    "origin_1": src_master_info["old_master_ip"],
                    "origin_2": src_master_info["old_slave_ip"],
                    "sync_dst1": dest_master_ip,
                    "sync_dst2": dest_slave_ip,
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

                if src_master_info["origin_db_version"] != db_version:  # 更新元数据中集群版本
                    act_kwargs.cluster["cluster_ids"] = [src_master_info["cluster_id"]]
                    act_kwargs.cluster["db_version"] = db_version
                    act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_cluster_version_update.__name__
                    src_sub_pipeline.add_act(
                        act_name=_("Redis-元数据更新集群版本"),
                        act_component_code=RedisDBMetaComponent.code,
                        kwargs=asdict(act_kwargs),
                    )

                    # 更新dbconfig中版本信息
                    act_kwargs.cluster["cluster_domain"] = src_master_info["immute_domain"]
                    act_kwargs.cluster["current_version"] = db_version
                    act_kwargs.cluster["target_version"] = src_master_info["origin_db_version"]

                    act_kwargs.get_redis_payload_func = RedisActPayload.redis_cluster_version_update_dbconfig.__name__
                    src_sub_pipeline.add_act(
                        act_name=_("{}-dbconfig更新版本").format(src_master_info["immute_domain"]),
                        act_component_code=RedisDBMetaComponent.code,
                        kwargs=asdict(act_kwargs),
                    )

                src_sub_pipelines.append(
                    src_sub_pipeline.build_sub_process(sub_name=_("{}同步子流程").format(src_master_info["cluster_name"]))
                )
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=src_sub_pipelines)

            # 刷新dbmon
            acts_list = []
            for ip in [dest_master_ip, dest_slave_ip] + migrate_data["src_ips"]:
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
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("主从实例迁移至{}").format(dest_master_ip)))

        redis_pipeline.add_parallel_sub_pipeline(sub_pipelines)
        redis_pipeline.run_pipeline()
