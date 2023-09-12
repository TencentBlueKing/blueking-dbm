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
import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple

from django.db import IntegrityError, transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.forms.models import model_to_dict

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.utils.time import datetime2str, strptime

from .constants import DtsOperateType, DtsTaskType
from .enums import DtsCopyType
from .models import (
    TbDtsServerBlacklist,
    TbTendisDtsDistributeLock,
    TbTendisDTSJob,
    TbTendisDtsTask,
    dts_task_clean_pwd_and_fmt_time,
    dts_task_format_time,
)
from .util import dts_job_cnt_and_status, dts_task_status, is_in_incremental_sync

logger = logging.getLogger("root")


def is_dtsserver_in_blacklist(payload: dict) -> bool:
    """判断dts_server是否在黑名单中"""
    return TbDtsServerBlacklist.objects.filter(ip=payload.get("ip")).exists()


def get_dts_history_jobs(payload: dict) -> dict:
    """获取迁移任务列表以及其对应task cnt"""

    where = Q()
    if "cluster_name" in payload:
        where &= Q(src_cluster__icontains=payload["cluster_name"]) | Q(dst_cluster__icontains=payload["cluster_name"])
    if "start_time" in payload:
        start_time = strptime(payload.get("start_time"))
        where &= Q(create_time__gte=start_time)
    if "end_time" in payload:
        end_time = strptime(payload.get("end_time"))
        where &= Q(create_time__lte=end_time)
    jobs = TbTendisDTSJob.objects.filter(where).order_by("-create_time")

    # 分页
    start_idx = 0
    end_idx = jobs.count()
    if "page" in payload and "page_size" in payload and payload.get("page_size") > 0:
        page = payload.get("page")
        page_size = payload.get("page_size")
        start_idx = (page - 1) * page_size
        end_idx = page * page_size
        if end_idx >= len(jobs):
            end_idx = len(jobs)

    resp = []
    for job in jobs[start_idx:end_idx]:
        status_ret = dts_job_cnt_and_status(job)

        job_json = model_to_dict(job)
        job_json.update(status_ret)

        # fill dst_copy_type with bill type
        if job_json["dts_copy_type"] == "":
            job_json["dts_copy_type"] = job_json["dts_bill_type"]

        job_json["create_time"] = datetime2str(job.create_time)
        job_json["update_time"] = datetime2str(job.update_time)
        resp.append(job_json)

    return {"total_cnt": jobs.count(), "jobs": resp}


def get_dts_job_detail(payload: dict) -> list:
    """获取迁移任务详情"""
    bill_id = payload.get("bill_id")
    src_cluster = payload.get("src_cluster")
    dst_cluster = payload.get("dst_cluster")

    return TbTendisDTSJob.objects.filter(
        Q(bill_id=bill_id) & Q(src_cluster=src_cluster) & Q(dst_cluster=dst_cluster)
    ).values()


def get_dts_job_tasks(payload: dict) -> list:
    """获取迁移任务task列表,失败的排在前面"""
    bill_id = payload.get("bill_id")
    src_cluster = payload.get("src_cluster")
    dst_cluster = payload.get("dst_cluster")
    tasks = TbTendisDtsTask.objects.filter(
        Q(bill_id=bill_id) & Q(src_cluster=src_cluster) & Q(dst_cluster=dst_cluster)
    ).order_by(
        # order by FIELD(status,-1,1,0,2),src_ip,src_port
        Case(
            When(status=-1, then=Value(0)),
            When(status=1, then=Value(1)),
            When(status=0, then=Value(2)),
            When(status=2, then=Value(3)),
            output_field=IntegerField(),
        ),
        "src_ip",
        "src_port",
    )
    resp = []
    for task in tasks:
        task_json = model_to_dict(task)
        dts_task_clean_pwd_and_fmt_time(task_json, task)
        task_json["status"] = dts_task_status(task)
        resp.append(task_json)
    return resp


