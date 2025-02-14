import type { HostInfo, InstanceListOperation, InstanceListSpecConfig, InstanceRelatedCluster } from '@services/types';

import { ClusterTypes } from '@common/const';

import { isRecentDays, utcDisplayTime } from '@utils';

import { t } from '@locales/index';

export default class MongodbInstance {
  static MONGODB_DISABLE = 'MONGODB_DISABLE';
  static MONGODB_INSTANCE_RELOAD = 'MONGODB_INSTANCE_RELOAD';
  static MONGODB_ENABLE = 'MONGODB_ENABLE';
  static MONGODB_DESTROY = 'MONGODB_DESTROY';

  static operationIconMap = {
    [MongodbInstance.MONGODB_DISABLE]: t('禁用中'),
    [MongodbInstance.MONGODB_INSTANCE_RELOAD]: t('重启中'),
    [MongodbInstance.MONGODB_ENABLE]: t('启用中'),
    [MongodbInstance.MONGODB_DESTROY]: t('删除中'),
  };

  static operationTextMap = {
    [MongodbInstance.MONGODB_DISABLE]: t('禁用任务执行中'),
    [MongodbInstance.MONGODB_INSTANCE_RELOAD]: t('实例重启任务进行中'),
    [MongodbInstance.MONGODB_ENABLE]: t('启用任务执行中'),
    [MongodbInstance.MONGODB_DESTROY]: t('删除任务执行中'),
  };

  static themes: Record<string, string> = {
    running: 'success',
  };
  static statusMap: Record<string, string> = {
    running: t('正常'),
    unavailable: t('异常'),
  };

  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  bk_os_name: string;
  bk_rack_id: number;
  bk_sub_zone: string;
  bk_sub_zone_id: number;
  bk_svr_device_cls_name: string;
  cluster_id: number;
  cluster_name: string;
  cluster_type: ClusterTypes;
  create_at: string;
  db_module_id: number;
  db_module_name: string;
  host_info: HostInfo;
  id: number;
  instance_address: string;
  ip: string;
  machine_type: string;
  master_domain: string;
  operations: InstanceListOperation[];
  port: number;
  related_clusters: InstanceRelatedCluster[];
  role: string;
  shard: string;
  slave_domain: string;
  spec_config: InstanceListSpecConfig;
  status: string;
  version: string;

  constructor(payload = {} as MongodbInstance) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_host_id = payload.bk_host_id;
    this.bk_os_name = payload.bk_os_name;
    this.bk_rack_id = payload.bk_rack_id;
    this.bk_sub_zone = payload.bk_sub_zone;
    this.bk_sub_zone_id = payload.bk_sub_zone_id;
    this.bk_svr_device_cls_name = payload.bk_svr_device_cls_name;
    this.cluster_id = payload.cluster_id;
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.create_at = payload.create_at;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.host_info = payload.host_info || {};
    this.id = payload.id;
    this.instance_address = payload.instance_address;
    this.ip = payload.ip;
    this.machine_type = payload.machine_type;
    this.master_domain = payload.master_domain;
    this.operations = payload.operations || [];
    this.port = payload.port;
    this.related_clusters = payload.related_clusters || [];
    this.role = payload.role;
    this.shard = payload.shard;
    this.slave_domain = payload.slave_domain;
    this.spec_config = payload.spec_config;
    this.status = payload.status;
    this.version = payload.version;
  }

  get isNew() {
    return isRecentDays(this.create_at, 24 * 3);
  }

  get dbStatusConfigureObj() {
    const text = MongodbInstance.statusMap[this.status] || '--';
    const theme = MongodbInstance.themes[this.status] || 'danger';
    return { text, theme };
  }

  get clusterTypeText() {
    return this.cluster_type === 'MongoReplicaSet' ? t('副本集') : t('分片集群');
  }

  get isRebooting() {
    return Boolean(this.operations.find((item) => item.ticket_type === MongodbInstance.MONGODB_INSTANCE_RELOAD));
  }

  get runningOperation() {
    const operateTicketTypes = Object.keys(MongodbInstance.operationTextMap);
    return this.operations.find((item) => operateTicketTypes.includes(item.ticket_type) && item.status === 'RUNNING');
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
    return MongodbInstance.operationTextMap[this.operationRunningStatus];
  }

  // 操作中的状态 icon
  get operationStatusIcon() {
    return MongodbInstance.operationIconMap[this.operationRunningStatus];
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

  get operationDisabled() {
    // 各个操作互斥，有其他任务进行中禁用操作按钮
    if (this.operationTicketId) {
      return true;
    }
    return false;
  }

  get operationTagTips() {
    return this.operations.map((item) => ({
      icon: MongodbInstance.operationIconMap[item.ticket_type],
      tip: MongodbInstance.operationTextMap[item.ticket_type],
      ticketId: item.ticket_id,
    }));
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }
}
