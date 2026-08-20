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
import traceback
from typing import Dict

from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _

from backend import env
from backend.components.hadb.client import HADBApi
from backend.configuration.constants import DBType, RedisFastRecoverEnum
from backend.configuration.models.dba import DBAdministrator
from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_meta.api.cluster.apis import query_cluster_by_hosts_biz
from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.db_meta.models import Cluster, ProxyInstance
from backend.exceptions import ApiRequestError, ApiResultError
from backend.ticket.constants import SwitchConfirmType, TicketType
from backend.ticket.models import Ticket
from backend.utils.time import datetime2timestamp

from .const import SWITCH_MAX_WAIT_SECONDS, SWITCH_SMALL, RedisSwitchHost
from .enums import AutofixItem, AutofixStatus, DBHASwitchResult
from .global_msg import GetOrSaveSwitchWait, NeedStartAutofix
from .message import get_ticket_heplers, send_msg_2_qywx
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


# 一但有IP 的所有实例完成切换, 那么就先对他发起自愈,没有的继续等
def check_and_process(batch_small: int, switch_hosts: Dict):
    """
    1. 检查IP 是否所有实例完成切换
    2. 检查30分钟内,是否已经发起过自愈
    3. 完全切换 & 没有发起自愈的---> 送入自愈队列
    4. 拿到需要等待的最小ID,等待进行下一次检查
    """
    succ_max_uid, wait_small_uid, ignore_max_uid, will_autofix = batch_small, 0, SWITCH_SMALL, {}
    now_timestamp = datetime2timestamp(datetime.datetime.now(timezone.utc))
    succ_cnt, wait_cnt, ignore_cnt = 0, 0, 0
    for swiched_host in switch_hosts.values():
        logger.info(
            "range check_and_process succ_max_uid:{}, wait_small_uid:{}, ignore_max_uid:{} ==".format(
                succ_max_uid, wait_small_uid, ignore_max_uid
            )
        )
        if (  # 这个IP 已经全部切换
            len(swiched_host.cluster_ports) == len(swiched_host.switch_ports)
            and len(swiched_host.sw_result) == 1
            and swiched_host.sw_result.get(DBHASwitchResult.SUCC.value)
        ):
            logger.info("machine all instance swithed success -_- {} {} ".format(swiched_host.ip, swiched_host))
            succ_cnt += 1
            # check if aleardy autofixed .
            try:
                if NeedStartAutofix(swiched_host):
                    will_autofix[swiched_host.ip] = swiched_host
                    logger.info("autofix_will_start ip:{}".format(swiched_host.ip))
                else:
                    logger.info("autofix_aleardy_started, this time will ignore :{}".format(swiched_host.ip))
            except Exception as e:
                # 单个IP处理异常不应影响其他IP，特别是不能影响其他成功IP进入自愈表
                logger.error(
                    "NeedStartAutofix failed for ip:{}, err:{}\n{}".format(swiched_host.ip, e, traceback.format_exc())
                )
            # 推进下一批轮询ID
            if succ_max_uid < swiched_host.sw_max_id:
                succ_max_uid = swiched_host.sw_max_id
        else:  # 没有切换完成的
            waiter = GetOrSaveSwitchWait(swiched_host.ip, swiched_host.sw_result)
            if (now_timestamp - float(waiter["start"])) > SWITCH_MAX_WAIT_SECONDS * 5:
                # 等待切换超时
                logger.info(
                    "machine NOT all instance swithed ,{} {}  wait timeout entry time : {} {}".format(
                        swiched_host.ip, swiched_host.switch_ports, waiter, swiched_host
                    )
                )
                ignore_cnt += 1
                swiched_host.ignore_fix = True
                # save ignore swithed host
                # 单个IP的忽略/建单异常不能中断整个循环，否则会导致同批次的成功IP无法落自愈表
                try:
                    save_ignore_host(swiched_host, "wait_timeout")
                except Exception as e:
                    logger.error(
                        "save_ignore_host failed for ip:{}, err:{}\n{}".format(
                            swiched_host.ip, e, traceback.format_exc()
                        )
                    )
                if wait_small_uid < swiched_host.sw_max_id:  # 不等了，跳过去
                    wait_small_uid = swiched_host.sw_max_id
            else:
                wait_cnt += 1
                logger.info(
                    "waiting switched_host:{} tobe all succ,min_id:{},max_id:{}".format(
                        swiched_host.ip, swiched_host.sw_min_id, swiched_host.sw_max_id
                    )
                )

    if succ_cnt == len(switch_hosts):
        logger.info(
            """all host switched all_completed, entry next foreach last_batch_small:{},current:{}""".format(
                batch_small, succ_max_uid
            )
        )
        batch_small = succ_max_uid + 1
    elif succ_cnt + ignore_cnt == len(switch_hosts):
        logger.info(
            """host will skiped, entry next foreach last_batch_small:{},current:{}""".format(
                batch_small, wait_small_uid
            )
        )
        batch_small = wait_small_uid + 1
    logger.info(
        "finally switch: succ_cnt:{},wait_cnt:{},ignore_cnt:{},all_switch:{},batch_small==>{}".format(
            succ_cnt, wait_cnt, ignore_cnt, len(switch_hosts), batch_small
        )
    )
    return batch_small, will_autofix


