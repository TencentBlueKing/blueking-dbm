const STATUS_FAILED = 'FAILED';
const STATUS_SUCCEEDED = 'SUCCEEDED';

export default class PartitionLog {
  static STATUS_FAILED = STATUS_FAILED;
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

  get isFailed() {
    return this.status === PartitionLog.STATUS_FAILED;
  }

  get isFinished() {
    return this.status === PartitionLog.STATUS_SUCCEEDED;
  }

  get statusIcon() {
    const iconMap = {
      [PartitionLog.STATUS_FAILED]: 'sync-failed',
      [PartitionLog.STATUS_SUCCEEDED]: 'sync-success',
    };

    return iconMap[this.status] || 'sync-default';
  }

  get statusText() {
    const statusMap = {
      [PartitionLog.STATUS_FAILED]: '执行失败',
      [PartitionLog.STATUS_SUCCEEDED]: '执行成功',
    };
    return statusMap[this.status] || '等待执行';
  }
}
