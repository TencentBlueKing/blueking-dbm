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
from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.delete_cc_service_instance import DelCCServiceInstComponent
from backend.flow.plugins.components.collections.mysql.clear_machine import SpiderRemoteClearMachineComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    DBMetaOPKwargs,
    DelServiceInstKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta

logger = logging.getLogger("flow")


class TenDBClusterDestroyFlow(object):
    """
    构建tendb cluster集群 (spider集群)下架流程抽象类
    支持不同云区域的db集群合并下架
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_cluster_info(cluster_id: int, bk_biz_id: int) -> dict:
        """
        根据cluster_id 获取到单节点集群实例信息
        @param cluster_id: 需要下架的集群id
        @param bk_biz_id: 需要下架集群对应的业务id
        """
        try:
            cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(cluster_id=cluster_id, bk_biz_id=bk_biz_id, message=_("集群不存在"))

        remote_objs = cluster.storageinstance_set.all()
        spider_objs = cluster.proxyinstance_set.all()
        ctl_objs = cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        )

        return {
            "id": cluster_id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "name": cluster.name,
            "remote_objs": remote_objs,
            "spider_port": spider_objs[0].port,
            "remote_ip_list": list(set([s.machine.ip for s in remote_objs])),
            "spider_ip_list": list(set([s.machine.ip for s in spider_objs])),
            "spider_ctl_port": ctl_objs[0].admin_port,
            "spider_ctl_ip_list": [c.machine.ip for c in ctl_objs],
        }

    def destroy_cluster(self):
        """
        定义spider集群下架流程，支持多集群下架模式
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        spider_destroy_pipeline = Builder(
            root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(self.data["cluster_ids"]))
        )
        sub_pipelines = []

        # 多集群下架时循环加入集群下架子流程
        for cluster_id in self.data["cluster_ids"]:

            # 获取集群的实例信息
            cluster = self.__get_cluster_info(cluster_id=cluster_id, bk_biz_id=int(self.data["bk_biz_id"]))

            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

            # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
            exec_act_kwargs = ExecActuatorKwargs(
                bk_cloud_id=int(cluster["bk_cloud_id"]),
            )

            # 先回收集群所有服务实例内容
            del_instance_list = []
            for inst in cluster["remote_objs"]:
                del_instance_list.append({"ip": inst.machine.ip, "port": inst.port})
            for ip in cluster["spider_ip_list"]:
                del_instance_list.append({"ip": ip, "port": cluster["spider_port"]})

            sub_pipeline.add_act(
                act_name=_("删除注册CC系统的服务实例"),
                act_component_code=DelCCServiceInstComponent.code,
                kwargs=asdict(
                    DelServiceInstKwargs(
                        cluster_id=cluster_id,
                        del_instance_list=del_instance_list,
                    )
                ),
            )

            # 阶段1 下发db-actuator介质包
            sub_pipeline.add_act(
                act_name=_("下发db-actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster["bk_cloud_id"],
                        exec_ip=list(set(cluster["remote_ip_list"] + cluster["spider_ip_list"])),
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            # 阶段2 清理机器级别配置
            # tendbcluster 的机器是集群独占的, 所以可以不用检查现行清理
            exec_act_kwargs.exec_ip = cluster["remote_ip_list"] + cluster["spider_ip_list"]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clear_machine_crontab.__name__
            sub_pipeline.add_act(
                act_name=_("清理机器级别配置"),
                act_component_code=SpiderRemoteClearMachineComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            # 阶段3 卸载相关db组件
            acts_list = []
            for spider_ip in cluster["spider_ip_list"]:
                exec_act_kwargs.exec_ip = spider_ip
                exec_act_kwargs.cluster = {"spider_port": cluster["spider_port"]}
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_spider_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("卸载spider实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            acts_list = []
            for ctl_ip in cluster["spider_ctl_ip_list"]:
                exec_act_kwargs.exec_ip = ctl_ip
                exec_act_kwargs.cluster = {"spider_ctl_port": cluster["spider_ctl_port"]}
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_spider_ctl_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("卸载中控实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            acts_list = []
            for mysql_inst in cluster["remote_objs"]:
                exec_act_kwargs.exec_ip = mysql_inst.machine.ip
                exec_act_kwargs.cluster = {"backend_port": mysql_inst.port}
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_uninstall_mysql_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("卸载mysql实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 阶段4 清空相关集群云信息；相关的cmdb注册信息
            sub_pipeline.add_act(
                act_name=_("清理db_meta元信息"),
                act_component_code=SpiderDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=SpiderDBMeta.tendb_cluster_destroy.__name__,
                        cluster={"id": cluster_id},
                    )
                ),
            )

            # # 阶段5 判断是否清理机器级别配置
            # exec_act_kwargs.exec_ip = cluster["remote_ip_list"] + cluster["spider_ip_list"]
            # exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_clear_machine_crontab.__name__
            # sub_pipeline.add_act(
            #     act_name=_("清理机器级别配置"),
            #     act_component_code=MySQLClearMachineComponent.code,
            #     kwargs=asdict(exec_act_kwargs),
            # )

            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("下架TenDB-Cluster集群[{}]").format(cluster["name"]))
            )

        spider_destroy_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        spider_destroy_pipeline.run_pipeline(is_drop_random_user=False)