def task_sync_stop_precheck(task: TbTendisDtsTask) -> Tuple[bool, str]:
    """同步完成前置检查"""

    if task.task_type not in [
        DtsTaskType.TENDISSSD_MAKESYNC.value,
        DtsTaskType.MAKE_CACHE_SYNC.value,
        DtsTaskType.WATCH_CACHE_SYNC.value,
        DtsTaskType.TENDISPLUS_SENDINCR.value,
    ]:
        return False, "{} task_type:{} cannot do sync_top operate".format(task.get_src_redis_addr(), task.task_type)

    if task.status != 1:
        return False, "{} status={} is not running status".format(task.get_src_redis_addr(), task.status)

    if task.tendis_binlog_lag > 300:
        return False, "{} binlog_lag={} > 300s".format(task.get_src_redis_addr(), task.tendis_binlog_lag)

    current_time = datetime.now(timezone.utc).astimezone()
    if task.update_time and (current_time - task.update_time).seconds > 300:
        return False, "{} the status has not been updated for more than 5 minutes,last update time:{}".format(
            task.get_src_redis_addr(), task.update_time
        )

    return True, ""


@transaction.atomic
def dts_job_disconnct_sync(payload: dict):
    """dts job断开同步,目前支持 同步完成(syncStopTodo)、强制终止(ForceKillTaskTodo) 两个操作"""

    bill_id = payload.get("bill_id")
    src_cluster = payload.get("src_cluster")
    dst_cluster = payload.get("dst_cluster")
    tasks = TbTendisDtsTask.objects.filter(
        Q(bill_id=bill_id) & Q(src_cluster=src_cluster) & Q(dst_cluster=dst_cluster)
    )

    # 判断是否增量同步中
    incremental_sync_running_cnt = 0
    for task in tasks:
        if is_in_incremental_sync(task):
            incremental_sync_running_cnt += 1

    # 如果全部 task 都是增量同步状态,则执行 正常断开同步操作
    # 否则 执行强制终止操作
    operate = DtsOperateType.FORCE_KILL_TODO
    if incremental_sync_running_cnt == len(tasks):
        operate = DtsOperateType.SYNC_STOP_TODO

    for task in tasks:
        if task.sync_operate == operate:
            continue
        task.sync_operate = operate
        task.message = operate + "..."
        task.update_time = datetime.now(timezone.utc).astimezone()
        task.save(update_fields=["sync_operate", "message", "update_time"])

    return list(tasks.values_list("id", flat=True))


@transaction.atomic
def dts_job_tasks_failed_retry(payload: dict):
    """dts tasks重试当前步骤"""

    tasks = TbTendisDtsTask.objects.filter(id__in=payload.get("task_ids"))
    for task in tasks:
        if task.src_have_list_keys > 0 and task.src_dbtype != ClusterType.TendisRedisInstance.value:
            """
            SrcHaveListKeys>0,其实只有在TendisSSD中才会出现,RedisInstance、tendisplus中很难发现是否有list类型的key
            而且当SrcHaveListKeys>0时,代表tendisSSD已经在 tredisump 阶段以后了,有list类型key情况下后续阶段重试是有风险的;
            RedisInstance不用管是否有list,因为有同名key存在时,通过restore replace会完全覆盖;
            """
            raise Exception("{} include list type keys,cannot retry".format(task.get_src_redis_addr()))
        if task.src_dbtype == ClusterType.TendisTendisSSDInstance.value:
            task.task_type = DtsTaskType.TENDISSSD_BACKUP.value
        elif task.src_dbtype == ClusterType.TendisRedisInstance.value:
            task.task_type = DtsTaskType.MAKE_CACHE_SYNC.value
        elif task.src_dbtype == ClusterType.TendisTendisplusInsance:
            task.task_type = DtsTaskType.TENDISPLUS_MAKESYNC.value
        else:
            raise Exception("{} src_dbtype:{} not support".format(task.get_src_redis_addr(), task.src_dbtype))

        task.status = 0
        task.message = "{} waiting for retry...".format(task.task_type)
        task.sync_operate = ""
        task.retry_times = task.retry_times + 1
        task.update_time = datetime.now()
        task.save(update_fields=["task_type", "status", "message", "sync_operate", "retry_times", "update_time"])

    return list(tasks.values_list("id", flat=True))


