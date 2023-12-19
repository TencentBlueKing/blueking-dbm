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
import datetime
import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext as _

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import DBType
from backend.configuration.models.dba import DBAdministrator
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta import api
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache, Cluster
from backend.db_periodic_task.local_tasks.db_meta.constants import QUERY_TEMPLATE, UNIFY_QUERY_PARAMS
from backend.db_report.enums import DbmonHeartbeatReportSubType
from backend.db_report.models import DbmonHeartbeatReport

logger = logging.getLogger("root")


def check_dbmon_heart_beat():
    _check_dbmon_heart_beat()


def query_by_cluster_dimension(cluster_domain, cap_key="heartbeat", cluster_type="dbmon"):
    logger.info("+===+++++=== cluster is: {} +++++===++++ ".format(cluster_domain))
    query_template = QUERY_TEMPLATE.get(cluster_type)
    if not query_template:
        logger.error("No query template for cluster type: %s,cluster name: %s", cluster_type, cluster_domain)
        return {}
    # now-5/15m ~ now
    end_time = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(minutes=query_template["range"])
    params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["start_time"] = int(start_time.timestamp())
    params["end_time"] = int(end_time.timestamp())
    # 设置要查询的 cluster_domain 变量
    params["query_configs"][0]["promql"] = query_template[cap_key].format(cluster_domain=cluster_domain)
    try:
        series = BKMonitorV3Api.unify_query(params, use_admin=True)["series"]
    except Exception as e:
        logger.error(f"Error occurred while doing  BKMonitorV3Api.unify_query(: {e}")
        raise NotImplementedError("{} get dbmon heartbeat failed from BKMonitorV3Api ".format(cluster_domain))

    dbmon_heartbeat_data = []
    for item in series:
        found = False
        # 获取的五个点，如果有一个为1，则认为心跳上报正常，如果都不为1则，心跳异常
        for value, time in item["datapoints"]:
            if value == 1:
                dbmon_heartbeat_data.append({"dimensions": item["dimensions"], "time": time, "value": value})
                found = True
                break
        if not found:
            dbmon_heartbeat_data.append(
                {"dimensions": item["dimensions"], "time": item["datapoints"][-1][1], "value": None}
            )
    return dbmon_heartbeat_data


def get_report_subtype_for_storage(cluster_type):
    if cluster_type == ClusterType.TwemproxyTendisSSDInstance.value:
        heart_beat_subtype = DbmonHeartbeatReportSubType.REDIS_SSD.value
    elif cluster_type == ClusterType.TendisPredixyTendisplusCluster.value:
        heart_beat_subtype = DbmonHeartbeatReportSubType.TENDISPLUS.value
    elif cluster_type == ClusterType.TendisTwemproxyRedisInstance.value:
        heart_beat_subtype = DbmonHeartbeatReportSubType.REDIS_CACHE.value
    else:
        raise NotImplementedError("Dbmon Not supported tendis type:{}".format(cluster_type))
    return heart_beat_subtype


def get_report_subtype_for_proxy(cluster_type):
    if cluster_type in [ClusterType.TwemproxyTendisSSDInstance.value, ClusterType.TendisTwemproxyRedisInstance.value]:
        heart_beat_subtype = DbmonHeartbeatReportSubType.TWEMPROXY.value
    elif cluster_type == ClusterType.TendisPredixyTendisplusCluster.value:
        heart_beat_subtype = DbmonHeartbeatReportSubType.PREDIXY.value
    else:
        raise NotImplementedError("Dbmon Not supported tendis type:{}".format(cluster_type))
    return heart_beat_subtype


