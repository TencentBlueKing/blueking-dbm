import logging
import os.path

from backend import env
from backend.configuration.constants import DBType
from backend.configuration.models import SystemSettings
from backend.db_meta.enums import MachineType
from backend.db_meta.models import Cluster, Machine, StorageInstance
from backend.db_package.models import Package
from backend.flow.consts import DBActuatorTypeEnum, MediumEnum, RiakActuatorActionEnum
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class RiakActPayload(object):
    """
    定义Riak不同的执行类型，拼接不同的payload参数，对应不同的dict结构体
    """

    def __init__(self, ticket_data: dict, cluster: dict):
        self.riak_pkg = None
        self.mysql_crond_pkg = None  # riak使用mysql-crond实现定时任务
        self.riak_monitor_pkg = None
        self.ticket_data = ticket_data
        self.cluster = cluster

    def get_sysinit_payload(self, **kwargs) -> dict:
        """
        系统配置初始化
        """
        return {
            "db_type": DBActuatorTypeEnum.Default.value,
            "action": RiakActuatorActionEnum.SysinitRiak.value,
            "payload": {"general": {}, "extend": {}},
        }

    def get_deploy_payload(self, **kwargs) -> dict:
        """
        部署节点
        """
        self.riak_pkg = Package.get_latest_package(
            version=self.ticket_data["db_version"], pkg_type=MediumEnum.Riak, db_type=DBType.Riak.value
        )
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.Deploy.value,
            "payload": {
                "general": {},
                "extend": {
                    "distributed_cookie": self.cluster["distributed_cookie"],
                    "ring_size": self.cluster["ring_size"],
                    "leveldb.expiration": self.cluster["leveldb.expiration"],
                    "leveldb.expiration.mode": self.cluster["leveldb.expiration.mode"],
                    "leveldb.expiration.retention_time": self.cluster["leveldb.expiration.retention_time"],
                    "pkg": {
                        "name": self.riak_pkg.name,
                        "md5": self.riak_pkg.md5,
                    },
                },
            },
        }

    def get_deploy_trans_payload(self, **kwargs) -> dict:
        """
        部署节点
        """
        self.riak_pkg = Package.get_latest_package(
            version=self.ticket_data["db_version"], pkg_type=MediumEnum.Riak, db_type=DBType.Riak.value
        )
        configs = kwargs["trans_data"]["configs"]
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.Deploy.value,
            "payload": {
                "general": {},
                "extend": {
                    "distributed_cookie": configs["distributed_cookie"],
                    "ring_size": configs["ring_size"],
                    "leveldb.expiration": configs["leveldb.expiration"],
                    "leveldb.expiration.mode": configs["leveldb.expiration.mode"],
                    "leveldb.expiration.retention_time": configs["leveldb.expiration.retention_time"],
                    "pkg": {
                        "name": self.riak_pkg.name,
                        "md5": self.riak_pkg.md5,
                    },
                },
            },
        }

    def get_join_cluster_payload(self, **kwargs) -> dict:
        """
        添加节点
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.JoinCluster.value,
            "payload": {
                "general": {},
                "extend": {
                    "distributed_cookie": self.cluster["distributed_cookie"],
                    "ring_size": self.cluster["ring_size"],
                    "base_node": kwargs["trans_data"]["base_node"],
                },
            },
        }

    def get_join_cluster_trans_payload(self, **kwargs) -> dict:
        """
        添加节点
        """
        configs = kwargs["trans_data"]["configs"]
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.JoinCluster.value,
            "payload": {
                "general": {},
                "extend": {
                    "distributed_cookie": configs["distributed_cookie"],
                    "ring_size": configs["ring_size"],
                    "base_node": kwargs["trans_data"]["base_node"],
                },
            },
        }

    def get_remove_node_payload(self, **kwargs) -> dict:
        """
        剔除节点
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.RemoveNode.value,
            "payload": {
                "general": {},
                "extend": {
                    "operate_nodes": kwargs["trans_data"]["operate_nodes"],
                },
            },
        }

    def get_commit_cluster_change_payload(self, **kwargs) -> dict:
        """
        集群变更生效
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.CommitClusterChange.value,
            "payload": {
                "general": {},
                "extend": {
                    "nodes": kwargs["trans_data"]["nodes"],
                },
            },
        }

    def get_transfer_payload(self, **kwargs) -> dict:
        """
        集群数据搬迁进度
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.Transfer.value,
            "payload": {
                "general": {},
                "extend": {"auto_stop": self.ticket_data["ticket_type"] == TicketType.RIAK_CLUSTER_SCALE_IN},
            },
        }

    def get_check_connections_payload(self, **kwargs) -> dict:
        """
        检查连接
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.CheckConnections.value,
            "payload": {
                "general": {},
                "extend": {},
            },
        }

    def get_init_bucket_type_payload(self, **kwargs) -> dict:
        """
        初始化bucket_type
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.InitBucketType.value,
            "payload": {
                "general": {},
                "extend": {
                    "bucket_types": self.cluster["bucket_types"],
                },
            },
        }

    def get_config_payload(self, **kwargs) -> dict:
        """
        系统配置初始化
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.GetConfig.value,
            "payload": {"general": {}, "extend": {}},
        }

    def get_uninstall_payload(self, **kwargs) -> dict:
        """
        下架
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.UnInstall.value,
            "payload": {
                "general": {},
                "extend": {"stopped": self.ticket_data["ticket_type"] == TicketType.RIAK_CLUSTER_DESTROY},
            },
        }

    def get_stop_payload(self, **kwargs) -> dict:
        """
        禁用
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.Stop.value,
            "payload": {
                "general": {},
                "extend": {},
            },
        }

    def get_start_payload(self, **kwargs) -> dict:
        """
        启用
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.Start.value,
            "payload": {
                "general": {},
                "extend": {},
            },
        }

    def get_restart_payload(self, **kwargs) -> dict:
        """
        启用
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.Restart.value,
            "payload": {
                "general": {},
                "extend": {},
            },
        }

    def get_install_monitor_payload(self, **kwargs) -> dict:
        """
        启用
        """
        self.mysql_crond_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLCrond)
        self.riak_monitor_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RiakMonitor, db_type=DBType.Riak.value
        )
        machine = Machine.objects.get(ip=kwargs["ip"])
        if machine.machine_type != MachineType.RIAK.value:
            logger.error(
                "install monitor error. Machine type is {} not {}".format(machine.machine_type, MachineType.RIAK.value)
            )
        storage = StorageInstance.objects.filter(machine__ip=kwargs["ip"])[0]

        # 监控自定义上报配置通过SystemSettings表获取
        bkm_dbm_report = SystemSettings.get_setting_value(key="BKM_DBM_REPORT")
        # 设置定时任务和调度计划
        schedules = [
            {"name": "riak-err-notice", "expression": "@every 1m"},
            {"name": "riak-load-health", "expression": "@every 1m"},
            {"name": "riak-ring-status", "expression": "@every 30s"},
            {"name": "riak-monitor-hardcode", "expression": "@every 30s"},
            {"name": "riak_connections_heart_beat", "expression": "@every 1m"},
        ]
        if self.ticket_data["ticket_type"] == TicketType.RIAK_CLUSTER_SCALE_OUT:
            cluster = Cluster.objects.get(id=self.ticket_data["cluster_id"])
            domain = cluster.immute_domain
        else:
            domain = self.ticket_data["domain"]

        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.DeployMonitor.value,
            "payload": {
                "general": {},
                "extend": {
                    "crond_pkg": {
                        "name": self.mysql_crond_pkg.name,
                        "md5": self.mysql_crond_pkg.md5,
                    },
                    "monitor_pkg": {
                        "name": self.riak_monitor_pkg.name,
                        "md5": self.riak_monitor_pkg.md5,
                    },
                    "crond_config": {
                        "ip": kwargs["ip"],
                        "bk_cloud_id": self.ticket_data["bk_cloud_id"],
                        "event_data_id": bkm_dbm_report["event"]["data_id"],
                        "event_data_token": bkm_dbm_report["event"]["token"],
                        "metrics_data_id": bkm_dbm_report["metric"]["data_id"],
                        "metrics_data_token": bkm_dbm_report["metric"]["token"],
                        "log_path": "logs",
                        "beat_path": env.MYSQL_CROND_BEAT_PATH,
                        "agent_address": env.MYSQL_CROND_AGENT_ADDRESS,
                    },
                    "monitor_config": {
                        "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                        "ip": kwargs["ip"],
                        "port": storage.port,
                        "bk_instance_id": storage.bk_instance_id,
                        "immute_domain": domain,
                        "machine_type": MachineType.RIAK.value,
                        "bk_cloud_id": self.ticket_data["bk_cloud_id"],
                        "log_path": "logs",
                        "items_config_file": "items-config.yaml",
                        "interact_timeout": 2,
                    },
                    "monitor_items": create_riak_monitor_items(schedules),
                    "jobs_config": {
                        "bk_biz_id": int(self.ticket_data["bk_biz_id"]),
                        "jobs": create_crond_jobs(schedules),
                    },
                },
            },
        }

    def get_stop_monitor_payload(self, **kwargs) -> dict:
        """
        关闭定时和监控
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.StopMonitor.value,
            "payload": {
                "general": {},
                "extend": {},
            },
        }

    def get_start_monitor_payload(self, **kwargs) -> dict:
        """
        启用定时和监控
        """
        return {
            "db_type": DBActuatorTypeEnum.Riak.value,
            "action": RiakActuatorActionEnum.StartMonitor.value,
            "payload": {
                "general": {},
                "extend": {},
            },
        }