def dts_distribute_trylock(payload: dict) -> bool:
    """dts 分布式锁,trylock,成功返回True,失败返回False"""
    lockkey = payload.get("lockkey")
    holder = payload.get("holder")
    ttl_sec = payload.get("ttl_sec")
    current_time = datetime.now(timezone.utc).astimezone()
    expire_time = current_time + timedelta(seconds=ttl_sec)
    lock_row = TbTendisDtsDistributeLock(
        lock_key=lockkey, holder=holder, creation_time=current_time, lock_expire_time=expire_time
    )
    err = None
    try:
        lock_row.save()
    except Exception as e:
        err = e
    if not err:
        return True

    if not (isinstance(err, IntegrityError) and "Duplicate entry" in err.args[1]):
        raise err

    # 可重入锁,lock_expire_time>now()代表锁未过期,可以重入,更新过期时间
    # update tb_tendis_dts_distribute_lock set lock_expire_time=?
    # where lock_key=? and holder=? and lock_expire_time>now();
    with transaction.atomic():
        updated_rows = TbTendisDtsDistributeLock.objects.filter(
            lock_key=lockkey, holder=holder, lock_expire_time__gt=current_time
        ).update(lock_expire_time=expire_time)
        if updated_rows == 1:
            return True

    # 锁存在,且已过期
    # lock_expire_time<now()代表锁已经过期,可以被其他应用获取,更新其holder和过期时间
    # update tb_tendis_dts_distribute_lock set holder=?,lock_expire_time=? where lock_key=? and lock_expire_time<now();
    with transaction.atomic():
        updated_rows = TbTendisDtsDistributeLock.objects.filter(
            lock_key=lockkey, lock_expire_time__lt=current_time
        ).update(holder=holder, lock_expire_time=expire_time)
        if updated_rows == 1:
            return True
    return False


def dts_distribute_unlock(payload: dict):
    """dts 分布式锁,unlock"""
    TbTendisDtsDistributeLock.objects.filter(lock_key=payload.get("lockkey"), holder=payload.get("holder")).delete()


def get_dts_server_migrating_tasks(payload: dict) -> list:
    """获取dts server迁移中的任务
    对tendiSSD来说,'迁移中' 指处于 'tendisBackup'、'backupfileFetch'、'tendisdump'、'cmdsImporter'中的task,
    不包含处于 status=-1 或 处于 makeSync 状态的task
    对tendisCache来说,'迁移中'指处于 'makeCacheSync'中的task,不包含处于 status=-1 或 处于 watchCacheSync 状态的task
    """

    dts_server = payload.get("dts_server")
    db_type = payload.get("db_type")
    task_types = payload.get("task_types")
    current_time = datetime.now(timezone.utc).astimezone()
    thirty_days_ago = current_time - timedelta(days=30)

    where = Q(bk_cloud_id=payload.get("bk_cloud_id"))
    if dts_server:
        where = where & Q(dts_server=dts_server)
    if db_type:
        where = where & Q(src_dbtype=db_type)
    if task_types:
        where = where & Q(task_type__in=task_types)
    where = where & Q(update_time__gt=thirty_days_ago)
    where = where & Q(status__in=[0, 1])

    rets = []
    for task in TbTendisDtsTask.objects.filter(where):
        json_data = model_to_dict(task)
        dts_task_clean_pwd_and_fmt_time(json_data, task)
        rets.append(json_data)
    return rets


def get_dts_server_max_sync_port(payload: dict) -> dict:
    """获取DtsServer上syncPort最大的task"""

    dts_server = payload.get("dts_server")
    db_type = payload.get("db_type")
    task_types = payload.get("task_types")
    current_time = datetime.now(timezone.utc).astimezone()
    thirty_days_ago = current_time - timedelta(days=30)

    where = Q(bk_cloud_id=payload.get("bk_cloud_id"))
    if dts_server:
        where = where & Q(dts_server=dts_server)
    if db_type:
        where = where & Q(src_dbtype=db_type)
    if task_types:
        where = where & Q(task_type__in=task_types)
    where = where & Q(update_time__gt=thirty_days_ago)
    where = where & Q(status=1)

    task = TbTendisDtsTask.objects.filter(where).order_by("-syncer_port").first()
    if task:
        json_data = model_to_dict(task)
        dts_task_clean_pwd_and_fmt_time(json_data, task)
        return json_data

    return None


