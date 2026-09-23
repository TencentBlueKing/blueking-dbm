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
from copy import deepcopy
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import DataStructureStatus, InstanceRole
from backend.db_meta.models import AppCache, Cluster
from backend.db_services.redis.rollback.constants import (
    ROLLBACK_CC_MODULE_NAME,
    ROLLBACK_CC_SET_NAME,
    ROLLBACK_VERSION,
)
from backend.db_services.redis.util import is_have_proxy, is_twemproxy_proxy_type
from backend.flow.consts import DEFAULT_REDIS_START_PORT, DEPENDENCIES_PLUGINS, WriteContextOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.redis_rollback.planner import RollbackPlanner
from backend.flow.plugins.components.collections.common.add_alarm_shield import AddAlarmShieldComponent
from backend.flow.plugins.components.collections.common.disable_alarm_shield import DisableAlarmShieldComponent
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.install_nodeman_plugin import (
    InstallNodemanPluginServiceComponent,
)
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.exec_shell_script import ExecuteShellScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.plugins.components.collections.redis.redis_rollback import (
    RedisRollbackDiskPrecheckComponent,
    RedisRollbackDownloadComponent,
)
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs, InstallNodemanPluginKwargs
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, RedisRollbackContext
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

logger = logging.getLogger("flow")

_DISK_SHELL = """
                REDIS_DATA_DIR_DATA=`df -k $REDIS_DATA_DIR | grep -iv Filesystem`
                REDIS_BACKUP_DIR_DATA=`df -k $REDIS_BACKUP_DIR | grep -iv Filesystem`
                BACKUP_DIR=`echo $REDIS_BACKUP_DIR`
                mkdir -p $BACKUP_DIR/dbbak/recover_redis/
                chown -R  mysql:mysql $BACKUP_DIR/dbbak/recover_redis/
                echo "<ctx>{\\\"redis_data_dir_data\\\":\\\"${REDIS_DATA_DIR_DATA}\\\", \\
                \\\"backup_dir\\\":\\\"${BACKUP_DIR}\\\",\\\"redis_backup_dir_data\\\":\\\"${REDIS_BACKUP_DIR_DATA}\\\"}</ctx>"
                """


