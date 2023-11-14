export default class Opeanarea {
  bk_biz_id: number;
  config_name: string;
  config_rules: {
    data_tblist: string[],
    priv_data: number[],
    schema_tblist: string[],
    source_db: string,
    target_db_pattern: string
  }[];
  create_at: string;
  creator: string;
  id: number;
  source_cluster: {
    bk_cloud_id: number;
    cluster_type: string;
    id: number;
    immute_domain: string;
    major_version: string;
    name: string;
    region: string;
  };
  source_cluster_id: number;
  update_at: string;
  updater: string;

  constructor(payload = {} as Opeanarea) {
    this.bk_biz_id = payload.bk_biz_id;
    this.config_name = payload.config_name;
    this.config_rules = payload.config_rules || [];
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.id = payload.id;
    this.source_cluster = payload.source_cluster || {};
    this.source_cluster_id = payload.source_cluster_id;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }
}
