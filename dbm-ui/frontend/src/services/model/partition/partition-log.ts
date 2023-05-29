const STATUS_PENDING = 'PENDING';
const STATUS_READY = 'READY';
const STATUS_RUNNING = 'RUNNING';
const STATUS_FAILED = 'FAILED';
const STATUS_FINISHED = 'FINISHED';
const STATUS_SUCCEEDED = 'SUCCEEDED';

export default class PartitionLog {
  static STATUS_PENDING = STATUS_PENDING;
  static STATUS_READY = STATUS_READY;
  static STATUS_RUNNING = STATUS_RUNNING;
  static STATUS_FAILED = STATUS_FAILED;
  static STATUS_FINISHED = STATUS_FINISHED;
  static STATUS_SUCCEEDED = STATUS_SUCCEEDED;

  check_info: string;
  execute_time: string;
  id: number;
  status: string;
  ticket_id: number;

  constructor(payload = {} as PartitionLog) {
    this.check_info = payload.check_info;
    this.execute_time = payload.execute_time;
    this.id = payload.id;
    this.status = payload.status;
    this.ticket_id = payload.ticket_id;
  }

  get statusText() {
    const statusMap = {
      [PartitionLog.STATUS_PENDING]: '等待执行',
      [PartitionLog.STATUS_READY]: '执行中',
      [PartitionLog.STATUS_RUNNING]: '执行中',
      [PartitionLog.STATUS_FAILED]: '执行失败',
      [PartitionLog.STATUS_FINISHED]: '执行成功',
      [PartitionLog.STATUS_SUCCEEDED]: '执行成功',
    };
    return statusMap[this.status] || '等待执行';
  }

  get statusIcon() {
    const iconMap = {
      [PartitionLog.STATUS_PENDING]: 'sync-default',
      [PartitionLog.STATUS_READY]: 'sync-pending',
      [PartitionLog.STATUS_RUNNING]: 'sync-pending',
      [PartitionLog.STATUS_FINISHED]: 'sync-success',
      [PartitionLog.STATUS_SUCCEEDED]: 'sync-success',
      [PartitionLog.STATUS_FAILED]: 'sync-failed',
    };

    return iconMap[this.status] || 'sync-default';
  }

  get isFinished() {
    return [PartitionLog.STATUS_FINISHED, PartitionLog.STATUS_SUCCEEDED].includes(this.status);
  }

  get isRunning() {
    return [PartitionLog.STATUS_READY, PartitionLog.STATUS_RUNNING].includes(this.status);
  }

  get isFailed() {
    return this.status === PartitionLog.STATUS_FAILED;
  }
}
