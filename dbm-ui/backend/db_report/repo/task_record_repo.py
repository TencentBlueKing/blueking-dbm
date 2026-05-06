import datetime
import logging
import threading
import traceback

import pytz
from django.utils import timezone

from backend.constants import DEFAULT_TIME_ZONE_AREA
from backend.db_report.models.task_record import TaskRecord

logger = logging.getLogger("celery")


class TaskRecordRepo:
    """TaskRecordRepo 用于记录周期任务的执行记录"""

    def create_task_record(
        self,
        db_type,
        task_name,
        task_type,
        task_status,
        task_result: str,
        start_time: datetime.datetime = timezone.now(),
        end_time: datetime.datetime = timezone.now(),
    ) -> TaskRecord:
        record = TaskRecord()
        record.db_type = db_type
        record.task_name = task_name
        record.task_type = task_type
        record.task_status = task_status
        record.task_result = task_result
        record.start_time = start_time
        record.end_time = end_time
        record.save()
        return record

    def update_task_record(
        self,
        record: TaskRecord,
        task_status,
        task_result,
        end_time,
        task_duration,
        total_num,
        success_num,
        warning_num,
        abnormal_num,
    ) -> None:
        record.task_status = task_status
        record.task_result = task_result
        record.end_time = end_time
        record.task_duration = task_duration
        record.cluster_num = total_num
        record.cluster_success_num = success_num
        record.cluster_warning_num = warning_num
        record.cluster_failed_num = abnormal_num
        record.save()

    def _update_task_record_periodically(self, task_id: int, stop_event: threading.Event) -> None:
        """
        后台线程：每1分钟更新一次任务记录的 update_at 字段

        Args:
            task_id: 任务记录ID
            stop_event: 停止事件，用于控制线程退出
        """
        update_interval = 60  # 60秒 = 1分钟

        while not stop_event.is_set():
            # 等待1分钟或直到收到停止信号
            if stop_event.wait(timeout=update_interval):
                # 收到停止信号，退出循环
                break

            # 更新 update_at 字段
            try:
                TaskRecord.objects.filter(id=task_id).update(update_at=timezone.now())
                logger.debug(f"Updated task_record {task_id} update_at field")
            except Exception as e:
                logger.error(f"Failed to update task_record {task_id} update_at: {e}")

    def execute_task_with_record(self, db_type: str, task_name: str, task_type: str, check_task_instance) -> None:
        """
        执行检查任务并记录执行结果

        Args:
            db_type: 数据库类型
            task_name: 任务名称
            task_type: 任务类型
            check_task_instance: 检查任务实例，需要实现 start() 方法，返回 (total_num, success_num, warning_num, abnormal_num)

        Returns:
            None
        """
        task = None
        total_num = success_num = warning_num = abnormal_num = 0
        task_status = "failed"
        task_result = ""
        stop_event = threading.Event()
        update_thread = None

        try:
            task = self.create_task_record(
                db_type=db_type,
                task_name=task_name,
                task_type=task_type,
                task_status="running",
                task_result="",
                start_time=timezone.now(),
            )

            # 启动后台线程，每1分钟更新一次 update_at 字段
            update_thread = threading.Thread(
                target=self._update_task_record_periodically, args=(task.id, stop_event), daemon=True
            )
            update_thread.start()
            # 执行检查任务
            total_num, success_num, warning_num, abnormal_num = check_task_instance.start()
            task_status = "success"
            task_result = ""
        except Exception as e:
            logger.error(f"{task_name} error: {e}\n{traceback.format_exc()}")
            task_status = "failed"
            task_result = str(e)
        finally:
            # 停止后台更新线程
            if stop_event:
                stop_event.set()

            # 等待后台线程结束（最多等待2秒）
            if update_thread and update_thread.is_alive():
                update_thread.join(timeout=2.0)

            if task:
                end_time = timezone.now()
                task_duration = int((end_time - task.start_time).total_seconds())
                self.update_task_record(
                    task,
                    task_status=task_status,
                    task_result=task_result,
                    end_time=end_time,
                    task_duration=task_duration,
                    total_num=total_num,
                    success_num=success_num,
                    warning_num=warning_num,
                    abnormal_num=abnormal_num,
                )


def get_report_day_from_time(time_now: datetime.datetime) -> int:
    """
    获取报告日期, 根据DEFAULT_TIME_ZONE_AREA获取报告日期
    """
    return int(time_now.astimezone(pytz.timezone(DEFAULT_TIME_ZONE_AREA)).date().strftime("%Y%m%d"))
