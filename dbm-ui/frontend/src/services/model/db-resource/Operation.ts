const STATUS_PENDING = 'PENDING';
const STATUS_RUNNING = 'RUNNING';
const STATUS_SUCCEEDED = 'SUCCEEDED';
const STATUS_FAILED = 'FAILED';
const STATUS_REVOKED = 'REVOKED';

const OPERATIN_TYPE_IMPORTED = 'imported';
const OPERATIN_TYPE_CONSUMED = 'consumed';

export default class Operation {
  static STATUS_PENDING = STATUS_PENDING;
  static STATUS_RUNNING = STATUS_RUNNING;
  static STATUS_SUCCEEDED = STATUS_SUCCEEDED;
  static STATUS_FAILED = STATUS_FAILED;
  static STATUS_REVOKED = STATUS_REVOKED;

  static OPERATIN_TYPE_IMPORTED = OPERATIN_TYPE_IMPORTED;
  static OPERATIN_TYPE_CONSUMED = OPERATIN_TYPE_CONSUMED;

  bk_biz_id: number;
  bk_host_ids: number[];
  create_time: string;
  operation_type: string;
  operator: string;
  request_id: string;
  status: string;
  task_id: string;
  ticket_id: string;
  total_count: number;
  update_time: string;

  constructor(payload = {} as Operation) {
    this.bk_biz_id = payload.bk_biz_id || 0;
    this.bk_host_ids = payload.bk_host_ids || [];
    this.create_time = payload.create_time;
    this.operation_type = payload.operation_type;
    this.operator = payload.operator;
    this.request_id = payload.request_id;
    this.status = payload.status;
    this.task_id = payload.task_id;
    this.ticket_id = payload.ticket_id;
    this.total_count = payload.total_count;
    this.update_time = payload.update_time;
  }

  get operationTypeText() {
    const textMap = {
      [Operation.OPERATIN_TYPE_IMPORTED]: '导入主机',
      [Operation.OPERATIN_TYPE_CONSUMED]: '消费主机',
    } as Record<string, string>;

    return textMap[this.operation_type];
  }

  get statusIcon() {
    const iconMap = {
      [Operation.STATUS_PENDING]: 'sync-default',
      [Operation.STATUS_RUNNING]: 'sync-pending',
      [Operation.STATUS_SUCCEEDED]: 'sync-success',
      [Operation.STATUS_FAILED]: 'sync-failed',
      [Operation.STATUS_REVOKED]: 'sync-failed',
    };

    return iconMap[this.status] || 'sync-default';
  }

  get statusText() {
    const textMap = {
      [Operation.STATUS_PENDING]: '等待执行',
      [Operation.STATUS_RUNNING]: '执行中',
      [Operation.STATUS_SUCCEEDED]: '执行成功',
      [Operation.STATUS_FAILED]: '执行失败',
      [Operation.STATUS_REVOKED]: '执行失败',
    };
    return textMap[this.status] || '等待执行';
  }

  get isRunning() {
    return this.status === Operation.STATUS_RUNNING;
  }
}
