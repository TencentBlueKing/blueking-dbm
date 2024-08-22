export default class SqlServerSingleInstance {
  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  cluster_id: number;
  cluster_name: string;
  cluster_type: string;
  create_at: string;
  db_module_id: number;
  db_module_name: string;
  host_info: {
    agent_id: string;
    alive: number;
    biz: {
      id: number;
      name: string;
    };
    cloud_area: {
      id: number;
      name: string;
    };
    cloud_id: number;
    host_id: number;
    host_name?: string;
    ip: string;
    ipv6: string;
    meta: {
      bk_biz_id: number;
      scope_id: number;
      scope_type: string;
    };
    scope_id: string;
    scope_type: string;
    os_name: string;
    bk_cpu: number;
    bk_disk: number;
    bk_mem: number;
    os_type: string;
    cpu: string;
    cloud_vendor: string;
    bk_idc_name: string;
  };
  id: number;
  instance_address: string;
  ip: string;
  machine_type: string;
  master_domain: string;
  permission: {
    sqlserver_view: boolean;
  };
  port: number;
  related_clusters: {
    alias: string;
    bk_biz_id: number;
    bk_cloud_id: number;
    cluster_name: string;
    cluster_type: string;
    creator: string;
    db_module_id: number;
    id: number;
    major_version: string;
    master_domain: string;
    phase: string;
    region: string;
    status: string;
    time_zone: string;
    updater: string;
  }[];
  role: string;
  slave_domain: string;
  spec_config: {
    id: number;
    cpu: {
      max: number;
      min: number;
    };
    mem: {
      max: number;
      min: number;
    };
    qps: {
      max: number;
      min: number;
    };
    name: string;
    count: number;
    device_class: string[];
    storage_spec: {
      size: number;
      type: string;
      mount_point: string;
    }[];
  };
  status: string;
  version: string;
  constructor(payload = {} as SqlServerSingleInstance) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_host_id = payload.bk_host_id;
    this.cluster_id = payload.cluster_id;
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.create_at = payload.create_at;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.host_info = payload.host_info;
    this.id = payload.id;
    this.instance_address = payload.instance_address;
    this.ip = payload.ip;
    this.machine_type = payload.machine_type;
    this.master_domain = payload.master_domain;
    this.permission = payload.permission;
    this.port = payload.port;
    this.related_clusters = payload.related_clusters;
    this.role = payload.role;
    this.slave_domain = payload.slave_domain;
    this.spec_config = payload.spec_config;
    this.status = payload.status;
    this.version = payload.version;
  }
}