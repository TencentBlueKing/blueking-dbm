export default class Partition {
  bk_biz_id: number;
  bk_cloud_id: number;
  check_info: string;
  cluster_id: number;
  create_time: string;
  creator: string;
  dblike: string;
  execute_time: string;
  expire_time: number;
  extra_partition: number;
  id: number;
  immute_domain: string;
  partition_column_type: string;
  partition_columns: string;
  partition_time_interval: number;
  partition_type: number;
  phase: string;
  port: number;
  reserved_partition: number;
  status: string;
  tblike: string;
  ticket_id: number;
  ticket_status: string;
  update_time: string;
  updator: string;

  constructor(payload = {} as Partition) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.check_info = payload.check_info;
    this.cluster_id = payload.cluster_id;
    this.create_time = payload.create_time;
    this.creator = payload.creator;
    this.dblike = payload.dblike;
    this.execute_time = payload.execute_time;
    this.expire_time = payload.expire_time;
    this.extra_partition = payload.extra_partition;
    this.id = payload.id;
    this.immute_domain = payload.immute_domain;
    this.partition_column_type = payload.partition_column_type;
    this.partition_columns = payload.partition_columns;
    this.partition_time_interval = payload.partition_time_interval;
    this.partition_type = payload.partition_type;
    this.phase = payload.phase;
    this.port = payload.port;
    this.reserved_partition = payload.reserved_partition;
    this.status = payload.status;
    this.tblike = payload.tblike;
    this.ticket_id = payload.ticket_id;
    this.ticket_status = payload.ticket_status;
    this.update_time = payload.update_time;
    this.updator = payload.updator;
  }
}
