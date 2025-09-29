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
from backend.db_meta.models import AppCache, BKCity, Cluster, Machine, ProxyInstance, StorageInstance
from backend.db_report.models import FailoverDrillReport
from backend.db_services.redis.autofix.enums import DBHASwitchResult
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket
from backend.utils.basic import generate_root_id

from ..common.failover_drill_base import BaseFailoverDrill, FailoverDrillTargetType
from .utils import send_drill_alert_to_qywx

DOMAIN_PREFIX: str = "cache"


class RedisFailoverDrillTaskStatus:
    # Pre-DBHA Status
    NO_CLUSTER = "no drill cluster"
    ABNORMAL_CLUSTER = "drill cluster abnormal"
    CLUSTER_ERROR = "cluster error"

    # Post-DBHA Status
    SWITCH_FAILED = "switch failed"
    SWITCHED_NO_AUTOFIX = "switched but autofix not generated"
    SWITCHED_AUTOFIX_ERROR = "switched but autofix failed"

    SUCCESS = "succeeded"


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
        instance_type: FailoverDrillTargetType,
    ):
        self.main_task_id = generate_root_id()
        self.labels = labels
        self.city = city
        self.bk_biz_id = bk_biz_id
        self.bk_cloud_id = bk_cloud_id
        self.city_map = city_map
        self.failover_drill_info = {}
        self.instance_type = instance_type
        self.init_report()

    @staticmethod
    def cluster_type() -> str:
        return ClusterType.TendisTwemproxyRedisInstance.value

    def init_report(self):
        FailoverDrillReport.objects.create(
            bk_biz_id=self.bk_biz_id,
            bk_cloud_id=self.bk_cloud_id,
            status=False,
            main_task_id=self.main_task_id,
            cluster_domain=self.get_immute_domain(),
            cluster_type=self.cluster_type(),
            city=self.city,
            instance_type=self.instance_type,
        )

    def get_immute_domain(self):
        """
        集群域名
        """
        app_cache = AppCache.objects.get(bk_biz_id=self.bk_biz_id)
        biz_name = app_cache.db_app_abbr
        cluster_name = self.get_cluster_name()
        return "{}.{}.{}.db".format(DOMAIN_PREFIX, cluster_name, biz_name)

    def get_instance_info(self, cluster, instance_type) -> dict:
        """
        根据选择目标角色返回IP和城市信息
        """
        match instance_type:
            case FailoverDrillTargetType.PROXY:
                ip = ProxyInstance.objects.filter(cluster=cluster).first().machine.ip
            case FailoverDrillTargetType.BACKEND:
                ip = (
                    cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER).first().machine.ip
                )
            case _:
                raise ValueError(f"Invalid instance role: {instance_type}, available roles: `proxy`, `backend`")

        logical_city_id = BKCity.objects.get(
            bk_idc_city_id=Machine.objects.get(ip=ip, bk_cloud_id=self.bk_cloud_id).bk_city_id
        ).logical_city_id

        return {
            "ip": ip,
            "logical_city_id": logical_city_id,
        }

    def get_failover_drill_params(self):
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
                        "main_task_id": self.main_task_id,
                        "cluster_id": cluster.id,
                        "bk_cloud_id": cluster.bk_cloud_id,
                        "cluster_type": cluster.cluster_type,
                        "types": [self.instance_type],
                        self.instance_type: self.get_instance_info(cluster, self.instance_type),
                    }
                ]
            }
        )

    def get_drill_ip(self):
        """
        获取演练目标主机的ip
        目前Redis演练只对一台Proxy或Backend进行
        """
        if self.instance_type == FailoverDrillTargetType.PROXY:
            return self.failover_drill_info["drill_infos"][0]["proxy"]["ip"]
        elif self.instance_type == FailoverDrillTargetType.BACKEND:
            return self.failover_drill_info["drill_infos"][0]["backend"]["ip"]
        else:
            raise ValueError("Proxy or backend is not set in failover drill info")

    def create_run_failover_drill_ticket(self):
        """
        构建参数，创建并执行容灾演练单据，返回待观察的实例
        """
        self.get_failover_drill_params()
        FailoverDrillReport.objects.filter(main_task_id=self.main_task_id).update(
            drill_info=_("容灾演练单据执行信息： {}").format(self.failover_drill_info)
        )
        Ticket.create_ticket(
            ticket_type=TicketType.REDIS_FAILOVER_DRILL,
            creator="dba",
            bk_biz_id=self.bk_biz_id,
            remark=_("容灾演练单据执行"),
            details=self.failover_drill_info,
            auto_execute=True,
        )

    def get_drill_instances(self):
        """
        获取演练实例
        """
        drill_ip = self.get_drill_ip()

        try:
            machine = Machine.objects.get(ip=drill_ip, bk_cloud_id=self.bk_cloud_id)
        except Machine.DoesNotExist:
            raise Machine.DoesNotExist(f"Machine with IP {drill_ip} and cloud_id {self.bk_cloud_id} does not exist")

        instance_model_map = {
            FailoverDrillTargetType.PROXY: ProxyInstance,
            FailoverDrillTargetType.BACKEND: StorageInstance,
        }

        instance_model = instance_model_map.get(self.instance_type)
        if not instance_model:
            raise ValueError(
                f"Invalid instance type: {self.instance_type}. " f"Valid types: {list(instance_model_map.keys())}"
            )

        instances = instance_model.objects.filter(machine=machine)
        return {f"{instance.machine.ip}:{instance.port}" for instance in instances}

    def get_dbha_info(self):
        """
        For Redis, this returns:
        dbha_infos: {
            "<ip>:<port>": <dbha_info>,
            "error": "",
        }
        """
        drill_instances = self.get_drill_instances()

        drill_ip = self.get_drill_ip()
        dbha_infos = {
            "error": "",
        }
        try:
            resp = self.get_dbha_switch_data()
            code = resp["code"]
            msg = resp["msg"]

            if code == 0:
                resp_data = resp["data"]
                for d in resp_data:
                    if d["ip"] == drill_ip or d["slave_ip"] == drill_ip:
                        key = "{}:{}".format(drill_ip, d["port"])  # slave_port == port
                        drill_instances.remove(key)
                        dbha_infos[key] = d
            else:
                dbha_infos["error"] += "HADB service query failed. code:{} msg:{}\n".format(code, msg)
        except Exception as e:
            dbha_infos["error"] += "HADB service query error:{}\n".format(e)

        queue_status = len(drill_instances) == 0
        if not queue_status:
            dbha_infos["error"] += "Not all instances is in the switch queue: {}\n".format(drill_instances)

        return dbha_infos, queue_status

    def update_drill_report(self, dbha_infos):
        """
        更新 DBHA 信息
        """
        instances = self.get_drill_instances()
        rpt = FailoverDrillReport.objects.get(main_task_id=self.main_task_id)

        start_times = []
        finished_times = []
        dbha_status = True

        for key, content in dbha_infos.items():
            if key in instances:
                rpt.dbha_info += f"{content}\n"
                dbha_status = content.get("status", DBHASwitchResult.FAIL) == DBHASwitchResult.SUCC and dbha_status

                switch_start_time = content.get("switch_start_time")
                if switch_start_time is not None:
                    start_times.append(switch_start_time)

                switch_finished_time = content.get("switch_finished_time")
                if switch_finished_time is not None:
                    finished_times.append(switch_finished_time)

        if len(dbha_infos["error"]) != 0:
            rpt.dbha_info += f"error found: {dbha_infos['error']}\n"

        rpt.dbha_status = dbha_status  # dbha status
        rpt.switch_start_time = min(start_times) if start_times else None
        rpt.switch_finished_time = max(finished_times) if finished_times else None

    def send_alert(self, failure_reason: str, task_status: str):
        send_drill_alert_to_qywx(
            city=self.city,
            bk_biz_id=self.bk_biz_id,
            cluster_domain=self.get_immute_domain(),
            instance_type=self.instance_type,
            drill_ip=self.get_drill_ip(),
            failure_reason=failure_reason,
            task_status=task_status,
        )
