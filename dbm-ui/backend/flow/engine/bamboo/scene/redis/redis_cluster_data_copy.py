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
import ast
import base64
import logging.config
from collections import defaultdict
from dataclasses import asdict

from django.db.models import Q
from django.utils.translation import ugettext as _

from backend.components import DRSApi
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceRole, InstanceStatus
from backend.db_meta.models import AppCache, Cluster
from backend.db_package.models import Package
from backend.db_services.redis.redis_dts.constants import (
    DTS_SWITCH_PREDIXY_PRECHECK,
    DTS_SWITCH_TWEMPROXY_PRECHECK,
    SERVERS_ADD_ETC_HOSTS,
    SERVERS_DEL_ETC_HOSTS,
)
from backend.db_services.redis.redis_dts.enums import (
    DtsBillType,
    DtsCopyType,
    DtsDataCheckFreq,
    DtsDataCheckType,
    DtsOnlineSwitchType,
    DtsSyncDisconnReminderFreq,
    DtsSyncDisconnType,
    DtsWriteMode,
)
from backend.db_services.redis.redis_dts.models import TbTendisDTSJob, TbTendisDtsTask
from backend.db_services.redis.redis_dts.util import (
    complete_redis_dts_kwargs_dst_data,
    complete_redis_dts_kwargs_src_data,
    get_cluster_info_by_id,
    get_etc_hosts_lines_and_ips,
    is_in_incremental_sync,
)
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.db_services.redis.util import (
    is_predixy_proxy_type,
    is_redis_instance_type,
    is_tendisplus_instance_type,
    is_tendisssd_instance_type,
    is_twemproxy_proxy_type,
)
from backend.flow.consts import ConfigFileEnum, MediumEnum, StateType, WriteContextOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs.redis_dts import (
    redis_dst_cluster_backup_and_flush,
    redis_dts_data_copy_atom_job,
)
from backend.flow.models import FlowTree
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.exec_shell_script import ExecuteShellScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.redis_dts import (
    NewDstClusterCloseJobAndWatchStatusComponent,
    NewDstClusterFlushJobAndWatchStatusComponent,
    NewDstClusterInstallJobAndWatchStatusComponent,
    NewDstClusterShutdownJobAndWatchStatusComponent,
    NewDtsOnlineSwitchJobAndWatchStatusComponent,
    RedisDtsDisconnectSyncComponent,
)
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, RedisDtsContext, RedisDtsOnlineSwitchContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_proxy_util import check_cluster_proxy_backends_consistent
from backend.utils.time import datetime2str

logger = logging.getLogger("flow")


