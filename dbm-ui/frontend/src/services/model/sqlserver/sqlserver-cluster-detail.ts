export default class SQLServerClusterDetail {
  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_entry_details: {
    cluster_entry_type: string;
    role: string;
    entry: string;
    target_details: {
      app: string;
      bk_cloud_id: number;
      dns_str: string;
      domain_name: string;
      domain_type: number;
      ip: string;
      last_change_time: string;
      manager: string;
      port: number;
      remark: string;
      start_time: string;
      status: string;
      uid: number;
    }[];
  }[];
  cluster_name: string;
  cluster_type: string;
  create_at: string;
  creator: string;
  db_module_name: string;
  id: number;
  master_domain: string;
  masters: {
    name: string;
    ip: string;
    port: number;
    instance?: string;
    status: string;
    phase: string;
    bk_instance_id: number;
    bk_host_id: number;
    bk_cloud_id: number;
    spec_config: {
      id: number;
    };
    bk_biz_id: number;
  }[];
  operations: {
    operator: string;
    cluster_id: number;
    flow_id: number;
    ticket_id: number;
    ticket_type: string;
    title: string;
    status: string;
  }[];
  phase: string;
  status: string;

  constructor(payload: SQLServerClusterDetail) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cluster_entry_details = payload.cluster_entry_details;
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_module_name = payload.db_module_name;
    this.id = payload.id;
    this.master_domain = payload.master_domain;
    this.masters = payload.masters;
    this.operations = payload.operations;
    this.phase = payload.phase;
    this.status = payload.status;
  }
}
