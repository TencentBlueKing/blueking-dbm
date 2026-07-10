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
import logging

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterEntryRole, InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster
from backend.flow.consts import DBA_ORACLE_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.oracle.base_flow import OracleBaseFlow
from backend.flow.engine.bamboo.scene.oracle.sub_task.add_slave_common import (
    _make_oracle_act,
    build_dg_and_duplicate_sub_flow,
    build_fetch_and_dispatch_files_sub_flow,
    build_media_transfer_sub_flow,
    build_new_machine_meta_kwargs,
    build_new_slave_setup_sub_flow,
    build_precheck_sub_flow,
    build_replace_common_sub_flow,
    build_replace_meta_kwargs_for_primary_standby,
    build_replace_meta_kwargs_for_single_none,
)
from backend.flow.plugins.components.collections.oracle.oracle_db_meta import OracleDBMetaComponent
from backend.flow.utils.oracle.oracle_act_payload import OracleActPayload
from backend.flow.utils.oracle.oracle_context_dataclass import AddSlaveContext

logger = logging.getLogger("flow")


class OracleAddSlaveFlow(OracleBaseFlow):
    """
    Oracle[添加从库/整机替换]单据的流程引擎

    资源池模式(ip_source=resource_pool):
    {
        "uid": "2022111212001000",
        "root_id": 123,
        "created_by": "admin",
        "bk_biz_id": 9991001,
        "ticket_type": "ORACLE_ADD_SLAVE",
        "infos": [
            {
                "cluster_id": 2,
                "old_node": {"ip": "1.1.1.1", "bk_cloud_id": 0},
                "replace_flag": False,
                "resource_spec": {"oracle": {"spec_id": 1, "count": 1}}
            }
        ],
        "ip_source": "resource_pool"
    }
    """

    def _build_replace_meta_kwargs(self, cluster: Cluster, info: dict, new_slave: str):
        """按集群类型返回 (元数据 kwargs, dns_role)."""
        if cluster.cluster_type == ClusterType.OraclePrimaryStandby.value:
            return (
                build_replace_meta_kwargs_for_primary_standby(
                    cluster_id=info["cluster_id"],
                    bk_biz_id=self.data["bk_biz_id"],
                    new_slave=new_slave,
                    old_node=info["old_node"]["ip"],
                ),
                ClusterEntryRole.SLAVE_ENTRY.value,
            )
        if cluster.cluster_type == ClusterType.OracleSingleNone.value:
            return (
                build_replace_meta_kwargs_for_single_none(
                    cluster_id=info["cluster_id"],
                    bk_biz_id=self.data["bk_biz_id"],
                    new_slave=new_slave,
                ),
                ClusterEntryRole.MASTER_ENTRY.value,
            )
        raise Exception(_("不支持的集群类型: {}, 仅支持 OraclePrimaryStandby / OracleSingleNone").format(cluster.cluster_type))

    def oracle_add_slave_flow(self):
        """
        oracle [添加从库/重建从库]流程
        """
        oracle_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        for info in self.data["infos"]:
            sub_data = copy.deepcopy(self.data)
            sub_data.pop("infos")
            sub_flow_data = {**info, **sub_data}
            sub_pipeline = SubBuilder(root_id=self.root_id, data=sub_flow_data)

            cluster = Cluster.objects.get(id=info["cluster_id"])
            bk_cloud_id = cluster.bk_cloud_id
            cluster_master = cluster.storageinstance_set.get(instance_role=InstanceRole.PRIMARY.value).machine.ip
            old_node = info["old_node"]["ip"]
            new_slave = info["new_slave"]["ip"]

            # 1. 环境预检查 + 依赖插件安装
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_precheck_sub_flow(
                    root_id=self.root_id, data=sub_flow_data, new_slave=new_slave, bk_cloud_id=bk_cloud_id
                )
            )

            # 2. 下发介质 (旧实例侧: old_node + cluster_master)
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_media_transfer_sub_flow(
                    root_id=self.root_id,
                    data=sub_flow_data,
                    bk_cloud_id=bk_cloud_id,
                    old_hosts=[old_node, cluster_master],
                    new_slave=new_slave,
                    db_version=self.data["db_version"],
                    patch_list=self.data["patch_list"],
                )
            )

            # 3. 获取集群配置 (add_slave 只从 old_node 取一次, 写入 configs)
            sub_pipeline.add_act(
                **_make_oracle_act(
                    act_name=_("获取集群配置"),
                    exec_ip=old_node,
                    bk_cloud_id=bk_cloud_id,
                    payload_func_name=OracleActPayload.get_config_payload.__name__,
                    run_as_system_user=DBA_ORACLE_USER,
                    write_payload_var=AddSlaveContext.get_configs_var_name(),
                )
            )

            # 4. 获取并下发参数与密码文件
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_fetch_and_dispatch_files_sub_flow(
                    root_id=self.root_id,
                    data=sub_flow_data,
                    bk_cloud_id=bk_cloud_id,
                    old_node=old_node,
                    new_slave=new_slave,
                    uid=self.data["uid"],
                )
            )

            # 5. 新备库软件与实例部署
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_new_slave_setup_sub_flow(
                    root_id=self.root_id,
                    data=sub_flow_data,
                    bk_cloud_id=bk_cloud_id,
                    old_node=old_node,
                    new_slave=new_slave,
                )
            )

            # 6. 配置 DataGuard + RMAN 在线复制 + 切日志/检查/实时应用 + 启动监听
            sub_pipeline.add_sub_pipeline(
                sub_flow=build_dg_and_duplicate_sub_flow(
                    root_id=self.root_id,
                    data=sub_flow_data,
                    bk_cloud_id=bk_cloud_id,
                    old_node=old_node,
                    new_slave=new_slave,
                    cluster_master=cluster_master,
                )
            )

            # 7. 仅 Oracle 单节点版集群需要校验旧实例是否为真实主节点
            if cluster.cluster_type == ClusterType.OracleSingleNone.value:
                sub_pipeline.add_act(
                    **_make_oracle_act(
                        act_name=_("旧实例是否为真实主节点"),
                        exec_ip=old_node,
                        bk_cloud_id=bk_cloud_id,
                        payload_func_name=OracleActPayload.get_real_master_payload.__name__,
                        run_as_system_user=DBA_ORACLE_USER,
                    )
                )

            # 8. 写入元数据 - 新增机器
            sub_pipeline.add_act(
                act_name=_("写入元数据-新增机器"),
                act_component_code=OracleDBMetaComponent.code,
                kwargs=build_new_machine_meta_kwargs(
                    bk_cloud_id=bk_cloud_id,
                    bk_biz_id=self.data["bk_biz_id"],
                    new_ip=new_slave,
                    resource_spec=info["resource_spec"],
                    created_by=self.data["created_by"],
                    cluster_type=cluster.cluster_type,
                ),
            )

            # 9. 若为替换场景, 追加替换公共子流程
            if info["replace_flag"]:
                meta_kwargs, dns_role = self._build_replace_meta_kwargs(cluster, info, new_slave)
                sub_pipeline.add_sub_pipeline(
                    sub_flow=build_replace_common_sub_flow(
                        root_id=self.root_id,
                        data=sub_flow_data,
                        cluster=cluster,
                        bk_cloud_id=bk_cloud_id,
                        old_node=old_node,
                        new_slave=new_slave,
                        cluster_master=cluster_master,
                        meta_kwargs=meta_kwargs,
                        dns_role=dns_role,
                    )
                )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("集群[{}][添加从库/整机替换]").format(cluster.immute_domain))
            )

        oracle_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        logger.info(_("构建Oracle[添加从库/整机替换]流程成功"))
        oracle_pipeline.run_pipeline(init_trans_data_class=AddSlaveContext())
