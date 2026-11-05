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
from copy import deepcopy
from typing import Dict, List

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import AppCache, BKCity, Cluster, Machine, ProxyInstance, StorageInstance
from backend.db_periodic_task.constants import FailoverDrillVersion
from backend.db_report.enums import ReportStateType
from backend.db_report.models import FailoverDrillReport
from backend.db_services.redis.autofix.enums import DBHASwitchResult
from backend.db_services.redis.util import is_support_redis_auotfix
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket
from backend.utils.basic import generate_root_id

from ..common.failover_drill_base import BaseFailoverDrill, DrillTarget, FailoverDrillTargetType
from .utils import send_drill_alert_to_qywx

DOMAIN_PREFIX: str = "cache"

V1_DRILL_CLUSTER_TYPES = [ClusterType.TendisTwemproxyRedisInstance.value]
# v2 演练覆盖所有支持自愈的 Redis 集群类型
V2_DRILL_CLUSTER_TYPES = [ct.value for ct in ClusterType.redis_cluster_types() if is_support_redis_auotfix(ct.value)]
# 没有接入层的集群类型，不做 proxy 演练
PROXYLESS_CLUSTER_TYPES = {ClusterType.TendisRedisInstance.value}


class RedisFailoverDrillTaskStatus:
    # Pre-DBHA Status
    NO_CLUSTER = "no drill cluster"
    NO_CLUSTER_DOMAIN = "no drill cluster domain configured"
    ABNORMAL_CLUSTER = "drill cluster abnormal"
    CLUSTER_ERROR = "cluster error"
    NO_DBHA_V2_SERVICE_IP = "dbha-v2 service ip unavailable"

    # Post-DBHA Status
    DBHA_QUERY_FAILED = "dbha switch queue query failed"
    SWITCH_FAILED = "switch failed"
    SWITCHED_NO_AUTOFIX = "switched but autofix not generated"
    SWITCHED_AUTOFIX_ERROR = "switched but autofix failed"

    SUCCESS = "succeeded"


UNKNOWN_CITY = "-"