def get_last_30days_to_exec_tasks(payload: dict) -> list:
    """获取最近30天内task_type类型的等待执行的tasks"""

    bk_cloud_id = payload.get("bk_cloud_id")
    dts_server = payload.get("dts_server")
    task_type = payload.get("task_type")
    db_type = payload.get("db_type")
    limit = payload.get("limit")
    status = payload.get("status")
    dts_server = dts_server.strip()
    task_type = task_type.strip()
    db_type = db_type.strip()
    current_time = datetime.now(timezone.utc).astimezone()
    thirty_days_ago = current_time - timedelta(days=30)

    where = Q(bk_cloud_id=bk_cloud_id)
    if dts_server:
        where = where & Q(dts_server=dts_server)
    if task_type:
        where = where & Q(task_type=task_type)
    if db_type:
        where = where & Q(src_dbtype=db_type)
    if limit <= 0:
        limit = 1
    where = where & Q(status=status)
    where = where & Q(create_time__gt=thirty_days_ago)
    tasks = TbTendisDtsTask.objects.filter(where).order_by("-src_cluster_priority", "create_time")[:limit]
    if not tasks:
        # logger.warning(
        #     "get_last_30days_to_exec_tasks empty records"
        #     ",bk_cloud_id:{},dts_server:{},task_type:{},db_type:{},status:{}".format(
        #         bk_cloud_id, dts_server, task_type, db_type, status
        #     )
        # )
        return []
    rets = []
    for task in tasks:
        json_data = model_to_dict(task)
        dts_task_format_time(json_data, task)
        rets.append(json_data)
    return rets


def get_last_30days_to_schedule_jobs(payload: dict) -> list:
    """获取最近30天内的等待调度的jobs
    billId、srcCluster、dstCluster唯一确定一个dts_job
    获取的dts_jobs必须满足:
    有一个待调度的task.dataSize < maxDataSize & status=0 & taskType="" & dtsServer="1.1.1.1"
    """

    max_data_size = payload.get("max_data_size")
    zone_name = payload.get("zone_name")
    db_type = payload.get("db_type")
    current_time = datetime.now(timezone.utc).astimezone()
    thirty_days_ago = current_time - timedelta(days=30)

    where = Q(bk_cloud_id=payload.get("bk_cloud_id"))
    where = where & Q(src_dbsize__lte=max_data_size)
    if zone_name:
        where = where & Q(src_ip_zonename=zone_name)
    if db_type:
        where = where & Q(src_dbtype=db_type)
    where = where & Q(dts_server="1.1.1.1") & Q(task_type="") & Q(status=0) & Q(create_time__gt=thirty_days_ago)
    jobs = TbTendisDtsTask.objects.filter(where).order_by("-src_cluster_priority", "create_time")
    if not jobs:
        # logger.warning(
        #     "get_last_30days_to_schedule_jobs empty records,"
        #     "bk_cloud_id={},max_data_size={},zone_name={},db_type={}".format(
        #         bk_cloud_id, max_data_size, zone_name, db_type
        #     )
        # )
        return []
    rets = []
    unique_set = set()
    for job in jobs:
        job_uniq_key = "{}-{}-{}".format(job.bill_id, job.src_cluster, job.dst_cluster)
        if job_uniq_key in unique_set:
            continue
        unique_set.add(job_uniq_key)
        json_data = model_to_dict(job)
        dts_task_clean_pwd_and_fmt_time(json_data, job)
        rets.append(json_data)
    return rets


def get_job_to_schedule_tasks(payload: dict) -> list:
    """获取一个job的所有待调度的tasks"""
    # bill_id: int, src_cluster: str, dst_cluster: str
    bill_id = payload.get("bill_id")
    src_cluster = payload.get("src_cluster")
    dst_cluster = payload.get("dst_cluster")
    if bill_id == 0 or not src_cluster or not dst_cluster:
        raise Exception(
            "invalid params,bill_id={},src_cluster={},dst_cluster={} all can't be empty".format(
                bill_id, src_cluster, dst_cluster
            )
        )
    current_time = datetime.now(timezone.utc).astimezone()
    thirty_days_ago = current_time - timedelta(days=30)

    where = Q(bill_id=bill_id) & Q(src_cluster=src_cluster) & Q(dst_cluster=dst_cluster)
    where = where & Q(update_time__gt=thirty_days_ago) & Q(dts_server="1.1.1.1") & Q(task_type="") & Q(status=0)
    tasks = TbTendisDtsTask.objects.filter(where).order_by("src_weight")
    if not tasks:
        logger.warning(
            "get_job_to_schedule_tasks empty records,bill_id={},src_cluster={},dst_cluster={}".format(
                bill_id, src_cluster, dst_cluster
            )
        )
        return []

    rets = []
    for task in tasks:
        json_data = model_to_dict(task)
        dts_task_clean_pwd_and_fmt_time(json_data, task)
        rets.append(json_data)
    return rets


