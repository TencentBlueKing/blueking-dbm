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

from typing import Dict, List, Tuple

from backend.flow.consts import ClusterNodeFailStatus, RedisLinkStatus, RedisRole, RedisSlotNum, RedisSlotSep
from backend.utils.redis import is_valid_ip


def decode_slots_from_str(
    slot_str: str, seq: str
) -> Tuple[List[int], Dict[int, bool], Dict[int, str], Dict[int, str]]:
    """
    DecodeSlotsFromStr 解析 slot 字符串,如 0-10,12,100-200,seq为','
    同时可以解析:
    migrating slot: ex: [42->-67ed2db8d677e59ec4a4cefb06858cf2a1a89fa1]
    importing slot: ex: [42-<-67ed2db8d677e59ec4a4cefb06858cf2a1a89fa1]
    """
    slot_map = {}
    migrating_slots = {}
    importing_slots = {}
    items = []
    slot = 0
    if seq == "" or seq == " " or seq == "\t" or seq == "\n":
        items = slot_str.split()
    else:
        items = slot_str.split(seq)
    for slot_item in items:
        slot_item = slot_item.strip()
        list02 = slot_item.split(RedisSlotSep.SLOT_SEPARATOR.value)
        if len(list02) == 3:
            separator = RedisSlotSep.SLOT_SEPARATOR.value + list02[1] + RedisSlotSep.SLOT_SEPARATOR.value
            slot = int(list02[0].lstrip("[").rstrip("]"))
            if separator == RedisSlotSep.IMPORTING_SEPARATOR.value:
                importing_slots[slot] = list02[2].rstrip("]")
            elif separator == RedisSlotSep.MIGRATING_SEPARATOR:
                migrating_slots[slot] = list02[2].rstrip("]")
            else:
                raise Exception("impossible to decode slotStr:{}".format(slot_item))
        elif len(list02) == 1:
            num01 = int(list02[0])
            if num01 < RedisSlotNum.MIN_SLOT.value or num01 > RedisSlotNum.MAX_SLOT.value:
                raise Exception(
                    "slot:{} in param:{} not correct,valid range [{},{}]".format(
                        num01,
                        slot_str,
                        RedisSlotNum.MIN_SLOT.value,
                        RedisSlotNum.MAX_SLOT.value,
                    )
                )
            slot_map[num01] = True
        elif len(list02) == 2:
            start = int(list02[0])
            end = int(list02[1])
            if start < RedisSlotNum.MIN_SLOT.value or start > RedisSlotNum.MAX_SLOT.value:
                raise Exception(
                    "slot:{} in param:{} not correct,valid range [{},{}]".format(
                        start,
                        slot_str,
                        RedisSlotNum.MIN_SLOT.value,
                        RedisSlotNum.MAX_SLOT.value,
                    )
                )
            if end < RedisSlotNum.MIN_SLOT.value or end > RedisSlotNum.MAX_SLOT.value:
                raise Exception(
                    "slot:{} in param:{} not correct,valid range [{},{}]".format(
                        end,
                        slot_str,
                        RedisSlotNum.MIN_SLOT.value,
                        RedisSlotNum.MAX_SLOT.value,
                    )
                )
            for num01 in range(start, end + 1):
                slot_map[num01] = True
    return list(slot_map.keys()), slot_map, migrating_slots, importing_slots


def convert_slot_to_str(slots: List[int]) -> str:
    """
    将slots:[0,1,2,3,4,10,11,12,13,17] 按照 0-4,10-13,17 打印
    """
    if len(slots) == 0:
        return ""
    str01 = ""
    start = slots[0]
    curr = slots[0]
    for item in slots:
        next = item
        if next == curr:
            continue
        if curr == next - 1:
            curr = next
            continue
        if start == curr:
            str01 = "{},{}".format(str01, start)
        else:
            str01 = "{},{}-{}".format(str01, start, curr)
        start = next
        curr = next
    if start == curr:
        str01 = "{},{}".format(str01, start)
    else:
        str01 = "{},{}-{}".format(str01, start, curr)
    str01 = str01.strip(",")
    return str01


