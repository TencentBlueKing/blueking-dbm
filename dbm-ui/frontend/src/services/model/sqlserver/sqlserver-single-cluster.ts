import TimeBaseClassModel from '@services/util/time-base-class';

import { t } from '@locales';

export default class SqlServerSingleCluster extends TimeBaseClassModel {
  static SQLSERVER_SINGLE_DESTROY = 'SQLSERVER_SINGLE_DESTROY';
  static SQLSERVER_SINGLE_DISABLE = 'SQLSERVER_SINGLE_DISABLE';
  static SQLSERVER_SINGLE_ENABLE = 'SQLSERVER_SINGLE_ENABLE';
  static operationIconMap = {
    [SqlServerSingleCluster.SQLSERVER_SINGLE_ENABLE]: 'qiyongzhong',
    [SqlServerSingleCluster.SQLSERVER_SINGLE_DISABLE]: 'jinyongzhong',
    [SqlServerSingleCluster.SQLSERVER_SINGLE_DESTROY]: 'shanchuzhong',
  };
  static operationTextMap = {
    [SqlServerSingleCluster.SQLSERVER_SINGLE_DESTROY]: t('删除任务执行中'),
    [SqlServerSingleCluster.SQLSERVER_SINGLE_DISABLE]: t('禁用任务执行中'),
    [SqlServerSingleCluster.SQLSERVER_SINGLE_ENABLE]: t('启用任务执行中'),
  };
  static statusMap: Record<string, string> = {
    running: t('正常'),
    unavailable: t('异常'),
  };
  static themes: Record<string, string> = {
    running: 'success',
  };

  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_alias: string;
  cluster_name: string;
  cluster_time_zone: string;
  cluster_type: string;
  cluster_type_name: string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  id: number;
  major_version: string;
  master_domain: string;
  operations: Array<{
    cluster_id: number,
    flow_id: number,
    operator: string,
    status: string,
    ticket_id: number,
    ticket_type: string,
    title: string,
  }>;
  phase: string;
  phase_name: string;
  region: string;
  slave_domain: string;
  status: string;
  storages: Array<{
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    bk_instance_id: number;
    instance: string;
    ip: string;
    name: string;
    port: number;
    spec_config: {
      count: number;
      cpu: {
        max: number;
        min: number;
      },
      id: number;
      mem: {
        max: number;
        min: number;
      },
      name: string;
      storage_spec: Array<{
        mount_point: string;
        size: number;
        type: string;
      }>;
    };
    status: string;
    phase: string;
  }>;
  update_at: string;
  updater: string;

  constructor(payload: SqlServerSingleCluster) {
    super(payload);
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cluster_alias = payload.cluster_alias;
    this.cluster_name = payload.cluster_name;
    this.cluster_time_zone = payload.cluster_time_zone;
    this.cluster_type = payload.cluster_type;
    this.cluster_type_name = payload.cluster_type_name;
    this.creator = payload.creator;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.id = payload.id;
    this.major_version = payload.major_version;
    this.master_domain = payload.master_domain;
    this.operations = payload.operations;
    this.phase = payload.phase;
    this.phase_name = payload.phase_name;
    this.region = payload.region;
    this.slave_domain = payload.slave_domain;
    this.status = payload.status;
    this.storages = payload.storages;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get dbStatusConfigureObj() {
    const text = SqlServerSingleCluster.statusMap[this.status] || '--';
    const theme = SqlServerSingleCluster.themes[this.status] || 'danger';
    return {
      text,
      theme,
    };
  }

  get runningOperation() {
    const operateTicketTypes = Object.keys(SqlServerSingleCluster.operationTextMap);
    return this.operations.find(item => operateTicketTypes.includes(item.ticket_type) && item.status === 'RUNNING');
  }

  // 操作中的状态
  get operationRunningStatus() {
    if (this.operations.length < 1) {
      return '';
    }
    const operation = this.runningOperation;
    if (!operation) {
      return '';
    }
    return operation.ticket_type;
  }

  // 操作中的状态描述文本
  get operationStatusText() {
    return SqlServerSingleCluster.operationTextMap[this.operationRunningStatus];
  }

  // 操作中的单据 ID
  get operationTicketId() {
    if (this.operations.length < 1) {
      return 0;
    }
    const operation = this.runningOperation;
    if (!operation) {
      return 0;
    }
    return operation.ticket_id;
  }
}