# 根据切换信息，获取下一次探测切换队列ID
def get_4_next_watch_ID(batch_small: int, switch_hosts: Dict) -> int:
    succ_max_uid, wait_small_uid, ignore_max_uid = batch_small, 0, SWITCH_SMALL
    now_timestamp = datetime2timestamp(datetime.datetime.now(timezone.utc))
    for swiched_host in switch_hosts.values():
        logger.info(
            "range get_4_next_watch_ID succ_max_uid:{}, wait_small_uid:{}, ignore_max_uid:{} ==".format(
                succ_max_uid, wait_small_uid, ignore_max_uid
            )
        )
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
        waiter = GetOrSaveSwitchWait(swiched_host.ip, swiched_host.sw_result)
        logger.info(
            "machine {} {} NOT all instance swithed , need wait seconds {}".format(
                swiched_host.ip, swiched_host.switch_ports, waiter
            )
        )
        if waiter["counter"] == 1:
            if wait_small_uid <= swiched_host.sw_min_id:
                wait_small_uid = swiched_host.sw_min_id
            else:
                logger.info(
                    "current wait_small_uid:{}, switched_host:{},min_id:{},max_id:{}".format(
                        wait_small_uid, swiched_host.ip, swiched_host.sw_min_id, swiched_host.sw_max_id
                    )
                )
        elif (now_timestamp - float(waiter["start"])) > SWITCH_MAX_WAIT_SECONDS:
            # 等待切换超时
            logger.info(
                "machine {} {} NOT all instance swithed , wait timeout entry time : {} {}".format(
                    swiched_host.ip, swiched_host.switch_ports, waiter, swiched_host
                )
            )
            swiched_host.ignore_fix = True
            # save ignore swithed host
            save_ignore_host(swiched_host, "wait_timeout")
            if ignore_max_uid >= swiched_host.sw_max_id:
                ignore_max_uid = swiched_host.sw_max_id + 1
        else:
            logger.info(
                "waiting switched_host:{} tobe all succ,min_id:{},max_id:{}".format(
                    swiched_host.ip, swiched_host.sw_min_id, swiched_host.sw_max_id
                )
            )

    # end for
    next_watch_id = succ_max_uid
    if wait_small_uid != 0:
        if wait_small_uid < succ_max_uid:
            next_watch_id = wait_small_uid
            logger.info("need 2 wait; somthing succd:{} >, but wait_small_uid:{}".format(succ_max_uid, wait_small_uid))
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
def save_swithed_host_by_cluster(switch_hosts: Dict):
    switched_cluster = {}
    # 以集群维度聚合故障信息
    for swiched_host in switch_hosts.values():
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

        # 部分切换（有成功也有失败/info）时，辅助 DBA 提主从切换单据
        if switched_host.instance_type == InstanceRole.REDIS_MASTER.value:
            ticket_url = ""
            succ_ports = switched_host.sw_result.get(DBHASwitchResult.SUCC.value, [])
            has_partial_switch = succ_ports and len(switched_host.sw_result) > 1
            if has_partial_switch:
                ticket_url = _create_master_slave_switch_ticket(switched_host, succ_ports)
            if ticket_url:
                msgs[_("主从切换单")] = ticket_url

        # proxy 切换失败时，辅助 DBA 提 proxy 整机替换单据
        if switched_host.instance_type in (MachineType.TWEMPROXY.value, MachineType.PREDIXY.value):
            proxy_ticket_url = _create_proxy_replace_ticket(switched_host)
            if proxy_ticket_url:
                msgs[_("Proxy替换单")] = proxy_ticket_url
        send_msg_2_qywx(title, msgs)


