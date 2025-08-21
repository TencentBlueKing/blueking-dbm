"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks.mysql_failover_drill.failover_drill import MysqlFailoverDrill
from backend.db_report.models import FailoverDrillReport
from backend.db_services.redis.autofix.enums import DBHASwitchResult
from backend.flow.engine.controller.spider import SpiderController
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


class TendbclusterFailoverDrill(MysqlFailoverDrill):
    """
    1、资源申请
    2、集群上架
    3、dbha触发
    4、集群禁用
    5、集群下架
    6、资源退回资源池
    """

    def init_report(self):
        # 默认任务是失败的，只有跑到最后才确认状态为True
        FailoverDrillReport.objects.create(
            bk_biz_id=self.bk_biz_id,
            bk_cloud_id=self.bk_cloud_id,
            status=False,
            main_task_id=self.main_task_id,
            cluster_domain=self.get_immute_domain(),
            cluster_type=ClusterType.TenDBCluster.value,
            city=self.city,
            dhha_status=DBHASwitchResult.FAIL.value,
        )

    def get_immute_domain(self):
        """
        @return:主从域名
        """
        cluster_name = self.get_cluster_name()
        db = "spider.{}.dbatest.db".format(cluster_name)
        return [db]

    def get_tendbcluster_cluster_apply_data(self):
        """
        集群搭建参数
        spider 参数不一样
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
                "ticket_type": "TENDBCLUSTER_APPLY",
                "uid": self.apply_root_id,
                "cluster_shard_num": 2,
                "remote_shard_num": 2,
                "remote_group": [
                    {
                        "master": {
                            "ip": self.resource_info["db_1"]["ip"],
                            "bk_host_id": self.resource_info["db_1"]["bk_host_id"],
                            "bk_biz_id": self.bk_biz_id,
                            "bk_cloud_id": self.bk_cloud_id,
                        },
                        "slave": {
                            "ip": self.resource_info["db_2"]["ip"],
                            "bk_host_id": self.resource_info["db_2"]["bk_host_id"],
                            "bk_biz_id": self.bk_biz_id,
                            "bk_cloud_id": self.bk_cloud_id,
                        },
                    }
                ],
                "spider_port": 25000,
                "spider_version": "Spider-3",
                "spider_ip_list": [
                    {
                        "ip": self.resource_info["proxy_1"]["ip"],
                        "bk_host_id": self.resource_info["proxy_1"]["bk_host_id"],
                        "bk_biz_id": self.bk_biz_id,
                        "bk_cloud_id": self.bk_cloud_id,
                    },
                    {
                        "ip": self.resource_info["proxy_2"]["ip"],
                        "bk_host_id": self.resource_info["proxy_2"]["bk_host_id"],
                        "bk_biz_id": self.bk_biz_id,
                        "bk_cloud_id": self.bk_cloud_id,
                    },
                ],
                "cluster_name": self.get_cluster_name(),
                "immutable_domain": self.get_immute_domain()[0],
            }
        )

    def tendbcluster_cluster_apply(self):
        """
        搭建容灾测试集群
        直接构建参数，拉起集群搭建flow
        @return:
        """
        self.get_tendbcluster_cluster_apply_data()
        SpiderController(root_id=self.apply_root_id, ticket_data=self.apply_cluster_info).spider_cluster_apply_scene()

    def get_failover_drill_data(self):
        """
        容灾演练执行参数
        spider 参数不一样
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
                        "spider": self.get_instance_info(cluster, "spider"),
                        "types": ["remote_master", "spider"],
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

    def get_tendbcluster_disable_data(self):
        """
        集群禁用执行参数
        spider 参数不一样
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
                "ticket_type": "TENDBCLUSTER_DISABLE",
                "force": False,
                "uid": self.disable_root_id,
                "is_only_add_slave_domain": False,
                "is_only_delete_slave_domain": False,
            }
        )

    def tendbcluster_cluster_disable(self):
        """
        集群禁用
        @return:
        """
        self.get_tendbcluster_disable_data()
        SpiderController(root_id=self.disable_root_id, ticket_data=self.disable_info).spider_cluster_disable_scene()

    def get_tendbcluster_destroy_data(self):
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
                "ticket_type": "TENDBCLUSTER_DESTROY",
                "force": False,
                "uid": self.destroy_root_id,
            }
        )

    def tendbcluster_cluster_destroy(self):
        """
        销毁容灾测试集群
        因为无法依赖自愈去恢复集群，直接销毁，下次演练再重建
        直接构建参数，拉起集群销毁flow
        上报完容灾演练信息再回收集群
        @return:
        """
        self.get_tendbcluster_destroy_data()
        # 单独执行下架流程前，保存资源信息，用于后面的资源池回退
        self.get_reimport_info()
        # 销毁前也再保存一份演练的参数信息用于手动修复执行时存取演练演练信息
        self.get_failover_drill_data()
        SpiderController(root_id=self.destroy_root_id, ticket_data=self.destroy_info).spider_cluster_destroy_scene()
