from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.add_system_user_in_cluster import (
    AddSystemUserInClusterComponent,
)
from backend.flow.utils.mysql.mysql_act_dataclass import (
    AddSpiderSystemUserKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

# from backend.flow.utils.mysql.mysql_context_dataclass import SpiderAddTmpNodeManualContext


class SpiderAddTmpNodeFlow(object):
    """
    TODO 通过域名查找主库ip、端口、集群中spider数量
    TODO
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def __get_dbctl_master_info(self):
        """
        根据域名获取中控主节点信息
        """
        # self.data["immutable_domain"]
        dbctl_master = {"ip": "127.0.0.1", "port": 26000}
        return dbctl_master

    def __get_spider_node_num(self):
        return 10

    def __get_spider_instance_info(self):
        info = {
            "spider_instances": [],
        }
        for ip_info in self.data["spider_ip_list"]:
            info["spider_instances"].append({"host": ip_info["ip"], "port": self.data["spider_port"]})
        return info

    def spider_add_tmp_node_with_resource_pool(self):
        """
        机器通过资源池获取
        """
        pass

    def spider_add_tmp_node_with_manual_input(self):
        """
        手动输入ip
        上架spider节点，授予中控访问权限
        需要根据域名查找到中控主节点，并加入路由
        """

        pipeline = Builder(root_id=self.root_id, data=self.data)
        # 子流程
        deploy_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        # 拼接执行原子任务活动节点需要的通用的私有参数结构体
        exec_act_kwargs = ExecActuatorKwargs(
            bk_cloud_id=int(self.data["bk_cloud_id"]),
            cluster_type=ClusterType.TenDBCluster,
        )

        # 1 分发安装文件
        deploy_pipeline.add_act(
            act_name=_("下发Spider/tdbCtl介质包"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=int(self.data["bk_cloud_id"]),
                    exec_ip=[ip_info["ip"] for ip_info in self.data["spider_ip_list"]],
                    file_list=GetFileList(db_type=DBType.MySQL).spider_master_install_package(
                        spider_version=self.data["spider_version"],
                    ),
                )
            ),
        )

        # 2 初始化机器，安装crond进程
        # 获取spider ip
        exec_act_kwargs.exec_ip = [ip_info["ip"] for ip_info in self.data["spider_ip_list"]]
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_sys_init_payload.__name__
        # 此处会下发act命令，实际是调用act去执行机器初始化
        # ExecuteDBActuatorScriptComponent用来构成act命令，并通过job下发
        deploy_pipeline.add_act(
            act_name=_("初始化机器"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )

        acts_list = []
        for ip_info in self.data["spider_ip_list"]:
            exec_act_kwargs.exec_ip = ip_info["ip"]
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_deploy_mysql_crond_payload.__name__
            acts_list.append(
                {
                    "act_name": _("部署mysql-crond"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
        deploy_pipeline.add_parallel_acts(acts_list=acts_list)

        #  3 并发安装spider
        acts_list = []
        auto_incr_value = self.__get_spider_node_num() + 1
        for spider_ip in self.data["spider_ip_list"]:
            exec_act_kwargs.exec_ip = spider_ip["ip"]
            exec_act_kwargs.cluster = {
                "immutable_domain": self.data["immutable_domain"],
                "auto_incr_value": auto_incr_value,
            }
            exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_install_spider_payload.__name__
            acts_list.append(
                {
                    "act_name": _("安装Spider实例"),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(exec_act_kwargs),
                }
            )
            auto_incr_value += 1
        deploy_pipeline.add_parallel_acts(acts_list=acts_list)

        # 4 spider上授权给中控
        dbctl_master_info = self.__get_dbctl_master_info()
        deploy_pipeline.add_act(
            act_name=_("spider上对中控主节点进行授权"),
            act_component_code=AddSystemUserInClusterComponent.code,
            kwargs=asdict(AddSpiderSystemUserKwargs(ctl_master_ip=dbctl_master_info["ip"])),
        )

        # 5 在中控主节点上生成临时spider节点的路由信息tdbctl create node ... with database;
        exec_act_kwargs.cluster = self.__get_spider_instance_info()
        exec_act_kwargs.exec_ip = dbctl_master_info
        exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_add_tmp_spider_node_payload.__name__
        deploy_pipeline.add_act(
            act_name=_("中控主节点注册临时spider节点路由信息"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        pipeline.add_sub_pipeline(
            sub_flow=deploy_pipeline.build_sub_process(sub_name=_("{}添加临时spider节点".format(self.data["cluster_name"])))
        )
        pipeline.run_pipeline()
