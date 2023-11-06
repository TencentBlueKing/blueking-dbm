"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, List

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole, MachineType
from backend.db_meta.models import Cluster
from backend.db_report.enums import RedisBackupCheckSubType
from backend.db_report.models import RedisBackupCheckReport
from backend.flow.consts import (
    DEFAULT_DB_MODULE_ID,
    DEFAULT_REDIS_START_PORT,
    DEFAULT_TWEMPROXY_SEG_TOTOL_NUM,
    ConfigTypeEnum,
    OperateTypeEnum,
    WriteContextOpType,
)

from .bklog_query import ClusterBackup

logger = logging.getLogger("root")


def check_binlog_backup():
    _check_tendis_binlog_backup()


def _check_tendis_binlog_backup():
    """
    tendisplus,ssd 2种架构：
    tendisplus 一个集群40节点，每个节点10 个kvstore，一般20分钟上传一次binlog，一小时3次，一天的备份文件数：
    40*10*24*3=28800，可怕的是，有几百节点的集群，这怕是把es查挂了哦，按节点纬度查询会更好些

    tendisplus,tendis ssd slave 实例必须要有备份binlog
    且binlog序号要连续

    """
    # 构建查询条件:tendisplus,ssd,cache,集群创建时间大于1天，巡检0点发起
    query = (
        Q(cluster_type=ClusterType.TendisPredixyTendisplusCluster)
        | Q(cluster_type=ClusterType.TwemproxyTendisSSDInstance)
        | Q(create_at__gt=timezone.now() - timedelta(days=1))
    )
    # 遍历集群
    for c in Cluster.objects.filter(query):
        logger.info("+===+++++===  start check {} binlog backup +++++===++++ ".format(c.immute_domain))
        logger.info("+===+++++===  cluster type is: {} +++++===++++ ".format(c.cluster_type))
        cluster_slave_instance = []  # 初始化集群slave列表，binlog只在slave上生成
        # 如果是tendisplus,需要单独校验每个节点的kvstore 的binlog连续性
        if c.cluster_type == ClusterType.TendisPredixyTendisplusCluster.value:
            # 获取 kvstorecount
            redis_config = __get_cluster_config(
                c.immute_domain, c.major_version, ConfigTypeEnum.DBConf, c.cluster_type, str(c.bk_biz_id)
            )
            kvstorecount = redis_config["kvstorecount"]
            logger.info("+===+++++===  kvstorecount is: {} +++++===++++ ".format(kvstorecount))

        for master_obj in c.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            slave_obj = master_obj.as_ejector.get().receiver
            current_datetime = timezone.now()
            # 计算时间差
            time_difference = current_datetime - slave_obj.create_at
            # 判断时间差是否大于等于24小时  # 过滤掉 刚扩容，重建热备-> 创建时间小于24小时
            if time_difference >= timedelta(hours=24):
                # 进行相应的操作
                cluster_slave_instance.append("{}{}{}".format(slave_obj.machine.ip, IP_PORT_DIVIDER, slave_obj.port))

        logger.info("+===+++++===  cluster slave instance  is: {} +++++===++++ ".format(cluster_slave_instance))
        backup = ClusterBackup(c.id, c.immute_domain)
        # 集群纬度的，假设一开始是备份完整的，后面会去校验对这个值进行赋值，如果有存在异常会赋值为False
        # 不管是全备份还是binlog,只要有异常，这个就是False

        now = datetime.now()
        yesterday = now - timedelta(days=1)
        start_time = datetime(yesterday.year, yesterday.month, yesterday.day)
        end_time = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
        #  	 +===+++++=== start_time is: 2023-10-25 00:00:00 ,end_time is :2023-10-25 23:59:59 +++++===++++
        logger.info("+===+++++=== start_time is: {} ,end_time is :{} +++++===++++ ".format(start_time, end_time))
        # 对slave 进行统计
        for instance in cluster_slave_instance:
            # 单个节点的成功的binlog备份文件
            suceess_binlog_file_list = []
            ip, port = instance.split(":")
            bklogs = backup.query_binlog_from_bklog(start_time, end_time, ip, port)
            # 如果节点维度没有数据，就不用在进行下面的了
            # 这里如果提升为集群维度的话，一般会有40*10*24*3=28800个文件，所以按节点维度来查
            if not bklogs:
                msg = _("无法查找到在时间范围内{}-{}，集群{}：{}的全备份日志").format(start_time, end_time, c.immute_domain, instance)
                logger.error(msg)
                RedisBackupCheckReport.objects.create(
                    creator=c.creator,
                    bk_biz_id=c.bk_biz_id,
                    bk_cloud_id=c.bk_cloud_id,
                    cluster=c.immute_domain,
                    cluster_type=c.cluster_type,
                    instance=instance,
                    status=False,
                    msg=msg,
                    subtype=RedisBackupCheckSubType.BinlogBackup.value,
                )

            else:
                for bklog in bklogs:
                    # 失败的记录，直接记录:同一条记录，不可能又存在失败的，又存在成功的，所以有失败的直接入库了
                    if bklog.get("backup_status", "") == "to_backup_system_failed":
                        logger.error("+===+++++=== to_backup_system_failed bklog: {} +++++===++++ ".format(bklog))
                        RedisBackupCheckReport.objects.create(
                            creator=c.creator,
                            bk_biz_id=c.bk_biz_id,
                            bk_cloud_id=c.bk_cloud_id,
                            cluster=c.immute_domain,
                            cluster_type=c.cluster_type,
                            instance=instance,
                            status=False,
                            msg=bklog["backup_status_info"],
                            subtype=RedisBackupCheckSubType.BinlogBackup.value,
                        )

                    # 对成功的进行处理，判断文件序号的完备性
                    if bklog.get("backup_status", "") == "to_backup_system_success":
                        suceess_binlog_file_list.append(bklog)

                #  tendisplus 的情况
                if c.cluster_type == ClusterType.TendisPredixyTendisplusCluster.value:
                    # 每个节点又分不同kvstore,校验binlog完整性
                    for i in range(0, int(kvstorecount)):
                        # 过滤不同kvstore
                        kvstore_filter = "-".join([str(ip), str(port), str(i)])
                        # 过滤后的包含指定kvstore的binlog列表
                        kvstore_binlogs_list = [
                            binlog for binlog in suceess_binlog_file_list if kvstore_filter in binlog["file_name"]
                        ]
                        # 检查是否获取到所有binlog
                        bin_index_list = is_get_all_binlog(kvstore_binlogs_list, c.cluster_type)
                        if len(bin_index_list) != 0:
                            msg = _("重复/缺失的binlog共{}个,重复/缺失的binlog index是:{},详细信息请查看error日志").format(
                                len(bin_index_list), bin_index_list
                            )
                            logger.error("+===+++++=== {}+++++===++++ ".format(msg))
                            RedisBackupCheckReport.objects.create(
                                creator=c.creator,
                                bk_biz_id=c.bk_biz_id,
                                bk_cloud_id=c.bk_cloud_id,
                                cluster=c.immute_domain,
                                cluster_type=c.cluster_type,
                                instance=instance,
                                status=False,
                                msg=msg,
                                subtype=RedisBackupCheckSubType.BinlogBackup.value,
                            )

                        # else:
                        # 这里打日志的话，有助于排查问题，但是日志有点多
                        # logger.info("+===+++++=== {} binlog 序号连续 +++++===++++ ".format(kvstore_filter))
                #  tendis ssd 的情况
                elif c.cluster_type == ClusterType.TwemproxyTendisSSDInstance.value:
                    # 校验binlog完整性
                    # 检查是否获取到所有binlog
                    bin_index_list = is_get_all_binlog(suceess_binlog_file_list, c.cluster_type)
                    if len(bin_index_list) != 0:
                        msg = _("重复/缺失的binlog共{}个,重复/缺失的binlog index是:{},详细信息请查看error日志").format(
                            len(bin_index_list), bin_index_list
                        )
                        logger.error("+===+++++=== {}+++++===++++ ".format(msg))
                        RedisBackupCheckReport.objects.create(
                            creator=c.creator,
                            bk_biz_id=c.bk_biz_id,
                            bk_cloud_id=c.bk_cloud_id,
                            cluster=c.immute_domain,
                            cluster_type=c.cluster_type,
                            instance=instance,
                            status=False,
                            msg=msg,
                            subtype=RedisBackupCheckSubType.BinlogBackup.value,
                        )
                    else:
                        logger.info(_("+===+++++=== {} binlog 序号连续 +++++===++++ ".format(instance)))