def _create_master_slave_switch_ticket(switched_host: RedisSwitchHost, succ_ports: list) -> str:
    """
    部分切换场景下，辅助 DBA 提 REDIS_MASTER_SLAVE_SWITCH 单据。
    只对切换成功的端口构造主从切换对，返回单据链接；失败时返回空字符串。
    """
    try:
        cluster = Cluster.objects.prefetch_related("storageinstance_set", "storageinstance_set__machine").get(
            id=switched_host.cluster_id
        )

        # 找到切换成功的 master 端口对应的 master->slave 对
        pairs = []
        for master_inst in cluster.storageinstance_set.filter(
            instance_role=InstanceRole.REDIS_MASTER.value,
            machine__ip=switched_host.ip,
        ):
            if master_inst.port not in succ_ports:
                continue
            # 通过复制关系找到对应的 slave
            ejector_qs = master_inst.as_ejector.select_related("receiver__machine")
            if not ejector_qs.exists():
                logger.warning(
                    _("_create_master_slave_switch_ticket: master %s:%s 没有对应的 slave，跳过"),
                    switched_host.ip,
                    master_inst.port,
                )
                continue
            slave_inst = ejector_qs.first().receiver
            pairs.append(
                {
                    "redis_master": switched_host.ip,
                    "redis_slave": slave_inst.machine.ip,
                }
            )

        if not pairs:
            logger.warning(
                _("_create_master_slave_switch_ticket: cluster %s 没有找到有效的主从切换对，跳过提单"),
                switched_host.immute_domain,
            )
            return _("没有找到有效的主从切换对，跳过提单")

        # 去重（同一 master->slave 对可能因多端口重复）
        seen, unique_pairs = set(), []
        for p in pairs:
            key = (p["redis_master"], p["redis_slave"])
            if key not in seen:
                seen.add(key)
                unique_pairs.append(p)

        details = {
            "force": True,
            "infos": [
                {
                    "cluster_ids": [switched_host.cluster_id],
                    "online_switch_type": SwitchConfirmType.NO_CONFIRM.value,
                    "pairs": unique_pairs,
                }
            ],
        }

        redisDBA = DBAdministrator.get_biz_db_type_admins(
            bk_biz_id=switched_host.bk_biz_id, db_type=DBType.Redis.value
        )
        ticket = Ticket.create_ticket(
            bk_biz_id=switched_host.bk_biz_id,
            ticket_type=TicketType.REDIS_MASTER_SLAVE_SWITCH.value,
            creator=redisDBA.users[0],
            remark=_("自动发起-部分切换辅助提单-{}".format(switched_host.ip)),
            details=details,
            helpers=get_ticket_heplers(),
        )
        ticket_url = "{}/tickets/{}".format(env.BK_SAAS_HOST.rstrip("/"), ticket.id)
        logger.info(
            _("_create_master_slave_switch_ticket: cluster %s 提单成功 ticket_id=%s url=%s"),
            switched_host.immute_domain,
            ticket.id,
            ticket_url,
        )
        return ticket_url
    except Exception as e:
        logger.error(
            _("_create_master_slave_switch_ticket: cluster %s 提单失败:\n%s"),
            switched_host.immute_domain,
            traceback.format_exc(),
        )
        return "{}".format(e)


def _create_proxy_replace_ticket(switched_host: RedisSwitchHost) -> str:
    """
    proxy 切换失败场景下，辅助 DBA 提 REDIS_PROXY_FAST_RECOVER（Proxy剔除和修复）单据。
    对故障 proxy 机器发起整机替换（先踢掉再修复），返回单据链接；失败时返回空字符串。
    """
    try:
        # 查询 proxy 机器的 bk_host_id
        proxy_inst = (
            ProxyInstance.objects.filter(
                machine__ip=switched_host.ip,
                cluster__id=switched_host.cluster_id,
            )
            .select_related("machine")
            .first()
        )

        if not proxy_inst:
            logger.warning(
                _("_create_proxy_replace_ticket: cluster %s ip %s 没有找到 ProxyInstance，跳过提单"),
                switched_host.immute_domain,
                switched_host.ip,
            )
            return _("没有找到Proxy实例")

        bk_host_id = proxy_inst.machine.bk_host_id

        details = {
            "infos": [
                {
                    "cluster_id": switched_host.cluster_id,
                    "proxy": [{"ip": switched_host.ip, "bk_host_id": bk_host_id}],
                    "operate_type": RedisFastRecoverEnum.PROXY_ENTRY_KICKOFF.value,
                    "restart_proxy": False,
                }
            ]
        }

        redisDBA = DBAdministrator.get_biz_db_type_admins(
            bk_biz_id=switched_host.bk_biz_id, db_type=DBType.Redis.value
        )
        ticket = Ticket.create_ticket(
            bk_biz_id=switched_host.bk_biz_id,
            ticket_type=TicketType.REDIS_PROXY_FAST_RECOVER.value,
            creator=redisDBA.users[0],
            remark=_("自动发起-proxy切换失败辅助提单-{}".format(switched_host.ip)),
            details=details,
            helpers=get_ticket_heplers(),
        )
        ticket_url = "{}/tickets/{}".format(env.BK_SAAS_HOST.rstrip("/"), ticket.id)
        logger.info(
            _("_create_proxy_replace_ticket: cluster %s ip %s 提单成功 ticket_id=%s url=%s"),
            switched_host.immute_domain,
            switched_host.ip,
            ticket.id,
            ticket_url,
        )
        return ticket_url
    except Exception as e:
        logger.error(
            _("_create_proxy_replace_ticket: cluster %s ip %s 提单失败:\n%s"),
            switched_host.immute_domain,
            switched_host.ip,
            traceback.format_exc(),
        )
        return "{}".format(e)
