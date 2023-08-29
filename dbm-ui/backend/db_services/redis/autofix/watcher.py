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
from typing import Dict, List

from django.utils.translation import ugettext as _

from backend.components.hadb.client import HADBApi
from backend.db_meta import api
from backend.exceptions import ApiRequestError, ApiResultError
from backend.utils.redis import RedisConn
from backend.utils.string import gen_random_str
from backend.utils.time import datetime2timestamp

from .const import REDIS_SWITCH_WAITER, SWITCH_MAX_WAIT_SECONDS, SWITCH_SMALL, RedisSwitchHost, RedisSwitchWait
from .enums import AutofixItem, AutofixStatus, DBHASwitchResult
from .models import RedisAutofixCore, RedisAutofixCtl, RedisIgnoreAutofix

logger = logging.getLogger("root")


def watcherGetByHosts() -> (int, dict):
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
        switch_logs = HADBApi.switch_logs(params={"sw_id": switch_id})
    except (ApiResultError, ApiRequestError, Exception) as error:  # pylint: disable=broad-except
        # 捕获ApiResultError, ApiRequestError和其他未知异常
        logger.warn("meet exception {}  when request switch logs".format(error))
        return 0, {}

    switch_hosts, batch_small_id = {}, SWITCH_SMALL
    for switch_log in switch_logs:
        swith_ip = switch_log["ip"]
        switch_id = int(switch_log["sw_id"])  # uid / sw_id
        if not switch_hosts.get(swith_ip):
            cluster = api.meta.query_cluster_by_hosts([swith_ip])  # return: [{},{}]
            if not cluster:
                logger.info("will ignore got none cluster info by ip {}".format(swith_ip))
                continue
            elif len(cluster) > 1:
                logger.info("will ignore got two+ cluster info by ip {} : {}".format(swith_ip, cluster))
                continue
            one_cluster = cluster[0]

            switch_hosts[swith_ip] = RedisSwitchHost(
                bk_biz_id=one_cluster["bk_biz_id"],
                cluster_id=one_cluster["cluster_id"],
                immute_domain=one_cluster["cluster"],
                cluster_type=one_cluster["cluster_type"],
                instance_type=one_cluster["instance_role"],
                bk_host_id=one_cluster["bk_host_id"],
                cluster_ports=one_cluster["cs_ports"],
                ip=swith_ip,
                switch_ports=[],
                sw_max_id=0,
                sw_min_id=SWITCH_SMALL,
                sw_result={},
            )
        current_host = switch_hosts[swith_ip]
        current_host.switch_ports.append(switch_log["port"])
        current_host.sw_result[switch_log["result"]] = switch_log["port"]

        # 这台机器的Max值
        if switch_id > current_host.sw_max_id:
            current_host.sw_max_id = switch_id
        # 本轮的small值
        if switch_id < batch_small_id:
            batch_small_id = switch_id
        # 这台机器的small值
        if switch_id < current_host.sw_min_id:
            current_host.sw_min_id = switch_id
    logger.info(
        "get smallest switchID {} from {} , with hosts : {}".format(batch_small_id, switch_id, switch_hosts.keys())
    )
    return batch_small_id, switch_hosts


