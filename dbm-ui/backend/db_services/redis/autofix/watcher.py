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
import datetime
import json
import logging
from typing import Dict

from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

from backend.components.hadb.client import HADBApi
from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta.api.cluster.apis import query_cluster_by_hosts_biz
from backend.db_meta.enums import ClusterType
from backend.exceptions import ApiRequestError, ApiResultError
from backend.utils.time import datetime2timestamp

from .const import REDIS_SWITCH_WAITER, SWITCH_MAX_WAIT_SECONDS, SWITCH_SMALL, RedisSwitchHost, RedisSwitchWait
from .enums import AutofixItem, AutofixStatus, DBHASwitchResult
from .message import send_msg_2_qywx
from .models import RedisAutofixCore, RedisAutofixCtl, RedisIgnoreAutofix

logger = logging.getLogger("root")


# 从切换队列拿到切换实例列表， 然后聚会成故障机器维度
def watcher_get_by_hosts() -> (int, dict):
    switch_id = 0
    try:
        switch_next = RedisAutofixCtl.objects.filter(ctl_name=AutofixItem.DBHA_ID.value).get()
        if switch_next:
            switch_id = int(switch_next.ctl_value)
    except RedisAutofixCtl.DoesNotExist:
        RedisAutofixCtl.objects.create(
            bk_cloud_id=0, bk_biz_id=0, ctl_value=0, ctl_name=AutofixItem.DBHA_ID.value
        ).save()

    logger.info("watch_dbha_switch_log from id {}".format(switch_id))
    try:
        switch_queues = HADBApi.switch_queue(
            params={"name": "query_switch_queue_by_uid", "query_args": {"uid": switch_id}}
        )
    except (ApiResultError, ApiRequestError, Exception) as error:  # pylint: disable=broad-except
        # 捕获ApiResultError, ApiRequestError和其他未知异常
        raise Exception("meet exception {}  when request switch logs".format(error))

    # 遍历切换队列，聚合故障机
    switch_hosts, batch_small_id = {}, SWITCH_SMALL
    if len(switch_queues) == 0:
        return switch_id, switch_hosts

    for switch_inst in switch_queues:
        switch_ip, switch_id = switch_inst["ip"], int(switch_inst["uid"])  # uid / sw_id
        if not switch_hosts.get(switch_ip):
            logger.info(
                "get new switched_fault_ip {}:{}, uid {}, db_type: {}:{}".format(
                    switch_ip, switch_inst["port"], switch_id, switch_inst["db_type"], switch_inst["db_role"]
                )
            )
            # 忽略没有集群信息、或者多集群共用的情况
            cluster = query_cluster_by_hosts_biz(
                [switch_ip], int(switch_inst["app"]), int(switch_inst["cloud_id"])
            )  # return: [{},{}]
            if not cluster:
                logger.info("will ignore got none cluster info by ip {}".format(switch_ip))
                continue
            one_cluster, all_ports = cluster[0], []
            for cls_obj in cluster:
                all_ports.extend(cls_obj["cs_ports"])
            switch_hosts[switch_ip] = RedisSwitchHost(
                bk_biz_id=one_cluster["bk_biz_id"],
                cluster_id=one_cluster["cluster_id"],
                immute_domain=";".join([cls_obj["cluster"] for cls_obj in cluster]),
                cluster_type=one_cluster["cluster_type"],
                instance_type=one_cluster["instance_role"],
                bk_host_id=one_cluster["bk_host_id"],
                cluster_ports=all_ports,
                ip=switch_ip,
                switch_ports=[],
                sw_max_id=0,
                sw_min_id=SWITCH_SMALL,
                ignore_fix=False,
                sw_result={},
            )

        current_host = switch_hosts[switch_ip]
        current_host.switch_ports.append(switch_inst["port"])
        if not current_host.sw_result.get(switch_inst["status"]):
            current_host.sw_result[switch_inst["status"]] = []
        current_host.sw_result[switch_inst["status"]].append(switch_inst["port"])

        # 这台机器的Max值
        if switch_id > current_host.sw_max_id:
            current_host.sw_max_id = switch_id
        # 本轮的small值
        if switch_id < batch_small_id:
            batch_small_id = switch_id
        # 这台机器的small值
        if switch_id < current_host.sw_min_id:
            current_host.sw_min_id = switch_id
    if len(switch_hosts) == 0:
        batch_small_id = switch_id
    logger.info(
        "get smallest switchID {} from {} , with hosts : {}".format(batch_small_id, switch_id, switch_hosts.keys())
    )
    return batch_small_id, switch_hosts


