import type { DetailBase, DetailSpecs } from '../common';

export interface Restore extends DetailBase {
  apply_details: {
    infos: {
      bk_cloud_id: number;
      resource_spec: {
        mongo_machine_set: {
          count: number;
          set_id: string;
          spec_id: {
            count: number;
            spec_id: number;
          };
          affinity: string;
          group_count: number;
          location_spec: {
            city: string;
            sub_zone_ids: any[];
          };
        };
      };
    }[];
    spec_id: {
      count: number;
      spec_id: number;
    };
    city_code: string;
    ip_source: string;
    db_version: string;
    node_count: number;
    start_port: number;
    bk_cloud_id: number;
    db_app_abbr: string;
    cluster_type: string;
    replica_sets: {
      name: string;
      domain: string;
      set_id: string;
    }[];
    oplog_percent: number;
    replica_count: number;
    node_replica_count: number;
    disaster_tolerance_level: string;
  };
  backupinfo: {
    [clusterId: string]: {
      app: string;
      app_name: string;
      bs_status: string;
      bs_tag: string;
      bs_taskid: string;
      bk_biz_id: number;
      bk_cloud_id: number;
      cluster_domain: string;
      cluster_id: number;
      cluster_name: string;
      cluster_type: string;
      end_time: string;
      file_name: string;
      file_path: string;
      file_size: number;
      meta_role: string;
      my_file_num: number;
      pitr_binlog_index: number;
      pitr_date: string;
      pitr_file_type: string;
      pitr_fullname: string;
      pitr_last_pos: number;
      report_type: string;
      releate_bill_id: string;
      releate_bill_info: string;
      role_type: string;
      server_ip: string;
      server_port: number;
      set_name: string;
      src: string;
      start_time: string;
      total_file_num: number;
    };
  };
  cluster_ids: number[];
  cluster_type: string;
  clusters: {
    [clusterId: string]: {
      alias: string;
      bk_biz_id: number;
      bk_cloud_id: number;
      cluster_type: string;
      cluster_type_name: string;
      creator: string;
      db_module_id: number;
      disaster_tolerance_level: string;
      id: number;
      immute_domain: string;
      major_version: string;
      name: string;
      phase: string;
      region: string;
      status: string;
      tag: any[];
      time_zone: string;
      updater: string;
    };
  };
  city_code: string;
  instance_per_host: number;
  ns_filter?: {
    db_patterns: string[];
    ignore_dbs: string[];
    ignore_tables: string[];
    table_patterns: string[];
  };
  resource_spec: {
    mongodb: {
      count: number;
      spec_id: number;
    };
  };
  rollback_time: string;
  specs: DetailSpecs;
}
