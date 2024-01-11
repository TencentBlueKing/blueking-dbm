import dayjs from 'dayjs';

import { t } from '@locales';

export default class mongodbInstance {
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
  cluster_id: number;
  cluster_name: string;
  cluster_type: string;
  create_at: string;
  db_module_id: string;
  id: number;
  instance_address: string;
  ip: number;
  machine_type: string;
  master_domain: string;
  operations: Array<{
    flow_id: string;
    instance_id: number;
    operator: number;
    status: string;
    ticket_id: number;
    ticket_type: string;
    title: string;
  }>;
  port: number;
  role: string;
  shard: string;
  slave_domain: string;
  spec_config: string;
  status: string;
  version: string;

  constructor(payload = {} as mongodbInstance) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_host_id = payload.bk_host_id;
    this.cluster_id = payload.cluster_id;
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.create_at = payload.create_at;
    this.db_module_id = payload.db_module_id;
    this.id = payload.id;
    this.instance_address = payload.instance_address;
    this.ip = payload.ip;
    this.machine_type = payload.machine_type;
    this.master_domain = payload.master_domain;
    this.operations = payload.operations || [];
    this.port = payload.port;
    this.role = payload.role;
    this.shard = payload.shard;
    this.slave_domain = payload.slave_domain;
    this.spec_config = payload.spec_config;
    this.status = payload.status;
    this.version = payload.version;
  }

  get isNew() {
    return dayjs().isBefore(dayjs(this.create_at).add(24, 'hour'));
  }

  get dbStatusConfigureObj() {
    const text = mongodbInstance.statusMap[this.status] || '--';
    const theme = mongodbInstance.themes[this.status] || 'danger';
    return { text, theme };
  }

  get clusterTypeText() {
    return this.cluster_type === 'MongoReplicaSet' ? t('副本集') : t('分片集群');
  }
}
