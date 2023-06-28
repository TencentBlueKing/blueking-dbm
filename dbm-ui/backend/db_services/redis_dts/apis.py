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

from django.db import IntegrityError, connection, transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.forms.models import model_to_dict
from django.utils.translation import ugettext_lazy as _

from backend.db_meta.enums import ClusterType
from backend.utils.time import datetime2str, strptime

from .constants import DtsOperateType, DtsTaskType
from .exceptions import GetDtsJobTasksException, TaskOperateException
from .models import (
    TbDtsServerBlacklist,
    TbTendisDtsDistributeLock,
    TbTendisDTSJob,
    TbTendisDtsTask,
    dts_task_binary_to_str,
    dts_task_clean_passwd_and_format_time,
    dts_task_format_time,
)

logger = logging.getLogger("redis_dts")


def is_dtsserver_in_blacklist(payload: dict) -> bool:
    """判断dts_server是否在黑名单中"""
    ip = payload.get("ip")
    row = TbDtsServerBlacklist.objects.filter(ip=ip)
    if row:
        return True
    return False


def get_dts_history_jobs(payload: dict) -> list:
    """获取迁移任务列表以及其对应task cnt"""
    local_tz = datetime.now(timezone.utc).astimezone().tzinfo
    where = Q()
    if "user" in payload:
        where &= Q(user=payload.get("user"))
    if "start_time" in payload:
        # start_time = strptime(payload.get("start_time")).replace(tzinfo=local_tz)
        start_time = strptime(payload.get("start_time"))
        where &= Q(create_time__gte=start_time)
    if "end_time" in payload:
        # end_time = strptime(payload.get("end_time")).replace(tzinfo=local_tz)
        end_time = strptime(payload.get("end_time"))
        # end_time = parse_datetime(payload.get("end_time"))
        where &= Q(create_time__lte=end_time)
    jobs = TbTendisDTSJob.objects.filter(where).order_by("-create_time")
    resp = []
    to_exec_cnt = 0
    running_cnt = 0
    failed_cnt = 0
    success_cnt = 0
    for job in jobs:
        tasks = TbTendisDtsTask.objects.filter(
            Q(bill_id=job.bill_id) & Q(src_cluster=job.src_cluster) & Q(dst_cluster=job.dst_cluster)
        )
        for task in tasks:
            if task.task_type == "" and task.status == 0:
                to_exec_cnt += 1
            elif task.task_type == DtsTaskType.TENDISSSD_BACKUP.value and task.status == 0:
                to_exec_cnt += 1
            elif task.task_type == DtsTaskType.TENDISSSD_BACKUP.value and task.status == 1:
                running_cnt += 1
            elif task.task_type != DtsTaskType.TENDISSSD_BACKUP.value and (task.status == 0 or task.status == 1):
                running_cnt += 1
            elif task.status == -1:
                failed_cnt += 1
            elif task.status == 2:
                success_cnt += 1
        job_json = model_to_dict(job)
        job_json["total_cnt"] = len(tasks)
        job_json["to_exec_cnt"] = to_exec_cnt
        job_json["running_cnt"] = running_cnt
        job_json["failed_cnt"] = failed_cnt
        job_json["success_cnt"] = success_cnt
        job_json["create_time"] = datetime2str(job.create_time)
        job_json["update_time"] = datetime2str(job.update_time)
        resp.append(job_json)
    return resp


def get_dts_job_detail(payload: dict) -> list:
    """获取迁移任务详情"""
    bill_id = payload.get("bill_id")
    src_cluster = payload.get("src_cluster")
    dst_cluster = payload.get("dst_cluster")
    jobs = TbTendisDTSJob.objects.filter(Q(bill_id=bill_id) & Q(src_cluster=src_cluster) & Q(dst_cluster=dst_cluster))
    resp = []
    for job in jobs:
        job_json = model_to_dict(job)
        resp.append(job_json)
    return resp


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
        dts_task_clean_passwd_and_format_time(task_json, task)
        dts_task_binary_to_str(task_json, task)
        resp.append(task_json)
    return resp


def task_sync_stop_precheck(task: TbTendisDtsTask) -> Tuple[bool, str]:
    """同步完成前置检查"""
    ok = False
    msg = ""
    if (
        task.task_type != DtsTaskType.TENDISSSD_MAKESYNC.value
        and task.task_type != DtsTaskType.MAKE_CACHE_SYNC.value
        and task.task_type != DtsTaskType.WATCH_CACHE_SYNC.value
        and task.task_type != DtsTaskType.TENDISPLUS_SENDINCR.value
    ):
        msg = "{} task_type:{} cannot do sync_top operate".format(task.get_src_redis_addr(), task.task_type)
        return ok, msg
    if task.status != 1:
        msg = "{} status={} is not running status".format(task.get_src_redis_addr(), task.status)
        return ok, msg
    if task.tendis_binlog_lag > 300:
        msg = "{} binlog_lag={} > 300s".format(task.get_src_redis_addr(), task.tendis_binlog_lag)
        return ok, msg
    current_time = datetime.now(timezone.utc).astimezone()
    if task.update_time and (current_time - task.update_time).seconds > 300:
        msg = "{} the status has not been updated for more than 5 minutes,last update time:{}".format(
            task.get_src_redis_addr(), task.update_time
        )
        return ok, msg
    ok = True
    return ok, msg


