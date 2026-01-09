"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import re
import time
from typing import Dict, List, Union

from django.utils.translation import gettext_lazy as _

from backend.components import DRSApi
from backend.db_meta.enums import AccessLayer
from backend.db_meta.models import Cluster, Machine
from backend.flow.consts import DEFAULT_REDIS_DBNUM
from backend.flow.utils.base.payload_handler import PayloadHandler


class RedisInfoService:
    """Redis信息查询服务"""

    def __init__(self, addr: str, immute_domain: str):
        """
        初始化Redis连接

        Args:
            addr: Redis主机地址
            immute_domain: 集群域名
        """
        self.addr = addr
        self.cluster_obj = Cluster.objects.get(immute_domain=immute_domain)
        self.bk_cloud_id = self.cluster_obj.bk_cloud_id
        self.machine_obj = Machine.objects.get(bk_cloud_id=self.bk_cloud_id, ip=addr.split(":")[0])
        passwd_ret = PayloadHandler.redis_get_password_by_cluster_id(self.cluster_obj.id)

        if self.machine_obj.access_layer == AccessLayer.PROXY.value:
            self.instance_password = passwd_ret.get("redis_proxy_password")
        else:
            self.instance_password = passwd_ret.get("redis_password")

    def _parse_info_section(self, section: str) -> Dict:
        """
        解析INFO命令返回的特定section
        """
        result = {}
        resp = DRSApi.redis_rpc(
            {
                "addresses": [self.addr],
                "db_num": DEFAULT_REDIS_DBNUM,
                "password": self.instance_password,
                "command": "INFO {}".format(section),
                "bk_cloud_id": self.bk_cloud_id,
            }
        )
        if not resp or len(resp) == 0:
            return result
        info_string = resp[0].get("result")

        # 按行分割
        lines = info_string.strip().split("\n")

        for line in lines:
            line = line.strip()

            # 跳过空行
            if not line:
                continue

            # 解析键值对（格式：key:value）
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                # 尝试转换为合适的数据类型
                parsed_value = self._parse_value(value)
                result[key] = parsed_value

        return result

    def _parse_value(self, value: str) -> Union[int, float, str]:
        """
        将字符串值转换为合适的数据类型
        """
        # 尝试转换为整数
        try:
            return int(value)
        except ValueError:
            pass

        # 尝试转换为浮点数
        try:
            return float(value)
        except ValueError:
            pass

        # 保持字符串
        return value

    def get_server_info(self) -> Dict:
        """
        获取Redis服务器基本信息
        """
        info = self._parse_info_section("server")
        return {
            "redis_version": info.get("redis_version", ""),
            "redis_mode": info.get("redis_mode", "standalone"),
            "os": info.get("os", ""),
            "arch_bits": info.get("arch_bits", 64),
            "process_id": info.get("process_id", 0),
            "tcp_port": info.get("tcp_port", 6379),
            "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            "uptime_in_days": info.get("uptime_in_days", 0),
            "hz": info.get("hz", 10),
            "configured_hz": info.get("configured_hz", 10),
        }

    def get_clients_info(self) -> Dict:
        """
        获取Redis客户端连接信息

        Returns:
            包含客户端信息的字典
        """
        info = self._parse_info_section("clients")
        return {
            "connected_clients": info.get("connected_clients", 0),
            "client_recent_max_input_buffer": info.get("client_recent_max_input_buffer", 0),
            "client_recent_max_output_buffer": info.get("client_recent_max_output_buffer", 0),
            "blocked_clients": info.get("blocked_clients", 0),
            "tracking_clients": info.get("tracking_clients", 0),
            "clients_in_timeout_table": info.get("clients_in_timeout_table", 0),
        }

    def get_memory_info(self) -> Dict:
        """
        获取Redis内存使用信息

        Returns:
            包含内存信息的字典
        """
        info = self._parse_info_section("memory")
        return {
            "used_memory": info.get("used_memory", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "used_memory_rss": info.get("used_memory_rss", 0),
            "used_memory_rss_human": info.get("used_memory_rss_human", "0B"),
            "used_memory_peak": info.get("used_memory_peak", 0),
            "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
            "total_system_memory": info.get("total_system_memory", 0),
            "total_system_memory_human": info.get("total_system_memory_human", "0B"),
            "used_memory_lua": info.get("used_memory_lua", 0),
            "used_memory_lua_human": info.get("used_memory_lua_human", "0B"),
            "maxmemory": info.get("maxmemory", 0),
            "maxmemory_human": info.get("maxmemory_human", "0B"),
            "maxmemory_policy": info.get("maxmemory_policy", "noeviction"),
            "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio", 1.0),
        }

    def get_persistence_info(self) -> Dict:
        """
        获取Redis持久化信息

        Returns:
            包含持久化信息的字典
        """
        info = self._parse_info_section("persistence")
        return {
            "loading": info.get("loading", 0),
            "rdb_changes_since_last_save": info.get("rdb_changes_since_last_save", 0),
            "rdb_bgsave_in_progress": info.get("rdb_bgsave_in_progress", 0),
            "rdb_last_save_time": info.get("rdb_last_save_time", 0),
            "rdb_last_bgsave_status": info.get("rdb_last_bgsave_status", "ok"),
            "rdb_last_bgsave_time_sec": info.get("rdb_last_bgsave_time_sec", -1),
            "rdb_current_bgsave_time_sec": info.get("rdb_current_bgsave_time_sec", -1),
            "aof_enabled": info.get("aof_enabled", 0),
            "aof_rewrite_in_progress": info.get("aof_rewrite_in_progress", 0),
            "aof_rewrite_scheduled": info.get("aof_rewrite_scheduled", 0),
            "aof_last_rewrite_time_sec": info.get("aof_last_rewrite_time_sec", -1),
            "aof_current_rewrite_time_sec": info.get("aof_current_rewrite_time_sec", -1),
            "aof_last_bgrewrite_status": info.get("aof_last_bgrewrite_status", "ok"),
        }

    def get_stats_info(self) -> Dict:
        """
        获取Redis统计信息

        Returns:
            包含统计信息的字典
        """
        info = self._parse_info_section("stats")
        return {
            "total_connections_received": info.get("total_connections_received", 0),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
            "total_net_input_bytes": info.get("total_net_input_bytes", 0),
            "total_net_output_bytes": info.get("total_net_output_bytes", 0),
            "instantaneous_input_kbps": info.get("instantaneous_input_kbps", 0.0),
            "instantaneous_output_kbps": info.get("instantaneous_output_kbps", 0.0),
            "rejected_connections": info.get("rejected_connections", 0),
            "sync_full": info.get("sync_full", 0),
            "sync_partial_ok": info.get("sync_partial_ok", 0),
            "sync_partial_err": info.get("sync_partial_err", 0),
            "expired_keys": info.get("expired_keys", 0),
            "evicted_keys": info.get("evicted_keys", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "pubsub_channels": info.get("pubsub_channels", 0),
            "pubsub_patterns": info.get("pubsub_patterns", 0),
        }

    def get_replication_info(self) -> Dict:
        """
        获取Redis复制信息

        Returns:
            包含复制信息的字典
        """
        info = self._parse_info_section("replication")
        result = {
            "role": info.get("role", "master"),
            "connected_slaves": info.get("connected_slaves", 0),
            "master_repl_offset": info.get("master_repl_offset", 0),
            "repl_backlog_active": info.get("repl_backlog_active", 0),
            "repl_backlog_size": info.get("repl_backlog_size", 0),
            "repl_backlog_first_byte_offset": info.get("repl_backlog_first_byte_offset", 0),
            "repl_backlog_histlen": info.get("repl_backlog_histlen", 0),
        }

        # 主节点特有字段
        if result["role"] == "master":
            result["slaves"] = self._parse_all_slaves_info(info)
            # slave0:ip=1.1.69.79,port=30000,state=online,offset=0,seq=29624230636
            result["master_replid"] = info.get("master_replid", "")
            result["master_replid2"] = info.get("master_replid2", "")
            result["second_repl_offset"] = info.get("second_repl_offset", -1)

        # 从节点特有字段
        if result["role"] == "slave":
            result["master_host"] = info.get("master_host", "")
            result["master_port"] = info.get("master_port", 0)
            result["master_link_status"] = info.get("master_link_status", "down")
            result["master_last_io_seconds_ago"] = info.get("master_last_io_seconds_ago", -1)
            result["master_sync_in_progress"] = info.get("master_sync_in_progress", 0)

        return result

    def get_cpu_info(self) -> Dict:
        """
        获取Redis CPU使用信息

        Returns:
            包含CPU信息的字典
        """
        info = self._parse_info_section("cpu")
        return {
            "used_cpu_sys": info.get("used_cpu_sys", 0.0),
            "used_cpu_user": info.get("used_cpu_user", 0.0),
            "used_cpu_sys_children": info.get("used_cpu_sys_children", 0.0),
            "used_cpu_user_children": info.get("used_cpu_user_children", 0.0),
        }

    def get_keyspace_info(self) -> List[Dict]:
        """
        获取Redis键空间信息

        Returns:
            包含所有数据库键空间信息的列表
        """
        info = self._parse_info_section("keyspace")
        result = []

        # 遍历所有数据库（db0, db1, ...）
        for key, value in info.items():
            if key.startswith("db"):
                db_index = int(key[2:])  # 提取数据库索引
                # value格式: "keys=10,expires=5,avg_ttl=1000"
                db_info = {"db_index": db_index}

                if isinstance(value, dict):
                    db_info["keys"] = value.get("keys", 0)
                    db_info["expires"] = value.get("expires", 0)
                    db_info["avg_ttl"] = value.get("avg_ttl", 0)
                else:
                    # 解析字符串格式
                    parts = value.split(",")
                    for part in parts:
                        k, v = part.split("=")
                        db_info[k] = int(v)

                result.append(db_info)

        return result

    def _parse_slave_info(self, slave_string: str) -> Dict:
        """
        解析单个从节点信息字符串
        """
        # 提取slave索引
        match = re.match(r"slave(\d+):(.*)", slave_string)
        if not match:
            raise ValueError(_("无效的slave信息格式:{}".format(slave_string)))

        slave_index = int(match.group(1))
        info_part = match.group(2)

        # 解析键值对
        result = {"slave_index": slave_index}

        pairs = info_part.split(",")
        for pair in pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                key = key.strip()
                value = value.strip()

                # 类型转换
                if key == "ip":
                    result[key] = value
                elif key == "port":
                    result[key] = int(value)
                elif key == "state":
                    result[key] = value
                elif key == "offset":
                    result[key] = int(value)
                elif key == "seq":
                    result[key] = int(value)
                else:
                    # 其他未知字段保持原样
                    result[key] = value

        return result

    def _parse_all_slaves_info(self, replication_info: Dict) -> List[Dict]:
        """
        从Redis INFO REPLICATION结果中解析所有从节点信息
        """
        slaves = []

        # 遍历所有slave键
        for key, value in replication_info.items():
            if key.startswith("slave"):
                # 构造完整的slave字符串
                slave_string = f"{key}:{value}"
                try:
                    slave_info = self._parse_slave_info(slave_string)
                    slaves.append(slave_info)
                except ValueError as e:
                    print(_("解析slave信息失败:{}".format(e)))
                    continue

        # 按slave_index排序
        slaves.sort(key=lambda x: x["slave_index"])

        return slaves

    def get_command_stats_delta(self, interval: float = 1.0) -> Dict:
        """
        获取命令统计增量信息（间隔采样）
        """
        # 第一次采样
        stats1 = self._get_command_stats()

        # 等待指定时间
        time.sleep(interval)

        # 第二次采样
        stats2 = self._get_command_stats()

        # 计算增量
        delta_stats = self._calculate_stats_delta(stats1, stats2, interval)

        return delta_stats

    def _get_command_stats(self) -> Dict:
        """
        获取当前的命令统计信息

        Returns:
            命令统计字典，key为命令名，value为统计信息
        """
        stats = {}
        info = self._parse_info_section("commandstats")

        for key, value in info.items():
            if key.startswith("cmdstat_"):
                # 提取命令名
                command = key[8:]  # 去掉 'cmdstat_' 前缀

                if isinstance(value, dict):
                    stats[command] = value
                elif isinstance(value, str):
                    # 解析格式：calls=100,usec=1000,usec_per_call=10.00
                    parsed = {}
                    parts = value.split(",")
                    for part in parts:
                        if "=" in part:
                            k, v = part.split("=", 1)
                            try:
                                parsed[k] = float(v)
                            except ValueError:
                                parsed[k] = v
                    stats[command] = parsed

        return stats

    def _calculate_stats_delta(self, stats1: Dict, stats2: Dict, interval: float) -> Dict:
        """
        计算两次采样之间的增量

        Args:
            stats1: 第一次采样的统计数据
            stats2: 第二次采样的统计数据
            interval: 采样间隔（秒）

        Returns:
            增量统计字典
        """
        delta_commands = []
        total_calls_per_sec = 0

        # 遍历第二次采样的所有命令
        for command, stats2_data in stats2.items():
            calls2 = int(stats2_data.get("calls", 0))
            usec2 = int(stats2_data.get("usec", 0))

            # 获取第一次采样的数据
            stats1_data = stats1.get(command, {})
            calls1 = int(stats1_data.get("calls", 0))
            usec1 = int(stats1_data.get("usec", 0))

            # 计算增量
            calls_delta = calls2 - calls1
            usec_delta = usec2 - usec1

            # 只统计有变化的命令
            if calls_delta > 0:
                calls_per_sec = int(calls_delta / interval)
                usec_per_sec = int(usec_delta / interval)
                avg_usec = usec_delta / calls_delta if calls_delta > 0 else 0.0

                delta_commands.append(
                    {
                        "command": command,
                        "calls_per_sec": calls_per_sec,
                        "usec_per_sec": usec_per_sec,
                        "avg_usec_per_call": round(avg_usec, 2),
                    }
                )

                total_calls_per_sec += calls_per_sec

        # 按每秒调用次数降序排序
        delta_commands.sort(key=lambda x: x["calls_per_sec"], reverse=True)

        return {
            "total_commands": len(delta_commands),
            "total_calls_per_sec": total_calls_per_sec,
            "commands": delta_commands,
        }