def get_job_src_ip_running_tasks(payload: dict) -> list:
    """获取一个job的所有待调度的tasks"""
    bill_id = payload.get("bill_id")
    src_cluster = payload.get("src_cluster")
    dst_cluster = payload.get("dst_cluster")
    src_ip = payload.get("src_ip")
    task_types = payload.get("task_types")
    current_time = datetime.now(timezone.utc).astimezone()
    thirty_days_ago = current_time - timedelta(days=30)
    where = Q(bill_id=bill_id) & Q(src_cluster=src_cluster) & Q(dst_cluster=dst_cluster) & Q(src_ip=src_ip)
    where = where & Q(update_time__gt=thirty_days_ago) & Q(status__in=(0, 1)) & Q(task_type__in=task_types)
    tasks = TbTendisDtsTask.objects.filter(where)
    if not tasks:
        logger.warning(
            "get_job_src_ip_running_tasks empty records,bill_id={},src_cluster={},dst_cluster={},src_ip={}".format(
                bill_id, src_cluster, dst_cluster, src_ip
            )
        )
        return []

    rets = []
    for task in tasks:
        json_data = model_to_dict(task)
        dts_task_clean_pwd_and_fmt_time(json_data, task)
        rets.append(json_data)
    return rets


def get_dts_task_by_id(payload: dict) -> dict:
    """根据task_id获取dts_task"""
    task_id = payload.get("task_id")

    try:
        task = TbTendisDtsTask.objects.get(id=task_id)
    except TbTendisDtsTask.DoesNotExist:
        logger.warning("dts task not found,task_id={}".format(task_id))
        return None

    json_data = model_to_dict(task)
    dts_task_format_time(json_data, task)
    return json_data


def dts_tasks_updates(paylod: dict):
    """批量更新dts_tasks
    :param
    task_ids: task_id列表
    update_params: 列名和值的对应关系,如 {"status": 1,"message": "test"}
    """
    task_ids = paylod.get("task_ids")
    col_to_val = paylod.get("col_to_val")
    if not task_ids:
        raise Exception("invalid params,task_ids can't be empty")
    if not col_to_val:
        raise Exception("invalid params,update_params can't be empty")
    rows_affected = TbTendisDtsTask.objects.filter(id__in=task_ids).update(**col_to_val)
    return rows_affected


def dts_test_redis_connections(payload: dict):
    """
    测试redis可连接性
    """
    data_copy_type = payload.get("data_copy_type")
    infos = payload.get("infos")
    cluster: Cluster = None
    redis_addr: str = ""
    redis_password: str = ""
    for info in infos:
        try:
            if data_copy_type == DtsCopyType.USER_BUILT_TO_DBM.value:
                cluster = Cluster.objects.get(id=int(info.get("dst_cluster")))
                redis_addr = info.get("src_cluster")
                redis_password = info.get("src_cluster_password")
            elif data_copy_type == DtsCopyType.COPY_TO_OTHER_SYSTEM.value:
                cluster = Cluster.objects.get(id=int(info.get("src_cluster")))
                redis_addr = info.get("dst_cluster")
                redis_password = info.get("dst_cluster_password")
            else:
                raise Exception(
                    "invalid data_copy_type:{},valid data_copy_type[{},{}]".format(
                        data_copy_type, DtsCopyType.USER_BUILT_TO_DBM.value, DtsCopyType.COPY_TO_OTHER_SYSTEM.value
                    )
                )
            DRSApi.redis_rpc(
                {
                    "addresses": [redis_addr],
                    "db_num": 0,
                    "password": redis_password,
                    "command": "ping",
                    "bk_cloud_id": cluster.bk_cloud_id,
                }
            )
        except Exception as e:
            logger.error("test redis connection failed,redis_addr:{},error:{}".format(redis_addr, e))
            raise Exception(
                "test redis connection failed,redis_addr:{},please check redis and password is ok".format(redis_addr)
            )
    return True