def create_crond_jobs(self: list) -> list:
    monitor_path = "/data/monitor/riak-monitor"
    jobs = []
    for schedule in self:
        cmd = "run"
        items = schedule["name"]
        if "hardcode" in schedule["name"]:
            cmd = "hardcode-run"
            items = "riak-db-up,riak_monitor_heart_beat"
        job = {
            "name": "{}{}".format(schedule["name"], schedule["expression"]),
            "enable": True,
            "command": os.path.join(monitor_path, "riak-monitor"),
            "args": [
                cmd,
                "--items",
                items,
                "-c",
                os.path.join(monitor_path, "runtime.yaml"),
            ],
            "schedule": schedule["expression"],
            "creator": "admin",
            "work_dir": "",
        }
        jobs.append(job)
    return jobs


def create_riak_monitor_items(self: list) -> list:
    items = []
    for schedule in self:
        if "hardcode" in schedule["name"]:
            item = {
                "name": "riak-db-up",
                "enable": True,
                "schedule": schedule["expression"],
                "machine_type": [MachineType.RIAK.value],
            }
            items.append(item)
            item = {
                "name": "riak_monitor_heart_beat",
                "enable": True,
                "schedule": schedule["expression"],
                "machine_type": [MachineType.RIAK.value],
            }
            items.append(item)
            continue
        item = {
            "name": schedule["name"],
            "enable": True,
            "schedule": schedule["expression"],
            "machine_type": [MachineType.RIAK.value],
        }
        items.append(item)
    return items