@transaction.atomic
def dts_tasks_operate(payload: dict):
    """dts task操作,目前支持 同步完成(syncStopTodo)、强制终止(ForceKillTaskTodo) 两个操作"""
    # taskids: list, operate: str
    task_ids = payload.get("task_ids")
    operate = payload.get("operate")
    if operate != DtsOperateType.SYNC_STOP_TODO.value and operate != DtsOperateType.FORCE_KILL_TODO.value:
        raise Exception(
            "operate:{} not [{},{}]".format(operate, DtsOperateType.SYNC_STOP_TODO.value, DtsOperateType.value)
        )
    if not task_ids:
        raise Exception("taskids:{} is empty".format(task_ids))
    tasks = TbTendisDtsTask.objects.filter(id__in=task_ids)
    for task in tasks:
        if operate == DtsOperateType.SYNC_STOP_TODO.value:
            precheck_ret = task_sync_stop_precheck(task)
            if not precheck_ret[0]:
                logger.warning("dts_tasks_operate fail,err:{}".format(precheck_ret[1]))
                raise Exception(precheck_ret[1])
        task.sync_operate = operate
        task.message = (operate + "...").encode("utf-8")
        task.update_time = datetime.now(timezone.utc).astimezone()
        task.save(update_fields=["sync_operate", "message", "update_time"])
    return None


@transaction.atomic
def dts_tasks_restart(payload: dict):
    """dts tasks重新开始"""
    task_ids = payload.get("task_ids")
    tasks = TbTendisDtsTask.objects.filter(id__in=task_ids)
    for task in tasks:
        if task.status != -1:
            raise Exception(
                "{} not failed(status={} not -1),restart not allowed".format(task.get_src_redis_addr(), task.status)
            )
        if task.src_dbtype == ClusterType.TendisTendisSSDInstance.value:
            task.task_type = DtsTaskType.TENDISSSD_BACKUP.value
        elif task.src_dbtype == ClusterType.TendisRedisInstance.value:
            task.task_type = DtsTaskType.MAKE_CACHE_SYNC.value
        elif task.src_dbtype == ClusterType.TendisTendisplusInsance:
            task.task_type = DtsTaskType.TENDISPLUS_MAKESYNC.value
        else:
            raise Exception("{} src_dbtype:{} not support".format(task.get_src_redis_addr(), task.src_dbtype))
        task.status = 0
        task.message = "task waiting for restart...".encode("utf-8")
        task.sync_operate = ""
        task.retry_times = task.retry_times + 1
        task.update_time = datetime.now(timezone.utc).astimezone()
        task.save(update_fields=["task_type", "status", "message", "sync_operate", "retry_times", "update_time"])


@transaction.atomic
def dts_tasks_retry(payload: dict):
    """dts tasks重试当前步骤"""
    taskids = payload.get("taskids")
    tasks = TbTendisDtsTask.objects.filter(id__in=taskids)
    for task in tasks:
        if task.status != -1:
            raise Exception(
                "{} not failed(status={} not -1),retry not allowed".format(task.get_src_redis_addr(), task.status)
            )
        if task.src_have_list_keys > 0 and task.src_dbtype != ClusterType.TendisRedisInstance.value:
            """
            SrcHaveListKeys>0,其实只有在TendisSSD中才会出现,RedisInstance、tendisplus中很难发现是否有list类型的key
            而且当SrcHaveListKeys>0时,代表tendisSSD已经在 tredisump 阶段以后了,有list类型key情况下后续阶段重试是有风险的;
            RedisInstance不用管是否有list,因为有同名key存在时,通过restore replace会完全覆盖;
            """
            raise Exception("{} include list type keys,cannot retry".format(task.get_src_redis_addr()))
        if task.task_type == DtsTaskType.TENDISSSD_WATCHOLDSYNC.value:
            task.task_type == DtsTaskType.TENDISSSD_MAKESYNC.value
        elif task.task_type == DtsTaskType.WATCH_CACHE_SYNC.value:
            task.task_type == DtsTaskType.MAKE_CACHE_SYNC.value
        elif (
            task.task_type == DtsTaskType.TENDISPLUS_SENDBULK.value
            or task.task_type == DtsTaskType.TENDISPLUS_SENDINCR.value
        ):
            task.task_type == DtsTaskType.TENDISPLUS_MAKESYNC.value
        task.status = 0
        task.message = "{} waiting for retry...".format(task.task_type).encode("utf-8")
        task.sync_operate = ""
        task.retry_times = task.retry_times + 1
        task.update_time = datetime.now()
        task.save(update_fields=["task_type", "status", "message", "sync_operate", "retry_times", "update_time"])


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
    lockkey = payload.get("lockkey")
    holder = payload.get("holder")
    TbTendisDtsDistributeLock.objects.filter(lock_key=lockkey, holder=holder).delete()


