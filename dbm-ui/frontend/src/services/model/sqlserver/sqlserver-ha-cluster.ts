import dayjs from 'dayjs';

import { t } from '@locales';

export default class SqlServerHaCluster {
  static SQLSERVER_HA_DISABLE = 'SQLSERVER_HA_DISABLE';
  static SQLSERVER_HA_DESTROY = 'SQLSERVER_HA_DESTROY';
  static SQLSERVER_HA_ENABLE = 'SQLSERVER_HA_ENABLE';
  static statusMap: Record<string, string> = {
    running: t('正常'),
    unavailable: t('异常'),
  };
  static themes: Record<string, string> = {
    running: 'success',
  };
  static operationIconMap = {
    [SqlServerHaCluster.SQLSERVER_HA_ENABLE]: 'qiyongzhong',
    [SqlServerHaCluster.SQLSERVER_HA_DISABLE]: 'jinyongzhong',
    [SqlServerHaCluster.SQLSERVER_HA_DESTROY]: 'shanchuzhong',
  };
  static operationTextMap = {
    [SqlServerHaCluster.SQLSERVER_HA_DESTROY]: t('删除任务执行中'),
    [SqlServerHaCluster.SQLSERVER_HA_DISABLE]: t('禁用任务执行中'),
    [SqlServerHaCluster.SQLSERVER_HA_ENABLE]: t('启用任务执行中'),
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
  create_at: Date | string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  id: number;
  major_version: string;
  master_domain: string;
  masters: {
      name: string;
      ip: string;
      port: number;
      instance: string;
      status: string;
      phase: string;
      bk_instance_id: number;
      bk_host_id: number;
      bk_cloud_id: number;
      spec_config: {
        id: number;
        cpu: {
            max: number;
            min: number;
        },
        mem: {
            max: number;
            min: number;
        },
        name: string;
        count: number;
        device_class: any[];
        storage_spec: Array<{
            size: number;
            type: string;
            mount_point: string;
        }>;
    };
      bk_biz_id: number;
  }[];
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
  slaves: {
    name: string;
    ip: string;
    port: number;
    instance: string;
    status: string;
    phase: string;
    bk_instance_id: number;
    bk_host_id: number;
    bk_cloud_id: number;
    spec_config: {
      id: number;
      cpu: {
          max: number;
          min: number;
      },
      mem: {
          max: number;
          min: number;
      },
      name: string;
      count: number;
      device_class: any[];
      storage_spec: Array<{
          size: number;
          type: string;
          mount_point: string;
      }>;
  };
    bk_biz_id: number;
}[];
  status: string;
  update_at: Date | string;
  updater: string;

  constructor(payload: SqlServerHaCluster) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cluster_alias = payload.cluster_alias;
    this.cluster_name = payload.cluster_name;
    this.cluster_time_zone = payload.cluster_time_zone;
    this.cluster_type = payload.cluster_type;
    this.cluster_type_name = payload.cluster_type_name;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.id = payload.id;
    this.major_version = payload.major_version;
    this.master_domain = payload.master_domain;
    this.masters = payload.masters;
    this.operations = payload.operations;
    this.phase = payload.phase;
    this.phase_name = payload.phase_name;
    this.region = payload.region;
    this.slave_domain = payload.slave_domain;
    this.slaves = payload.slaves;
    this.status = payload.status;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get isNew() {
    return dayjs().isBefore(dayjs(this.create_at).add(24, 'hour'));
  }

  get dbStatusConfigureObj() {
    const text = SqlServerHaCluster.statusMap[this.status] || '--';
    const theme = SqlServerHaCluster.themes[this.status] || 'danger';
    return {
      text,
      theme,
    };
  }

  get runningOperation() {
    const operateTicketTypes = Object.keys(SqlServerHaCluster.operationTextMap);
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
    return SqlServerHaCluster.operationTextMap[this.operationRunningStatus];
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