class ClusterNodeData:
    """
    保存redis cluster节点信息
    与'cluster nodes'命令返回的信息对应
    """

    def __init__(self):
        self.node_id = ""
        self.addr = ""
        self.ip = ""
        self.port = 0
        self.cport = 0
        self.role = ""
        self.is_myself = False
        self.link_state = ""
        self.master_id = ""
        self.fail_status = []
        self.ping_sent = 0
        self.pong_recv = 0
        self.config_epoch = 0
        self.slot_src_str = ""
        self.slots = []
        self.slots_map = {}
        self.migrating_slots = {}
        self.importing_slots = {}

    def __str__(self):
        return (
            "Redis ID:{},Addr:{},role:{},master:{},link:{},status:{},slots:{},"
            "migratingSlotsCnt:{},importingSlotsCnt:{}".format(
                self.node_id,
                self.addr,
                self.get_role(),
                self.master_id,
                self.link_state,
                self.fail_status,
                convert_slot_to_str(self.slots),
                len(self.migrating_slots),
                len(self.importing_slots),
            )
        )

    def set_role(self, flags):
        self.role = ""
        vals = flags.split(",")
        for val in vals:
            if val == RedisRole.MASTER.value:
                self.role = RedisRole.MASTER.value
            elif val == RedisRole.SLAVE.value:
                self.role = RedisRole.SLAVE.value

        if self.role == "":
            raise Exception(f"node setRole failed,addr:{self.addr},flags:{flags}")

    def get_role(self):
        if self.role == RedisRole.MASTER.value:
            return RedisRole.MASTER.value
        elif self.role == RedisRole.SLAVE.value:
            return RedisRole.SLAVE.value
        else:
            if self.master_id != "":
                return RedisRole.SLAVE.value
            if len(self.slots) > 0:
                return RedisRole.MASTER.value

        return RedisRole.UNKNOWN.value

    @property
    def slot_cnt(self):
        return len(self.slots)

    def set_link_status(self, status):
        self.link_state = ""
        if status == RedisLinkStatus.CONNECTED.value:
            self.link_state = RedisLinkStatus.CONNECTED.value
        elif status == RedisLinkStatus.DISCONNECTED.value:
            self.link_state = RedisLinkStatus.CONNECTED.value

        if self.link_state == "":
            raise Exception(f"Node SetLinkStatus failed,addr:{self.addr},status:{status}")

    def set_failure_status(self, flags):
        self.fail_status = []
        vals = flags.split(",")
        for val in vals:
            if val == ClusterNodeFailStatus.FAIL.value:
                self.fail_status.append(ClusterNodeFailStatus.FAIL.value)
            elif val == ClusterNodeFailStatus.PFAIL.value:
                self.fail_status.append(ClusterNodeFailStatus.PFAIL.value)
            elif val == ClusterNodeFailStatus.HANDSHAKE.value:
                self.fail_status.append(ClusterNodeFailStatus.HANDSHAKE.value)
            elif val == ClusterNodeFailStatus.NOADDR.value:
                self.fail_status.append(ClusterNodeFailStatus.NOADDR.value)
            elif val == ClusterNodeFailStatus.NOFLAGS.value:
                self.fail_status.append(ClusterNodeFailStatus.NOFLAGS.value)

    def set_referent_master(self, ref):
        self.master_id = ""
        if ref == "-":
            return
        self.master_id = ref

    def is_running(self):
        return len(self.fail_status) == 0 and self.link_state == RedisLinkStatus.CONNECTED.value


def decode_cluster_nodes(input: str) -> List[ClusterNodeData]:
    """
    解析redis cluster nodes命令返回的信息
    与'cluster nodes'命令返回的信息对应
    """
    infos = []
    lines = input.split("\n")
    for line in lines:
        values = line.split()
        if len(values) < 8:
            # last line is always empty
            # not enough values in line split, skip line
            continue
        else:
            node = ClusterNodeData()

            node.node_id = values[0]
            # remove trailing port for cluster internal protocol
            ipPort: list = values[1].split("@")
            node.addr = ipPort[0]
            if node.addr != "":
                list02 = node.addr.split(":")
                if is_valid_ip(list02[0]):
                    node.ip = list02[0]
                else:
                    l01 = node.addr.split(".")
                    if len(l01) > 0:
                        node.ip = l01[0]
                node.port = int(list02[1])
            node.cport = int(ipPort[1])
            node.set_role(values[2])
            node.set_failure_status(values[2])
            node.set_referent_master(values[3])
            node.ping_sent = int(values[4])
            node.pong_recv = int(values[5])
            node.config_epoch = int(values[6])
            node.set_link_status(values[7])

            for slot in values[8:]:
                if node.slot_src_str == "":
                    node.slot_src_str = slot
                else:
                    node.slot_src_str = f"{node.slot_src_str} {slot}"
                slots01, _, importing_slots, migrating_slots = decode_slots_from_str(slot, " ")
                node.slots.extend(slots01)
                for s01 in slots01:
                    node.slots_map[s01] = True
                for s01, nodeid in importing_slots.items():
                    node.importing_slots[s01] = nodeid
                for s01, nodeid in migrating_slots.items():
                    node.migrating_slots[s01] = nodeid

            if values[2].startswith("myself"):
                node.is_myself = True
            infos.append(node)

    return infos


def get_masters_with_slots(input: str) -> List[ClusterNodeData]:
    """
    获取所有有slots的master节点
    """
    nodes = decode_cluster_nodes(input)
    masters = []
    for node in nodes:
        if node.get_role() == RedisRole.MASTER.value and node.slot_cnt > 0:
            masters.append(node)
    return masters


def group_slaves_by_master_id(input: str) -> Dict[str, List[ClusterNodeData]]:
    """
    按照master id分组slave节点
    """
    nodes = decode_cluster_nodes(input)
    masters = {}
    for node in nodes:
        if node.get_role() == RedisRole.SLAVE.value:
            if node.master_id in masters:
                masters[node.master_id].append(node)
            else:
                masters[node.master_id] = [node]
    return masters


