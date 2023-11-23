export default class tendbhaInstance {
  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  cluster_id: number;
  cluster_name: string;
  create_at: string;
  db_module_id: number;
  id: number;
  instance_address: string;
  ip: string;
  master_domain: string;
  port: number;
  role: string;
  slave_domain: string;
  spce_config: Record<'id', number>;
  status: string;
  version: string;

  constructor(payload = {}  as tendbhaInstance) {
    this.bk_cloud_id = payload.bk_cloud_id || 0;
    this.bk_cloud_name = payload.bk_cloud_name || '';
    this.bk_host_id = payload.bk_host_id || 0;
    this.cluster_id = payload.cluster_id || 0;
    this.cluster_name = payload.cluster_name || '';
    this.create_at = payload.create_at || '';
    this.db_module_id = payload.db_module_id || 0;
    this.id = payload.id || 0;
    this.instance_address = payload.instance_address || '';
    this.ip = payload.ip || '';
    this.master_domain = payload.master_domain || '';
    this.port = payload.port || 0;
    this.role = payload.role || '';
    this.slave_domain = payload.slave_domain || '';
    this.spce_config = payload.spce_config || {};
    this.status = payload.status || '';
    this.version = payload.version || '';
  }
}