def get_dts_server_migrating_tasks(payload: dict) -> list:
    """获取dts server迁移中的任务
    对tendiSSD来说,'迁移中' 指处于 'tendisBackup'、'backupfileFetch'、'tendisdump'、'cmdsImporter'中的task,
    不包含处于 status=-1 或 处于 makeSync 状态的task
    对tendisCache来说,'迁移中'指处于 'makeCacheSync'中的task,不包含处于 status=-1 或 处于 watchCacheSync 状态的task
    """
    bk_cloud_id = payload.get("bk_cloud_id")
    dts_server = payload.get("dts_server")
    db_type = payload.get("db_type")
    task_types = payload.get("task_types")
    current_time = datetime.now(timezone.utc).astimezone()
    thirty_days_ago = current_time - timedelta(days=30)
    where = Q(bk_cloud_id=bk_cloud_id)
    if dts_server:
        where = where & Q(dts_server=dts_server)
    if db_type:
        where = where & Q(src_dbtype=db_type)
    if task_types:
        where = where & Q(task_type__in=task_types)
    where = where & Q(update_time__gt=thirty_days_ago)
    where = where & Q(status__in=[0, 1])
    tasks = TbTendisDtsTask.objects.filter(where)
    rets = []
    for task in tasks:
        json_data = model_to_dict(task)
        dts_task_clean_passwd_and_format_time(json_data, task)
        dts_task_binary_to_str(json_data, task)
        rets.append(json_data)
    return rets


def get_dts_server_max_sync_port(payload: dict) -> dict:
    """获取DtsServer上syncPort最大的task"""
    bk_cloud_id = payload.get("bk_cloud_id")
    dts_server = payload.get("dts_server")
    db_type = payload.get("db_type")
    task_types = payload.get("task_types")
    current_time = datetime.now(timezone.utc).astimezone()
    thirty_days_ago = current_time - timedelta(days=30)
    where = Q(bk_cloud_id=bk_cloud_id)
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
        dts_task_clean_passwd_and_format_time(json_data, task)
        dts_task_binary_to_str(json_data, task)
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
        dts_task_binary_to_str(json_data, task)
        rets.append(json_data)
    return rets


def get_last_30days_to_schedule_jobs(payload: dict) -> list:
    """获取最近30天内的等待调度的jobs
    billId、srcCluster、dstCluster唯一确定一个dts_job
    获取的dts_jobs必须满足:
    有一个待调度的task.dataSize < maxDataSize & status=0 & taskType="" & dtsServer="1.1.1.1"
    """
    bk_cloud_id = payload.get("bk_cloud_id")
    max_data_size = payload.get("max_data_size")
    zone_name = payload.get("zone_name")
    db_type = payload.get("db_type")
    current_time = datetime.now(timezone.utc).astimezone()
    thirty_days_ago = current_time - timedelta(days=30)
    where = Q(bk_cloud_id=bk_cloud_id)
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
        dts_task_clean_passwd_and_format_time(json_data, job)
        dts_task_binary_to_str(json_data, job)
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
        dts_task_clean_passwd_and_format_time(json_data, task)
        dts_task_binary_to_str(json_data, task)
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
        dts_task_clean_passwd_and_format_time(json_data, task)
        dts_task_binary_to_str(json_data, task)
        rets.append(json_data)
    return rets


def get_dts_task_by_id(payload: dict) -> dict:
    """根据task_id获取dts_task"""
    task_id = payload.get("task_id")
    task = TbTendisDtsTask.objects.get(id=task_id)
    if not task:
        logger.warning("dts task not found,task_id={}".format(task_id))
        return None
    json_data = model_to_dict(task)
    dts_task_format_time(json_data, task)
    dts_task_binary_to_str(json_data, task)
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
    if "message" in col_to_val:
        col_to_val["message"] = col_to_val["message"].encode("utf-8")
    if "key_white_regex" in col_to_val:
        col_to_val["key_white_regex"] = col_to_val["key_white_regex"].encode("utf-8")
    if "key_black_regex" in col_to_val:
        col_to_val["key_black_regex"] = col_to_val["key_black_regex"].encode("utf-8")
    rows_affected = TbTendisDtsTask.objects.filter(id__in=task_ids).update(**col_to_val)
    return rows_affected
