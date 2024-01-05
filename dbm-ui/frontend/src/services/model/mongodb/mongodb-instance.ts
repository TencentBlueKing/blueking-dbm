import dayjs from 'dayjs';

import { t } from '@/locales';

export default class mongodbInstance {
  static themes: Partial<Record<string, string>> = {
    running: 'success',
  };
  static statusMap: Record<string, string> = {
    running: '正常',
    unavailable: '异常',
  };
  static staticClusterType: string = 'replicaset';
  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  cluster_id: number;
  cluster_name: string;
  cluster_type: string;
  create_at: string;
  db_module_id: string;
  id: number;
  ip: number;
  instance_address: string;
  machine_type: string;
  master_domain: string;
  port: number;
  role: string;
  shard: string;
  slave_domain: string;
  spec_config: string;
  status: string;
  version: string;
  constructor(payload = {} as mongodbInstance) {
    this.create_at = payload.create_at;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_host_id = payload.bk_host_id;
    this.db_module_id = payload.db_module_id;
    this.db_module_id = payload.db_module_id;
    this.machine_type = payload.machine_type;
    this.master_domain = payload.master_domain;
    this.port = payload.port;
    this.shard = payload.shard;
    this.spec_config = payload.spec_config;
    this.slave_domain = payload.slave_domain;
    this.version = payload.version;
    this.instance_address = payload.instance_address;
    this.cluster_id = payload.cluster_id;
    this.cluster_type = payload.cluster_type;
    this.role = payload.role;
    this.status = payload.status;
    this.ip = payload.ip;
    this.cluster_name = payload.cluster_name;
    this.id = payload.id;
  }

  get isNew() {
    return dayjs().isBefore(dayjs(this.create_at).add(24, 'hour'));
  }

  get getStuts() {
    const text = mongodbInstance.statusMap[this.status] || '--';
    const flag = mongodbInstance.themes[this.status] || 'danger';
    return { text, flag };
  }

  get clusterTypeText() {
    return this.cluster_type === mongodbInstance.staticClusterType ? t('分片集群') : t('副本集');
  }
}