class RedisClusterDataCopyFlow(object):
    """
    redis集群数据复制
    """

    def __init__(self, root_id, data):
        self.root_id = root_id
        self.data = data

    def redis_cluster_data_copy_flow(self):
        self.data_copy_precheck()

        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        bk_biz_id = self.data["bk_biz_id"]
        write_mode = self.data["write_mode"]
        dts_copy_type = self.__get_dts_copy_type()
        sub_pipelines = []
        # redis_pipeline.add_act(act_name=_("Redis-人工确认"), act_component_code=PauseComponent.code, kwargs={})
        if self.data["ticket_type"] == DtsBillType.REDIS_CLUSTER_ROLLBACK_DATA_COPY.value:
            self.data["sync_disconnect_setting"] = {}
            self.data["sync_disconnect_setting"]["type"] = ""
            self.data["sync_disconnect_setting"]["reminder_frequency"] = ""

            # 回档实例数据回写 不用校验
            self.data["data_check_repair_setting"] = {}
            self.data["data_check_repair_setting"]["type"] = DtsDataCheckType.NO_CHECK_NO_REPAIR.value
            self.data["data_check_repair_setting"]["execution_frequency"] = ""

        for info in self.data["infos"]:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = RedisDtsContext.__name__
            act_kwargs.file_list = trans_files.redis_base()
            act_kwargs.is_update_trans_data = True
            act_kwargs.cluster = {}
            act_kwargs.cluster["dts_bill_type"] = self.data["ticket_type"]
            act_kwargs.cluster["dts_copy_type"] = dts_copy_type
            act_kwargs.cluster["info"] = info
            complete_redis_dts_kwargs_src_data(bk_biz_id, dts_copy_type, info, act_kwargs)
            complete_redis_dts_kwargs_dst_data(self.__get_dts_biz_id(info), dts_copy_type, "", info, act_kwargs)

            if (
                dts_copy_type != DtsCopyType.COPY_TO_OTHER_SYSTEM
                and write_mode == DtsWriteMode.FLUSHALL_AND_WRITE_TO_REDIS
            ):
                sub_pipeline.add_sub_pipeline(redis_dst_cluster_backup_and_flush(self.root_id, self.data, act_kwargs))

            etc_hosts_param = get_etc_hosts_lines_and_ips(bk_biz_id, dts_copy_type, info, None)

            # 添加/etc/hosts
            act_kwargs.exec_ip = etc_hosts_param["ip_list"]
            act_kwargs.write_op = WriteContextOpType.APPEND.value
            act_kwargs.cluster["shell_command"] = SERVERS_ADD_ETC_HOSTS.format(etc_hosts_param["etc_hosts_lines"])
            sub_pipeline.add_act(
                act_name=_("{}等添加etc_hosts").format(etc_hosts_param["ip_list"][0]),
                act_component_code=ExecuteShellScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 数据复制
            sub_pipeline.add_sub_pipeline(redis_dts_data_copy_atom_job(self.root_id, self.data, act_kwargs))

            if self.data["ticket_type"] == DtsBillType.REDIS_CLUSTER_ROLLBACK_DATA_COPY.value:
                act_kwargs.cluster["bill_id"] = int(self.data["uid"])
                act_kwargs.cluster["src_cluster"] = act_kwargs.cluster["src"]["cluster_addr"]
                act_kwargs.cluster["dst_cluster"] = act_kwargs.cluster["dst"]["cluster_addr"]
                sub_pipeline.add_act(
                    act_name=_("断开同步关系"),
                    act_component_code=RedisDtsDisconnectSyncComponent.code,
                    kwargs=asdict(act_kwargs),
                )

            # 删除/etc/hosts
            act_kwargs.exec_ip = etc_hosts_param["ip_list"]
            act_kwargs.write_op = WriteContextOpType.APPEND.value
            act_kwargs.cluster["shell_command"] = SERVERS_DEL_ETC_HOSTS.format(etc_hosts_param["etc_hosts_lines"])
            sub_pipeline.add_act(
                act_name=_("{}等删除etc_hosts").format(etc_hosts_param["ip_list"][0]),
                act_component_code=ExecuteShellScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_("数据复制:{}->{}").format(
                        act_kwargs.cluster["src"]["cluster_addr"], act_kwargs.cluster["dst"]["cluster_addr"]
                    )
                )
            )
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()

    def __get_dts_copy_type(self) -> str:
        if self.data["ticket_type"] in [
            DtsBillType.REDIS_CLUSTER_SHARD_NUM_UPDATE.value,
            DtsBillType.REDIS_CLUSTER_TYPE_UPDATE.value,
        ]:
            return self.data["ticket_type"]
        else:
            return self.data["dts_copy_type"]

    def __get_dts_biz_id(self, info: dict) -> int:
        if (
            self.data["ticket_type"] == DtsBillType.REDIS_CLUSTER_DATA_COPY
            and self.data["dts_copy_type"] == DtsCopyType.DIFF_APP_DIFF_CLUSTER
        ):
            return info["dst_bk_biz_id"]
        else:
            return self.data["bk_biz_id"]

    def data_copy_precheck(self):
        src_cluster_set: set = set()
        bk_biz_id = self.data["bk_biz_id"]
        dts_copy_type = self.__get_dts_copy_type()
        src_cluster: Cluster = None
        dst_cluster: Cluster = None
        for info in self.data["infos"]:
            if info["src_cluster"] in src_cluster_set:
                raise Exception(_("源集群{}重复了").format(info["src_cluster"]))
            src_cluster_set.add(info["src_cluster"])

            if dts_copy_type not in [
                DtsCopyType.USER_BUILT_TO_DBM.value,
                DtsCopyType.COPY_FROM_ROLLBACK_INSTANCE.value,
            ]:
                # 源集群是否存在
                try:
                    src_cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=int(info["src_cluster"]))
                except Cluster.DoesNotExist:
                    raise Exception("src_cluster {} does not exist".format(info["src_cluster"]))
                # 源集群是否每个running的master都有slave
                running_masters = src_cluster.storageinstance_set.filter(
                    status=InstanceStatus.RUNNING.value, instance_role=InstanceRole.REDIS_MASTER.value
                )
                for master in running_masters:
                    if not master.as_ejector or not master.as_ejector.first():
                        master_inst = "{}:{}".format(master.machine.ip, master.port)
                        raise Exception(_("源集群{}存在master:{}没有slave").format(info["src_cluster"], master_inst))

            if dts_copy_type != DtsCopyType.COPY_TO_OTHER_SYSTEM.value:
                try:
                    dst_cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=int(info["dst_cluster"]))
                except Cluster.DoesNotExist:
                    raise Exception("dst_cluster {} does not exist".format(info["dst_cluster"]))

            if dts_copy_type == DtsCopyType.COPY_FROM_ROLLBACK_INSTANCE.value:
                # 数据构造任务是否存在
                rollback_task: TbTendisRollbackTasks = None
                recovery_time = None
                try:
                    recovery_time = datetime2str(info["recovery_time_point"])
                    rollback_task = TbTendisRollbackTasks.objects.get(
                        temp_cluster_proxy=info["src_cluster"], recovery_time_point=recovery_time, destroyed_status=0
                    )
                except TbTendisRollbackTasks.DoesNotExist:
                    raise Exception(
                        "rollback task(src_cluster:{} recovery_time_point:{} \
                                     destroyed_status:0) does not exist".format(
                            info["src_cluster"], info["recovery_time_point"]
                        )
                    )
                # 数据构造临时集群是否可访问
                proxy_password_bytes = ast.literal_eval(rollback_task.temp_proxy_password)
                redis_password_bytes = ast.literal_eval(rollback_task.temp_redis_password)
                try:
                    DRSApi.redis_rpc(
                        {
                            "addresses": [rollback_task.temp_cluster_proxy],
                            "db_num": 0,
                            "password": base64.b64decode(proxy_password_bytes).decode("utf-8"),
                            "command": "ping",
                            "bk_cloud_id": dst_cluster.bk_cloud_id,
                        }
                    )
                except Exception as e:
                    raise Exception(
                        "rollback task(temp_cluster_proxy:{}) redis ping failed".format(
                            rollback_task.temp_cluster_proxy
                        )
                    )
                try:
                    DRSApi.redis_rpc(
                        {
                            "addresses": rollback_task.temp_instance_range,
                            "db_num": 0,
                            "password": base64.b64decode(redis_password_bytes).decode("utf-8"),
                            "command": "ping",
                            "bk_cloud_id": dst_cluster.bk_cloud_id,
                        }
                    )
                except Exception as e:
                    raise Exception(
                        _("数据构造临时集群存在 redis 访问失败的情况,临时集群 redis:{}").format(rollback_task.temp_instance_range)
                    )

    def __get_domain_prefix_by_cluster_type(self, cluster_type: str) -> str:
        if is_redis_instance_type(cluster_type):
            return "cache"
        elif is_tendisplus_instance_type(cluster_type):
            return "tendisplus"
        elif is_tendisssd_instance_type(cluster_type):
            return "ssd"
        return ""

    def get_dst_cluster_install_param(self, info: dict) -> dict:
        install_param = {}
        src_cluster_info = get_cluster_info_by_id(
            bk_biz_id=self.data["bk_biz_id"], cluster_id=int(info["src_cluster"])
        )
        app_info = AppCache.objects.get(bk_biz_id=self.data["bk_biz_id"])
        install_param["bk_biz_id"] = self.data["bk_biz_id"]
        install_param["bk_cloud_id"] = src_cluster_info["bk_cloud_id"]
        install_param["created_by"] = self.data["created_by"]
        install_param["shard_num"] = info["cluster_shard_num"]
        install_param["cluster_name"] = src_cluster_info["cluster_name"] + "migrate"
        install_param["cluster_alias"] = src_cluster_info["cluster_name"] + " shard num update"
        install_param["cluster_type"] = info.get("target_cluster_type", src_cluster_info["cluster_type"])
        install_param["src_cluster_type"] = src_cluster_info["cluster_type"]
        install_param["db_version"] = info.get("db_version", src_cluster_info["cluster_version"])
        install_param["src_db_version"] = src_cluster_info["cluster_version"]
        install_param["cluster_password"] = src_cluster_info["cluster_password"]
        install_param["redis_password"] = src_cluster_info["redis_password"]
        install_param["redis_databases"] = src_cluster_info["redis_databases"]
        install_param["max_disk"] = info["max_disk"]
        install_param["maxmemory"] = info["maxmemory"]
        install_param["region"] = src_cluster_info["region"]
        install_param["cluster_port"] = int(src_cluster_info["cluster_port"]) + 100
        domain_prefix = self.__get_domain_prefix_by_cluster_type(install_param["cluster_type"])
        install_param["cluster_domain"] = "{}{}.{}.{}.db".format(
            domain_prefix, install_param["cluster_port"], install_param["cluster_name"], app_info.db_app_abbr
        )
        install_param["proxy"] = info["proxy"]
        install_param["backend_group"] = info["backend_group"]
        install_param["resource_spec"] = info["resource_spec"]
        return install_param

    def get_db_versions_by_cluster_type(self, cluster_type: str) -> list:
        if is_redis_instance_type(cluster_type):
            ret = Package.objects.filter(db_type=DBType.Redis.value, pkg_type=MediumEnum.Redis.value).values_list(
                "version", flat=True
            )
            return list(ret)
        elif is_tendisplus_instance_type(cluster_type):
            ret = Package.objects.filter(db_type=DBType.Redis.value, pkg_type=MediumEnum.TendisPlus.value).values_list(
                "version", flat=True
            )
            return list(ret)
        elif is_tendisssd_instance_type(cluster_type):
            ret = Package.objects.filter(db_type=DBType.Redis.value, pkg_type=MediumEnum.TendisSsd.value).values_list(
                "version", flat=True
            )
            return list(ret)
        raise Exception("cluster_type:{} not a redis cluster type?".format(cluster_type))

    def shard_num_or_cluster_type_update_precheck(self):
        src_cluster_set: set = set()
        bk_biz_id = self.data["bk_biz_id"]
        for info in self.data["infos"]:
            if info["src_cluster"] in src_cluster_set:
                raise Exception(_("源集群{}重复了").format(info["src_cluster"]))
            src_cluster_set.add(info["src_cluster"])

            src_cluster: Cluster = None
            try:
                src_cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=int(info["src_cluster"]))
            except Cluster.DoesNotExist:
                raise Exception("src_cluster {} does not exist".format(info["src_cluster"]))

            if self.data["ticket_type"] == DtsBillType.REDIS_CLUSTER_SHARD_NUM_UPDATE.value:
                if info["current_shard_num"] == info["cluster_shard_num"]:
                    raise Exception(
                        "current_shard_num:{} == cluster_shard_num:{}".format(
                            info["current_shard_num"], info["cluster_shard_num"]
                        ),
                    )
                running_masters = src_cluster.storageinstance_set.filter(
                    status=InstanceStatus.RUNNING.value, instance_role=InstanceRole.REDIS_MASTER.value
                )
                if running_masters.count() == info["cluster_shard_num"]:
                    raise Exception(
                        "src_cluster:{} running_masters:{} == cluster_shard_num:{}".format(
                            src_cluster.immute_domain, running_masters.count(), info["cluster_shard_num"]
                        ),
                    )
                if info.get("db_version", "") != "":
                    if info["db_version"] not in self.get_db_versions_by_cluster_type(src_cluster.cluster_type):
                        raise Exception(
                            "src_cluster:{} db_version:{} not in src_cluster_type:{} db_versions:{}".format(
                                src_cluster.immute_domain,
                                info["db_version"],
                                src_cluster.cluster_type,
                                self.get_db_versions_by_cluster_type(src_cluster.cluster_type),
                            )
                        )
            elif self.data["ticket_type"] == DtsBillType.REDIS_CLUSTER_TYPE_UPDATE.value:
                if info["current_cluster_type"] == info["target_cluster_type"]:
                    raise Exception(
                        "current_cluster_type:{} == target_cluster_type:{}".format(
                            info["current_cluster_type"], info["target_cluster_type"]
                        ),
                    )
                if info["target_cluster_type"] == src_cluster.cluster_type:
                    raise Exception(
                        "target_cluster_type:{} == src_cluster:{} cluster_type:{}".format(
                            info["target_cluster_type"], src_cluster.immute_domain, src_cluster.cluster_type
                        ),
                    )
                if info.get("db_version", "") == "":
                    raise Exception("src_cluster:{} db_version is empty".format(info["src_cluster"]))
                if info["db_version"] not in self.get_db_versions_by_cluster_type(info["target_cluster_type"]):
                    raise Exception(
                        "src_cluster:{} db_version:{} not in target_cluster_type:{} db_versions:{}".format(
                            info["src_cluster"],
                            info["db_version"],
                            info["target_cluster_type"],
                            self.get_db_versions_by_cluster_type(info["target_cluster_type"]),
                        )
                    )
            # 检查所有 src proxys backends 一致
            check_cluster_proxy_backends_consistent(cluster_id=int(info["src_cluster"]), cluster_password="")

    def is_dst_cluster_installed(self, info: dict, taregt_param: dict) -> bool:
        """
        判断目标集群是否已经安装;
        如果集群存在,shard_num 和 密码都相同,则认为已经安装
        """
        cluster: Cluster = None
        try:
            cluster = Cluster.objects.get(bk_biz_id=taregt_param["bk_biz_id"], name=taregt_param["cluster_name"])
        except Cluster.DoesNotExist:
            return False
        running_masters = cluster.storageinstance_set.filter(
            status=InstanceStatus.RUNNING.value, instance_role=InstanceRole.REDIS_MASTER.value
        )
        if len(running_masters) != info["cluster_shard_num"]:
            logger.error(
                "target cluster {} installed,but shard_num:%{} != cluster_shard_num:{}".format(
                    taregt_param["cluster_name"], len(running_masters), info["cluster_shard_num"]
                )
            )
            raise Exception(
                "target cluster {} installed,but shard_num:%{} != cluster_shard_num:{}".format(
                    taregt_param["cluster_name"], len(running_masters), info["cluster_shard_num"]
                )
            )
        cluster_info = get_cluster_info_by_id(bk_biz_id=cluster.bk_biz_id, cluster_id=cluster.id)
        if cluster_info["cluster_password"] != taregt_param["cluster_password"]:
            logger.error(
                "target cluster {} installed,but proxy_password != target proxy_password".format(
                    taregt_param["cluster_name"]
                )
            )
            raise Exception(
                "target cluster {} installed,but proxy_password != target proxy_password".format(
                    taregt_param["cluster_name"]
                )
            )
        return True

    def shard_num_or_cluster_type_update_flow(self):
        self.shard_num_or_cluster_type_update_precheck()

        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        bk_biz_id = self.data["bk_biz_id"]
        dts_copy_type = self.__get_dts_copy_type()
        self.data["dts_copy_type"] = dts_copy_type
        self.data["write_mode"] = DtsWriteMode.DELETE_AND_WRITE_TO_REDIS.value
        self.data["sync_disconnect_setting"] = {}
        self.data["sync_disconnect_setting"]["type"] = DtsSyncDisconnType.KEEP_SYNC_WITH_REMINDER.value
        self.data["sync_disconnect_setting"]["reminder_frequency"] = DtsSyncDisconnReminderFreq.ONCE_DAILY.value
        # self.data["data_check_repair_setting"]["type"] = DtsDataCheckType.DATA_CHECK_AND_REPAIR.value
        self.data["data_check_repair_setting"]["execution_frequency"] = DtsDataCheckFreq.ONCE_AFTER_REPLICATION.value
        for info in self.data["infos"]:
            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = RedisDtsContext.__name__
            act_kwargs.is_update_trans_data = True
            act_kwargs.file_list = trans_files.redis_base()
            act_kwargs.cluster = {}
            act_kwargs.cluster["dts_bill_type"] = self.data["ticket_type"]
            act_kwargs.cluster["dts_copy_type"] = dts_copy_type
            dst_install_param = self.get_dst_cluster_install_param(info)
            act_kwargs.cluster["dst_install_param"] = dst_install_param
            act_kwargs.cluster["cluster_type"] = dst_install_param["src_cluster_type"]
            self.data["db_version"] = dst_install_param["src_db_version"]

            etc_hosts_param = get_etc_hosts_lines_and_ips(bk_biz_id, dts_copy_type, info, dst_install_param)

            data_copy_info = {
                "src_cluster": str(info["src_cluster"]),
                "dst_cluster": dst_install_param["cluster_domain"]
                + IP_PORT_DIVIDER
                + str(dst_install_param["cluster_port"]),
                "dst_cluster_password": dst_install_param["cluster_password"],
                "key_white_regex": "*",
                "key_black_regex": "",
            }
            complete_redis_dts_kwargs_src_data(bk_biz_id, dts_copy_type, info, act_kwargs)
            complete_redis_dts_kwargs_dst_data(
                self.__get_dts_biz_id(data_copy_info),
                dts_copy_type,
                dst_install_param["cluster_type"],
                data_copy_info,
                act_kwargs,
            )
            redis_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            dst_cluster_installed = self.is_dst_cluster_installed(info, dst_install_param)
            if not dst_cluster_installed:
                # 如果目标集群未安装,则安装
                redis_pipeline.add_act(
                    act_name=_("集群:{}安装任务并检测任务状态").format(dst_install_param["cluster_name"]),
                    act_component_code=NewDstClusterInstallJobAndWatchStatusComponent.code,
                    kwargs=asdict(act_kwargs),
                )
            else:
                # 如果目标集群已安装,则备份+清理
                # redis_pipeline.add_sub_pipeline(
                #     redis_dst_cluster_backup_and_flush(self.root_id, self.data, act_kwargs)
                # )
                redis_pipeline.add_act(
                    act_name=_("集群:{}清档任务并检测任务状态".format(act_kwargs.cluster["dst"]["cluster_addr"])),
                    act_component_code=NewDstClusterFlushJobAndWatchStatusComponent.code,
                    kwargs=asdict(act_kwargs),
                )

            # 添加/etc/hosts
            act_kwargs.exec_ip = etc_hosts_param["ip_list"]
            act_kwargs.write_op = WriteContextOpType.APPEND.value
            act_kwargs.cluster["shell_command"] = SERVERS_ADD_ETC_HOSTS.format(etc_hosts_param["etc_hosts_lines"])
            redis_pipeline.add_act(
                act_name=_("{}等添加etc_hosts").format(etc_hosts_param["ip_list"][0]),
                act_component_code=ExecuteShellScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            act_kwargs.cluster["info"] = data_copy_info
            redis_pipeline.add_sub_pipeline(redis_dts_data_copy_atom_job(self.root_id, self.data, act_kwargs))

            if info.get("online_switch_type", "") == DtsOnlineSwitchType.USER_CONFIRM.value:
                redis_pipeline.add_act(act_name=_("Redis-人工确认"), act_component_code=PauseComponent.code, kwargs={})

            redis_pipeline.add_act(
                act_name=_("在线切换任务并检测任务状态"),
                act_component_code=NewDtsOnlineSwitchJobAndWatchStatusComponent.code,
                kwargs=asdict(act_kwargs),
            )
            redis_pipeline.add_act(
                act_name=_("集群:{}禁用任务并检测任务状态").format(dst_install_param["cluster_name"]),
                act_component_code=NewDstClusterCloseJobAndWatchStatusComponent.code,
                kwargs=asdict(act_kwargs),
            )
            redis_pipeline.add_act(
                act_name=_("集群:{}下架任务并检测任务状态").format(dst_install_param["cluster_name"]),
                act_component_code=NewDstClusterShutdownJobAndWatchStatusComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # 删除/etc/hosts
            act_kwargs.exec_ip = etc_hosts_param["ip_list"]
            act_kwargs.write_op = WriteContextOpType.APPEND.value
            act_kwargs.cluster["shell_command"] = SERVERS_DEL_ETC_HOSTS.format(etc_hosts_param["etc_hosts_lines"])
            redis_pipeline.add_act(
                act_name=_("{}等删除etc_hosts").format(etc_hosts_param["ip_list"][0]),
                act_component_code=ExecuteShellScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
        redis_pipeline.run_pipeline()

    def __online_switch_precheck(self):
        for info in self.data["infos"]:
            where = (
                Q(bill_id=info["bill_id"]) & Q(src_cluster=info["src_cluster"]) & Q(dst_cluster=info["dst_cluster"])
            )
            job_row = TbTendisDTSJob.objects.filter(where).first()
            if not job_row:
                logger.error(
                    "get dts job not found,bill_id:{} src_cluster:{} dst_cluster:{}".format(
                        info["bill_id"],
                        info["src_cluster"],
                        info["dst_cluster"],
                    )
                )
                raise Exception(
                    "get dts job not found,bill_id:{} src_cluster:{} dst_cluster:{}".format(
                        info["bill_id"],
                        info["src_cluster"],
                        info["dst_cluster"],
                    )
                )
            if job_row.last_data_check_repair_flow_id != "":
                stat = FlowTree.objects.get(root_id=job_row.last_data_check_repair_flow_id).status
                if stat != StateType.FINISHED.value:
                    logger.error(
                        "dts job({}:{}->{}) last data check repair flow status:{}".format(
                            info["bill_id"],
                            info["src_cluster"],
                            info["dst_cluster"],
                            stat,
                        )
                    )
                    raise Exception(
                        "dts job({}:{}->{}) last data check repair flow status:{}".format(
                            info["bill_id"],
                            info["src_cluster"],
                            info["dst_cluster"],
                            stat,
                        )
                    )

            for row in TbTendisDtsTask.objects.filter(where).all():
                if not is_in_incremental_sync(row):
                    logger.error(
                        "dts task({}:{}->{}) not in incremental sync".format(
                            row.src_ip,
                            row.src_port,
                            info["dst_cluster"],
                        )
                    )
                    raise Exception(
                        "dts task({}:{}->{}) not in incremental sync".format(
                            row.src_ip,
                            row.src_port,
                            info["dst_cluster"],
                        )
                    )

    def __get_proxy_ips(self, cluster_id) -> list:
        proxy_ips = []
        cluster = Cluster.objects.get(id=cluster_id)
        for proxy in cluster.proxyinstance_set.all():
            proxy_ips.append(proxy.machine.ip)
        return proxy_ips

    def __get_proxy_precheck_template(self, cluster_type: str) -> str:
        precheck_template: str = ""
        if is_twemproxy_proxy_type(cluster_type):
            precheck_template = DTS_SWITCH_TWEMPROXY_PRECHECK
        elif is_predixy_proxy_type(cluster_type):
            precheck_template = DTS_SWITCH_PREDIXY_PRECHECK
        return precheck_template

    def __is_proxy_type_update(self, src_cluster_type: str, dst_cluster_type: str) -> bool:
        if is_twemproxy_proxy_type(src_cluster_type) and is_twemproxy_proxy_type(dst_cluster_type):
            return False
        if is_predixy_proxy_type(src_cluster_type) and is_predixy_proxy_type(dst_cluster_type):
            return False
        return True

    def __get_proxy_version_by_cluster_type(self, cluster_type: str) -> str:
        if is_twemproxy_proxy_type(cluster_type):
            return ConfigFileEnum.Twemproxy.value
        elif is_predixy_proxy_type(cluster_type):
            return ConfigFileEnum.Predixy.value
        return ""

    def __get_cluster_master_slave_ports(self, bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        master_ports, slave_ports = defaultdict(list), defaultdict(list)

        for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            master_ports[master_obj.machine.ip].append(master_obj.port)
            if master_obj.as_ejector and master_obj.as_ejector.first():
                my_slave_obj = master_obj.as_ejector.get().receiver
                slave_ports[my_slave_obj.machine.ip].append(my_slave_obj.port)
        return {
            "master_ports": master_ports,
            "slave_ports": slave_ports,
        }

    def online_switch_flow(self):
        self.__online_switch_precheck()
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)

        for info in self.data["infos"]:
            where = (
                Q(bill_id=info["bill_id"]) & Q(src_cluster=info["src_cluster"]) & Q(dst_cluster=info["dst_cluster"])
            )
            job_row = TbTendisDTSJob.objects.filter(where).first()
            src_cluster_info = get_cluster_info_by_id(int(job_row.app), job_row.src_cluster_id)
            src_cluster_info["proxy_ips"] = self.__get_proxy_ips(job_row.src_cluster_id)

            cluster = Cluster.objects.get(bk_biz_id=int(job_row.app), id=job_row.src_cluster_id)
            src_running_master = cluster.storageinstance_set.filter(
                instance_role=InstanceRole.REDIS_MASTER.value, status=InstanceStatus.RUNNING
            ).first()

            dst_cluster_info = get_cluster_info_by_id(int(job_row.app), job_row.dst_cluster_id)
            dst_cluster_info["proxy_ips"] = self.__get_proxy_ips(job_row.dst_cluster_id)
            cluster = Cluster.objects.get(bk_biz_id=int(job_row.app), id=job_row.dst_cluster_id)
            dst_running_master = cluster.storageinstance_set.filter(
                instance_role=InstanceRole.REDIS_MASTER.value, status=InstanceStatus.RUNNING
            ).first()

            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = RedisDtsOnlineSwitchContext.__name__
            act_kwargs.is_update_trans_data = True
            act_kwargs.file_list = trans_files.redis_base()
            act_kwargs.cluster = {}

            redis_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            acts_list = []
            for proxy_ip in src_cluster_info["proxy_ips"]:
                sh_cmd = self.__get_proxy_precheck_template(src_cluster_info["cluster_type"])
                sh_cmd = sh_cmd.replace("{{SRC_PROXY_IP}}", proxy_ip)
                sh_cmd = sh_cmd.replace("{{SRC_PROXY_PORT}}", src_cluster_info["cluster_port"])
                sh_cmd = sh_cmd.replace("{{SRC_PROXY_PASSWORD}}", src_cluster_info["cluster_password"])

                act_kwargs.exec_ip = proxy_ip
                act_kwargs.write_op = WriteContextOpType.APPEND.value
                act_kwargs.cluster["shell_command"] = sh_cmd
                acts_list.append(
                    {
                        "act_name": _("{} 前置检查").format(proxy_ip),
                        "act_component_code": ExecuteShellScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                        "write_payload_var": "src_proxy_config",
                    }
                )
            redis_pipeline.add_parallel_acts(acts_list)

            acts_list = []
            for proxy_ip in dst_cluster_info["proxy_ips"]:
                sh_cmd = self.__get_proxy_precheck_template(dst_cluster_info["cluster_type"])
                sh_cmd = sh_cmd.replace("{{SRC_PROXY_IP}}", proxy_ip)
                sh_cmd = sh_cmd.replace("{{SRC_PROXY_PORT}}", dst_cluster_info["cluster_port"])
                sh_cmd = sh_cmd.replace("{{SRC_PROXY_PASSWORD}}", dst_cluster_info["cluster_password"])

                act_kwargs.exec_ip = proxy_ip
                act_kwargs.write_op = WriteContextOpType.APPEND.value
                act_kwargs.cluster["shell_command"] = sh_cmd
                acts_list.append(
                    {
                        "act_name": _("{} 前置检查").format(proxy_ip),
                        "act_component_code": ExecuteShellScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                        "write_payload_var": "dst_proxy_config",
                    }
                )
            redis_pipeline.add_parallel_acts(acts_list)

            # 再次初始化 redis_act_payload,以便actuator中能获取前面 前置检查结果
            redis_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            # 下发 proxy 安装介质,actuator介质
            acts_list = []
            act_kwargs.file_list = trans_files.redis_cluster_apply_proxy(dst_cluster_info["cluster_type"])
            act_kwargs.exec_ip = src_cluster_info["proxy_ips"]
            acts_list.append(
                {
                    "act_name": _("{} proxys下发介质").format(src_cluster_info["cluster_domain"]),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )

            act_kwargs.file_list = trans_files.redis_cluster_apply_proxy(src_cluster_info["cluster_type"])
            act_kwargs.exec_ip = dst_cluster_info["proxy_ips"]
            acts_list.append(
                {
                    "act_name": _("{} proxys下发介质").format(dst_cluster_info["cluster_domain"]),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
            redis_pipeline.add_parallel_acts(acts_list)

            # src proxy 执行在线切换
            target_proxy_ip = dst_cluster_info["proxy_ips"][0]
            acts_list = []
            for proxy_ip in src_cluster_info["proxy_ips"]:
                act_kwargs.exec_ip = proxy_ip
                act_kwargs.cluster = {}
                act_kwargs.cluster["dts_bill_id"] = int(info["bill_id"])
                act_kwargs.cluster["src_proxy_ip"] = proxy_ip
                act_kwargs.cluster["src_proxy_port"] = int(src_cluster_info["cluster_port"])
                act_kwargs.cluster["src_proxy_password"] = src_cluster_info["cluster_password"]
                act_kwargs.cluster["src_cluster_type"] = src_cluster_info["cluster_type"]
                act_kwargs.cluster["my_dst_proxy_ip"] = target_proxy_ip
                act_kwargs.cluster["dst_proxy_port"] = int(dst_cluster_info["cluster_port"])
                act_kwargs.cluster["dst_proxy_password"] = dst_cluster_info["cluster_password"]
                act_kwargs.cluster["dst_cluster_type"] = dst_cluster_info["cluster_type"]
                act_kwargs.cluster["dst_redis_ip"] = dst_running_master.machine.ip
                act_kwargs.cluster["dst_redis_port"] = int(dst_running_master.port)
                act_kwargs.get_redis_payload_func = RedisActPayload.redis_dts_src_proxys_online_switch_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("{} 执行在线切换").format(proxy_ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            redis_pipeline.add_parallel_acts(acts_list=acts_list)

            act_kwargs.cluster = {
                "bill_id": int(info["bill_id"]),
                "src_cluster": info["src_cluster"],
                "dst_cluster": info["dst_cluster"],
            }
            redis_pipeline.add_act(
                act_name=_("断开同步关系"),
                act_component_code=RedisDtsDisconnectSyncComponent.code,
                kwargs=asdict(act_kwargs),
            )

            # dst proxy 执行在线切换
            target_proxy_ip = src_cluster_info["proxy_ips"][0]
            acts_list = []
            for proxy_ip in dst_cluster_info["proxy_ips"]:
                act_kwargs.exec_ip = proxy_ip
                act_kwargs.cluster = {}
                act_kwargs.cluster["dts_bill_id"] = int(info["bill_id"])
                act_kwargs.cluster["src_proxy_ip"] = proxy_ip
                act_kwargs.cluster["src_proxy_port"] = int(dst_cluster_info["cluster_port"])
                act_kwargs.cluster["src_proxy_password"] = dst_cluster_info["cluster_password"]
                act_kwargs.cluster["src_cluster_type"] = dst_cluster_info["cluster_type"]
                act_kwargs.cluster["my_dst_proxy_ip"] = target_proxy_ip
                act_kwargs.cluster["dst_proxy_port"] = int(src_cluster_info["cluster_port"])
                act_kwargs.cluster["dst_proxy_password"] = src_cluster_info["cluster_password"]
                act_kwargs.cluster["dst_cluster_type"] = src_cluster_info["cluster_type"]
                act_kwargs.cluster["dst_redis_ip"] = src_running_master.machine.ip
                act_kwargs.cluster["dst_redis_port"] = int(src_running_master.port)
                act_kwargs.get_redis_payload_func = RedisActPayload.redis_dts_dst_proxys_online_switch_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("{} 执行在线切换").format(proxy_ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            redis_pipeline.add_parallel_acts(acts_list=acts_list)

            # 交换源集群、目标集群的storageinstance 元数据
            act_kwargs.cluster = {
                "src_cluster_id": src_cluster_info["cluster_id"],
                "dst_cluster_id": dst_cluster_info["cluster_id"],
                "meta_func_name": RedisDBMeta.dts_online_switch_swap_two_cluster_storage.__name__,
            }
            redis_pipeline.add_act(
                act_name=_("交换源集群、目标集群的storageinstance 元数据"),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(act_kwargs),
            )

            acts_list = []
            # 交换源集群、目标集群的 redis 配置
            act_kwargs.cluster = {
                "bk_biz_id": int(job_row.app),
                "src_cluster_domain": src_cluster_info["cluster_domain"],
                "src_cluster_version": src_cluster_info["cluster_version"],
                "src_cluster_type": src_cluster_info["cluster_type"],
                "dst_cluster_domain": dst_cluster_info["cluster_domain"],
                "dst_cluster_version": dst_cluster_info["cluster_version"],
                "dst_cluster_type": dst_cluster_info["cluster_type"],
            }
            act_kwargs.get_redis_payload_func = RedisActPayload.dts_swap_redis_config.__name__
            acts_list.append(
                {
                    "act_name": _("交换源集群、目标集群的 redis 配置"),
                    "act_component_code": RedisConfigComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )

            # 交换源集群、目标集群的 proxy 版本信息
            act_kwargs.cluster = {
                "bk_biz_id": int(job_row.app),
                "src_cluster_domain": src_cluster_info["cluster_domain"],
                "src_proxy_version": self.__get_proxy_version_by_cluster_type(src_cluster_info["cluster_type"]),
                "src_cluster_type": src_cluster_info["cluster_type"],
                "dst_cluster_domain": dst_cluster_info["cluster_domain"],
                "dst_proxy_version": self.__get_proxy_version_by_cluster_type(dst_cluster_info["cluster_type"]),
                "dst_cluster_type": dst_cluster_info["cluster_type"],
            }
            act_kwargs.get_redis_payload_func = RedisActPayload.dts_swap_proxy_config_version.__name__
            acts_list.append(
                {
                    "act_name": _("交换源集群、目标集群的 proxy 版本信息"),
                    "act_component_code": RedisConfigComponent.code,
                    "kwargs": asdict(act_kwargs),
                }
            )
            redis_pipeline.add_parallel_acts(acts_list=acts_list)

            # src_cluster的 new master/salve 重装 dbmon
            app = AppCache.get_app_attr(job_row.app, "db_app_abbr")
            app_name = AppCache.get_app_attr(job_row.app, "bk_biz_name")
            act_kwargs.cluster = {}
            act_kwargs.cluster["servers"] = [
                {
                    "app": app,
                    "app_name": app_name,
                    "bk_biz_id": str(job_row.app),
                    "bk_cloud_id": int(job_row.bk_cloud_id),
                    "cluster_name": src_cluster_info["cluster_name"],
                    "cluster_type": src_cluster_info["cluster_type"],
                    "cluster_domain": src_cluster_info["cluster_domain"],
                }
            ]
            # 执行到这里重装dbmon,此时src_cluster和 dst_cluster 已经交换了 storageinstances
            # 但是在确定flow 流程静态信息时,这些 master/slave 依然属于 dst_cluster
            # 所以这里获取的是 dst_cluster的 master/slave ip ports
            src_master_slave_ports = self.__get_cluster_master_slave_ports(int(job_row.app), job_row.dst_cluster_id)
            acts_list = []
            for ip, ports in src_master_slave_ports["master_ports"].items():
                act_kwargs.cluster["servers"][0]["server_ip"] = ip
                act_kwargs.cluster["servers"][0]["server_ports"] = ports
                act_kwargs.cluster["servers"][0]["meta_role"] = InstanceRole.REDIS_MASTER.value
                act_kwargs.exec_ip = ip
                act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
                acts_list.append(
                    {
                        "act_name": _("{} 重装 dbmon").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            for ip, ports in src_master_slave_ports["slave_ports"].items():
                act_kwargs.cluster["servers"][0]["server_ip"] = ip
                act_kwargs.cluster["servers"][0]["server_ports"] = ports
                act_kwargs.cluster["servers"][0]["meta_role"] = InstanceRole.REDIS_SLAVE.value
                act_kwargs.exec_ip = ip
                act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
                acts_list.append(
                    {
                        "act_name": _("{} 重装 dbmon").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            redis_pipeline.add_parallel_acts(acts_list=acts_list)

            # dst_cluster的 new master/slave 重装 dbmon
            act_kwargs.cluster = {}
            act_kwargs.cluster["servers"] = [
                {
                    "app": app,
                    "app_name": app_name,
                    "bk_biz_id": str(job_row.app),
                    "bk_cloud_id": int(job_row.bk_cloud_id),
                    "cluster_name": dst_cluster_info["cluster_name"],
                    "cluster_type": dst_cluster_info["cluster_type"],
                    "cluster_domain": dst_cluster_info["cluster_domain"],
                }
            ]
            # 执行到这里重装dbmon,此时src_cluster和 dst_cluster 已经交换了 storageinstances
            # 但是在确定flow 流程静态信息时,这些 master/slave 依然属于 src_cluster
            # 所以这里获取的是 src_cluster的 master/slave ip ports
            dst_master_slave_ports = self.__get_cluster_master_slave_ports(int(job_row.app), job_row.src_cluster_id)
            acts_list = []
            for ip, ports in dst_master_slave_ports["master_ports"].items():
                act_kwargs.cluster["servers"][0]["server_ip"] = ip
                act_kwargs.cluster["servers"][0]["server_ports"] = ports
                act_kwargs.cluster["servers"][0]["meta_role"] = InstanceRole.REDIS_MASTER.value
                act_kwargs.exec_ip = ip
                act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
                acts_list.append(
                    {
                        "act_name": _("{} 重装 dbmon").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            for ip, ports in dst_master_slave_ports["slave_ports"].items():
                act_kwargs.cluster["servers"][0]["server_ip"] = ip
                act_kwargs.cluster["servers"][0]["server_ports"] = ports
                act_kwargs.cluster["servers"][0]["meta_role"] = InstanceRole.REDIS_SLAVE.value
                act_kwargs.exec_ip = ip
                act_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
                acts_list.append(
                    {
                        "act_name": _("{} 重装 dbmon").format(ip),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(act_kwargs),
                    }
                )
            redis_pipeline.add_parallel_acts(acts_list=acts_list)

        redis_pipeline.run_pipeline()