# 根据切换信息，获取下一次探测切换队列ID
def get_4_next_watch_ID(batch_small: int, switch_hosts: Dict) -> int:
    succ_max_uid, wait_small_uid, ignore_max_uid = batch_small, 0, SWITCH_SMALL
    now_timestamp = datetime2timestamp(datetime.datetime.now(timezone.utc))
    for swiched_host in switch_hosts.values():
        # 已经全部切换
        if (
            len(swiched_host.cluster_ports) == len(swiched_host.switch_ports)
            and len(swiched_host.sw_result) == 1
            and swiched_host.sw_result.get(DBHASwitchResult.SUCC.value)
        ):
            logger.info("machine {} {} all instance swithed success -_- ".format(swiched_host.ip, swiched_host))
            if swiched_host.sw_max_id >= succ_max_uid:
                succ_max_uid = swiched_host.sw_max_id + 1
            continue
        # 需要等待切换
        logger.info(
            "machine {} {} NOT all instance swithed success ! {}".format(
                swiched_host.ip, swiched_host.switch_ports, swiched_host
            )
        )
        waiter = REDIS_SWITCH_WAITER.get(swiched_host.ip)
        if not waiter:
            REDIS_SWITCH_WAITER[swiched_host.ip] = RedisSwitchWait(
                ip=swiched_host,
                err=swiched_host.sw_result,
                entry=datetime2timestamp(datetime.datetime.now(timezone.utc)),
                counter=1,
            )
            logger.info(
                "machine {} {} NOT all instance swithed , need wait seconds {}".format(
                    swiched_host.ip, swiched_host.switch_ports, swiched_host
                )
            )
            if wait_small_uid <= swiched_host.sw_min_id:
                wait_small_uid = swiched_host.sw_min_id
            continue
        elif (now_timestamp - waiter.entry) > SWITCH_MAX_WAIT_SECONDS:
            if (now_timestamp - waiter.entry) > SWITCH_MAX_WAIT_SECONDS * 6:
                waiter.entry = now_timestamp
                waiter.counter = 1
                waiter.err = ""
                logger.info(
                    "machine {} {} NOT all instance swithed , need wait seconds. {}".format(
                        swiched_host.ip, swiched_host.switch_ports, swiched_host
                    )
                )
                if wait_small_uid <= swiched_host.sw_min_id:
                    wait_small_uid = swiched_host.sw_min_id
                continue
            # 等待切换超时
            logger.info(
                "machine {} {} NOT all instance swithed , wait timeout entry time : {} {}".format(
                    swiched_host.ip, swiched_host.switch_ports, waiter.entry, swiched_host
                )
            )
            swiched_host.ignore_fix = True
            # save ignore swithed host
            save_ignore_host(swiched_host, "wait_timeout")
            if ignore_max_uid >= swiched_host.sw_max_id:
                ignore_max_uid = swiched_host.sw_max_id + 1
        else:
            logger.info(
                "machine {} {} NOT all instance swithed , continue wait entry time : {} {}".format(
                    swiched_host.ip, swiched_host.switch_ports, waiter.entry, swiched_host
                )
            )
            if wait_small_uid <= swiched_host.sw_min_id:
                wait_small_uid = swiched_host.sw_min_id
            waiter.counter = waiter.counter + 1

    # end for
    next_watch_id = succ_max_uid
    logger.warn(
        "get watch uids, ignore_max_uid:{},wait_small_uid:{},next_watch_id:{},switch_hosts:{}".format(
            ignore_max_uid, wait_small_uid, next_watch_id, switch_hosts.keys()
        )
    )
    if ignore_max_uid > succ_max_uid and ignore_max_uid != SWITCH_SMALL:
        logger.info("set next watch id from {} ==> {} , it has ignore item ".format(next_watch_id, ignore_max_uid))
        next_watch_id = ignore_max_uid

    if succ_max_uid > wait_small_uid and wait_small_uid != 0:
        logger.info("set next watch id from {} ==> {} , it has wait item ".format(next_watch_id, wait_small_uid))
        next_watch_id = wait_small_uid

    return next_watch_id