def get4NextWatchID(batch_small: int, switch_hosts: Dict) -> int:
    succ_max_uid, wait_small_uid, ignore_max_uid = batch_small, 0, SWITCH_SMALL
    now_timestamp = datetime2timestamp(datetime.datetime.now())
    for swiched_host in switch_hosts.values():
        # 已经全部切换
        if (
            len(swiched_host.cluster_ports) == len(swiched_host.switch_ports)
            and len(swiched_host.sw_result) == 1
            and swiched_host.sw_result.get(DBHASwitchResult.SUCC.value)
        ):
            logger.info(
                "machine {} {} all instance swithed success -_- ".format(swiched_host.ip, swiched_host.switch_ports)
            )
            if swiched_host.sw_max_id > succ_max_uid:
                succ_max_uid = swiched_host.sw_max_id + 1
            continue
        # 需要等待切换
        logger.info(
            "machine {} {} NOT all instance swithed success ! {}".format(
                swiched_host.ip, swiched_host.switch_ports, swiched_host.sw_result
            )
        )
        waiter = REDIS_SWITCH_WAITER.get(swiched_host.ip)
        if not waiter:
            REDIS_SWITCH_WAITER[swiched_host.ip] = RedisSwitchWait(
                ip=swiched_host,
                err=swiched_host.sw_result,
                entry=datetime2timestamp(datetime.datetime.now()),
                counter=1,
            )
            logger.info(
                "machine {} {} NOT all instance swithed , need wait seconds {}".format(
                    swiched_host.ip, swiched_host.switch_ports, swiched_host.sw_result
                )
            )
            if wait_small_uid < swiched_host.sw_min_id:
                wait_small_uid = swiched_host.sw_min_id
            continue
        elif (now_timestamp - waiter.entry) > SWITCH_MAX_WAIT_SECONDS:
            if (now_timestamp - waiter.entry) > SWITCH_MAX_WAIT_SECONDS * 6:
                waiter.entry = now_timestamp
                waiter.counter = 1
                waiter.err = ""
                logger.info(
                    "machine {} {} NOT all instance swithed , need wait seconds.".format(
                        swiched_host.ip, swiched_host.switch_ports
                    )
                )
                if wait_small_uid < swiched_host.sw_min_id:
                    wait_small_uid = swiched_host.sw_min_id
                continue
            # 等待切换超时
            logger.info(
                "machine {} {} NOT all instance swithed , wait timeout entry time : {} {}".format(
                    swiched_host.ip, swiched_host.switch_ports, waiter.entry, swiched_host.sw_result
                )
            )
            # save ignore swithed host
            saveIgnoreHost(swiched_host, "wait_timeout")
            if ignore_max_uid > swiched_host.sw_max_id:
                ignore_max_uid = swiched_host.sw_max_id
        else:
            logger.info(
                "machine {} {} NOT all instance swithed , continue wait entry time : {} {}".format(
                    swiched_host.ip, swiched_host.switch_ports, waiter.entry, swiched_host.sw_result
                )
            )
            if wait_small_uid < swiched_host.sw_min_id:
                wait_small_uid = swiched_host.sw_min_id
            waiter.counter = waiter.counter + 1

    # end for
    next_watch_id = succ_max_uid
    logger.warn(
        "get watch uids, ignore_max_uid:{},wait_small_uid:{},next_watch_id:{},switch_hosts:{},waiter:{}".format(
            ignore_max_uid, wait_small_uid, next_watch_id, switch_hosts.keys(), waiter
        )
    )
    if ignore_max_uid > succ_max_uid and ignore_max_uid != SWITCH_SMALL:
        logger.info("set next watch id from {} ==> {} , it has ignore item ".format(next_watch_id, ignore_max_uid))
        next_watch_id = ignore_max_uid

    if succ_max_uid > wait_small_uid and wait_small_uid != 0:
        logger.info("set next watch id from {} ==> {} , it has wait item ".format(next_watch_id, wait_small_uid))
        next_watch_id = wait_small_uid

    return next_watch_id


def saveSwithedHostByCluster(batch_small: int, switch_hosts: Dict):
    switched_cluster = {}
    for swiched_host in switch_hosts.values():
        if swiched_host.sw_max_id < batch_small:
            cluster = swiched_host.immute_domain
            if not switched_cluster.get(cluster):
                switched_cluster[cluster] = {
                    "bk_biz_id": swiched_host.bk_biz_id,
                    "cluster_id": swiched_host.cluster_id,
                    "cluster_type": swiched_host.cluster_type,
                    "immute_domain": cluster,
                    "fault_machines": [],
                    "deal_status": AutofixStatus.AF_TICKET.value,
                    "status_version": gen_random_str(12),
                }
            switched_cluster[cluster]["fault_machines"].append(
                {"instance_type": swiched_host.instance_type, "ip": swiched_host.ip}
            )

    for cluster in switched_cluster.values():
        logger.info(
            "autofix cluster {} with hosts {} begin".format(cluster["immute_domain"], cluster["fault_machines"])
        )
        RedisAutofixCore.objects.create(
            bk_cloud_id=0,
            bk_biz_id=cluster["bk_biz_id"],
            cluster_id=cluster["cluster_id"],
            immute_domain=cluster["immute_domain"],
            cluster_type=cluster["cluster_type"],
            fault_machines=json.dumps(cluster["fault_machines"]),
            deal_status=cluster["deal_status"],
            status_version=cluster["status_version"],
        ).save()


def saveIgnoreHost(switched_host: RedisSwitchHost, msg):
    RedisIgnoreAutofix.objects.create(
        bk_cloud_id=0,
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
    ).save()
