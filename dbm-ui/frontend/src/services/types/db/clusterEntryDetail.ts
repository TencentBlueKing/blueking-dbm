export interface ClusterEntryDetail {
  cluster_entry_type: string;
  entry: string;
  role: string;
  target_details: {
    app: string;
    bk_cloud_iduid: number;
    dns_str: string;
    domain_name: string;
    domain_typeuid: number;
    ip: string;
    last_change_time: string;
    manager: string;
    port: number;
    remark: string;
    start_time: string;
    status: string;
    uid: number;
  }[];
}