# 把故障切换成功后的机器/集群信息保存起来
def save_swithed_host_by_cluster(batch_small: int, switch_hosts: Dict):
    switched_cluster = {}
    # 以集群维度聚合故障信息
    for swiched_host in switch_hosts.values():
        if swiched_host.sw_max_id < batch_small and not swiched_host.ignore_fix:
            cluster = swiched_host.immute_domain
            if swiched_host.cluster_type == ClusterType.TendisRedisInstance.value:
                cluster = swiched_host.ip  # 主从集群 ； 用机器来聚合
            if not switched_cluster.get(cluster):
                switched_cluster[cluster] = {
                    "bk_biz_id": swiched_host.bk_biz_id,
                    "cluster_id": swiched_host.cluster_id,
                    "cluster_type": swiched_host.cluster_type,
                    "immute_domain": cluster,
                    "fault_machines": [],
                    "deal_status": AutofixStatus.AF_TICKET.value,
                    "status_version": get_random_string(length=12),
                }
            switched_cluster[cluster]["fault_machines"].append(
                {"instance_type": swiched_host.instance_type, "ip": swiched_host.ip}
            )
    # 按照集群维度保存信息
    for cluster in switched_cluster.values():
        logger.info(
            "autofix cluster {} with hosts {} begin".format(cluster["immute_domain"], cluster["fault_machines"])
        )
        RedisAutofixCore.objects.create(
            bk_cloud_id=DEFAULT_BK_CLOUD_ID,
            bk_biz_id=cluster["bk_biz_id"],
            cluster_id=cluster["cluster_id"],
            immute_domain=cluster["immute_domain"],
            cluster_type=cluster["cluster_type"],
            fault_machines=json.dumps(cluster["fault_machines"]),
            deal_status=cluster["deal_status"],
            status_version=cluster["status_version"],
        ).save()


# 把需要忽略自愈的保存起来
def save_ignore_host(switched_host: RedisSwitchHost, msg):
    RedisIgnoreAutofix.objects.update_or_create(
        bk_cloud_id=DEFAULT_BK_CLOUD_ID,
        bk_biz_id=switched_host.bk_biz_id,
        cluster_id=switched_host.cluster_id,
        immute_domain=switched_host.immute_domain,
        cluster_type=switched_host.cluster_type,
        cluster_ports=switched_host.cluster_ports,
        bk_host_id=switched_host.bk_host_id,
        ip=switched_host.ip,
        instance_type=switched_host.instance_type,
        switch_ports=switched_host.switch_ports,
        sw_min_id=switched_host.sw_min_id,
        sw_max_id=switched_host.sw_max_id,
        sw_result=json.dumps(switched_host.sw_result),
        ignore_msg=msg,
    )

    if switched_host.cluster_type in [
        ClusterType.TwemproxyTendisSSDInstance.value,
        ClusterType.TendisTwemproxyRedisInstance.value,
        ClusterType.TendisPredixyRedisCluster.value,
        ClusterType.TendisPredixyTendisplusCluster.value,
        ClusterType.TendisRedisInstance.value,
    ]:
        msgs, title = {}, _("{}-😢忽略自愈😓".format(switched_host.immute_domain))
        msgs[_("BKID")] = switched_host.bk_biz_id
        msgs[_("故障机器")] = switched_host.ip
        msgs[_("实例类型")] = switched_host.instance_type
        msgs[_("切换成功")] = _("{}".format((switched_host.sw_result.get("success", []))))
        msgs[_("切换失败")] = _("😩{}😭".format((switched_host.sw_result.get("failed", []))))
        send_msg_2_qywx(title, msgs)