class RedisRollbackFlow:
    """Redis rollback v2: shard-keyed backup discovery + plan-driven pipeline.

    Pipeline stages: Gate evaluation -> Media transfer -> Disk precheck -> Backup download
    -> Single-boot restore -> Instance metadata -> Transfer to rollback CC module
    -> dbmon/proxy deployment -> Key filtering -> Save rollback task record.
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def redis_rollback(self):
        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = [self.build_cluster_rollback(info) for info in self.data["infos"]]
        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        return pipeline.run_pipeline()

    def build_cluster_rollback(self, info: dict):
        cluster = Cluster.objects.get(id=info["cluster_id"])
        dest_ips = [host["ip"] for host in info.get("redis") or []]
        plan = RollbackPlanner(cluster, info).build(dest_ips=dest_ips, pack=True)
        is_drill = self.data.get("is_rollback_drill", False)
        cluster_ticket_data = deepcopy(self.data)
        cluster_ticket_data.update(
            {
                "immute_domain": plan.immute_domain,
                "domain_name": plan.immute_domain,
                "bk_cloud_id": plan.bk_cloud_id,
                "cluster_type": plan.cluster_type,
                "db_version": plan.db_version,
                "proxy_port": plan.proxy_port,
            }
        )

        redis_pipeline = SubBuilder(root_id=self.root_id, data=cluster_ticket_data)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = RedisRollbackContext.__name__
        act_kwargs.file_list = GetFileList(db_type=DBType.Redis).redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.bk_cloud_id = plan.bk_cloud_id
        act_kwargs.cluster = {
            "immute_domain": plan.immute_domain,
            "domain_name": plan.immute_domain,
            "bk_biz_id": plan.bk_biz_id,
            "bk_cloud_id": plan.bk_cloud_id,
            "cluster_type": plan.cluster_type,
            "db_version": plan.db_version,
            "proxy_port": plan.proxy_port,
            "operate": _("REDIS_ROLLBACK"),
        }

        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        if not is_drill:
            shield_kwargs = deepcopy(act_kwargs)
            redis_pipeline.add_act(
                act_name=_("屏蔽临时主机告警-{}").format(dest_ips),
                act_component_code=AddAlarmShieldComponent.code,
                kwargs={
                    **asdict(shield_kwargs),
                    "description": _("Redis回档-屏蔽告警-{}").format(plan.immute_domain),
                    "dimensions": [
                        {"name": "appid", "values": [str(plan.bk_biz_id)]},
                        {"name": "bk_target_ip", "values": dest_ips},
                    ],
                    "duration_seconds": int(self.data.get("alarm_shield_duration_seconds", 2 * 3600)),
                },
            )

        trans_acts = []
        init_acts = []
        for ip in dest_ips:
            trans_kwargs = deepcopy(act_kwargs)
            # Instance installation runs inline during restore; transfer all packages (actuator, redis, tools, dbmon).
            trans_kwargs.file_list = GetFileList(db_type=DBType.Redis).redis_cluster_apply_backend(plan.db_version)
            trans_kwargs.exec_ip = ip
            trans_acts.append(
                {
                    "act_name": _("Redis-{}-下发介质包").format(ip),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(trans_kwargs),
                }
            )
            init_kwargs = deepcopy(act_kwargs)
            init_kwargs.exec_ip = ip
            init_kwargs.get_redis_payload_func = RedisActPayload.get_sys_init_payload.__name__
            init_acts.append(
                {
                    "act_name": _("初始化机器"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(init_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=trans_acts)
        redis_pipeline.add_parallel_acts(acts_list=init_acts)

        plugin_acts = [
            {
                "act_name": _("Redis-安装backup-client工具-{}").format(dest_ips),
                "act_component_code": DownloadBackupClientComponent.code,
                "kwargs": asdict(
                    DownloadBackupClientKwargs(
                        bk_cloud_id=plan.bk_cloud_id,
                        bk_biz_id=int(self.data["bk_biz_id"]),
                        ip_list=dest_ips,
                    )
                ),
            }
        ]
        if not is_drill:
            for plugin_name in DEPENDENCIES_PLUGINS:
                plugin_acts.append(
                    {
                        "act_name": _("安装[{}]插件").format(plugin_name),
                        "act_component_code": InstallNodemanPluginServiceComponent.code,
                        "kwargs": asdict(
                            InstallNodemanPluginKwargs(
                                bk_cloud_id=int(plan.bk_cloud_id), ips=dest_ips, plugin_name=plugin_name
                            )
                        ),
                        "timeout": 300,
                    }
                )
        redis_pipeline.add_parallel_acts(acts_list=plugin_acts)

        disk_kwargs = deepcopy(act_kwargs)
        disk_kwargs.exec_ip = dest_ips
        disk_kwargs.write_op = WriteContextOpType.APPEND.value
        disk_kwargs.cluster["shell_command"] = _DISK_SHELL
        redis_pipeline.add_act(
            act_name=_("获取磁盘使用情况: {}").format(dest_ips[:3]),
            act_component_code=ExecuteShellScriptComponent.code,
            kwargs=asdict(disk_kwargs),
            write_payload_var="disk_used",
        )

        disk_acts = []
        for dest_host in plan.dest_hosts:
            precheck_kwargs = deepcopy(act_kwargs)
            precheck_kwargs.exec_ip = dest_host.ip
            precheck_kwargs.cluster["download_bytes"] = dest_host.download_bytes
            disk_acts.append(
                {
                    "act_name": _("redis 回档磁盘预检-{}").format(dest_host.ip),
                    "act_component_code": RedisRollbackDiskPrecheckComponent.code,
                    "kwargs": {
                        **asdict(precheck_kwargs),
                        "download_bytes": dest_host.download_bytes,
                        "unpacked_bytes": dest_host.unpacked_bytes,
                    },
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=disk_acts)

        os_account = PayloadHandler.redis_get_os_account()
        download_subs = []
        for dest_host in plan.dest_hosts:
            sub = SubBuilder(root_id=self.root_id, data=cluster_ticket_data)
            sub.add_act(
                act_name=_("下载备份到{}").format(dest_host.ip),
                act_component_code=RedisRollbackDownloadComponent.code,
                kwargs={
                    "bk_cloud_id": plan.bk_cloud_id,
                    "task_ids": dest_host.task_ids,
                    "dest_ip": dest_host.ip,
                    "login_user": os_account["os_user"],
                    "login_passwd": os_account["os_password"],
                    "reason": "redis rollback",
                    "download_bytes": dest_host.download_bytes,
                    "set_trans_data_dataclass": RedisRollbackContext.__name__,
                },
            )
            download_subs.append(sub.build_sub_process(sub_name=_("下载备份-{}").format(dest_host.ip)))

        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=download_subs)

        if not self.data.get("skip_mannual_confirm", False):
            redis_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

        resource_spec = info["resource_spec"]["redis"]
        cluster_dst_instance = [
            "{}{}{}".format(dest_host.ip, IP_PORT_DIVIDER, port)
            for dest_host in plan.dest_hosts
            for port in dest_host.ports
        ]

        recover_acts = []
        for dest_host in plan.dest_hosts:
            host_items = [item for item in plan.items if item.dest_ip == dest_host.ip]
            recover_kwargs = deepcopy(act_kwargs)
            recover_kwargs.exec_ip = dest_host.ip
            recover_kwargs.is_update_trans_data = False
            recover_kwargs.get_redis_payload_func = RedisActPayload.redis_rollback_payload.__name__
            recover_kwargs.cluster = {
                "dest_ip": dest_host.ip,
                # Empty: the actuator uses $REDIS_BACKUP_DIR, the same source _DISK_SHELL reports for download.
                "dest_dir": "",
                "recover_at": plan.recover_at.strftime("%Y-%m-%d %H:%M:%S") if plan.recover_at else "",
                "immute_domain": plan.immute_domain,
                "domain_name": plan.immute_domain,
                "cluster_type": plan.cluster_type,
                "db_version": plan.db_version,
                "instances": [
                    {
                        "source_ip": item.source_ip,
                        "source_port": item.source_port,
                        "dest_port": item.dest_port,
                        "full_files": [f.file_name for f in item.full_files],
                        "binlog_files": [],
                    }
                    for item in host_items
                ],
            }
            recover_acts.append(
                {
                    "act_name": _("Redis-{}-安装并回档恢复").format(dest_host.ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(recover_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=recover_acts)

        install_meta_acts = []
        for dest_host in plan.dest_hosts:
            meta_install_kwargs = deepcopy(act_kwargs)
            meta_install_kwargs.cluster.update(
                {
                    "meta_func_name": RedisDBMeta.redis_install.__name__,
                    "new_master_ips": [dest_host.ip],
                    "new_slave_ips": [],
                    "ports": dest_host.ports,
                    "start_port": DEFAULT_REDIS_START_PORT,
                    "inst_num": 0,
                    "spec_id": resource_spec["id"],
                    "spec_config": resource_spec,
                }
            )
            install_meta_acts.append(
                {
                    "act_name": _("Redis-{}-写入实例元数据").format(dest_host.ip),
                    "act_component_code": RedisDBMetaComponent.code,
                    "kwargs": asdict(meta_install_kwargs),
                }
            )
        redis_pipeline.add_parallel_acts(acts_list=install_meta_acts)

        cc_kwargs = deepcopy(act_kwargs)
        cc_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_rollback_cc_transfer.__name__
        cc_kwargs.cluster["temp_instances"] = cluster_dst_instance
        redis_pipeline.add_act(
            act_name=_("Redis-临时节点转移到{}/{}模块").format(ROLLBACK_CC_SET_NAME, ROLLBACK_CC_MODULE_NAME),
            act_component_code=RedisDBMetaComponent.code,
            kwargs=asdict(cc_kwargs),
        )

        if not is_drill:
            self._install_dbmon(plan, act_kwargs, redis_pipeline)

        self._deploy_proxy(plan, act_kwargs, dest_ips, redis_pipeline)

        if plan.key_filter.enabled:
            self._add_key_filter(plan, act_kwargs, redis_pipeline)

        prod_instance_range = [
            item.shard.current_master or "{}:{}".format(item.source_ip, item.source_port) for item in plan.items
        ]
        prod_temp_pairs = [
            ["{}:{}".format(item.source_ip, item.source_port), "{}:{}".format(item.dest_ip, item.dest_port)]
            for item in plan.items
        ]
        recover_at = plan.recover_at
        if hasattr(recover_at, "isoformat"):
            recover_at_value = recover_at.isoformat()
        else:
            recover_at_value = str(recover_at)

        meta_kwargs = deepcopy(act_kwargs)
        meta_kwargs.cluster = {
            "domain_name": plan.immute_domain,
            "bk_cloud_id": plan.bk_cloud_id,
            "prod_cluster_type": plan.cluster_type,
            "prod_cluster": plan.immute_domain,
            "prod_cluster_id": plan.cluster_id,
            "specification": resource_spec,
            "prod_instance_range": prod_instance_range,
            "temp_cluster_type": plan.cluster_type,
            "temp_instance_range": cluster_dst_instance,
            "temp_cluster_proxy": "{}:{}".format(dest_ips[0], plan.proxy_port),
            "prod_temp_instance_pairs": prod_temp_pairs,
            "host_count": len(dest_ips),
            "recovery_time_point": recover_at_value,
            "status": DataStructureStatus.COMPLETED,
            "meta_func_name": RedisDBMeta.data_construction_tasks_operate.__name__,
            "cluster_type": plan.cluster_type,
            "rollback_version": ROLLBACK_VERSION,
            "rollback_mode": plan.select_mode,
            "backup_identify": plan.backup_identify or "",
            "rollback_detail": plan.to_rollback_detail(),
        }
        redis_pipeline.add_act(
            act_name=_("写入构造记录元数据"), act_component_code=RedisDBMetaComponent.code, kwargs=asdict(meta_kwargs)
        )

        if not is_drill:
            redis_pipeline.add_act(
                act_name=_("解除临时主机告警屏蔽-{}").format(dest_ips),
                act_component_code=DisableAlarmShieldComponent.code,
                kwargs=asdict(act_kwargs),
            )
        return redis_pipeline.build_sub_process(sub_name=_("集群[{}]回档").format(plan.immute_domain))

    def _install_dbmon(self, plan, act_kwargs, pipeline):
        app = AppCache.get_app_attr(plan.bk_biz_id, "db_app_abbr")
        app_name = AppCache.get_app_attr(plan.bk_biz_id, "bk_biz_name")
        acts = []
        for dest_host in plan.dest_hosts:
            dbmon_kwargs = deepcopy(act_kwargs)
            dbmon_kwargs.exec_ip = dest_host.ip
            dbmon_kwargs.cluster["servers"] = [
                {
                    "app": app,
                    "app_name": app_name,
                    "bk_biz_id": str(plan.bk_biz_id),
                    "bk_cloud_id": int(plan.bk_cloud_id),
                    "server_ip": dest_host.ip,
                    "server_ports": dest_host.ports,
                    "meta_role": InstanceRole.REDIS_MASTER.value,
                    "cluster_name": plan.immute_domain,
                    "cluster_type": plan.cluster_type,
                    "cluster_domain": plan.immute_domain,
                    # Temporary instances do not participate in source shards; leave empty to avoid polluting shard_value.
                    "server_shards": {},
                    "cache_backup_mode": "",
                }
            ]
            dbmon_kwargs.get_redis_payload_func = RedisActPayload.bkdbmon_install.__name__
            acts.append(
                {
                    "act_name": _("Redis-{}-安装监控").format(dest_host.ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(dbmon_kwargs),
                }
            )
        pipeline.add_parallel_acts(acts_list=acts)

    def _deploy_proxy(self, plan, act_kwargs, dest_ips, pipeline):
        if not is_have_proxy(plan.cluster_type):
            act_kwargs.new_install_proxy_exec_ip = dest_ips[0]
            return
        act_kwargs.new_install_proxy_exec_ip = dest_ips[0]
        trans_kwargs = deepcopy(act_kwargs)
        trans_kwargs.exec_ip = dest_ips[0]
        trans_kwargs.file_list = GetFileList(db_type=DBType.Redis).redis_cluster_apply_proxy(plan.cluster_type)
        pipeline.add_act(
            act_name=_("{}proxy下发介质包").format(dest_ips[0]),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(trans_kwargs),
        )
        servers = []
        if is_twemproxy_proxy_type(plan.cluster_type):
            for item in plan.items:
                servers.append("{}:{} {} {} 1".format(item.dest_ip, item.dest_port, "admin", item.shard.shard_value))
        proxy_kwargs = deepcopy(act_kwargs)
        proxy_kwargs.exec_ip = dest_ips[0]
        proxy_kwargs.cluster["servers"] = servers
        proxy_kwargs.get_redis_payload_func = RedisActPayload.add_twemproxy_payload.__name__
        pipeline.add_act(
            act_name=_("{}安装proxy实例").format(dest_ips[0]),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(proxy_kwargs),
        )

    def _add_key_filter(self, plan, act_kwargs, pipeline):
        acts = []
        for dest_host in plan.dest_hosts:
            filter_kwargs = deepcopy(act_kwargs)
            filter_kwargs.exec_ip = dest_host.ip
            filter_kwargs.is_update_trans_data = False
            filter_kwargs.get_redis_payload_func = RedisActPayload.redis_rollback_key_filter_payload.__name__
            filter_kwargs.cluster = {
                "domain_name": plan.immute_domain,
                "white_regex": plan.key_filter.white_regex,
                "black_regex": plan.key_filter.black_regex,
                "filter_mode": plan.key_filter.filter_mode,
                dest_host.ip: dest_host.ports,
                "path": "",
            }
            acts.append(
                {
                    "act_name": _("Redis-{}-key过滤").format(dest_host.ip),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(filter_kwargs),
                }
            )
        if acts:
            pipeline.add_parallel_acts(acts_list=acts)