def is_get_all_binlog(binlogs_list: List, tendis_type: str):
    """
    检查是否获取到所有binlog
    返回重复的文件序号和缺失的文件序号
    """

    # 1. 获取binlog_file_list里每个字典的file_name值组成新的binlog_file_name_list
    binlog_file_name_list = [item["file_name"] for item in binlogs_list]
    # 2. 根据binlog_file_name_list如 0002437，0002438来排序
    if tendis_type == ClusterType.TendisPredixyTendisplusCluster.value:
        # binlog-xxxx-30002-0-0002437-20230911164611.log.zst
        sorted_binlog_file_name_list = sorted(binlog_file_name_list, key=lambda x: int(x.split("-")[4]))
    elif tendis_type == ClusterType.TwemproxyTendisSSDInstance.value:
        # binlog-xxxx-30002-0002500-20230913101206.log.zst
        sorted_binlog_file_name_list = sorted(binlog_file_name_list, key=lambda x: int(x.split("-")[3]))
    else:
        raise NotImplementedError("is_get_all_binlog: Not supported tendis type: %s" % tendis_type)
    # 3. 判断是否连续重复
    missing_files = []
    duplicate_files = set()
    previous_number = None
    previous_file_name = None

    for file_name in sorted_binlog_file_name_list:
        if tendis_type == ClusterType.TendisPredixyTendisplusCluster.value:
            current_number = int(file_name.split("-")[4])
        elif tendis_type == ClusterType.TwemproxyTendisSSDInstance.value:
            current_number = int(file_name.split("-")[3])
        # 检查是否重复
        if current_number in duplicate_files:
            logger.error(_("文件序号重复: {}".format(current_number)))
            logger.error(_("文件重复: {}".format(file_name)))
            return [current_number]
        # 检查是否连续
        if previous_number is not None and current_number - previous_number > 1:
            logger.error(_("缺失时打印排序后的当前文件:{}和上一个文件: {}".format(previous_file_name, file_name)))
            missing_files.extend(range(previous_number + 1, current_number))
        duplicate_files.add(current_number)
        previous_number = current_number
        previous_file_name = file_name
    # 4. 判断是否连续的结果
    if missing_files:
        logger.error(_("缺少的文件序号: {}").format(missing_files))
    return missing_files


def __get_cluster_config(domain_name: str, db_version: str, conf_type: str, namespace: str, bk_biz_id: str) -> Any:
    """
    获取已部署的实例配置,这里主要是拿tendisplus kvstore
    """
    data = DBConfigApi.query_conf_item(
        params={
            "bk_biz_id": bk_biz_id,
            "level_name": LevelName.CLUSTER,
            "level_value": domain_name,
            "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
            "conf_file": db_version,
            "conf_type": conf_type,
            "namespace": namespace,
            "format": FormatType.MAP,
        }
    )
    return data["content"]