def build_drill_targets(conf: Dict) -> List[DrillTarget]:
    """
    按配置生成演练目标：
    - v1：每个城市一个目标，cache.failover-drill-{城市缩写}.{业务缩写}.db，忽略 cluster_domain
    - v2：一行配置对应一个专用演练集群，恒为一个目标；域名为空时由演练单元终止并告警，城市由演练主机解析
    """
    version = conf.get("version") or FailoverDrillVersion.V1.value
    if version == FailoverDrillVersion.V2:
        return [DrillTarget(city="", immute_domain=(conf.get("cluster_domain") or "").strip())]

    biz_abbr = AppCache.objects.get(bk_biz_id=conf["bk_biz_id"]).db_app_abbr
    return [
        DrillTarget(city=city, immute_domain="{}.failover-drill-{}.{}.db".format(DOMAIN_PREFIX, abbr, biz_abbr))
        for city, abbr in conf["city_map"].items()
    ]


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
        version: str = FailoverDrillVersion.V1.value,
        immute_domain: str = "",
        cluster_type: str = ClusterType.TendisTwemproxyRedisInstance.value,
    ):
        self.main_task_id = generate_root_id()
        self.drill_cluster_type = cluster_type
        self.labels = labels
        # 指定域名的演练不带城市，待拿到演练主机后再解析
        self.resolve_city = not city
        self.city = city or UNKNOWN_CITY
        self.bk_biz_id = bk_biz_id
        self.bk_cloud_id = bk_cloud_id
        self.city_map = city_map
        self.version = version
        self.immute_domain = immute_domain
        self.failover_drill_info = {}
        self.instance_type = instance_type
        self.target_instances = []
        self.init_report()

    def cluster_type(self) -> str:
        return self.drill_cluster_type

    def init_report(self):
        FailoverDrillReport.objects.create(
            bk_biz_id=self.bk_biz_id,
            bk_cloud_id=self.bk_cloud_id,
            state=ReportStateType.ABNORMAL,
            dbha_status=DBHASwitchResult.INFO,
            main_task_id=self.main_task_id,
            cluster_domain=self.get_immute_domain(),
            cluster_type=self.cluster_type(),
            city=self.city,
            instance_type=self.instance_type,
            version=self.version,
        )

    def get_immute_domain(self):
        """
        集群域名，v2 只认配置的域名，不回退到 v1 命名规则
        """
        if self.immute_domain or self.version == FailoverDrillVersion.V2:
            return self.immute_domain
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

    def resolve_city_by_ip(self, ip: str) -> str:
        try:
            bk_city_id = Machine.objects.get(ip=ip, bk_cloud_id=self.bk_cloud_id).bk_city_id
            return BKCity.objects.get(bk_idc_city_id=bk_city_id).logical_city.name
        except Exception:  # pylint: disable=broad-except
            return UNKNOWN_CITY

    def get_drill_logical_city_id(self):
        return self.failover_drill_info["drill_infos"][0][self.instance_type]["logical_city_id"]

    def cluster_filters(self) -> Dict:
        """
        演练集群的查询条件：v1 要求业务/云区域/类型都与配置一致；v2 的云区域取自集群，不参与校验
        """
        filters = {
            "immute_domain": self.get_immute_domain(),
            "bk_biz_id": self.bk_biz_id,
            "cluster_type": self.cluster_type(),
        }
        if self.version != FailoverDrillVersion.V2:
            filters["bk_cloud_id"] = self.bk_cloud_id
        return filters

    def adopt_cluster_cloud(self, cluster: Cluster):
        """
        v2 的云区域以演练集群为准，并回写报告
        """
        if self.version != FailoverDrillVersion.V2 or self.bk_cloud_id == cluster.bk_cloud_id:
            return
        self.bk_cloud_id = cluster.bk_cloud_id
        FailoverDrillReport.objects.filter(main_task_id=self.main_task_id).update(bk_cloud_id=self.bk_cloud_id)

    def get_failover_drill_params(self):
        """
        Redis容灾演练单据参数
        """
        filters = self.cluster_filters()
        try:
            cluster = Cluster.objects.get(**filters)
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(
                immute_domain=filters["immute_domain"], bk_biz_id=self.bk_biz_id, message=_("集群不存在")
            )
        self.adopt_cluster_cloud(cluster)

        self.failover_drill_info.update(
            {
                "drill_infos": [
                    {
                        "main_task_id": self.main_task_id,
                        "cluster_id": cluster.id,
                        "bk_cloud_id": cluster.bk_cloud_id,
                        "cluster_type": cluster.cluster_type,
                        "dbha_version": self.version,
                        "types": [self.instance_type],
                        self.instance_type: self.get_instance_info(cluster, self.instance_type),
                    }
                ]
            }
        )

        if self.resolve_city:
            self.city = self.resolve_city_by_ip(self.get_drill_ip())
            FailoverDrillReport.objects.filter(main_task_id=self.main_task_id).update(city=self.city)

    def get_drill_ip(self):
        """
        获取演练目标主机的ip
        目前Redis演练只对一台Proxy或Backend进行
        """
        if not self.failover_drill_info:
            return "<IP not set>"
        if self.instance_type not in FailoverDrillTargetType.valid_types():
            raise ValueError(_(f"Invalid instance_type: {self.instance_type}"))

        return self.failover_drill_info["drill_infos"][0][self.instance_type]["ip"]

    def create_run_failover_drill_ticket(self):
        """
        构建参数，创建并执行容灾演练单据，返回待观察的实例
        """
        if not self.failover_drill_info:
            self.get_failover_drill_params()
        self.target_instances = (
            self.get_drill_instances()
        )  # For later checks, in case targets are switched and deleted.
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
            "query_failed": bool,  # 切换队列查询本身失败，结果不能说明 DBHA 是否切换
        }
        """
        drill_instances = deepcopy(self.target_instances)
        drill_ip = self.get_drill_ip()
        dbha_infos = {
            "error": "",
            "query_failed": False,
        }
        try:
            resp = self.get_dbha_switch_data()
            code = resp["code"]
            msg = resp["msg"]

            if code == 0:
                resp_data = resp["data"]
                for d in resp_data:
                    if drill_ip in (d.get("ip"), d.get("slave_ip")):
                        key = "{}:{}".format(drill_ip, d["port"])  # slave_port == port
                        drill_instances.discard(key)
                        # 同一实例可能有多条切换记录，优先保留成功的那条
                        if dbha_infos.get(key, {}).get("status") != DBHASwitchResult.SUCC:
                            dbha_infos[key] = d
            else:
                dbha_infos["query_failed"] = True
                dbha_infos["error"] += "HADB service query failed. code:{} msg:{}\n".format(code, msg)
        except Exception as e:
            dbha_infos["query_failed"] = True
            dbha_infos["error"] += "HADB service query error:{}\n".format(e)

        queue_status = len(drill_instances) == 0
        if not queue_status:
            dbha_infos["error"] += "Not all instances is in the switch queue: {}\n".format(drill_instances)

        return dbha_infos, queue_status

    def update_drill_report(self, dbha_infos):
        """
        更新 DBHA 信息
        """
        instances = deepcopy(self.target_instances)
        rpt = FailoverDrillReport.objects.get(main_task_id=self.main_task_id)

        start_times = []
        finished_times = []
        switch_results = []

        for key, content in dbha_infos.items():
            if key in instances:
                rpt.dbha_info += f"{content}\n"
                switch_results.append(content.get("status", DBHASwitchResult.FAIL) == DBHASwitchResult.SUCC)

                switch_start_time = content.get("switch_start_time")
                if switch_start_time is not None:
                    start_times.append(switch_start_time)

                switch_finished_time = content.get("switch_finished_time")
                if switch_finished_time is not None:
                    finished_times.append(switch_finished_time)

        if len(dbha_infos["error"]) != 0:
            rpt.dbha_info += f"error found: {dbha_infos['error']}\n"

        # 查询失败或切换队列无匹配记录时没有切换结果，不能记为成功
        dbha_status = bool(switch_results) and all(switch_results)
        rpt.dbha_status = DBHASwitchResult.SUCC if dbha_status else DBHASwitchResult.FAIL
        rpt.switch_start_time = min(start_times) if start_times else None
        rpt.switch_finished_time = max(finished_times) if finished_times else None
        rpt.save(
            update_fields=[
                "dbha_info",
                "dbha_status",
                "switch_start_time",
                "switch_finished_time",
            ]
        )

    def send_alert(self, failure_reason: str, task_status: str):
        send_drill_alert_to_qywx(
            city=self.city,
            bk_biz_id=self.bk_biz_id,
            cluster_domain=self.get_immute_domain(),
            instance_type=self.instance_type,
            drill_ip=self.get_drill_ip(),
            failure_reason=failure_reason,
            task_status=task_status,
            version=self.version,
        )
