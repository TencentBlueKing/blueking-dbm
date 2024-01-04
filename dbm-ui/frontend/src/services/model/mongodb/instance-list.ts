import dayjs from 'dayjs';

export default class InstanceList {
  static themes: Partial<Record<string, string>> = {
    running: 'success',
  };
  static statusMap: Record<string, string> = {
    running: '正常',
    unavailable: '异常',
  };
  static staticClusterType: string = 'replicaset';
  // sharded
  [key: string]: any;
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
  constructor(payload = {} as InstanceList) {
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
    const text = InstanceList.statusMap[this.status] ? InstanceList.statusMap[this.status] : '--';
    const flag = InstanceList.themes[this.status] || 'danger';
    return { text, flag } as any;
  }
  get getPayload() {
    const payload = {
      level_name: 'cluster',
      conf_type: 'dbconf',
      level_value: 0,
      meta_cluster_type: '',
      version: '',
    };
    Object.keys(this).forEach((key) => {
      const value = this[key];
      if (key === 'version') {
        Object.assign(payload, { [key]: value });
      } else if (key === 'cluster_id') {
        payload.level_value = value;
      } else if (key === 'cluster_type') {
        payload.meta_cluster_type = value;
      }
    });
    return payload;
  }
  get ClusterType() {
    let string = '';
    if (InstanceList.staticClusterType === 'replicaset') {
      string = 'mongodb_replicaset_resources';
    } else if (InstanceList.staticClusterType === 'sharded') {
      string = 'mongodb_sharded_resources';
    }
    return string;
  }
  switchClusterType(flag: boolean) {
    console.log(InstanceList.staticClusterType, '888');

    if (flag) {
      InstanceList.staticClusterType = 'replicaset';
    } else {
      InstanceList.staticClusterType = 'sharded';
    }
  }
}

