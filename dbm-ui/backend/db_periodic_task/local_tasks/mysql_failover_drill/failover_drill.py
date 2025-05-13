"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from django.utils.translation import ugettext as _

from backend.components.dbresource.client import DBResourceApi
from backend.components.hadb.client import HADBApi
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.exceptions import ClusterNotExistException, DBMetaException
from backend.db_meta.models import BKCity, Cluster, Machine, ProxyInstance
from backend.db_report.models.failover_drill_report import FailoverDrillReport
from backend.db_services.dbresource.exceptions import (
    ResourceApplyException,
    ResourceApplyInsufficientException,
    ResourceReturnException,
)
from backend.db_services.redis.autofix.enums import DBHASwitchResult
from backend.flow.engine.bamboo.scene.mysql.mysql_ha_disable_flow import MySQLHADisableFlow
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket.constants import ResourceApplyErrCode, TicketType
from backend.ticket.models import Ticket
from backend.utils.basic import generate_root_id


class MysqlFailoverDrill:
    """
    1、资源申请
    2、集群上架
    3、dbha触发
    4、集群禁用
    5、集群下架
    6、资源退回资源池
    """

    def __init__(
        self, city: str, labels: List[str], bk_biz_id: int, bk_cloud_id: int, db_module_id: int, city_map: Dict
    ):
        self.main_task_id = generate_root_id()
        self.resource_root_id = generate_root_id()
        self.apply_root_id = generate_root_id()
        self.disable_root_id = generate_root_id()
        self.destroy_root_id = generate_root_id()
        self.reimport_resource_id = generate_root_id()
        self.labels = labels
        self.city = city
        self.bk_biz_id = bk_biz_id
        self.bk_cloud_id = bk_cloud_id
        self.resource_info = {}
        self.db_module_id = db_module_id
        self.city_map = city_map
        self.apply_cluster_info = {}
        self.failover_drill_info = {}
        self.disable_info = {}
        self.destroy_info = {}
        self.reimport_resource_info = {}
        self.init_report()

    def init_report(self):
        # 默认任务是失败的，只有跑到最后才确认状态为True
        FailoverDrillReport.objects.create(
            bk_biz_id=self.bk_biz_id,
            bk_cloud_id=self.bk_cloud_id,
            status=False,
            main_task_id=self.main_task_id,
            cluster_domain=self.get_immute_domain(),
            cluster_type=ClusterType.TenDBHA.value,
            city=self.city,
            dhha_status=DBHASwitchResult.FAIL.value,
        )

    def get_city_abbr(self):
        """
        @return: 城市缩写
        """
        return self.city_map.get(self.city, "default")

    def get_cluster_name(self):
        """
        @return:集群名称
        """
        city_abbr = self.get_city_abbr()
        return "failover-drill-{}".format(city_abbr)

    def get_immute_domain(self):
        """
        @return:主从域名
        """
        cluster_name = self.get_cluster_name()
        db = "failover.{}.dbatest.db".format(cluster_name)
        dr = "failover.{}.dbatest.dr".format(cluster_name)
        return [db, dr]

    def apply_ha_resource(self):
        """
        资源池申请资源
        资源参数结构体
        @return:
        """
        apply_params = {
            "for_biz_id": self.bk_biz_id,
            "resource_type": "mysql",
            "details": [
                {
                    "bk_cloud_id": self.bk_cloud_id,
                    "group_mark": "backend_group",
                    "location_spec": {
                        "city": self.city,
                    },
                    "count": 4,
                    "labels": self.labels,
                },
            ],
            "task_id": self.resource_root_id,
            "bill_id": self.resource_root_id,
            "bill_type": "MYSQL_HA_APPLY",
            "operator": "dba",
        }

        resp = DBResourceApi.resource_apply(params=apply_params, raw=True)
        if resp["code"] == ResourceApplyErrCode.RESOURCE_LAKE:
            info = _("资源不足申请失败，请前往补货后重试{}").format(resp.get("message"))
            self.update_drill_report(info)
            raise ResourceApplyInsufficientException(info)
        elif resp["code"] != 0:
            info = _("资源池相关服务出现未知异常，请联系管理员处理。错误信息: [{}]{}").format(resp["code"], resp.get("message"))
            self.update_drill_report(info)
            raise ResourceApplyException(info)

        # 资源参数，用于后面集群搭建
        keys = ["db_1", "db_2", "proxy_1", "proxy_2"]
        self.resource_info.update({"city": self.get_city_abbr()})
        for i in range(len(keys)):
            self.resource_info.update(
                {
                    keys[i]: {
                        "ip": resp["data"][0]["data"][i]["ip"],
                        "bk_host_id": resp["data"][0]["data"][i]["bk_host_id"],
                    }
                }
            )

    def get_ha_cluster_apply_data(self):
        """
        集群搭建参数
        @return:
        """
        self.apply_cluster_info.update(
            {
                "bk_biz_id": self.bk_biz_id,
                "bk_cloud_id": self.bk_cloud_id,
                "charset": "utf8mb4",
                "created_by": "dba",
                "db_module_id": self.db_module_id,
                "module": str(self.db_module_id),
                "db_version": "MySQL-5.7",
                "disaster_tolerance_level": "CROS_SUBZONE",
                "city": self.city,
                "inst_num": 1,
                "start_mysql_port": 20000,
                "start_proxy_port": 10000,
                "ticket_type": "MYSQL_HA_APPLY",
                "uid": self.apply_root_id,
                "apply_infos": [
                    {
                        "clusters": [
                            {
                                "name": self.get_cluster_name(),
                                "master": self.get_immute_domain()[0],
                                "slave": self.get_immute_domain()[1],
                            }
                        ],
                        "mysql_ip_list": [
                            {
                                "bk_biz_id": self.bk_biz_id,
                                "bk_cloud_id": self.bk_cloud_id,
                                "bk_host_id": self.resource_info["db_1"]["bk_host_id"],
                                "ip": self.resource_info["db_1"]["ip"],
                            },
                            {
                                "bk_biz_id": self.bk_biz_id,
                                "bk_cloud_id": self.bk_cloud_id,
                                "bk_host_id": self.resource_info["db_2"]["bk_host_id"],
                                "ip": self.resource_info["db_2"]["ip"],
                            },
                        ],
                        "proxy_ip_list": [
                            {
                                "bk_biz_id": self.bk_biz_id,
                                "bk_cloud_id": self.bk_cloud_id,
                                "bk_host_id": self.resource_info["proxy_1"]["bk_host_id"],
                                "ip": self.resource_info["proxy_1"]["ip"],
                            },
                            {
                                "bk_biz_id": self.bk_biz_id,
                                "bk_cloud_id": self.bk_cloud_id,
                                "bk_host_id": self.resource_info["proxy_2"]["bk_host_id"],
                                "ip": self.resource_info["proxy_2"]["ip"],
                            },
                        ],
                    },
                ],
            }
        )

    def ha_cluster_apply(self):
        """
        搭建容灾测试集群
        直接构建参数，拉起集群搭建flow
        @return:
        """
        self.get_ha_cluster_apply_data()
        MySQLController(root_id=self.apply_root_id, ticket_data=self.apply_cluster_info).mysql_ha_apply_scene()

    def get_instance_info(self, cluster, instance_role: str) -> dict:
        if instance_role == "remote_master":
            # TendbCluster取查询到的第一个ip作为执行ip，只是验证功能，不关注具体实例
            ip = cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER).first().machine.ip
        elif instance_role == "spider":
            # spider类型的直接拿中控去验证
            ip = cluster.tendbcluster_ctl_primary_address().split(":")[0]
        elif instance_role == "proxy":
            # proxy取第一个，不关注具体实例
            ip = ProxyInstance.objects.filter(cluster=cluster).first().machine.ip
        else:
            raise DBMetaException(message=_("集群实例类型无法用于容灾演练"))

        logical_city_id = BKCity.objects.get(
            bk_idc_city_id=Machine.objects.get(ip=ip, bk_cloud_id=cluster.bk_cloud_id).bk_city_id
        ).logical_city_id

        return {
            "ip": ip,
            "logical_city_id": logical_city_id,
        }

    def get_failover_drill_data(self):
        """
        容灾演练执行参数
        @return:
        """
        try:
            cluster = Cluster.objects.get(
                bk_biz_id=self.bk_biz_id, immute_domain=self.get_immute_domain()[0], bk_cloud_id=self.bk_cloud_id
            )
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(
                immute_domain=self.get_immute_domain()[0], bk_biz_id=self.bk_biz_id, message=_("集群不存在")
            )

        self.failover_drill_info.update(
            {
                "drill_infos": [
                    {
                        "cluster_id": cluster.id,
                        "bk_cloud_id": cluster.bk_cloud_id,
                        "cluster_type": cluster.cluster_type,
                        "remote_master": self.get_instance_info(cluster, "remote_master"),
                        "proxy": self.get_instance_info(cluster, "proxy"),
                        "types": ["remote_master", "proxy"],
                    }
                ],
            }
        )

    def create_run_failover_drill_ticket(self):
        """
        构建参数，创建并执行容灾测试单据
        @return:
        """
        self.get_failover_drill_data()
        drill_report = FailoverDrillReport.objects.get(main_task_id=self.main_task_id)
        drill_report.drill_info = _("dbha演练执行信息：{}".format(self.failover_drill_info))
        drill_report.save()
        Ticket.create_ticket(
            ticket_type=TicketType.MYSQL_FAILOVER_DRILL,
            creator="dba",
            bk_biz_id=self.bk_biz_id,
            remark=_("容灾演练单据执行"),
            details=self.failover_drill_info,
            auto_execute=True,
        )

    def get_ha_cluster_disable_data(self):
        """
        集群禁用执行参数
        @return:
        """
        try:
            cluster = Cluster.objects.get(
                bk_biz_id=self.bk_biz_id, immute_domain=self.get_immute_domain()[0], bk_cloud_id=self.bk_cloud_id
            )
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(
                immute_domain=self.get_immute_domain()[0], bk_biz_id=self.bk_biz_id, message=_("集群不存在")
            )

        self.disable_info.update(
            {
                "bk_biz_id": self.bk_biz_id,
                "cluster_ids": [cluster.id],
                "created_by": "dba",
                "ticket_type": "MYSQL_HA_DISABLE",
                "force": False,
                "uid": self.disable_root_id,
            }
        )

    def ha_cluster_disable(self):
        """
        集群禁用
        @return:
        """
        self.get_ha_cluster_disable_data()
        MySQLHADisableFlow(root_id=self.disable_root_id, data=self.disable_info).disable_mysql_ha_flow()

    def get_ha_cluster_destroy_data(self):
        """
        集群下架参数
        @return:
        """
        try:
            cluster = Cluster.objects.get(
                bk_biz_id=self.bk_biz_id, immute_domain=self.get_immute_domain()[0], bk_cloud_id=self.bk_cloud_id
            )
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(
                immute_domain=self.get_immute_domain()[0], bk_biz_id=self.bk_biz_id, message=_("集群不存在")
            )

        self.destroy_info.update(
            {
                "bk_biz_id": self.bk_biz_id,
                "cluster_ids": [cluster.id],
                "created_by": "dba",
                "ticket_type": "MYSQL_HA_DESTROY",
                "force": False,
                "uid": self.destroy_root_id,
            }
        )

    def ha_cluster_destroy(self):
        """
        销毁容灾测试集群
        因为无法依赖自愈去恢复集群，直接销毁，下次演练再重建
        直接构建参数，拉起集群销毁flow
        上报完容灾演练信息再回收集群
        @return:
        """
        self.get_ha_cluster_destroy_data()
        # 单独执行下架流程前，保存资源信息，用于后面的资源池回退
        self.get_reimport_info()
        self.get_failover_drill_data()
        MySQLController(root_id=self.destroy_root_id, ticket_data=self.destroy_info).mysql_ha_destroy_scene()

    def get_hosts_from_db_meta(self):
        """
        用来实际从元数据表中查询机器信息
        @return:

        """
        try:
            cluster = Cluster.objects.get(
                bk_biz_id=self.bk_biz_id, immute_domain=self.get_immute_domain()[0], bk_cloud_id=self.bk_cloud_id
            )
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(
                immute_domain=self.get_immute_domain()[0], bk_biz_id=self.bk_biz_id, message=_("集群不存在")
            )

        machines = cluster.get_cluster_related_machines(cluster_ids=[cluster.id])
        hosts = []
        for machine in machines:
            info = {"ip": machine.ip, "host_id": machine.bk_host_id, "bk_cloud_id": machine.bk_cloud_id}
            hosts.append(info)

        return hosts

    def get_one_report_info(self, info):
        return {"ip": info["ip"], "host_id": info["bk_host_id"], "bk_cloud_id": info["bk_cloud_id"]}

    def get_reimport_info(self):
        if len(self.apply_cluster_info.get("apply_infos", [])) > 0:
            ip_list = (
                self.apply_cluster_info["apply_infos"][0]["mysql_ip_list"]
                + self.apply_cluster_info["apply_infos"][0]["proxy_ip_list"]
            )
            hosts = [self.get_one_report_info(info) for info in ip_list]
        else:
            hosts = self.get_hosts_from_db_meta()

        apply_params = {
            "for_biz": self.bk_biz_id,
            "bk_biz_id": self.bk_biz_id,
            "resource_type": "mysql",
            "hosts": hosts,
            "labels": ["1"],
            "task_id": self.reimport_resource_id,
            "bill_id": self.reimport_resource_id,
            "bill_type": "RESOURCE_IMPORT",
            "operator": "dba",
        }
        self.reimport_resource_info.update(apply_params)

    def reimport_ha_resource(self):
        try:
            resp = DBResourceApi.resource_import(params=self.reimport_resource_info, raw=True)
            if resp["code"] != 0:
                info = _("资源退回异常，请查看服务日志处理！错误信息: [{}]{}".format(resp["code"], resp.get["message"]))
                self.update_drill_report(info)
                raise ResourceReturnException(info)
        except Exception as e:
            info = _("资源服务请求异常，请查看服务日志处理！错误信息: {}".format(e))
            self.update_drill_report(info)
            raise ResourceReturnException(info)

    def update_drill_report(
        self, info: str, dbha_info: str = "", status: bool = False, dbha_status: str = DBHASwitchResult.FAIL.value
    ):
        drill_report = FailoverDrillReport.objects.get(main_task_id=self.main_task_id)
        drill_report.task_info = "{}\n{}".format(drill_report.task_info, info)
        drill_report.status = status
        drill_report.dbha_status = dbha_status
        drill_report.dbha_info = dbha_info
        drill_report.save()

    def get_drill_ip(self):
        drill_ip = []
        for drill_info in self.failover_drill_info["drill_infos"]:
            for t in drill_info["types"]:
                drill_ip.append(drill_info[t]["ip"])
        return drill_ip

    def get_dbha_info(self):
        drill_ip = self.get_drill_ip()
        dbha_info = ""
        dbha_status = DBHASwitchResult.FAIL.value
        finished_time = datetime.now().astimezone(timezone.utc)
        start_time = finished_time - timedelta(minutes=10)
        kwargs = {
            "cloud_id": self.bk_cloud_id,
            "app": str(self.bk_biz_id),
            "switch_start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "switch_finished_time": finished_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        flag = 0
        try:
            resp = HADBApi.switch_queue(params={"name": "query_switch_queue", "query_args": kwargs}, raw=True)
            code = resp["code"]
            msg = resp["msg"]

            if code == 0:
                resp_data = resp["data"]
                for d in resp_data:
                    for ip in drill_ip:
                        if d["ip"] == ip:
                            dbha_info += "{}\n".format(d)
                            flag += 1
            else:
                dbha_info += "HADB service query failed. code:{} msg:{}\n".format(code, msg)
        except Exception as e:
            dbha_info += "HADB service query error:{}\n".format(e)

        if flag == 2:
            dbha_status = DBHASwitchResult.SUCC.value

        return dbha_info, dbha_status