def _check_dbmon_heart_beat():
    """
    获取dbmon心跳信息
    """
    # 构建查询条件:tendisplus,ssd,cache,集群创建时间大于2小时，刚开始可能上报有延时，超时时间好像是2小时
    query = (
        Q(cluster_type=ClusterType.TendisPredixyTendisplusCluster)
        | Q(cluster_type=ClusterType.TwemproxyTendisSSDInstance)
        | Q(cluster_type=ClusterType.TendisTwemproxyRedisInstance)
        | Q(create_at__gt=timezone.now() - timedelta(hours=2))
    )
    # 遍历集群
    for c in Cluster.objects.filter(query):
        logger.info("+===+++++===  start check {} dbmon heartbeat +++++===++++ ".format(c.immute_domain))
        logger.info("+===+++++===  cluster type is: {} +++++===++++ ".format(c.cluster_type))
        # 初始化集群机器列表
        cluster_nodes = []
        try:
            cluster_info = api.cluster.nosqlcomm.other.get_cluster_detail(c.id)[0]
        except Exception as e:
            logger.error(f"Error occurred while getting cluster_info: {e}")
            raise NotImplementedError("{} get cluster_info failed".format(c.immute_domain))
        cluster_nodes.extend(cluster_info["redis_master_ips_set"])
        cluster_nodes.extend(cluster_info["redis_slave_ips_set"])
        cluster_nodes.extend(cluster_info["twemproxy_ips_set"])
        logger.info("+===+++++===  cluster all nodes  is: {} +++++===++++ ".format(cluster_nodes))
        try:
            # 通过bk_biz_id获取dba列表,业务没设置的话，用平台的配置
            redis_dba = DBAdministrator().get_biz_db_type_admins(c.bk_biz_id, DBType.Redis)
            app = AppCache.objects.get(bk_biz_id=c.bk_biz_id).db_app_abbr
        except Exception as e:
            logger.error(f"Error occurred while getting redis_dba and app: {e}")
            raise NotImplementedError("{} get redis_dba and ap failed".format(c.immute_domain))

        # 按集群查询
        #   这样子可能结果为[],整个集群都没数据 dbmon_heartbeat_data:[]
        #   也有可能部分ip没有数据
        #   通过集合拿到缺失心跳的ip
        dbmon_heartbeat_data = query_by_cluster_dimension(c.immute_domain)
        # 缺失心跳的或者心跳为None的
        missing_heartbeat_ips = set(cluster_nodes) - {
            data["dimensions"]["target"] for data in dbmon_heartbeat_data if data["value"] == 1
        }
        logger.warning(_("+===+++++=== missing_heartbeat_ips 实例:{}  +++++===++++ ".format(missing_heartbeat_ips)))
        for ip in missing_heartbeat_ips:
            # 如果是后端存储节点，再区分cache ,ssd ,tendisplus
            if ip in cluster_info["redis_master_ips_set"] or ip in cluster_info["redis_slave_ips_set"]:
                heart_beat_subtype = get_report_subtype_for_storage(c.cluster_type)
                # 获取端口范围：30000-30010
                port_ranges = []
                if ip in cluster_info["redis_master_ips_set"]:
                    redis_set = cluster_info["redis_master_set"]
                elif ip in cluster_info["redis_slave_ips_set"]:
                    redis_set = cluster_info["redis_slave_set"]
                else:
                    raise NotImplementedError("Dbmon ip:{} not in cluster:{}".format(ip, c.immute_domain))
                # ssd 和cache 有segment，tendisplus没有
                for item in redis_set:
                    if item.startswith(ip):
                        if c.cluster_type in [
                            ClusterType.TwemproxyTendisSSDInstance.value,
                            ClusterType.TendisTwemproxyRedisInstance.value,
                        ]:
                            # 格式为 "ip:port range"
                            ip_port, range = item.split(" ")
                            ip, port = ip_port.split(IP_PORT_DIVIDER)
                            port_ranges.append(port)
                        elif c.cluster_type == ClusterType.TendisPredixyTendisplusCluster.value:
                            # 格式为 "ip:port"
                            ip, port = item.split(IP_PORT_DIVIDER)
                            port_ranges.append(port)
                        else:
                            raise NotImplementedError("Dbmon Not supported tendis type:{}".format(c.cluster_type))
                if len(port_ranges) > 1:
                    start_port = min(port_ranges)
                    end_port = max(port_ranges)
                    port_range = f"{start_port}-{end_port}"
                # tendisplus 后面线上是部署1个实例
                elif len(port_ranges) == 1:
                    port_range = port_ranges
                else:
                    raise NotImplementedError(
                        "Dbmon ip:{} not get port_ranges for cluster:{}".format(ip, c.immute_domain)
                    )
                instance = "{} {}".format(ip, port_range)
            # 如果是代理proxy，再区分是twemproxy还是predixy
            elif ip in cluster_info["twemproxy_ips_set"]:
                twemproxy_ports = cluster_info.get("twemproxy_ports", [])
                instance = "{} {}".format(ip, twemproxy_ports[0])
                heart_beat_subtype = get_report_subtype_for_proxy(c.cluster_type)
            else:
                raise NotImplementedError(" %s is not identified in Dbmon" % ip)
            msg = _("实例 {} dbmon 心跳超时").format(instance)
            try:
                # 心跳超时的时间点就用这条记录的创建时间代替了，这里对时间要求不严格
                DbmonHeartbeatReport.objects.create(
                    creator=c.creator,
                    bk_biz_id=c.bk_biz_id,
                    bk_cloud_id=c.bk_cloud_id,
                    status=False,
                    msg=msg,
                    cluster_type=heart_beat_subtype,
                    cluster=c.immute_domain,
                    instance=instance,
                    app=app,
                    dba=redis_dba,
                )
                logger.warning(_("+===+++++=== 实例 {} dbmon 心跳超时  +++++===++++ ".format(instance)))
            except Exception as e:
                logger.error(f"Error occurred while inserting data: {e}")
                raise NotImplementedError("{} insert data failed".format(c.immute_domain))