class CmdClusterInfo:
    def __init__(self):
        self.cluster_state = ""
        self.cluster_slots_assigned = 0
        self.cluster_slots_ok = 0
        self.cluster_slots_pfail = 0
        self.cluster_slots_fail = 0
        self.cluster_known_nodes = 0
        self.cluster_zize = 0
        self.cluster_current_epoch = 0
        self.cluster_my_epoch = 0
        self.cluster_stats_messages_pingsent = 0
        self.cluster_stats_messages_pongsent = 0
        self.cluster_stats_messages_meetsent = 0
        self.cluster_stats_messages_publishsent = 0
        self.cluster_stats_messages_updatesent = 0
        self.cluster_stats_messages_sent = 0
        self.cluster_stats_messages_ping_received = 0
        self.cluster_stats_messages_pong_received = 0
        self.cluster_stats_messages_meet_received = 0
        self.cluster_stats_messages_update_received = 0
        self.cluster_stats_messages_received = 0

    def __str__(self) -> str:
        return (
            "cluster_state:{},"
            "cluster_slots_assigned:{},"
            "cluster_slots_ok:{},"
            "cluster_slots_pfail:{},"
            "cluster_known_nodes:{},"
            "cluster_zize:{},"
            "cluster_current_epoch:{},"
            "cluster_my_epoch:{},"
            "cluster_stats_messages_pingSent:{},"
            "cluster_stats_messages_pongSent:{},"
            "cluster_stats_messages_meetSent:{},"
            "cluster_stats_messages_publishSent:{},"
            "cluster_stats_messages_updateSent:{},"
            "cluster_stats_messages_sent:{},"
            "cluster_stats_messages_ping_received:{},"
            "cluster_stats_messages_pong_received:{},"
            "cluster_stats_messages_meet_received:{},"
            "cluster_stats_messages_update_received:{},"
            "cluster_stats_messages_received:{}".format(
                self.cluster_state,
                self.cluster_slots_assigned,
                self.cluster_slots_ok,
                self.cluster_slots_pfail,
                self.cluster_known_nodes,
                self.cluster_zize,
                self.cluster_current_epoch,
                self.cluster_my_epoch,
                self.cluster_stats_messages_pingsent,
                self.cluster_stats_messages_pongsent,
                self.cluster_stats_messages_meetsent,
                self.cluster_stats_messages_publishsent,
                self.cluster_stats_messages_updatesent,
                self.cluster_stats_messages_sent,
                self.cluster_stats_messages_ping_received,
                self.cluster_stats_messages_pong_received,
                self.cluster_stats_messages_meet_received,
                self.cluster_stats_messages_update_received,
                self.cluster_stats_messages_received,
            )
        )


def decode_cluster_info(cmd_ret: str):
    """
    解析redis 'cluster info'命令返回的信息
    """
    cluster_info = CmdClusterInfo()
    list01 = cmd_ret.split("\n")
    for item01 in list01:
        item01 = item01.strip()
        if len(item01) == 0:
            continue
        list02 = item01.split(":", 1)
        if len(list02) < 2:
            continue
        if list02[0] == "cluster_state":
            cluster_info.cluster_state = list02[1]
        elif list02[0] == "cluster_slots_assigend":
            cluster_info.cluster_slots_assigned = int(list02[1])
        elif list02[0] == "cluster_slots_ok":
            cluster_info.cluster_slots_ok = int(list02[1])
        elif list02[0] == "cluster_slots_pfail":
            cluster_info.cluster_slots_pfail = int(list02[1])
        elif list02[0] == "cluster_known_nodes":
            cluster_info.cluster_known_nodes = int(list02[1])
        elif list02[0] == "cluster_size":
            cluster_info.cluster_zize = int(list02[1])
        elif list02[0] == "cluster_current_epoch":
            cluster_info.cluster_current_epoch = int(list02[1])
        elif list02[0] == "cluster_my_epoch":
            cluster_info.cluster_my_epoch = int(list02[1])
        elif list02[0] == "cluster_stats_messages_ping_sent":
            cluster_info.cluster_stats_messages_pingsent = int(list02[1])
        elif list02[0] == "cluster_stats_messages_pong_sent":
            cluster_info.cluster_stats_messages_pongsent = int(list02[1])
        elif list02[0] == "cluster_stats_messages_meet_sent":
            cluster_info.cluster_stats_messages_meetsent = int(list02[1])
        elif list02[0] == "cluster_stats_messages_sent":
            cluster_info.cluster_stats_messages_sent = int(list02[1])
        elif list02[0] == "cluster_stats_messages_ping_received":
            cluster_info.cluster_stats_messages_ping_received = int(list02[1])
        elif list02[0] == "cluster_stats_messages_pong_received":
            cluster_info.cluster_stats_messages_pong_received = int(list02[1])
        elif list02[0] == "cluster_stats_messages_meet_received":
            cluster_info.cluster_stats_messages_meet_received = int(list02[1])
        elif list02[0] == "cluster_stats_messages_update_received":
            cluster_info.cluster_stats_messages_update_received = int(list02[1])
        elif list02[0] == "cluster_stats_messages_received":
            cluster_info.cluster_stats_messages_received = int(list02[1])
    return cluster_info
