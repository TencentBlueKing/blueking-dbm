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
from typing import Dict, List

from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import BKCity, Cluster, Machine, ProxyInstance
from backend.db_report.models import FailoverDrillReport
from backend.db_services.redis.autofix.enums import DBHASwitchResult
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket
from backend.utils.basic import generate_root_id

from ..common.failover_drill_base import BaseFailoverDrill

DBATEST_BIZ_NAME: str = "dbatest"


class RedisFailoverDrill(BaseFailoverDrill):
    """
    Redis容灾演练
    """

    def __init__(
        self,
        city: str,
        labels: List[str],
        bk_biz_id: int,
        bk_cloud_id: int,
        city_map: Dict,
    ):
        self.main_task_id = generate_root_id()
        self.labels = labels
        self.city = city
        self.bk_biz_id = bk_biz_id
        self.bk_cloud_id = bk_cloud_id
        self.city_map = city_map
        self.failover_drill_info = {}
        self.init_report()

    @staticmethod
    def cluster_type() -> str:
        return ClusterType.TendisTwemproxyRedisInstance.value

    def get_immute_domain(self):
        """
        集群域名
        """
        cluster_name = self.get_cluster_name()
        return "failover.{}.{}.db".format(cluster_name, DBATEST_BIZ_NAME)

    def get_instance_info(self, cluster, instance_role) -> dict:
        """
        根据选择目标角色返回IP和城市信息
        """
        match instance_role:
            case "proxy":
                ip = ProxyInstance.objects.filter(cluster=cluster).first().machine.ip
            case "backend":
                ip = (
                    cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER).first().machine.ip
                )
            case _:
                raise ValueError(f"Invalid instance role: {instance_role}, available roles: `proxy`, `backend`")

        logical_city_id = BKCity.objects.get(
            bk_idc_city_id=Machine.objects.get(ip=ip, bk_cloud_id=self.bk_cloud_id).bk_city_id
        ).logical_city_id

        return {
            "ip": ip,
            "logical_city_id": logical_city_id,
        }

    def get_failover_drill_prarams(self, target_type):
        """
        Redis容灾演练单据参数
        """
        try:
            domain = self.get_immute_domain()
            cluster = Cluster.objects.get(bk_biz_id=self.bk_biz_id, immute_domain=domain, bk_cloud_id=self.bk_cloud_id)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(immute_domain=domain, bk_biz_id=self.bk_biz_id, message=_("集群不存在"))

        self.failover_drill_info.update(
            {
                "drill_infos": [
                    {
                        "cluster_id": cluster.id,
                        "bk_cloud_id": cluster.bk_cloud_id,
                        "cluster_type": cluster.cluster_type,
                        "types": [target_type],
                        target_type: self.get_instance_info(cluster, target_type),
                    }
                ]
            }
        )

    def get_drill_ip(self):
        """
        获取演练目标主机的ip
        目前Redis演练只对一台Proxy或Backend进行
        """
        if "proxy" in self.failover_drill_info["drill_infos"][0]:
            return self.failover_drill_info["drill_infos"][0]["proxy"]["ip"]
        elif "backend" in self.failover_drill_info["drill_infos"][0]:
            return self.failover_drill_info["drill_infos"][0]["backend"]["ip"]
        else:
            raise ValueError("Proxy or backend is not set in failover drill info")

    def create_run_failover_drill_ticket(self, target_type):
        """
        构建参数，创建并执行容灾演练单据
        """
        self.get_failover_drill_prarams(target_type)
        report = FailoverDrillReport.objects.get(main_task_id=self.main_task_id)
        report.drill_info = _("容灾演练单据执行信息： {}".format(self.failover_drill_info))
        report.save()
        Ticket.create_ticket(
            ticket_type=TicketType.REDIS_FAILOVER_DRILL,
            creator="dba",
            bk_biz_id=self.bk_biz_id,
            remark=_("容灾演练单据执行"),
            details=self.failover_drill_info,
            auto_execute=True,
        )

    def get_dbha_info(self):
        drill_ip = self.get_drill_ip()
        dbha_info = ""
        dbha_status = DBHASwitchResult.FAIL.value
        flag = False
        try:
            resp = self.get_dbha_switch_data()
            code = resp["code"]
            msg = resp["msg"]

            if code == 0:
                resp_data = resp["data"]
                for d in resp_data:
                    if d["ip"] == drill_ip or d["slave_ip"] == drill_ip:
                        dbha_info += "{}\n".format(d)
                        flag = True
            else:
                dbha_info += "HADB service query failed. code:{} msg:{}\n".format(code, msg)
        except Exception as e:
            dbha_info += "HADB service query error:{}\n".format(e)

        if flag:
            dbha_status = DBHASwitchResult.SUCC.value

        return dbha_info, dbha_status, dbha_status == DBHASwitchResult.SUCC.value
